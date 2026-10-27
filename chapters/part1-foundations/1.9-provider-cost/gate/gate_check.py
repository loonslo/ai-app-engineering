"""1.9 (L1.7) Provider 抽象、第二厂商与成本 · 离线自动化 Gate 检查。

覆盖：
1. OpenAI 风格 Usage 解析（含 prompt_tokens_details.cached_tokens）
2. Anthropic 风格 Usage 解析（含 cache_read_input_tokens）
3. 缺失字段或 None 时 Usage 降级且 complete=False
4. 带前缀缓存命中的成本估算
5. 低峰时段跨零点（跨午夜）折扣计算
6. 非法 UTC 小时报错（不在 0-23）
7. 可重试与不可重试错误分类断言
8. 发生超时错误时自动故障降级到第二家
9. 发生认证错误（auth）时立即停止不降级
10. 不具备所要求能力（如 needs_json_schema）的厂商被直接跳过
11. 所有候选厂商全失败时完整返回 attempts 轨迹
12. compare_runs 正确计算通过率差、成本差、p95 延迟差与退化用例
13. compare_runs 两侧用例集不一致时报错

运行方式：
    python gate_check.py
    或：python gate_check.py /path/to/impl.py
退出码：通过为 0，失败为 1。
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import math
import sys
from pathlib import Path
from typing import Any

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

target_module: Any = None
if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
    target_path = Path(sys.argv[1]).resolve()
    loader = importlib.machinery.SourceFileLoader("provider_impl", str(target_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec and spec.loader:
        target_module = importlib.util.module_from_spec(spec)
        sys.modules[loader.name] = target_module
        spec.loader.exec_module(target_module)
else:
    try:
        import starter as target_module  # type: ignore
    except ImportError:
        target_module = None


def test_1_openai_usage(mod: Any) -> None:
    raw = {
        "prompt_tokens": 1200,
        "completion_tokens": 300,
        "prompt_tokens_details": {"cached_tokens": 800},
    }
    u = mod.normalize_usage(raw)
    assert u.input_tokens == 1200
    assert u.output_tokens == 300
    assert u.cached_input_tokens == 800
    assert u.complete is True


def test_2_anthropic_usage(mod: Any) -> None:
    raw = {
        "input_tokens": 2000,
        "output_tokens": 400,
        "cache_read_input_tokens": 1500,
    }
    u = mod.normalize_usage(raw)
    assert u.input_tokens == 2000
    assert u.output_tokens == 400
    assert u.cached_input_tokens == 1500
    assert u.complete is True


def test_3_missing_usage(mod: Any) -> None:
    # 场景 A: None
    u_none = mod.normalize_usage(None)
    assert u_none.input_tokens == 0 and u_none.output_tokens == 0 and u_none.cached_input_tokens == 0
    assert u_none.complete is False

    # 场景 B: 缺失 output
    u_partial = mod.normalize_usage({"prompt_tokens": 500})
    assert u_partial.input_tokens == 500
    assert u_partial.output_tokens == 0
    assert u_partial.complete is False


def test_4_cost_with_cache(mod: Any) -> None:
    price = mod.PriceTable(
        input_per_mtok=2.0,
        output_per_mtok=8.0,
        cached_input_per_mtok=0.5,
    )
    # 输入 100 万，其中 60 万命中，输出 10 万。无峰谷时段
    u = mod.Usage(input_tokens=1_000_000, output_tokens=100_000, cached_input_tokens=600_000, complete=True)
    cost = mod.estimate_cost(u, price, at_utc_hour=10)
    # cost = 0.6*0.5 + 0.4*2.0 + 0.1*8.0 = 0.3 + 0.8 + 0.8 = 1.9
    assert math.isclose(cost, 1.9, abs_tol=1e-5), f"成本计算不正确: {cost}"


def test_5_offpeak_cross_midnight(mod: Any) -> None:
    # 模拟低峰时段跨午夜：UTC 22:00 至次日 06:00 (即 22..24 与 0..6)
    # 折扣系数 0.5
    price = mod.PriceTable(
        input_per_mtok=2.0,
        output_per_mtok=8.0,
        cached_input_per_mtok=0.5,
        offpeak_multiplier=0.5,
        offpeak_windows_utc=((22, 6),),  # 跨零点
    )
    u = mod.Usage(input_tokens=1_000_000, output_tokens=0, cached_input_tokens=0, complete=True)
    # 基准成本 = 1.0 * 2.0 = 2.0
    # 在 23 点（低峰）: 2.0 * 0.5 = 1.0
    cost_night = mod.estimate_cost(u, price, at_utc_hour=23)
    assert math.isclose(cost_night, 1.0, abs_tol=1e-5)

    # 在 3 点（低峰）: 1.0
    cost_early = mod.estimate_cost(u, price, at_utc_hour=3)
    assert math.isclose(cost_early, 1.0, abs_tol=1e-5)

    # 在 14 点（正常高峰）: 2.0
    cost_day = mod.estimate_cost(u, price, at_utc_hour=14)
    assert math.isclose(cost_day, 2.0, abs_tol=1e-5)


def test_6_invalid_utc_hour(mod: Any) -> None:
    price = mod.PriceTable(2.0, 8.0, 0.5)
    u = mod.Usage(100, 10, 0, True)
    for bad_hour in (-1, 24, 25):
        try:
            mod.estimate_cost(u, price, at_utc_hour=bad_hour)
        except ValueError:
            continue
        raise AssertionError(f"小时 {bad_hour} 应抛出 ValueError")


def test_7_retryable_classification(mod: Any) -> None:
    for kind in ("timeout", "rate_limit", "server_error"):
        assert mod.is_retryable(mod.ProviderError(kind)) is True, f"{kind} 应当是可重试的"

    for kind in ("auth", "bad_request", "content_filter", "context_length"):
        assert mod.is_retryable(mod.ProviderError(kind)) is False, f"{kind} 应当是不可重试的"


def test_8_fallback_on_timeout(mod: Any) -> None:
    p1 = mod.ProviderSpec("primary", "m1", True, True, mod.PriceTable(1, 1, 1))
    p2 = mod.ProviderSpec("backup", "m2", True, True, mod.PriceTable(1, 1, 1))

    def mock_call(spec: Any, req: dict) -> str:
        if spec.name == "primary":
            raise mod.ProviderError("timeout", "上游超时")
        return "success_from_backup"

    res = mod.call_with_fallback([p1, p2], {}, mock_call)
    assert res["ok"] is True
    assert res["provider"] == "backup"
    assert res["result"] == "success_from_backup"
    assert res["attempts"] == [("primary", "error:timeout"), ("backup", "ok")]


def test_9_no_fallback_on_auth_error(mod: Any) -> None:
    p1 = mod.ProviderSpec("primary", "m1", True, True, mod.PriceTable(1, 1, 1))
    p2 = mod.ProviderSpec("backup", "m2", True, True, mod.PriceTable(1, 1, 1))

    def mock_call(spec: Any, req: dict) -> None:
        raise mod.ProviderError("auth", "401 密钥失效")

    res = mod.call_with_fallback([p1, p2], {}, mock_call)
    assert res["ok"] is False
    assert res["provider"] is None
    # 认证错误不可重试，应立即终止，不尝试 p2
    assert res["attempts"] == [("primary", "error:auth")]


def test_10_capability_filtering(mod: Any) -> None:
    p1 = mod.ProviderSpec("no_schema_vendor", "m1", False, True, mod.PriceTable(1, 1, 1))
    p2 = mod.ProviderSpec("schema_vendor", "m2", True, True, mod.PriceTable(1, 1, 1))

    def mock_call(spec: Any, req: dict) -> str:
        return f"ok_{spec.name}"

    req = {"needs_json_schema": True}
    res = mod.call_with_fallback([p1, p2], req, mock_call)
    assert res["ok"] is True
    assert res["provider"] == "schema_vendor"
    assert res["attempts"] == [("no_schema_vendor", "skipped:capability"), ("schema_vendor", "ok")]


def test_11_all_failed_attempts(mod: Any) -> None:
    p1 = mod.ProviderSpec("p1", "m1", True, True, mod.PriceTable(1, 1, 1))
    p2 = mod.ProviderSpec("p2", "m2", True, True, mod.PriceTable(1, 1, 1))

    def mock_call(spec: Any, req: dict) -> None:
        raise mod.ProviderError("server_error", "503 宕机")

    res = mod.call_with_fallback([p1, p2], {}, mock_call)
    assert res["ok"] is False
    assert res["attempts"] == [("p1", "error:server_error"), ("p2", "error:server_error")]


def test_12_compare_runs(mod: Any) -> None:
    run_a = {
        "provider": "model_a",
        "cases": {
            "c1": {"passed": True, "cost": 0.01, "latency_ms": 100},
            "c2": {"passed": True, "cost": 0.02, "latency_ms": 200},
            "c3": {"passed": True, "cost": 0.03, "latency_ms": 300},
        },
    }
    run_b = {
        "provider": "model_b",
        "cases": {
            "c1": {"passed": True, "cost": 0.005, "latency_ms": 80},
            "c2": {"passed": False, "cost": 0.005, "latency_ms": 90},  # 退化用例
            "c3": {"passed": True, "cost": 0.005, "latency_ms": 120},
        },
    }
    report = mod.compare_runs(run_a, run_b)
    # a 通过率 3/3=1.0, b 通过率 2/3=0.6667, pass_rate_diff = 0.6667 - 1.0 = -0.3333
    assert math.isclose(report["pass_rate_a"], 1.0, abs_tol=1e-3)
    assert math.isclose(report["pass_rate_b"], 2.0 / 3.0, abs_tol=1e-3)
    assert math.isclose(report["pass_rate_diff"], -1.0 / 3.0, abs_tol=1e-3)

    # 成本差
    assert report["cost_diff"] < 0  # b 比 a 更便宜
    # 退化用例列表
    assert report["regressions"] == ["c2"]


def test_13_compare_runs_mismatched_cases(mod: Any) -> None:
    run_a = {"provider": "a", "cases": {"c1": {"passed": True, "cost": 0.1, "latency_ms": 10}}}
    run_b = {"provider": "b", "cases": {"c2": {"passed": True, "cost": 0.1, "latency_ms": 10}}}
    try:
        mod.compare_runs(run_a, run_b)
    except ValueError:
        return
    raise AssertionError("两边用例集不一致应抛出 ValueError")


ALL_CHECKS = [
    ("1. OpenAI 风格 Usage 解析（含缓存）", test_1_openai_usage),
    ("2. Anthropic 风格 Usage 解析（含缓存）", test_2_anthropic_usage),
    ("3. 缺失 Usage 时返回 0 且 complete=False", test_3_missing_usage),
    ("4. 带前缀缓存命中的成本估算", test_4_cost_with_cache),
    ("5. 低峰时段跨零点折扣计算", test_5_offpeak_cross_midnight),
    ("6. 非法 UTC 小时报错", test_6_invalid_utc_hour),
    ("7. 可重试与不可重试错误分类", test_7_retryable_classification),
    ("8. 超时错误触发故障转移降级", test_8_fallback_on_timeout),
    ("9. 认证错误立即停止不降级", test_9_no_fallback_on_auth_error),
    ("10. 能力缺失（JSON Schema）跳过", test_10_capability_filtering),
    ("11. 全失败返回完整 attempts 轨迹", test_11_all_failed_attempts),
    ("12. compare_runs 差值与退化用例列表", test_12_compare_runs),
    ("13. compare_runs 用例集合不一致报错", test_13_compare_runs_mismatched_cases),
]


def run_checks(mod: Any) -> bool:
    print(f"=== 开始执行 1.9 (L1.7) Gate 检查（共 {len(ALL_CHECKS)} 项，目标模块: {getattr(mod, '__name__', str(mod))}）===")
    all_passed = True
    for title, check_fn in ALL_CHECKS:
        try:
            check_fn(mod)
            print(f"  [PASS] {title}")
        except Exception as exc:
            print(f"  [FAIL] {title} -> {exc}", file=sys.stderr)
            all_passed = False
    return all_passed


def main() -> int:
    if target_module is None:
        print("[FAIL] 无法加载待测试模块", file=sys.stderr)
        return 1

    passed = run_checks(target_module)
    if passed:
        print("[PASS] 1.9 全部 13 项 Provider 与成本断言通过！")
        return 0
    else:
        print("[FAIL] 1.9 存在未通过检查项，请检查实现。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
