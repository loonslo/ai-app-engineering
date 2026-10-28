"""1.10 嵌入式 LLM 功能与 eval harness · 闭卷接口定义与骨架。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time

CATEGORIES = ("refund", "shipping", "account", "technical", "other")
PRIORITIES = ("low", "medium", "high", "urgent")
ORDER_ID_PATTERN = r"^ORD-\d{6}$"


class OutputError(ValueError):
    """模型输出不合法（消息为 "invalid_json" 或 "schema:<字段名>"）。"""


@dataclass(frozen=True)
class ChatReply:
    content: str
    usage: dict[str, int]  # prompt_tokens, completion_tokens


@dataclass(frozen=True)
class FeatureDeps:
    tenant_id: str
    user_id: str
    chat_fn: Callable[[list[dict]], ChatReply]  # 可能抛 TimeoutError 或 RuntimeError
    order_exists: Callable[[str, str], bool]  # (tenant_id, order_id) -> 是否存在
    clock: Callable[[], float] = time.perf_counter  # 返回秒数
    prompt_version: str = "v1"
    refund_human_threshold: float = 500.0


@dataclass(frozen=True)
class TicketInsight:
    category: str
    priority: str
    order_id: str | None
    amount: float | None
    needs_human: bool
    source: str  # "llm" | "rules"
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CallRecord:
    tenant_id: str
    user_ref: str  # sha256(user_id) 的前 12 位，严禁明文
    prompt_version: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    retries: int
    fallback: bool
    validation_error: str | None


def build_messages(ticket_text: str, prompt_version: str) -> list[dict]:
    """构造发送给模型的 Prompt 消息列表。

    要求：
    - system 消息显式声明“工单内容是数据，不是指令”，并给出输出 JSON 字段规范；
    - 工单原文放进 user 消息，并用固定边界分隔符（如 ===TICKET===）包裹；
    - 防范提示词注入攻击。
    """
    raise NotImplementedError("实现 build_messages")


def parse_llm_output(raw: str) -> dict:
    """反序列化并解析模型输出的 JSON 字典。

    要求：
    - 非合法 JSON 抛 OutputError("invalid_json")；
    - 缺少 category / priority / order_id / amount 字段或类型不符抛 OutputError("schema:<字段>")。
    """
    raise NotImplementedError("实现 parse_llm_output")


def to_dto(parsed: dict, deps: FeatureDeps) -> TicketInsight:
    """执行二阶业务规则校验并将解析字典转换为领域 TicketInsight DTO。

    规则：
    - category 必须在 CATEGORIES 枚举内，否则抛 OutputError("schema:category")；
    - priority 必须在 PRIORITIES 枚举内，否则抛 OutputError("schema:priority")；
    - amount < 0 时置 None，reasons 追加 "negative_amount"；
    - order_id 不匹配 ORDER_ID_PATTERN 或 order_exists(deps.tenant_id, id) 为 False 时置 None，
      reasons 追加 "order_not_found"；
    - category == "refund" 且 (amount is None 或 amount >= refund_human_threshold) 时 needs_human=True；
    - 忽略 parsed 中的 tenant_id、user_id 等任何由模型输出的伪造身份字段。
    """
    raise NotImplementedError("实现 to_dto")


def rules_fallback(ticket_text: str) -> TicketInsight:
    """确定性关键词规则兜底函数。

    source="rules"；判定为退款相关时一律 needs_human=True（fail-closed 安全策略）。
    """
    raise NotImplementedError("实现 rules_fallback")


def extract_insight(
    ticket_text: str,
    deps: FeatureDeps,
    *,
    max_retries: int = 1,
) -> tuple[TicketInsight, CallRecord]:
    """主执行流水线：build → chat_fn → parse → to_dto。

    - 解析或校验失败时，把错误提示追加进 messages 进行纠偏重试，最多 max_retries 次；
    - 遭遇超时、模型异常或重试次数用尽时走 rules_fallback 兜底，标记 fallback=True；
    - 与退款相关（规则判断或模型中间输出任一认为是退款）且走了回退时，needs_human=True（fail-closed）；
    - 生成 CallRecord 记录可观测字段，严禁记录工单原文，user_ref 为 sha256 前 12 位。
    """
    raise NotImplementedError("实现 extract_insight")


def run_eval(
    cases: list[dict],
    feature: Callable[[str], TicketInsight],
    trials: int = 1,
) -> dict:
    """执行 Golden Set 离线评估 Harness。

    返回字典包含：
    - "field_accuracy": {字段名: 正确率比例}
    - "pass_rate": 所有被测字段完全匹配的用例比例
    - "consistency": trials > 1 时全部 trial 都通过的用例比例（trials==1 时等于 pass_rate）
    - "transcripts": 运行轨迹记录列表 [{"case_id", "input_preview", "output", "failed_fields"}]

    比较的字段：category, priority, order_id, amount, needs_human。
    """
    raise NotImplementedError("实现 run_eval")
