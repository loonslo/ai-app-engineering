"""章节 2.11 · Cross-Encoder 重排与多模态解析（原生实现）

==========================================================
为什么需要重排（Rerank）？
- 向量双塔模型（Bi-Encoder）将 Query 与 Document 独立编码为向量，计算速度快（毫秒级），但无法捕捉词与词之间的交叉注意力（Cross-Attention）；
- 交叉编码器（Cross-Encoder）将 (Query, Document) 拼接后输入完整 Transformer，能精确计算相关性得分，但计算开销大；
- 工业级标准方案：“混合检索/粗召回（召回 Top 10-20）→ Cross-Encoder 精排（截取 Top 3-5）”。

本文件为纯原生 Python 实现，不依赖 LangChain：
1. 原生重排函数 rerank 与 recall@k 评估指标
2. 使用 common.get_cross_encoder() 执行 Cross-Encoder 重排精算
3. 多模态读图函数 ask_image（可选，使用 OpenAI-compatible VLM 端点）

运行：python tools/run_chapter.py 2.11
==========================================================
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Callable

import numpy as np

try:
    from common import LONG_DOC, embed_texts, get_cross_encoder
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from common import LONG_DOC, embed_texts, get_cross_encoder


# ----------------------------------------------------------
# 1. Gate 闭卷规范函数
# ----------------------------------------------------------


def rerank(
    query: str,
    docs: list[dict],
    score_fn: Callable[[str, str], float],
    top_k: int = 3,
) -> list[dict]:
    """按 score_fn 对候选片段打分并重排。

    docs 形如 [{"id": str, "text": str}, ...]。
    返回 [{"id": str, "text": str, "score": float}]，按分数降序排列，最多 top_k 条。
    """
    if top_k < 1:
        raise ValueError(f"top_k 必须 >= 1：{top_k}")
    if not isinstance(docs, list):
        raise ValueError("docs 必须是列表")
    if not docs:
        return []

    scored = []
    for idx, d in enumerate(docs):
        if not isinstance(d, dict) or "id" not in d or "text" not in d:
            raise ValueError("doc 必须包含 id 和 text 字段")
        if not isinstance(d["id"], str) or not isinstance(d["text"], str):
            raise ValueError("id 和 text 必须是字符串")
        try:
            s = score_fn(query, d["text"])
        except Exception as exc:
            raise ValueError(f"score_fn 评分异常：{exc}") from exc
        if not isinstance(s, (int, float)) or isinstance(s, bool):
            raise ValueError(f"score_fn 返回非数值：{s!r}")
        scored.append((
            -float(s),
            idx,
            {
                "id": d["id"],
                "text": d["text"],
                "score": float(s),
            },
        ))

    scored.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in scored[:top_k]]


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """计算 recall@k：前 k 个结果覆盖了多少相关 ID。"""
    if k < 1:
        raise ValueError(f"k 必须 >= 1：{k}")
    if not relevant_ids:
        return 0.0
    top_k_set = set(retrieved_ids[:k])
    hits = sum(1 for rid in relevant_ids if rid in top_k_set)
    return float(hits / len(relevant_ids))


# ----------------------------------------------------------
# 2. 原生 Cross-Encoder 精排与多模态扩展
# ----------------------------------------------------------


def native_cross_encoder_score(query: str, text: str) -> float:
    """使用本地 bge-reranker 评分；若未下载本地模型则降级为离线相似度估计。"""
    try:
        model = get_cross_encoder()
        score = model.predict([(query, text)])[0]
        return float(score)
    except Exception:
        # 本地重排模型未下载时做可读离线降级
        q_chars = set(query)
        overlap = sum(1 for c in text if c in q_chars)
        return float(overlap / max(1, len(query)))


def ask_image(image_path: str, question: str) -> str:
    """使用视觉模型分析图像（选做方向）。"""
    p = Path(image_path)
    if not p.is_file():
        return f"[跳过多模态] 图片文件不存在：{image_path}"

    b64 = base64.b64encode(p.read_bytes()).decode()
    vlm_model = os.getenv("VLM_MODEL", "qwen-vl-max")
    api_key = os.getenv("VLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", "local-demo"))
    base_url = os.getenv("VLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=vlm_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
    )
    return resp.choices[0].message.content or ""


if __name__ == "__main__":
    print("=== 2.11 Cross-Encoder 重排与精排演示 ===")

    # 1. 准备长语料片段
    raw_text = Path(LONG_DOC).read_text(encoding="utf-8")
    chunks: list[dict] = []
    step = 100
    for i in range(0, len(raw_text), step):
        t = raw_text[i : i + 130].strip()
        if t:
            chunks.append({"id": f"chunk_{len(chunks)+1}", "text": t})

    # 2. 向量粗召回 top-8
    query = "LangGraph 适合哪些复杂的业务场景"
    print(f"查询：'{query}'")

    doc_texts = [c["text"] for c in chunks]
    vectors = embed_texts(doc_texts)
    q_vec = embed_texts([query])[0]
    scores = np.dot(np.array(vectors, dtype=np.float32), np.array(q_vec, dtype=np.float32))
    rough_top8_idx = np.argsort(-scores)[:8]
    rough_candidates = [chunks[i] for i in rough_top8_idx]

    print("\n【阶段一：向量粗召回 Top 8】")
    for r, c in enumerate(rough_candidates, 1):
        print(f"  [{r}] {c['id']}: {c['text'][:45]}...")

    # 3. Cross-Encoder 精排 top-3
    reranked = rerank(query, rough_candidates, native_cross_encoder_score, top_k=3)
    print("\n【阶段二：Cross-Encoder 精排 Top 3】")
    for r, item in enumerate(reranked, 1):
        print(f"  Top {r} [{item['id']}] 得分: {item['score']:.4f} -> {item['text'][:45]}...")
