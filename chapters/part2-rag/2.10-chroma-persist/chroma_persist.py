"""章节 2.10 · 向量持久化与增量同步（原生实现）

==========================================================
为什么需要原生向量持久化与增量同步？
1. 内存向量索引（如纯内存 FAISS/NumPy）程序一退出就丢失，重启需重新全量向量化，开销巨大；
2. 生产环境中，文档更新频繁，若每次更新都全量重建，成本与停机时间不可接受；
3. 本章采用原生 chromadb.PersistentClient 实现：
   - 确定性 ID：由 sha256(source + str(index) + text) 唯一生成，天然具备幂等性
   - 增量 Upsert：已存在的片段无需重复写入，内容变动时自动更新
   - 版本清理：源文件全量更新时，通过 metadata 过滤删除旧片段
   - 元数据过滤：按 source、page 精确限定检索范围
   - 预计算向量：统一通过 common.embed_texts() 计算后写入

运行：python tools/run_chapter.py 2.10
==========================================================
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import chromadb

try:
    from common import embed_texts
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from common import embed_texts


# ----------------------------------------------------------
# 1. Gate 闭卷规范类（提供 JSON 格式持久化参考解）
# ----------------------------------------------------------


class StoreError(ValueError):
    """持久化/写入/查询失败。"""


class PersistentVectorStore:
    """基于 JSON 文件持久化的最小确定性向量库（供 Gate 验收）。"""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.rows: list[dict] = []
        self._existing_ids: set[str] = set()
        self._dim: int | None = None

    def add(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict] | None = None,
    ) -> None:
        if not isinstance(ids, list) or not isinstance(vectors, list):
            raise StoreError("ids 和 vectors 必须是列表")
        if len(ids) != len(vectors):
            raise StoreError(f"长度不一致：{len(ids)} vs {len(vectors)}")

        if metadata is None:
            metadata = [{} for _ in ids]
        elif not isinstance(metadata, list) or len(metadata) != len(ids):
            raise StoreError("metadata 必须是与 ids 等长的列表")

        batch_ids = set()
        for i in ids:
            if not isinstance(i, str) or not i:
                raise StoreError("id 必须是非空字符串")
            if i in batch_ids or i in self._existing_ids:
                raise StoreError(f"id 重复：{i}")
            batch_ids.add(i)

        dim = self._dim
        for v in vectors:
            if not isinstance(v, list) or not v:
                raise StoreError("vector 必须是非空列表")
            if dim is None:
                dim = len(v)
            elif len(v) != dim:
                raise StoreError(f"向量维度不一致：期望 {dim}，实际 {len(v)}")

        self._dim = dim
        for i, v, m in zip(ids, vectors, metadata):
            if not isinstance(m, dict):
                raise StoreError("metadata 必须是字典")
            self._existing_ids.add(i)
            self.rows.append({
                "id": i,
                "vector": [float(x) for x in v],
                "metadata": dict(m),
            })

    def search(self, vector: list[float], k: int = 3) -> list[dict]:
        if k < 1:
            raise StoreError(f"k 必须 >= 1：{k}")
        if not self.rows:
            return []
        if not isinstance(vector, list) or len(vector) != self._dim:
            raise StoreError(f"查询维度不一致：期望 {self._dim}，实际 {len(vector)}")

        norm_q = math.sqrt(sum(x * x for x in vector))
        scored = []
        for idx, r in enumerate(self.rows):
            dot = sum(x * y for x, y in zip(vector, r["vector"]))
            norm_v = math.sqrt(sum(x * x for x in r["vector"]))
            s = 0.0 if (norm_q == 0 or norm_v == 0) else dot / (norm_q * norm_v)
            scored.append((-s, idx, r))

        scored.sort(key=lambda item: (item[0], item[1]))
        return [
            {
                "id": item[2]["id"],
                "score": -item[0],
                "metadata": dict(item[2]["metadata"]),
            }
            for item in scored[:k]
        ]

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "dim": self._dim,
                "rows": self.rows,
            }
            self.path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            raise StoreError(f"保存失败：{exc}") from exc

    @classmethod
    def load(cls, path: str | Path) -> "PersistentVectorStore":
        p = Path(path)
        if not p.is_file():
            raise StoreError(f"文件不存在：{path}")
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            raise StoreError(f"JSON 解析失败：{exc}") from exc

        if not isinstance(raw, dict) or "rows" not in raw:
            raise StoreError("存储文件格式错误")

        store = cls(p)
        store._dim = raw.get("dim")
        for r in raw["rows"]:
            if "id" not in r or "vector" not in r:
                raise StoreError("记录缺少 id 或 vector")
            rid = r["id"]
            if rid in store._existing_ids:
                raise StoreError(f"文件中存在重复 id：{rid}")
            store._existing_ids.add(rid)
            store.rows.append({
                "id": rid,
                "vector": [float(x) for x in r["vector"]],
                "metadata": dict(r.get("metadata", {})),
            })
        return store


# ----------------------------------------------------------
# 2. 原生 Chroma PersistentClient 与增量同步实现
# ----------------------------------------------------------


def make_chunk_id(source: str, index: int, text: str) -> str:
    """由 sha256(source + index + text) 生成确定性哈希 ID。"""
    raw = f"{source}#{index}#{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sync_document_to_chroma(
    collection: chromadb.Collection,
    source: str,
    chunks: list[dict],
    delete_old: bool = False,
) -> dict[str, int]:
    """增量同步片段到 Chroma 集合中。"""
    if delete_old:
        # 当源文件更新时，通过元数据过滤删除旧片段
        collection.delete(where={"source": source})

    if not chunks:
        return {"total": 0, "upserted": 0}

    ids = [make_chunk_id(source, c["index"], c["text"]) for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [
        {"source": source, "index": c["index"], "category": c.get("category", "faq")}
        for c in chunks
    ]
    vectors = embed_texts(texts)

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=vectors,
        metadatas=metadatas,
    )
    return {"total": len(chunks), "upserted": len(ids)}


if __name__ == "__main__":
    print("=== 2.10 Chroma 向量持久化与增量同步演示 ===")
    persist_path = Path(__file__).resolve().parent / "chroma_db"
    client = chromadb.PersistentClient(path=str(persist_path))
    col = client.get_or_create_collection(name="kb_demo")

    sample_source = "service_policy.txt"
    demo_chunks = [
        {"index": 1, "text": "售后退款在审核通过后 3 个工作日内原路到账。", "category": "refund"},
        {"index": 2, "text": "普通商品支持 7 天无理由退换货（需包装完整）。", "category": "refund"},
        {"index": 3, "text": "普通快递默认 48 小时内发货，偏远地区除外。", "category": "shipping"},
    ]

    print("\n[第一次同步] 写入初始 3 个片段...")
    sync_document_to_chroma(col, sample_source, demo_chunks, delete_old=False)
    print(f"当前 Chroma 集合记录总数：{col.count()}")

    print("\n[第二次同步（幂等测试）] 原样重新写入...")
    sync_document_to_chroma(col, sample_source, demo_chunks, delete_old=False)
    print(f"再次写入后总数未变（确定性 ID 保证幂等）：{col.count()}")

    # 模拟文件更新：退款改为 2 个工作日，更新同步
    print("\n[源文件更新] 删除旧片段并写入更新后的片段...")
    updated_chunks = [
        {"index": 1, "text": "售后退款在审核通过后 2 个工作日内极速到账。", "category": "refund"},
        {"index": 2, "text": "普通商品支持 7 天无理由退换货（需包装完整）。", "category": "refund"},
    ]
    sync_document_to_chroma(col, sample_source, updated_chunks, delete_old=True)
    print(f"更新同步后当前集合记录总数：{col.count()}")

    # 元数据过滤检索
    print("\n[带元数据过滤的检索演示]")
    query = "退款多久到账"
    qv = embed_texts([query])[0]
    results = col.query(
        query_embeddings=[qv],
        where={"category": "refund"},
        n_results=2,
    )
    for doc, meta, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        print(f"  [{meta['source']}#{meta['index']}] 距离: {distance:.4f} -> {doc}")
