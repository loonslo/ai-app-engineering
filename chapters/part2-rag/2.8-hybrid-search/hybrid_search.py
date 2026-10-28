"""章节 2.8 · 混合检索与 RRF 融合（原生实现）

==========================================================
为什么需要混合检索？
- 向量检索擅长语义泛化（问"手机怎么退货"能匹配"退款售后流程"）；
- 但面对专有名词、特定型号、精准编号（如"FAISS"、"v2.31"、"ORD-9981"）时，向量空间距离可能模糊；
- BM25 擅长字面精确命中，但对同义词无能为力。
混合检索（Hybrid Search）同时运行两路检索，并通过倒数排名融合（RRF, Reciprocal Rank Fusion）
将两路结果合并，在 2026 年是文档问答系统的标准默认配置。

运行：python tools/run_chapter.py 2.8 hybrid_search.py
==========================================================
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

try:
    from common import LONG_DOC, embed_texts
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from common import LONG_DOC, embed_texts


# ----------------------------------------------------------
# 1. Gate 闭卷规范函数
# ----------------------------------------------------------


def rrf_fuse(
    rankings: list[list[str]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[dict]:
    """Reciprocal Rank Fusion（RRF 倒数排名融合）。

    输入多路排序（每路是 id 列表，rank 从 1 开始）。
    返回 [{"id": str, "score": float}]，按 score 降序排列。
    """
    if not rankings:
        return []
    if all(len(r) == 0 for r in rankings):
        return []
    if k < 1:
        raise ValueError(f"k 必须 >= 1：{k}")

    if weights is None:
        weights = [1.0] * len(rankings)
    else:
        if len(weights) != len(rankings):
            raise ValueError(
                f"weights 长度与 rankings 不一致：{len(weights)} vs {len(rankings)}"
            )
        if any(w < 0 for w in weights):
            raise ValueError("weights 权重不能为负数")

    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    counter = 0

    for r_idx, ranking in enumerate(rankings):
        seen_in_r = set()
        w = weights[r_idx]
        for rank, item_id in enumerate(ranking, 1):
            if item_id in seen_in_r:
                continue
            seen_in_r.add(item_id)
            if item_id not in first_seen:
                first_seen[item_id] = counter
                counter += 1
            scores[item_id] = scores.get(item_id, 0.0) + w * (1.0 / (k + rank))

    rows = [{"id": item_id, "score": score} for item_id, score in scores.items()]
    rows.sort(key=lambda r: (-r["score"], first_seen[r["id"]]))
    return rows


def hybrid_search(
    vector_ids: list[str],
    bm25_ids: list[str],
    k: int = 4,
    weights: tuple[float, float] = (0.5, 0.5),
) -> list[dict]:
    """把向量和 BM25 两路结果融合并取 top-k。"""
    if k < 1:
        raise ValueError(f"k 必须 >= 1：{k}")
    if not vector_ids and not bm25_ids:
        return []
    fused = rrf_fuse([vector_ids, bm25_ids], k=60, weights=list(weights))
    return fused[:k]


# ----------------------------------------------------------
# 2. 原生 BM25 + 向量检索端到端实现
# ----------------------------------------------------------


def tokenize_chinese(text: str) -> list[str]:
    """中文单字与英文/数字单词切分，无需第三方分词依赖。"""
    return re.findall(r"[\u4e00-\u9fa5]|[a-zA-Z0-9_\.\-]+", text.lower())


class NativeHybridPipeline:
    """结合 rank_bm25 与原生语义向量的混合检索器。"""

    def __init__(self, chunks: list[dict]):
        self.chunks = {c["id"]: c for c in chunks}
        self.chunk_ids = [c["id"] for c in chunks]
        self.texts = [c["text"] for c in chunks]

        # 1. 构建 BM25 索引
        tokenized_corpus = [tokenize_chinese(t) for t in self.texts]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # 2. 构建向量索引
        self.vectors = embed_texts(self.texts) if self.texts else []

    def search_bm25(self, query: str, top_n: int = 5) -> list[str]:
        tokens = tokenize_chinese(query)
        scores = self.bm25.get_scores(tokens)
        top_idx = np.argsort(-scores)[:top_n]
        return [self.chunk_ids[i] for i in top_idx if scores[i] > 0]

    def search_vector(self, query: str, top_n: int = 5) -> list[str]:
        if not self.vectors:
            return []
        qv = embed_texts([query])[0]
        mat = np.array(self.vectors, dtype=np.float32)
        q = np.array(qv, dtype=np.float32)
        scores = np.dot(mat, q)
        top_idx = np.argsort(-scores)[:top_n]
        return [self.chunk_ids[i] for i in top_idx]

    def retrieve(
        self,
        query: str,
        k: int = 3,
        weights: tuple[float, float] = (0.5, 0.5),
    ) -> list[dict]:
        bm25_ids = self.search_bm25(query, top_n=10)
        vector_ids = self.search_vector(query, top_n=10)
        fused = hybrid_search(vector_ids, bm25_ids, k=k, weights=weights)

        results = []
        for item in fused:
            cid = item["id"]
            results.append({
                "id": cid,
                "score": item["score"],
                "text": self.chunks[cid]["text"],
            })
        return results


if __name__ == "__main__":
    print("=== 2.8 混合检索（BM25 + 向量检索 + RRF 融合）演示 ===")

    # 准备包含专有名词与一般描述的语料
    raw_text = Path(LONG_DOC).read_text(encoding="utf-8")
    chunks_data = []
    step = 120
    for i in range(0, len(raw_text), step):
        t = raw_text[i : i + 150].strip()
        if t:
            chunks_data.append({"id": f"chunk_{len(chunks_data)+1}", "text": t})

    pipeline = NativeHybridPipeline(chunks_data)
    print(f"语料切分完毕，共构建 {len(chunks_data)} 个片段的索引。\n")

    query = "MCP 协议与标准化工具解耦"
    print(f"评测查询：'{query}'")

    bm25_top = pipeline.search_bm25(query, top_n=3)
    vec_top = pipeline.search_vector(query, top_n=3)
    hybrid_top = pipeline.retrieve(query, k=3)

    print(f"\n[BM25 单路召回]：{bm25_top}")
    print(f"[向量 单路召回]：{vec_top}")
    print("\n[RRF 混合融合 Top 3]：")
    for rank, h in enumerate(hybrid_top, 1):
        print(f"  Top {rank} [{h['id']}] 得分: {h['score']:.5f} -> {h['text'][:60]}...")
