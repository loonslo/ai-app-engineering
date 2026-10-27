"""1.10 Pydantic AI Gate · 自动化检查脚本。

总计 6 项断言检查，覆盖：
1. 合法模型输出转换为领域 DTO（test_1_valid_output_to_dto）
2. 枚举外非法值通过 ModelRetry 触发模型重试纠偏并成功（test_2_model_retry_on_invalid_enum）
3. 持续非法或模型异常时回退到规则兜底（test_3_consecutive_invalid_fallback）
4. 租户身份与权限边界严格取自 deps（test_4_tenant_identity_from_deps）
5. check_order 工具通过 RunContext 访问注入依赖（test_5_check_order_via_run_context）
6. 离线底线：设置 ALLOW_MODEL_REQUESTS=False，全量通过 FunctionModel 驱动（test_6_offline_enforcement）

运行方式：
    python gate_check_pai.py
    或传入具体实现模块路径：python gate_check_pai.py ../embedded_feature_pai.py
退出码：全部通过为 0，任一失败为 1。
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from typing import Any

# 强行封锁网络请求，遵守离线底线
import pydantic_ai.models
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False

from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import FunctionModel  # noqa: E402

CURRENT_DIR = Path(__file__).resolve().parent
CHAPTER_DIR = CURRENT_DIR.parent
if str(CHAPTER_DIR) not in sys.path:
    sys.path.insert(0, str(CHAPTER_DIR))

# 导入领域契约与依赖类型
from embedded_feature import FeatureDeps, TicketInsight  # noqa: E402

# 确定被测模块
target_module: Any = None
if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
    target_path = Path(sys.argv[1]).resolve()
    loader = importlib.machinery.SourceFileLoader("target_impl_pai", str(target_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec and spec.loader:
        target_module = importlib.util.module_from_spec(spec)
        sys.modules[loader.name] = target_module
        spec.loader.exec_module(target_module)
else:
    try:
        import starter_pai as target_module  # type: ignore
    except ImportError:
        target_module = None


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
    assert isinstance(insight, TicketInsight), f"应返回 TicketInsight，实际为 {type(insight)}"
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
            # 第一次返回非法 category
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
        # 第二次重试纠正为合法 category
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
        # 永远返回非法值，耗尽重试
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
    # 退款类规则必须 fail-closed
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
        # 第一轮：模型主动调用 check_order 工具
        has_tool_return = any(
            isinstance(p, ToolReturnPart) and p.tool_name == "check_order"
            for m in messages
            for p in getattr(m, "parts", [])
        )
        if not has_tool_return:
            return ModelResponse(
                parts=[ToolCallPart("check_order", {"order_id": "ORD-112233"})]
            )
        # 第二轮：获得工具返回值后输出最终结构
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


def test_6_offline_enforcement(mod: Any) -> None:
    assert pydantic_ai.models.ALLOW_MODEL_REQUESTS is False, (
        "离线底线失效：pydantic_ai.models.ALLOW_MODEL_REQUESTS 应为 False"
    )


ALL_CHECKS = [
    ("1. 合法输出转为 DTO", test_1_valid_output_to_dto),
    ("2. 枚举外值触发 ModelRetry 并在重试后成功", test_2_model_retry_on_invalid_enum),
    ("3. 连续非法或异常回退至规则降级（fail-closed）", test_3_consecutive_invalid_fallback),
    ("4. 租户身份与校验边界严格取自 deps", test_4_tenant_identity_from_deps),
    ("5. check_order 工具经由 RunContext 正确调用", test_5_check_order_via_run_context),
    ("6. 离线底线：ALLOW_MODEL_REQUESTS 为 False", test_6_offline_enforcement),
]


def main() -> int:
    mod_name = getattr(target_module, "__name__", str(target_module))
    print(f"=== 开始执行 1.10 Pydantic AI Gate 检查（共 {len(ALL_CHECKS)} 项，目标模块: {mod_name}）===")
    if target_module is None:
        print("[FAIL] 未能加载被测模块，请检查传入文件路径或 starter_pai.py。")
        return 1

    passed_count = 0
    failed_count = 0

    for title, test_fn in ALL_CHECKS:
        try:
            test_fn(target_module)
            print(f"  [PASS] {title}")
            passed_count += 1
        except Exception as e:
            print(f"  [FAIL] {title} -> {type(e).__name__}: {e}")
            failed_count += 1

    if failed_count == 0:
        print(f"[PASS] 1.10 Pydantic AI 全部 {passed_count} 项 Gate 检查通过！")
        return 0
    else:
        print(f"[FAIL] 1.10 Pydantic AI 存在 {failed_count} 项未通过，请检查实现。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
