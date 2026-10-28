"""1.10 Pydantic AI Gate · 自动化检查脚本。

总计 6 项断言检查，覆盖：
1. 合法模型输出转换为领域 DTO（test_1_valid_output_to_dto）
2. 枚举外非法值通过 ModelRetry 触发模型重试纠偏并成功（test_2_model_retry_on_invalid_enum）
3. 持续非法或模型异常时回退到规则兜底（test_3_consecutive_invalid_fallback）
4. 租户身份与权限边界严格取自 deps（test_4_tenant_identity_from_deps）
5. check_order 工具通过 RunContext 访问注入依赖（test_5_check_order_via_run_context）
6. 订单不存在时 order_id 置 None 并记录 order_not_found（test_6_non_existent_order_sanitized）

运行方式：
    python gate_check_pai.py
    或：python gate_check_pai.py --module path/to/impl.py
退出码：全部通过为 0，任一失败为 1。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pydantic_ai.models
# 强行封锁网络请求，遵守离线底线
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False

from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import FunctionModel  # noqa: E402

HERE = Path(__file__).resolve().parent
CHAPTER_DIR = HERE.parent
if str(CHAPTER_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER_DIR))

# 导入领域契约与依赖类型（严格从 starter.py 导入，不依赖参考实现）
try:
    import gate.starter as _starter_mod
except ImportError:
    import starter as _starter_mod

sys.modules["starter"] = _starter_mod
sys.modules["gate.starter"] = _starter_mod

FeatureDeps = _starter_mod.FeatureDeps
TicketInsight = _starter_mod.TicketInsight


def load_module(path: Path):
    if not path.exists():
        raise SystemExit(f"找不到待测模块：{path}")
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("pai_candidate", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pai_candidate"] = module
    spec.loader.exec_module(module)
    return module


class Gate:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, module_path: Path, gate_name: str) -> int:
        passed = sum(row["ok"] for row in self.rows)
        total = len(self.rows)
        for row in self.rows:
            mark = "PASS" if row["ok"] else "FAIL"
            print(f"[{mark}] {row['name']}" + ("" if row["ok"] else f"  <- {row['error']}"))
        print(f"\n{passed}/{total} passed")
        if passed != total:
            print("gate 未通过：先修 FAIL 项，不要打开参考实现。")
        out = {
            "gate": gate_name,
            "module": str(module_path),
            "passed": passed,
            "total": total,
            "ok": passed == total,
            "checks": self.rows,
        }
        (HERE / "gate_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if passed == total else 1


def test_1_valid_output_to_dto(mod: Any) -> None:
    def model_fn(messages: list, info: Any) -> ModelResponse:
        tool_name = info.output_tools[0].name
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name,
                    {
                        "category": "refund",
                        "priority": "urgent",
                        "order_id": "ORD-123456",
                        "amount": 199.0,
                    },
                )
            ]
        )

    model = FunctionModel(model_fn)
    agent = mod.build_agent(model)

    deps = FeatureDeps(
        tenant_id="tenant_alpha",
        user_id="user_001",
        chat_fn=lambda msgs: None,  # type: ignore
        order_exists=lambda tid, oid: tid == "tenant_alpha" and oid == "ORD-123456",
    )

    insight = mod.extract_with_agent(
        agent, "请处理订单 ORD-123456 的 199 元退款请求", deps
    )
    assert isinstance(insight, TicketInsight) or type(insight).__name__ == "TicketInsight", f"应返回 TicketInsight，实际为 {type(insight)}"
    assert insight.category == "refund"
    assert insight.priority == "urgent"
    assert insight.order_id == "ORD-123456"
    assert insight.amount == 199.0
    assert insight.source == "llm"


def test_2_model_retry_on_invalid_enum(mod: Any) -> None:
    attempt_count = 0

    def model_fn(messages: list, info: Any) -> ModelResponse:
        nonlocal attempt_count
        attempt_count += 1
        tool_name = info.output_tools[0].name
        if attempt_count == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name,
                        {
                            "category": "invalid_category_xyz",
                            "priority": "low",
                        },
                    )
                ]
            )
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name,
                    {
                        "category": "technical",
                        "priority": "medium",
                    },
                )
            ]
        )

    model = FunctionModel(model_fn)
    agent = mod.build_agent(model)

    deps = FeatureDeps(
        tenant_id="tenant_alpha",
        user_id="user_001",
        chat_fn=lambda msgs: None,  # type: ignore
        order_exists=lambda tid, oid: False,
    )

    insight = mod.extract_with_agent(agent, "系统崩溃报错 500", deps)
    assert attempt_count >= 2, f"应触发至少 1 次重试纠偏，实际调用次数: {attempt_count}"
    assert insight.category == "technical"
    assert insight.priority == "medium"
    assert insight.source == "llm"


def test_3_consecutive_invalid_fallback(mod: Any) -> None:
    def model_fn(messages: list, info: Any) -> ModelResponse:
        tool_name = info.output_tools[0].name
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name,
                    {
                        "category": "bad_cat_forever",
                        "priority": "low",
                    },
                )
            ]
        )

    model = FunctionModel(model_fn)
    agent = mod.build_agent(model)

    deps = FeatureDeps(
        tenant_id="tenant_alpha",
        user_id="user_001",
        chat_fn=lambda msgs: None,  # type: ignore
        order_exists=lambda tid, oid: False,
    )

    insight = mod.extract_with_agent(agent, "申请退货退款，请处理", deps)
    assert insight.source == "rules", f"重试耗尽后应走 rules 兜底，实际 source: {insight.source}"
    assert insight.needs_human is True, "退款类走规则兜底时必须 needs_human=True"


def test_4_tenant_identity_from_deps(mod: Any) -> None:
    queried_tenants: list[str] = []

    def tracking_order_exists(tid: str, oid: str) -> bool:
        queried_tenants.append(tid)
        return True

    def model_fn(messages: list, info: Any) -> ModelResponse:
        tool_name = info.output_tools[0].name
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name,
                    {
                        "category": "shipping",
                        "priority": "low",
                        "order_id": "ORD-654321",
                    },
                )
            ]
        )

    model = FunctionModel(model_fn)
    agent = mod.build_agent(model)

    deps = FeatureDeps(
        tenant_id="strict_tenant_999",
        user_id="user_abc",
        chat_fn=lambda msgs: None,  # type: ignore
        order_exists=tracking_order_exists,
    )

    insight = mod.extract_with_agent(agent, "包裹到哪里了 ORD-654321", deps)
    assert insight.order_id == "ORD-654321"
    assert "strict_tenant_999" in queried_tenants, "订单校验必须使用 deps 中注入的租户"


def test_5_check_order_via_run_context(mod: Any) -> None:
    checked_calls: list[tuple[str, str]] = []

    def mock_order_exists(tid: str, oid: str) -> bool:
        checked_calls.append((tid, oid))
        return oid == "ORD-112233"

    def model_fn(messages: list, info: Any) -> ModelResponse:
        has_tool_return = any(
            isinstance(p, ToolReturnPart) and p.tool_name == "check_order"
            for m in messages
            for p in getattr(m, "parts", [])
        )
        if not has_tool_return:
            return ModelResponse(
                parts=[ToolCallPart("check_order", {"order_id": "ORD-112233"})]
            )
        tool_name = info.output_tools[0].name
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name,
                    {
                        "category": "account",
                        "priority": "low",
                        "order_id": "ORD-112233",
                    },
                )
            ]
        )

    model = FunctionModel(model_fn)
    agent = mod.build_agent(model)

    deps = FeatureDeps(
        tenant_id="tenant_ctx_test",
        user_id="user_ctx",
        chat_fn=lambda msgs: None,  # type: ignore
        order_exists=mock_order_exists,
    )

    insight = mod.extract_with_agent(agent, "查下订单 ORD-112233", deps)
    assert ("tenant_ctx_test", "ORD-112233") in checked_calls, f"check_order 参数不匹配：{checked_calls}"
    assert insight.order_id == "ORD-112233"


def test_6_non_existent_order_sanitized(mod: Any) -> None:
    def model_fn(messages: list, info: Any) -> ModelResponse:
        tool_name = info.output_tools[0].name
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name,
                    {
                        "category": "shipping",
                        "priority": "low",
                        "order_id": "ORD-999999",
                        "amount": None,
                    },
                )
            ]
        )

    model = FunctionModel(model_fn)
    agent = mod.build_agent(model)

    deps = FeatureDeps(
        tenant_id="tenant_alpha",
        user_id="user_001",
        chat_fn=lambda msgs: None,  # type: ignore
        order_exists=lambda tid, oid: False,
    )

    insight = mod.extract_with_agent(agent, "包裹到哪了 ORD-999999", deps)
    assert insight.order_id is None, f"未查到的订单号应置为 None，实际为: {insight.order_id}"
    assert "order_not_found" in insight.reasons, f"未查到订单应在 reasons 中包含 order_not_found: {insight.reasons}"


def main() -> int:
    parser = argparse.ArgumentParser(description="1.10 Pydantic AI Gate 检查")
    parser.add_argument("--module", default=str(HERE / "starter_pai.py"), help="待测试模块路径")
    parser.add_argument("positional", nargs="?", default=None, help="位置参数（兼容旧调用）")
    args = parser.parse_args()

    target_path = Path(args.positional or args.module).resolve()
    core = load_module(target_path)
    gate = Gate()

    gate.check("1. 合法输出转为 DTO", lambda: test_1_valid_output_to_dto(core))
    gate.check("2. 枚举外值触发 ModelRetry 并在重试后成功", lambda: test_2_model_retry_on_invalid_enum(core))
    gate.check("3. 连续非法或异常回退至规则降级（fail-closed）", lambda: test_3_consecutive_invalid_fallback(core))
    gate.check("4. 租户身份与校验边界严格取自 deps", lambda: test_4_tenant_identity_from_deps(core))
    gate.check("5. check_order 工具经由 RunContext 正确调用", lambda: test_5_check_order_via_run_context(core))
    gate.check("6. 订单不存在时 order_id 置 None 并记录 order_not_found", lambda: test_6_non_existent_order_sanitized(core))

    return gate.report(target_path, "L1.10-embedded-feature-pai")


if __name__ == "__main__":
    sys.exit(main())
