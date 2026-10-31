"""L4.5：用真实 SDK 和脚本化 FunctionModel 检查订单客服，不联网、不读 .env。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import httpx
from openai import AsyncOpenAI
from pydantic_ai import Agent, models
from pydantic_ai.messages import ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider

models.ALLOW_MODEL_REQUESTS = False
HERE = Path(__file__).resolve().parent
ANSWER = {"reply": "已处理", "order_id": "A100", "action": "none", "needs_human": False}
REFUND = {"order_id": "A100", "amount": 20, "idempotency_key": "refund-1"}


def load_module(path: Path):
    if not path.exists():
        raise SystemExit(f"找不到实现文件：{path}")
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("candidate_l416", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class Gate:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, path: Path) -> int:
        passed = sum(row["ok"] for row in self.rows)
        for row in self.rows:
            print(f"[{'PASS' if row['ok'] else 'FAIL'}] {row['name']}" + (f" <- {row['error']}" if row["error"] else ""))
        print(f"\n{passed}/{len(self.rows)} passed")
        report = {"gate": "L4.5-pydantic-ai-agent", "module": str(path), "passed": passed,
                  "total": len(self.rows), "ok": passed == len(self.rows), "checks": self.rows}
        (HERE / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return int(not report["ok"])


def scripted(actions: list[tuple[str, dict]]) -> FunctionModel:
    """一条 SDK ModelResponse 算一次模型请求；最终答案也走 SDK 的输出工具。"""
    def respond(messages, info):
        index = sum(isinstance(message, ModelResponse) for message in messages)
        name, args = actions[min(index, len(actions) - 1)]
        if name == "answer":
            name = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(name, args, tool_call_id=f"call-{index}")])
    return FunctionModel(respond)


def parts(history, kind):
    return [part for message in history for part in message.parts if isinstance(part, kind)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    path = Path(parser.parse_args().module).resolve()
    core = load_module(path)
    gate = Gate()

    def deps():
        return core.SupportDeps("shop-a", "user-1", {
            "shop-a": {"A100": {"status": "已发货", "amount": 20}},
            "shop-b": {"B200": {"status": "另一租户的秘密", "amount": 90}},
        }, [])

    def execute(actions, *, limit=5, state=None):
        state = state if state is not None else deps()
        agent = core.build_support_agent(scripted(actions))
        result = core.run_turn(agent, state, "处理订单", [], request_limit=limit)
        return agent, state, result

    def pending(order_id="A100"):
        return execute([("request_refund", {**REFUND, "order_id": order_id}), ("answer", ANSWER)])

    def test_sdk():
        agent = core.build_support_agent(scripted([("answer", ANSWER)]))
        expect(isinstance(agent, Agent), "期望真实 pydantic_ai.Agent")

    def test_query():
        _, _, result = execute([("get_order", {"order_id": "A100"}), ("answer", ANSWER)])
        returns = parts(result["history"], ToolReturnPart)
        expect(isinstance(result["output"], core.SupportAnswer), "期望 SupportAnswer")
        expect(any(isinstance(p.content, dict) and p.content.get("status") == "已发货" for p in returns),
               "期望 get_order 真正返回当前租户订单")
        expect(result["error"] is None and not result["pending_approvals"], "查询应正常结束")

    def test_tenant():
        _, _, result = execute([("get_order", {"order_id": "B200"}), ("answer", ANSWER)])
        content = str([p.content for p in parts(result["history"], ToolReturnPart)])
        expect("未找到" in content and "另一租户的秘密" not in content, "期望跨租户查询仅返回未找到")

    def test_pending():
        _, state, result = pending()
        expect(result["pending_approvals"] == ["call-0"], f"期望待审 call-0，实际 {result['pending_approvals']}")
        expect(result["output"] is None and not state.refunds, "待审时不能执行退款或生成最终输出")

    def test_approved(replay=False):
        agent, state, result = pending()
        history = core.load_history(core.dump_history(result["history"]))
        for _ in range(2 if replay else 1):
            resumed = core.resume_after_approval(agent, state, history, {"call-0": True}, request_limit=5)
            expect(resumed["output"] is not None and resumed["error"] is None, "批准后应完成 SDK 续跑")
        expect(len(state.refunds) == 1, f"期望仅执行一次退款，实际 {len(state.refunds)}")
        row = state.refunds[0]
        expect(all(row[key] == value for key, value in {**REFUND, "tenant_id": "shop-a", "user_id": "user-1"}.items()),
               "退款记录须绑定当前租户、用户和调用参数")

    def test_denied():
        def respond(messages, info):
            returned = parts(messages, ToolReturnPart)
            if not returned:
                return ModelResponse(parts=[ToolCallPart("request_refund", REFUND, tool_call_id="deny-1")])
            answer = {**ANSWER, "reply": str(returned[-1].content)}
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, answer)])
        state = deps()
        agent = core.build_support_agent(FunctionModel(respond))
        result = core.run_turn(agent, state, "退款", [], request_limit=5)
        result = core.resume_after_approval(agent, state, result["history"], {"deny-1": False}, request_limit=5)
        expect(not state.refunds, "拒绝后不能执行退款")
        expect("人工拒绝退款" in result["output"].reply, "拒绝原因必须经工具结果进入模型上下文及回复")

    def test_retry(bad):
        _, _, result = execute([("answer", bad), ("answer", ANSWER)])
        expect(result["output"].reply == ANSWER["reply"], "期望非法输出经重试后纠正")
        expect(bool(parts(result["history"], RetryPromptPart)), "期望 SDK 的 ModelRetry 反馈进入历史")

    def test_request_budget():
        _, _, result = execute([("get_order", {"order_id": "A100"})], limit=1)
        expect(result["error"] == "usage_limit" and result["output"] is None, "期望请求预算耗尽后返回 usage_limit")
        expect(bool(parts(result["history"], ToolCallPart)), "预算耗尽也应保留真实轨迹")

    def test_tool_budget():
        def respond(_messages, _info):
            return ModelResponse(parts=[ToolCallPart("get_order", {"order_id": "A100"}, tool_call_id=f"many-{i}")
                                        for i in range(3)])
        agent = core.build_support_agent(FunctionModel(respond))
        result = core.run_turn(agent, deps(), "批量查询", [], request_limit=2)
        expect(result["error"] == "usage_limit", "期望同一响应的多工具调用触发 tool_calls_limit")

    def test_history():
        agent, state, result = execute([("get_order", {"order_id": "A100"}), ("answer", ANSWER)])
        text = core.dump_history(result["history"])
        restored = core.load_history(text)
        expect(restored == result["history"] and core.dump_history(restored) == text, "期望完整 SDK 历史无损往返")
        next_turn = core.run_turn(agent, state, "继续", restored, request_limit=5)
        expect(next_turn["history"][:len(restored)] == restored, "下一轮必须携带此前历史")

    def test_guard():
        network_calls = []
        def forbidden(request):
            network_calls.append(request)
            raise AssertionError("不应触达 HTTP transport")
        client = AsyncOpenAI(api_key="offline-only", http_client=httpx.AsyncClient(transport=httpx.MockTransport(forbidden)))
        model = OpenAIChatModel("offline-only", provider=OpenAIProvider(openai_client=client))
        agent = core.build_support_agent(model)
        try:
            core.run_turn(agent, deps(), "不允许外部模型", [], request_limit=1)
        except RuntimeError as exc:
            expect("ALLOW_MODEL_REQUESTS" in str(exc), f"期望 SDK 禁请求异常，实际 {type(exc).__name__}")
        else:
            raise AssertionError("期望 ALLOW_MODEL_REQUESTS=False 阻止真实模型")
        expect(not network_calls, "禁止请求必须在 transport 前生效")

    def test_override():
        agent = core.build_support_agent(scripted([("answer", {**ANSWER, "reply": "原模型"})]))
        with agent.override(model=TestModel(call_tools=[], custom_output_args=ANSWER)):
            result = core.run_turn(agent, deps(), "冒烟", [], request_limit=3)
        expect(result["output"].reply == ANSWER["reply"], "TestModel 应通过 override 替换原模型")

    def test_refund_tenant():
        agent, state, result = pending("B200")
        result = core.resume_after_approval(agent, state, result["history"], {"call-0": True}, request_limit=5)
        expect(not state.refunds, "即使审批通过，工具也不能跨租户退款")
        expect(any("未找到" in str(p.content) for p in parts(result["history"], ToolReturnPart)), "跨租户退款应说明未找到")

    gate.check("01 使用真实 SDK Agent", test_sdk)
    gate.check("02 正常查询执行工具", test_query)
    gate.check("03 跨租户查询未找到", test_tenant)
    gate.check("04 退款暂停待审批", test_pending)
    gate.check("05 批准后执行一次", test_approved)
    gate.check("06 重放同一审批幂等", lambda: test_approved(True))
    gate.check("07 拒绝后不执行并说明", test_denied)
    gate.check("08 空白回复 ModelRetry", lambda: test_retry({**ANSWER, "reply": "  "}))
    gate.check("09 退款缺订单 ModelRetry", lambda: test_retry({**ANSWER, "action": "refund_requested", "order_id": None}))
    gate.check("10 请求数用量上限", test_request_budget)
    gate.check("11 工具调用数上限", test_tool_budget)
    gate.check("12 历史往返与下一轮恢复", test_history)
    gate.check("13 禁止真实模型请求生效", test_guard)
    gate.check("14 TestModel 与 Agent.override", test_override)
    gate.check("15 已批准退款仍受租户限制", test_refund_tenant)
    return gate.report(path)


if __name__ == "__main__":
    raise SystemExit(main())
