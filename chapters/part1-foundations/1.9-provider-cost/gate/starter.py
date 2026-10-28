"""1.9 (L1.7) Provider 抽象、第二厂商与成本 · 闭卷接口定义与骨架。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PriceTable:
    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float
    offpeak_multiplier: float = 1.0
    offpeak_windows_utc: tuple[tuple[int, int], ...] = ()  # [start_hour, end_hour)，可跨零点，如 ( (16, 24), (0, 0.5) )


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    model: str
    supports_json_schema: bool
    supports_tools: bool
    price: PriceTable


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    complete: bool  # 原始 usage 是否齐全无缺失


class ProviderError(Exception):
    """供应商 API 调用异常封装。"""

    def __init__(self, kind: str, message: str = "") -> None:
        # kind ∈ {"timeout", "rate_limit", "server_error", "auth", "bad_request", "content_filter", "context_length"}
        super().__init__(kind if not message else f"{kind}: {message}")
        self.kind = kind
        self.message = message


def normalize_usage(raw: Mapping[str, Any] | None) -> Usage:
    """标准化不同厂商的 Usage 统计数据。

    支持：
    1. OpenAI / DeepSeek 风格：prompt_tokens、completion_tokens，
       缓存字段：prompt_tokens_details.cached_tokens 或 prompt_cache_hit_tokens；
    2. Anthropic 风格：input_tokens、output_tokens、cache_read_input_tokens。

    缺失时按 0 计，complete=False；None 直接返回全 0 且 complete=False。
    """
    raise NotImplementedError("实现 Usage 归一化")


def estimate_cost(usage: Usage, price: PriceTable, at_utc_hour: int) -> float:
    """结合时段峰谷系数与缓存命中计算实际成本。

    at_utc_hour 必须在 0–23 之间，否则抛 ValueError。
    若 at_utc_hour 落在任一 offpeak 窗口内，整笔成本乘以 offpeak_multiplier。
    """
    raise NotImplementedError("实现带时段与缓存的成本计算")


def is_retryable(error: ProviderError) -> bool:
    """判断错误是否属于可重试/可切换下一家厂商的暂时性故障。

    可重试: timeout, rate_limit, server_error
    不可重试: auth, bad_request, content_filter, context_length
    """
    raise NotImplementedError("实现错误重试研判")


def call_with_fallback(
    providers: list[ProviderSpec],
    request: dict[str, Any],
    call_fn: Callable[[ProviderSpec, dict[str, Any]], Any],
) -> dict[str, Any]:
    """按顺序尝试多个候选供应商，执行带能力过滤与故障转移的调用。

    - request["needs_json_schema"] 为真且厂商不支持时跳过，结果标记为 ("name", "skipped:capability")；
    - 遇到可重试错误，记录 ("name", "error:<kind>") 并换下一家；
    - 遇到不可重试错误，记录 ("name", "error:<kind>") 并立即终止；
    - 成功返回 {"ok": True, "provider": str, "result": Any, "attempts": list}；
    - 全部失败返回 {"ok": False, "provider": None, "result": None, "attempts": list}。
    """
    raise NotImplementedError("实现带故障转移的调用调度")


def compare_runs(run_a: dict[str, Any], run_b: dict[str, Any]) -> dict[str, Any]:
    """对比两组运行评测结果。

    run = {"provider": str, "cases": {case_id: {"passed": bool, "cost": float, "latency_ms": int}}}
    返回：
    - pass_rate_a, pass_rate_b, pass_rate_diff (b - a)
    - avg_cost_a, avg_cost_b, cost_diff (b - a)
    - p95_latency_ms_a, p95_latency_ms_b, p95_diff (b - a)（最近秩法）
    - regressions: a 通过而 b 失败的 case_id 列表

    两边用例集合不一致时抛 ValueError。
    """
    raise NotImplementedError
