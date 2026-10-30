"""L2.12 Gate：真实资料知识库 v1 · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
kb_pipeline.py。实现下面的核心组件，然后运行：

    python chapters/part2-rag/2.15-real-corpus-kb-gate/gate/gate_check.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class SourceFile:
    name: str
    pages: tuple[str | None, ...]  # None 表示该页无法提取文本（如扫描页）


@dataclass(frozen=True)
class Chunk:
    source: str
    page: int  # 从 1 开始
    index: int  # 页内从 1 开始
    text: str


@dataclass(frozen=True)
class IngestReport:
    chunks: tuple[Chunk, ...]
    failures: tuple[tuple[str, int, str], ...]  # (source, page, reason)


def ingest(files: list[SourceFile], split_fn: Callable[[str], list[str]]) -> IngestReport:
    """逐页处理文件：
    - 页为 None 时记失败，reason="no_text_layer"；
    - 页内容去空白后为空时记失败，reason="empty_page"；
    - 表格行（包含 '|' 分隔符的非空行）按行独立保留为 Chunk，不跨行合并；
    - 其余普通文本合并后交给 split_fn(text) -> list[str] 切分；
    - Chunk.page 从 1 开始，Chunk.index 在页内从 1 递增。
    """
    raise NotImplementedError("实现文档接入与切分 ingest")


def answer_with_citations(
    question: str,
    retrieve_fn: Callable[[str], list[tuple[Chunk, float]]],
    chat_fn: Callable[[list[dict]], str],
    *,
    min_score: float,
) -> dict:
    """检索并生成带引用的回答：
    - retrieve_fn(question) -> list[(Chunk, score)]；
    - 没有分数 >= min_score 的片段时拒答，且不得调用 chat_fn：
      {"refused": True, "answer": "资料中未找到足够支持该问题的证据，已安全拒答。", "citations": []}；
    - 否则构造对话消息：将检索到的资料放置在 user 消息中明确的分隔符内，并声明资料是只读数据而非系统指令；
    - 引用格式为 "source#p<page>#<index>"，只能引用实际传给模型的片段；
    - 返回 {"refused": False, "answer": 回答文本, "citations": 引用列表}。
    """
    raise NotImplementedError("实现带引用回答 answer_with_citations")


def evaluate(cases: list[dict], answer_fn: Callable[[dict], dict]) -> dict:
    """评测知识库问答系统指标。

    指标计算公式：
    1. refusal_accuracy（拒答准确率）：
       在所有用例（样本总数 N = len(cases)）上计算：
       (ans['refused'] == case['should_refuse']) 的样本比例。
    2. hit_at_5（Top-5 召回命中率）：
       仅在【应答用例】（case['should_refuse'] == False）上计算，分母为应答用例总数。
       若用例无 gold_sources 则记命中；
       否则优先取回答中的 ans.get('retrieved')，若无则取用例中的 case.get('retrieved', [])；
       当 top-5 中至少存在一个片段匹配任一 gold_sources（前缀以 '<gold>#' 开头或完全相等）时记为命中（1.0），否则记 0.0。
    3. citation_accuracy（引用准确率）：
       仅在【应答用例】（case['should_refuse'] == False）上计算，分母为应答用例总数。
       若系统未拒答且 citations 非空，且每一个 gold_sources 均至少有一个 citation 覆盖
       （前缀以 '<gold>#' 开头或完全相等），记为通过（1.0）；
       若系统错误拒答或引用缺失/未覆盖全，记 0.0。
       （注：拒答用例不计入 citation_accuracy 与 hit_at_5 的分母）。
    4. 返回字典包含:
       - 'citation_accuracy': float
       - 'refusal_accuracy': float
       - 'hit_at_5': float
       - 'details': list[dict]（逐题记录 id, refusal_ok, citation_ok, hit_at_5）
    """
    raise NotImplementedError("实现评测函数 evaluate")


def ablation(
    configs: dict[str, Callable],
    cases: list[dict],
    evaluate_fn: Callable[[list[dict], Callable], dict],
    **kwargs,
) -> list[dict]:
    """多配置消融实验对比：
    - configs 为配置名称到 answer_fn 的映射；
    - 每个配置生成一行结果字典：
      {"name": str, "citation_accuracy": float, "refusal_accuracy": float, "hit_at_5": float, "avg_latency_ms": float}；
    - avg_latency_ms 默认统计用例列表中记录的 'latency_ms' 假时钟字段并计算算术平均值（若缺失则缺省为 0.0）；
    - 若传入内部参数 `_measure_real_latency=True`（参考流水线使用），则切换为实测调用 answer_fn 的物理毫秒耗时。
    """
    raise NotImplementedError("实现消融实验 ablation")


def gate_thresholds(report: dict) -> list[str]:
    """门禁阈值检查：
    - citation_accuracy < 0.9 记未达标；
    - refusal_accuracy < 0.9 记未达标；
    - hit_at_5 < 0.8 记未达标；
    - 返回全部未达标项说明列表。
    """
    raise NotImplementedError("实现门禁阈值检查 gate_thresholds")


def validate_cases(path: str | Path) -> list[dict]:
    """校验评测集文件并返回样本列表：
    - 读取 JSON 文件，必须为列表且长度 >= 30；
    - 校验每条用例必须包含 id, question, should_refuse, gold_sources 字段且 id 唯一；
    - 必须包含至少一条拒答用例 (should_refuse=True) 与 Prompt 注入测试用例；
    - 校验失败抛 ValueError。
    """
    raise NotImplementedError("实现评测集校验 validate_cases")
