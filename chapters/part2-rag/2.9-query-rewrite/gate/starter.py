"""L2.6 查询改写与 Agentic Retrieval · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
query_rewrite.py。实现下面四个函数/接口，然后运行：

    python chapters/part2-rag/2.9-query-rewrite/gate/gate_check.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


def build_rewrite_prompt(question: str, history: list[dict] | None = None) -> str:
    """构造 Multi-Query 改写 prompt。

    要求：
    - 包含原问题；
    - 有 history 时把最近几轮拼进去（每条 "role: content"）；
    - 明确要求“输出多条不同说法，一行一条，不要编号/解释”。
    """
    raise NotImplementedError("实现改写 prompt")


def parse_rewrites(text: str, max_queries: int = 4) -> list[str]:
    """把模型输出解析成去重后的查询列表。

    要求：
    - 去掉行首编号（1. / 1) / - / •）和空白；
    - 丢掉空行和与问题无关的说明行（只保留非空）；
    - 去重，保持出现顺序；
    - 最多 max_queries 条；max_queries < 1 -> ValueError；
    - text 不是字符串 -> ValueError。
    """
    raise NotImplementedError("实现改写解析")


def rewrite_query(
    question: str,
    llm_fn: Callable[[str], str],
    history: list[dict] | None = None,
    max_queries: int = 4,
) -> dict:
    """生成改写查询。

    返回 {"queries": list[str], "error": str | None}。
    要求：
    - 空问题 -> ValueError；max_queries < 1 -> ValueError；
    - 原问题始终在 queries[0]；
    - 模型输出为空/解析后没有新查询 -> queries=[原问题]，error="empty_rewrite"；
    - 模型异常 -> queries=[原问题]，error="model_error"；
    - 正常 -> 原问题 + 解析结果，去重后截断到 max_queries。
    """
    raise NotImplementedError("实现查询改写")


@dataclass(frozen=True)
class Hit:
    source: str
    index: int
    score: float
    text: str


@dataclass(frozen=True)
class AgenticResult:
    hits: tuple[Hit, ...]           # 按 source#index 去重，按 score 降序
    rounds: int
    queries: tuple[str, ...]
    stopped_reason: str             # "enough" | "no_rewrite" | "max_rounds"


def agentic_retrieve(
    question: str,
    search_fn: Callable[[str], list[Hit]],
    rewrite_fn: Callable[[str, list[Hit]], str | None],
    *,
    max_rounds: int = 3,
    min_hits: int = 2,
) -> AgenticResult:
    """每轮用当前查询调用 search_fn(query) -> list[Hit]，结果累计去重；
    累计命中数 >= min_hits 时停止，原因 "enough"；
    rewrite_fn(question, hits_so_far) 返回 None 时停止，原因 "no_rewrite"；
    轮数达到 max_rounds 时停止，原因 "max_rounds"；max_rounds < 1 或 min_hits < 1 抛 ValueError。
    """
    raise NotImplementedError("实现 agentic_retrieve")
