"""章节 2.7 · 切分策略对比消融（原生实现）

==========================================================
RAG 答得准不准，第一道关口不是模型，是“文档切得好不好”。
本章用原生 Python 对比不同切分策略对检索效果的影响，输出消融对比表：
1. 纯原生实现，不依赖 LangChain
2. 实现了保边界切分 split_preserving_boundaries 与切分统计 chunk_stats
3. 对比小块无重叠、小块有重叠、大块有重叠、结构边界切分四种策略
4. 输出块数、平均长度、最大长度和召回片段的相似度对比

运行：python tools/run_chapter.py 2.7
==========================================================
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

try:
    from common import LONG_DOC, embed_texts
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from common import LONG_DOC, embed_texts


# ----------------------------------------------------------
# 1. Gate 闭卷规范函数
# ----------------------------------------------------------


def split_preserving_boundaries(text: str, max_chars: int) -> list[str]:
    """优先按段落、再按句子标点、最后硬切，保证每段不超过 max_chars。"""
    if not isinstance(text, str) or not text.strip():
        return []
    if max_chars <= 0:
        raise ValueError("max_chars 必须大于 0")
    if len(text) <= max_chars:
        return [text]

    # 1. 优先按段落切分
    if "\n\n" in text:
        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        cur = ""
        for p in paragraphs:
            if not p:
                continue
            if len(p) > max_chars:
                if cur:
                    chunks.append(cur)
                    cur = ""
                chunks.extend(split_preserving_boundaries(p, max_chars))
            elif len(cur) + (2 if cur else 0) + len(p) <= max_chars:
                cur = cur + "\n\n" + p if cur else p
            else:
                if cur:
                    chunks.append(cur)
                cur = p
        if cur:
            chunks.append(cur)
        return [c for c in chunks if c.strip()]

    # 2. 段落超长按句子标点切分
    sentences = [s for s in re.split(r"(?<=[。！？!?\n])", text) if s]
    if len(sentences) > 1:
        chunks = []
        cur = ""
        for s in sentences:
            if not s:
                continue
            if len(s) > max_chars:
                if cur:
                    chunks.append(cur)
                    cur = ""
                # 硬切
                for i in range(0, len(s), max_chars):
                    chunks.append(s[i : i + max_chars])
            elif len(cur) + len(s) <= max_chars:
                cur += s
            else:
                if cur:
                    chunks.append(cur)
                cur = s
        if cur:
            chunks.append(cur)
        return [c for c in chunks if c.strip()]

    # 3. 单句超长硬切
    return [
        text[i : i + max_chars]
        for i in range(0, len(text), max_chars)
        if text[i : i + max_chars].strip()
    ]


def chunk_stats(chunks: list[str]) -> dict:
    """统计切分块指标。"""
    count = len(chunks)
    empty_count = sum(1 for c in chunks if len(c) == 0)
    if count == 0:
        return {"count": 0, "avg_len": 0, "max_len": 0, "empty_count": 0}
    max_len = max(len(c) for c in chunks)
    avg_len = sum(len(c) for c in chunks) / count
    return {
        "count": count,
        "avg_len": avg_len,
        "max_len": max_len,
        "empty_count": empty_count,
    }


# ----------------------------------------------------------
# 2. 滑动窗口切分与消融实验
# ----------------------------------------------------------


def sliding_window_split(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """基础字符滑动窗口切分。"""
    if not text.strip():
        return []
    step = max(1, chunk_size - overlap)
    chunks = []
    for start in range(0, len(text), step):
        c = text[start : start + chunk_size]
        if c.strip():
            chunks.append(c)
        if start + chunk_size >= len(text):
            break
    return chunks


def retrieve_top_k(
    query: str,
    chunks: list[str],
    k: int = 2,
) -> list[tuple[float, str]]:
    """原生向量化检索 top-k。"""
    if not chunks:
        return []
    vectors = embed_texts(chunks)
    q_vec = embed_texts([query])[0]
    mat = np.array(vectors, dtype=np.float32)
    q = np.array(q_vec, dtype=np.float32)
    scores = np.dot(mat, q)
    top_indices = np.argsort(-scores)[:k]
    return [(float(scores[idx]), chunks[idx]) for idx in top_indices]


def run_ablation() -> None:
    text = Path(LONG_DOC).read_text(encoding="utf-8")
    query = "LangGraph 最大的价值是什么"

    strategies = [
        ("小块 + 无重叠", lambda t: sliding_window_split(t, 60, 0)),
        ("小块 + 有重叠", lambda t: sliding_window_split(t, 60, 20)),
        ("大块 + 有重叠", lambda t: sliding_window_split(t, 300, 50)),
        ("保结构自然切分", lambda t: split_preserving_boundaries(t, 120)),
    ]

    print("=== 切分策略对比消融实验 ===")
    print(f"评测查询：'{query}'\n")
    print(f"{'策略名称':<14} | {'块数':<4} | {'平均长':<6} | {'最大长':<6} | {'Top1 得分':<9} | Top1 片段预览")
    print("-" * 80)

    for name, split_fn in strategies:
        chunks = split_fn(text)
        stats = chunk_stats(chunks)
        hits = retrieve_top_k(query, chunks, k=2)
        top1_score, top1_text = hits[0] if hits else (0.0, "")
        preview = top1_text.replace("\n", " ")[:30]
        print(
            f"{name:<14} | {stats['count']:<4} | {stats['avg_len']:<6.1f} | {stats['max_len']:<6} | {top1_score:<9.4f} | {preview}..."
        )


if __name__ == "__main__":
    run_ablation()
