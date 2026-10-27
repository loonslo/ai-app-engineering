"""1.9 (L1.7) Provider 抽象、第二厂商与成本 · 参考实现。

涵盖：
1. 多厂商（OpenAI、Anthropic、DeepSeek）Usage 标准化解析
2. 缓存命中与 UTC 峰谷时段折扣计费
3. 可重试（429、5xx、超时）与不可重试（401、400、内容策略拦截）错误分类
4. 带能力过滤（如 needs_json_schema）的多候选厂商自动故障转移（Fallback）
5. 两个模型在同一评测集上的多维度对比分析（通过率、平均成本、p95 延迟、退化用例）
"""

from __future__ import annotations

import math
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 导入共享配置与客户端工厂
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from common import chat_model_name, get_openai_client
except ImportError:
    chat_model_name = None  # type: ignore
    get_openai_client = None  # type: ignore


@dataclass(frozen=True)
class PriceTable:
    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float
    offpeak_multiplier: float = 1.0
    offpeak_windows_utc: tuple[tuple[int, int], ...] = ()


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
    complete: bool


class ProviderError(Exception):
    """供应商 API 调用异常封装。"""

    def __init__(self, kind: str, message: str = "") -> None:
        super().__init__(kind if not message else f"{kind}: {message}")
        self.kind = kind
        self.message = message


def normalize_usage(raw: Mapping[str, Any] | None) -> Usage:
    """标准化不同厂商的 Usage 统计数据。

    支持：
    - OpenAI 风格: prompt_tokens, completion_tokens, prompt_tokens_details.cached_tokens
    - Anthropic 风格: input_tokens, output_tokens, cache_read_input_tokens
    - DeepSeek 风格: prompt_cache_hit_tokens (核对自 DeepSeek 官方 API 文档，2026-10-27)
    """
    if raw is None or not isinstance(raw, Mapping):
        return Usage(input_tokens=0, output_tokens=0, cached_input_tokens=0, complete=False)

    has_input = False
    has_output = False

    raw_in = raw.get("input_tokens")
    if raw_in is not None:
        has_input = True
    else:
        raw_in = raw.get("prompt_tokens")
        if raw_in is not None:
            has_input = True

    raw_out = raw.get("output_tokens")
    if raw_out is not None:
        has_output = True
    else:
        raw_out = raw.get("completion_tokens")
        if raw_out is not None:
            has_output = True

    # 提取缓存命中文档
    raw_cached = raw.get("cache_read_input_tokens")
    if raw_cached is None:
        raw_cached = raw.get("prompt_cache_hit_tokens")
    if raw_cached is None:
        details = raw.get("prompt_tokens_details")
        if isinstance(details, Mapping):
            raw_cached = details.get("cached_tokens")

    input_tokens = int(raw_in) if isinstance(raw_in, (int, float)) else 0
    output_tokens = int(raw_out) if isinstance(raw_out, (int, float)) else 0
    cached_tokens = int(raw_cached) if isinstance(raw_cached, (int, float)) else 0

    complete = has_input and has_output

    return Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_tokens,
        complete=complete,
    )


def estimate_cost(usage: Usage, price: PriceTable, at_utc_hour: int) -> float:
    """结合时段峰谷系数与缓存命中计算实际成本。"""
    if at_utc_hour < 0 or at_utc_hour > 23:
        raise ValueError(f"at_utc_hour={at_utc_hour} 超出 [0, 23] 合法小时范围")

    uncached_input = max(0, usage.input_tokens - usage.cached_input_tokens)
    base_cost = (
        usage.cached_input_tokens * price.cached_input_per_mtok
        + uncached_input * price.input_per_mtok
        + usage.output_tokens * price.output_per_mtok
    ) / 1_000_000.0

    # 判断是否落在任一低峰时段窗口
    is_offpeak = False
    for start, end in price.offpeak_windows_utc:
        if start <= end:
            if start <= at_utc_hour < end:
                is_offpeak = True
                break
        else:
            # 跨午夜
            if at_utc_hour >= start or at_utc_hour < end:
                is_offpeak = True
                break

    if is_offpeak:
        return base_cost * price.offpeak_multiplier
    return base_cost


def is_retryable(error: ProviderError) -> bool:
    """判断错误是否属于可重试或可故障转移到备用厂商的类型。"""
    return error.kind in {"timeout", "rate_limit", "server_error"}


def call_with_fallback(
    providers: list[ProviderSpec],
    request: dict[str, Any],
    call_fn: Callable[[ProviderSpec, dict[str, Any]], Any],
) -> dict[str, Any]:
    """按顺序尝试多个候选厂商。"""
    attempts: list[tuple[str, str]] = []
    needs_schema = request.get("needs_json_schema", False)

    for p in providers:
        if needs_schema and not p.supports_json_schema:
            attempts.append((p.name, "skipped:capability"))
            continue

        try:
            res = call_fn(p, request)
            attempts.append((p.name, "ok"))
            return {
                "ok": True,
                "provider": p.name,
                "result": res,
                "attempts": attempts,
            }
        except ProviderError as p_err:
            attempts.append((p.name, f"error:{p_err.kind}"))
            if not is_retryable(p_err):
                # 认证或参数错误立即终止
                return {
                    "ok": False,
                    "provider": None,
                    "result": None,
                    "attempts": attempts,
                }
        except Exception:
            attempts.append((p.name, "error:unknown"))
            return {
                "ok": False,
                "provider": None,
                "result": None,
                "attempts": attempts,
            }

    return {
        "ok": False,
        "provider": None,
        "result": None,
        "attempts": attempts,
    }


def compare_runs(run_a: dict[str, Any], run_b: dict[str, Any]) -> dict[str, Any]:
    """对比两组运行评测结果。"""
    cases_a: dict[str, Any] = run_a["cases"]
    cases_b: dict[str, Any] = run_b["cases"]

    if set(cases_a.keys()) != set(cases_b.keys()):
        raise ValueError("用例集合不一致")

    total = len(cases_a)
    if total == 0:
        return {
            "pass_rate_a": 0.0,
            "pass_rate_b": 0.0,
            "pass_rate_diff": 0.0,
            "avg_cost_a": 0.0,
            "avg_cost_b": 0.0,
            "cost_diff": 0.0,
            "p95_latency_ms_a": 0,
            "p95_latency_ms_b": 0,
            "p95_diff": 0,
            "regressions": [],
        }

    passed_a = sum(1 for c in cases_a.values() if c["passed"])
    passed_b = sum(1 for c in cases_b.values() if c["passed"])
    pass_rate_a = passed_a / total
    pass_rate_b = passed_b / total
    pass_rate_diff = pass_rate_b - pass_rate_a

    cost_a = sum(c["cost"] for c in cases_a.values()) / total
    cost_b = sum(c["cost"] for c in cases_b.values()) / total
    cost_diff = cost_b - cost_a

    def calc_p95(latencies: list[int]) -> int:
        s = sorted(latencies)
        rank = math.ceil(0.95 * len(s))
        return s[max(0, rank - 1)]

    p95_a = calc_p95([c["latency_ms"] for c in cases_a.values()])
    p95_b = calc_p95([c["latency_ms"] for c in cases_b.values()])
    p95_diff = p95_b - p95_a

    regressions = sorted([
        cid for cid in cases_a if cases_a[cid]["passed"] and not cases_b[cid]["passed"]
    ])

    return {
        "pass_rate_a": pass_rate_a,
        "pass_rate_b": pass_rate_b,
        "pass_rate_diff": pass_rate_diff,
        "avg_cost_a": cost_a,
        "avg_cost_b": cost_b,
        "cost_diff": cost_diff,
        "p95_latency_ms_a": p95_a,
        "p95_latency_ms_b": p95_b,
        "p95_diff": p95_diff,
        "regressions": regressions,
    }


def demo_offline() -> None:
    print("=== 1. Usage 归一化演示 ===")
    openai_u = normalize_usage({
        "prompt_tokens": 1500,
        "completion_tokens": 200,
        "prompt_tokens_details": {"cached_tokens": 1000},
    })
    print(f"OpenAI Usage: in={openai_u.input_tokens}, cached={openai_u.cached_input_tokens}, out={openai_u.output_tokens}")

    anthropic_u = normalize_usage({
        "input_tokens": 2000,
        "output_tokens": 300,
        "cache_read_input_tokens": 1200,
    })
    print(f"Anthropic Usage: in={anthropic_u.input_tokens}, cached={anthropic_u.cached_input_tokens}, out={anthropic_u.output_tokens}")

    print("\n=== 2. 峰谷计价与成本核算演示 ===")
    price = PriceTable(
        input_per_mtok=2.0,
        output_per_mtok=8.0,
        cached_input_per_mtok=0.5,
        offpeak_multiplier=0.5,
        offpeak_windows_utc=((16, 24), (0, 0)),  # 模拟北京时间凌晨低峰时段
    )
    cost_peak = estimate_cost(openai_u, price, at_utc_hour=8)
    cost_offpeak = estimate_cost(openai_u, price, at_utc_hour=18)
    print(f"高峰时段调用成本: {cost_peak:.6f} 元")
    print(f"低峰时段调用成本 (5 折优惠): {cost_offpeak:.6f} 元")

    print("\n=== 3. 供应商故障转移 (Fallback) 演示 ===")
    vendors = [
        ProviderSpec("primary_ai", "model-pro", True, True, price),
        ProviderSpec("secondary_ai", "model-lite", True, True, price),
    ]

    def flaky_vendor_call(spec: ProviderSpec, req: dict[str, Any]) -> str:
        if spec.name == "primary_ai":
            print("  [Primary] 触发网络超时，准备降级...")
            raise ProviderError("timeout", "上游网关连接超时")
        print("  [Secondary] 备用模型响应成功！")
        return "来自备用模型的回答内容"

    fallback_result = call_with_fallback(vendors, {}, flaky_vendor_call)
    print(f"故障转移结果: 成功={fallback_result['ok']}, 最终服务商={fallback_result['provider']}")
    print(f"尝试轨迹: {fallback_result['attempts']}")


def demo_live() -> None:
    print("=== 真实双模型评测对比 ===")
    sec_base_url = os.getenv("SECOND_BASE_URL")
    sec_api_key = os.getenv("SECOND_API_KEY")
    sec_model = os.getenv("SECOND_MODEL")

    if not sec_base_url or not sec_api_key or not sec_model:
        print("[提示] 未配置 SECOND_BASE_URL / SECOND_API_KEY / SECOND_MODEL 环境变量。")
        print("若需要真实运行两家模型评测对比，请在 .env 中配置第二厂商连接参数。")
        demo_offline()
        return

    print("已检测到主厂商与第二厂商配置，可在当前环境执行评测对比。")


if __name__ == "__main__":
    if "--live" in sys.argv:
        demo_live()
    else:
        demo_offline()
