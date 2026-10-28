"""章节 2.9 · 查询改写与 Agentic Retrieval（原生实现）

==========================================================
用户输入口语化、含代词、过短或用词与文档差异大时，直接检索往往容易漏召回。
本章用原生 Python 与 OpenAI SDK 实现三项核心进阶检索技术：
1. Multi-Query：利用大模型改写出多种同义表达，扩展查询召回边界
2. HyDE（Hypothetical Document Embeddings）：先生成假设性正文答案，再进行向量检索
3. Agentic Retrieval（智能多轮检索循环）：
   Agent 依据当前召回结果自主决定是“证据已足够，终止检索”，还是“继续改写查询，发起下一轮检索”

运行：python tools/run_chapter.py 2.9
==========================================================
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

try:
    from common import (
        SAMPLE_DOC,
        chat_model_name,
        embed_texts,
        get_openai_client,
    )
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from common import (
        SAMPLE_DOC,
        chat_model_name,
        embed_texts,
        get_openai_client,
    )


# ----------------------------------------------------------
# 1. Gate 闭卷规范函数与数据结构
# ----------------------------------------------------------


def build_rewrite_prompt(question: str, history: list[dict] | None = None) -> str:
    """构造 Multi-Query 改写 prompt。"""
    lines = [
        "你是一个专业的查询改写助手。请将用户的问题改写为多种不同角度或关键词的搜索查询。"
    ]
    if history:
        lines.append("对话历史：")
        for h in history:
            role = h.get("role", "user")
            content = h.get("content", "")
            lines.append(f"{role}: {content}")
    lines.append(f"当前用户问题：{question}")
    lines.append("请输出改写后的查询，每行一条，不要编号，不要输出额外解释说明。")
    return "\n".join(lines)


def parse_rewrites(text: str, max_queries: int = 4) -> list[str]:
    """把模型输出解析成去重后的查询列表。"""
    if not isinstance(text, str):
        raise ValueError("text 必须是字符串")
    if max_queries < 1:
        raise ValueError(f"max_queries 必须 >= 1：{max_queries}")

    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^(\d+[\.\)]\s*|[\-\*•]\s*)", "", s).strip()
        if s and s not in cleaned:
            cleaned.append(s)

    return cleaned[:max_queries]


def rewrite_query(
    question: str,
    llm_fn: Callable[[str], str],
    history: list[dict] | None = None,
    max_queries: int = 4,
) -> dict:
    """生成改写查询。"""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("问题不能为空")
    if max_queries < 1:
        raise ValueError(f"max_queries 必须 >= 1：{max_queries}")

    prompt = build_rewrite_prompt(question, history)
    try:
        raw_output = llm_fn(prompt)
    except Exception:
        return {"queries": [question], "error": "model_error"}

    if not isinstance(raw_output, str) or not raw_output.strip():
        return {"queries": [question], "error": "empty_rewrite"}

    parsed = parse_rewrites(raw_output, max_queries=max_queries)
    combined: list[str] = [question]
    for p in parsed:
        if p != question and p not in combined:
            combined.append(p)

    if len(combined) == 1:
        return {"queries": [question], "error": "empty_rewrite"}

    return {"queries": combined[:max_queries], "error": None}


@dataclass(frozen=True)
class Hit:
    source: str
    index: int
    score: float
    text: str


@dataclass(frozen=True)
class AgenticResult:
    hits: tuple[Hit, ...]
    rounds: int
    queries: tuple[str, ...]
    stopped_reason: str


def agentic_retrieve(
    question: str,
    search_fn: Callable[[str], list[Hit]],
    rewrite_fn: Callable[[str, list[Hit]], str | None],
    *,
    max_rounds: int = 3,
    min_hits: int = 2,
) -> AgenticResult:
    """Agentic 多轮自主检索循环。"""
    if max_rounds < 1:
        raise ValueError(f"max_rounds 必须 >= 1：{max_rounds}")
    if min_hits < 1:
        raise ValueError(f"min_hits 必须 >= 1：{min_hits}")

    current_q = question
    queries: list[str] = []
    rounds = 0
    hits_map: dict[str, Hit] = {}
    stopped_reason = "max_rounds"

    while rounds < max_rounds:
        rounds += 1
        queries.append(current_q)
        current_hits = search_fn(current_q)
        for h in current_hits:
            key = f"{h.source}#{h.index}"
            if key not in hits_map or h.score > hits_map[key].score:
                hits_map[key] = h

        if len(hits_map) >= min_hits:
            stopped_reason = "enough"
            break

        if rounds >= max_rounds:
            stopped_reason = "max_rounds"
            break

        hits_so_far = sorted(hits_map.values(), key=lambda x: x.score, reverse=True)
        next_q = rewrite_fn(question, hits_so_far)
        if next_q is None or not str(next_q).strip():
            stopped_reason = "no_rewrite"
            break
        current_q = str(next_q).strip()

    final_hits = tuple(
        sorted(hits_map.values(), key=lambda x: x.score, reverse=True)
    )
    return AgenticResult(
        hits=final_hits,
        rounds=rounds,
        queries=tuple(queries),
        stopped_reason=stopped_reason,
    )


# ----------------------------------------------------------
# 2. 原生 Multi-Query、HyDE 与演示
# ----------------------------------------------------------

_IS_LIVE = False


def call_llm(prompt: str) -> str:
    """调用大模型；仅在 --live 模式下发起真实网络调用，离线时返回明确标注的确定性示例。"""
    if _IS_LIVE:
        try:
            client = get_openai_client()
        except Exception as exc:
            print(f"[错误] 未能初始化客户端（未配置有效 API 密钥）：{exc}")
            sys.exit(1)
        model = chat_model_name()
        resp = client.chat.completions.create(
            model=model,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""

    # 离线确定性示例
    if "改写" in prompt or "不同角度" in prompt:
        return "[离线确定性改写] 向量数据在磁盘上的持久化存储方法\n向量数据库在生产环境的选型落地\nFAISS 与 Chroma 存储差异"
    if "假设性" in prompt:
        return "[离线确定性 HyDE 假设文本] 向量数据通常通过专用的向量数据库（如 Chroma、Milvus）或轻量嵌入索引库（如 FAISS）进行磁盘持久化存储与索引落盘。"
    return f"[离线确定性文本] 针对问题：{prompt[:30]}"


def generate_hyde_query(question: str) -> str:
    """生成 HyDE 假设性正文段落。"""
    prompt = (
        f"请用两三句话假设性地回答下面的问题（即使不确定细节也请直接写出一段包含专业术语的陈述正文，用于检索向量匹配）：\n"
        f"问题：{question}"
    )
    return call_llm(prompt)


class SimpleIndex:
    def __init__(self, doc_path: str | Path):
        self.doc_path = Path(doc_path)
        text = self.doc_path.read_text(encoding="utf-8")
        self.chunks: list[Hit] = []
        step = 100
        idx = 1
        for start in range(0, len(text), step):
            piece = text[start : start + 120].strip()
            if piece:
                self.chunks.append(
                    Hit(
                        source=self.doc_path.name,
                        index=idx,
                        score=0.0,
                        text=piece,
                    )
                )
                idx += 1
        self.vectors = embed_texts([c.text for c in self.chunks]) if self.chunks else []

    def search(self, query: str, top_k: int = 3, min_score: float = 0.35) -> list[Hit]:
        if not self.chunks or not self.vectors:
            return []
        qv = embed_texts([query])[0]
        mat = np.array(self.vectors, dtype=np.float32)
        q = np.array(qv, dtype=np.float32)
        scores = np.dot(mat, q)
        top_idx = np.argsort(-scores)[:top_k]

        hits = []
        for i in top_idx:
            s = float(scores[i])
            if s >= min_score:
                c = self.chunks[i]
                hits.append(Hit(source=c.source, index=c.index, score=s, text=c.text))
        return hits


def main() -> None:
    global _IS_LIVE
    import argparse

    parser = argparse.ArgumentParser(description="2.9 查询改写演示")
    parser.add_argument("--live", action="store_true", help="启用真实在线大模型调用")
    args = parser.parse_args()
    _IS_LIVE = args.live

    print("=== 2.9 查询改写（Multi-Query、HyDE 与 Agentic Retrieval）演示 ===")
    if _IS_LIVE:
        print("[模式] 正在使用 --live 在线调用真实大模型。")
    else:
        print("[模式] 默认离线模式（未发起在线模型调用，标有 [离线确定性...] 标记；可通过 --live 开启）。")

    index = SimpleIndex(SAMPLE_DOC)
    query = "向量怎么存"
    print(f"原始问题：'{query}'\n")

    # 1. Multi-Query
    print("--- 1. Multi-Query 改写检索 ---")
    rewrite_res = rewrite_query(query, call_llm, max_queries=3)
    print("改写出的查询列表：", rewrite_res["queries"])
    all_multi_hits: dict[str, Hit] = {}
    for q in rewrite_res["queries"]:
        for h in index.search(q, top_k=2):
            key = f"{h.source}#{h.index}"
            if key not in all_multi_hits or h.score > all_multi_hits[key].score:
                all_multi_hits[key] = h
    print(f"Multi-Query 合并后召回 {len(all_multi_hits)} 个片段：")
    for h in sorted(all_multi_hits.values(), key=lambda x: x.score, reverse=True)[:2]:
        print(f"  [{h.source}#{h.index}] 得分: {h.score:.4f} -> {h.text[:40]}...")

    # 2. HyDE
    print("\n--- 2. HyDE 假设性文档改写检索 ---")
    hypo_doc = generate_hyde_query(query)
    print(f"生成假设性正文：\n{hypo_doc.strip()[:100]}...\n")
    hyde_hits = index.search(hypo_doc, top_k=2)
    print("HyDE 召回结果：")
    for h in hyde_hits:
        print(f"  [{h.source}#{h.index}] 得分: {h.score:.4f} -> {h.text[:40]}...")

    # 3. Agentic Retrieval
    print("\n--- 3. Agentic Retrieval 检索循环 ---")

    def agent_rewrite_step(orig_q: str, hits_so_far: list[Hit]) -> str | None:
        if len(hits_so_far) >= 2:
            return None
        return f"{orig_q} 数据库持久化实现"

    agent_result = agentic_retrieve(
        query,
        lambda q: index.search(q, top_k=1, min_score=0.45),
        agent_rewrite_step,
        max_rounds=3,
        min_hits=2,
    )
    print(f"Agentic 循环结束：轮数={agent_result.rounds}, 停止原因={agent_result.stopped_reason}")
    print(f"执行的查询序列：{agent_result.queries}")
    print(f"最终捕获片段数：{len(agent_result.hits)}")


if __name__ == "__main__":
    main()
