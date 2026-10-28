"""章节 2.2 · 向量化与语义检索（原生实现）

==========================================================
本章解决核心问题：怎么从一堆片段里，找出和用户问题最相关的几块？
通过纯原生 Python + NumPy 实现语义向量检索，不依赖 LangChain：
1. 原生向量化：使用 common.embed_texts()（基于 sentence-transformers）
2. 原生相似度计算：向量归一化后，余弦相似度等价于点积
3. 演示 NumPy 暴力检索与可选 FAISS-CPU 索引
4. 演示三类典型失败模式：同义词歧义、专有名词缩写、数字/版本号

运行：python tools/run_chapter.py 2.2
==========================================================
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

import numpy as np

try:
    from common import SAMPLE_DOC, embed_texts as common_embed_texts
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from common import SAMPLE_DOC, embed_texts as common_embed_texts


# ----------------------------------------------------------
# 1. Gate 闭卷规范函数与 VectorIndex
# ----------------------------------------------------------


def cosine(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。"""
    if not a or not b or len(a) != len(b):
        raise ValueError("向量不能为空且维度必须一致")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_texts(
    texts: list[str],
    embed_fn: Callable[[str], list[float]],
) -> list[list[float]]:
    """逐条把文本变成向量。"""
    if not isinstance(texts, list):
        raise ValueError("texts 必须是列表")
    if not texts:
        return []

    res: list[list[float]] = []
    dim: int | None = None
    for t in texts:
        if not isinstance(t, str):
            raise ValueError(f"文本必须是字符串：{t!r}")
        v = embed_fn(t)
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("embed_fn 必须返回非空 list[float]")
        if dim is None:
            dim = len(v)
        elif len(v) != dim:
            raise ValueError(f"向量维度不一致：期望 {dim}，实际 {len(v)}")
        res.append([float(x) for x in v])
    return res


class VectorIndex:
    """内存向量索引：add 建索引，search 找 top-k。"""

    def __init__(self) -> None:
        self._ids: set[str] = set()
        self._rows: list[dict] = []
        self._dim: int | None = None

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        if not isinstance(ids, list) or not isinstance(vectors, list):
            raise ValueError("ids 和 vectors 必须是列表")
        if len(ids) != len(vectors):
            raise ValueError(
                f"ids 与 vectors 长度不一致：{len(ids)} vs {len(vectors)}"
            )

        batch_ids = set()
        for i in ids:
            if not isinstance(i, str) or not i:
                raise ValueError("id 必须是非空字符串")
            if i in batch_ids or i in self._ids:
                raise ValueError(f"id 重复：{i}")
            batch_ids.add(i)

        dim = self._dim
        for v in vectors:
            if not isinstance(v, list) or len(v) == 0:
                raise ValueError("vector 必须是非空列表")
            if dim is None:
                dim = len(v)
            elif len(v) != dim:
                raise ValueError(f"向量维度不一致：期望 {dim}，实际 {len(v)}")

        self._dim = dim
        for id_val, v in zip(ids, vectors):
            self._ids.add(id_val)
            self._rows.append({
                "id": id_val,
                "vector": [float(x) for x in v],
            })

    def search(self, vector: list[float], k: int = 3) -> list[dict]:
        if k < 1:
            raise ValueError(f"k 必须 >= 1：{k}")
        if not self._rows:
            return []
        if not isinstance(vector, list) or len(vector) != self._dim:
            raise ValueError(f"查询维度不匹配：期望 {self._dim}，实际 {len(vector)}")

        scored = []
        for idx, row in enumerate(self._rows):
            s = cosine(vector, row["vector"])
            scored.append((s, idx, row["id"]))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [{"id": item[2], "score": item[0]} for item in scored[:k]]


# ----------------------------------------------------------
# 2. NumPy 向量点积与 FAISS 索引演示
# ----------------------------------------------------------


def numpy_top_k(
    query_vec: list[float],
    doc_vectors: list[list[float]],
    chunks: list[dict],
    k: int = 3,
) -> list[dict]:
    """使用 NumPy 矩阵乘法计算归一化点积相似度并排序。"""
    if not doc_vectors or not chunks:
        return []
    mat = np.array(doc_vectors, dtype=np.float32)
    q = np.array(query_vec, dtype=np.float32)
    scores = np.dot(mat, q)
    top_indices = np.argsort(-scores)[:k]
    return [
        {
            "chunk": chunks[idx],
            "score": float(scores[idx]),
        }
        for idx in top_indices
    ]


def faiss_top_k(
    query_vec: list[float],
    doc_vectors: list[list[float]],
    chunks: list[dict],
    k: int = 3,
) -> list[dict]:
    """可选：使用 FAISS IndexFlatIP（内积索引）检索 top-k。"""
    try:
        import faiss
    except ImportError:
        return []

    dim = len(query_vec)
    index = faiss.IndexFlatIP(dim)
    mat = np.array(doc_vectors, dtype=np.float32)
    index.add(mat)

    q = np.array([query_vec], dtype=np.float32)
    distances, indices = index.search(q, k)
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx >= 0:
            results.append({"chunk": chunks[idx], "score": float(dist)})
    return results


def demonstrate_failure_modes() -> None:
    """演示语义向量检索的三类典型失效现象。"""
    print("--- 演示三类典型失效现象 ---")
    corpus = [
        {"id": "doc1", "text": "苹果公司发布了最新款旗舰手机 iPhone 17。"},
        {"id": "doc2", "text": "烟台红富士苹果口感脆甜，富含丰富的维生素 C。"},
        {"id": "doc3", "text": "系统运行环境升级至 Linux Kernel 6.12，支持最新硬件。"},
        {"id": "doc4", "text": "系统当前版本为 v2.31，即将升级到 v2.32。"},
        {"id": "doc5", "text": "本次退款金额为 500 元，预计 3 个工作日到账。"},
        {"id": "doc6", "text": "本次充值金额为 5000 元，感谢您的支持。"},
    ]
    texts = [c["text"] for c in corpus]
    vectors = common_embed_texts(texts)

    queries = [
        ("同义词歧义", "我想买好吃的苹果", "doc2"),
        ("专有名词与新概念", "Linux 6.12 内核特性", "doc3"),
        ("数字与版本号极近", "当前版本是 v2.32 吗", "doc4"),
    ]

    for category, q, target_id in queries:
        qv = common_embed_texts([q])[0]
        hits = numpy_top_k(qv, vectors, corpus, k=2)
        top_id = hits[0]["chunk"]["id"]
        print(f"[{category}] 查询：'{q}'")
        print(
            f"  Top 1: {top_id} (得分 {hits[0]['score']:.4f}) -> {hits[0]['chunk']['text']}"
        )
        print(
            f"  Top 2: {hits[1]['chunk']['id']} (得分 {hits[1]['score']:.4f}) -> {hits[1]['chunk']['text']}"
        )
        print()


if __name__ == "__main__":
    print("=== 2.2 向量化与语义检索原生演示 ===")

    # 1. 加载并切分 SAMPLE_DOC
    text = Path(SAMPLE_DOC).read_text(encoding="utf-8")
    chunks = []
    step = 100
    for i in range(0, len(text), step):
        sub = text[i : i + 120]
        if sub.strip():
            chunks.append({"id": f"chunk_{len(chunks)+1}", "text": sub})

    print(f"文档切成 {len(chunks)} 个片段。")

    # 2. 向量化
    doc_texts = [c["text"] for c in chunks]
    doc_vectors = common_embed_texts(doc_texts)
    print(f"向量化完成，维度：{len(doc_vectors[0])}（已归一化）")

    # 3. 检索测试
    query = "怎么使用向量检索"
    q_vec = common_embed_texts([query])[0]
    hits = numpy_top_k(q_vec, doc_vectors, chunks, k=3)
    print(f"\n查询：'{query}' 的 NumPy Top 3：")
    for h in hits:
        print(f"  [{h['chunk']['id']}] (得分: {h['score']:.4f}) {h['chunk']['text'][:50]}...")

    # 4. 失效模式演示
    print()
    demonstrate_failure_modes()
