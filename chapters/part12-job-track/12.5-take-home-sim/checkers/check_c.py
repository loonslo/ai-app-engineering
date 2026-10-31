"""J5 任务 C 离线检查器：脚本化的决策函数与假工具，不联网。用 --module 指定你的实现。"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parent / "fixtures"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    if spec is None or spec.loader is None:
        raise ValueError("无法加载候选模块")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate"] = module
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class Checker:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            self.rows.append((name, False, f"{type(exc).__name__}: {exc}"))
        else:
            self.rows.append((name, True, ""))

    def report(self) -> int:
        passed = sum(ok for _, ok, _ in self.rows)
        for name, ok, error in self.rows:
            print(f"[{'PASS' if ok else 'FAIL'}] {name} {error}")
        print(f"{passed}/{len(self.rows)} passed")
        return 0 if passed == len(self.rows) else 1


def parse_module(default: str) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE.parent / "starters" / default))
    return Path(parser.parse_args().module).resolve()


def main() -> int:
    core = load_module(parse_module("solution_c.py"))
    checker = Checker()

    def script(*steps):
        iterator = iter(steps)
        seen: list[list] = []

        def decide(task, trace):
            seen.append(list(trace))
            step = next(iterator, {"final": "脚本用完"})
            if isinstance(step, Exception):
                raise step
            return step

        return decide, seen

    def make_tools():
        calls: list[tuple] = []

        def lookup(order_id):
            calls.append(("lookup", order_id))
            return {"order_id": order_id, "status": "shipped"}

        def delete_order(order_id):
            calls.append(("delete_order", order_id))
            return "deleted"

        def explode(**_):
            calls.append(("explode",))
            raise RuntimeError("tool down")

        return {"lookup": lookup, "delete_order": delete_order, "explode": explode}, calls

    def normal_flow():
        tools, calls = make_tools()
        decide, seen = script({"tool": "lookup", "args": {"order_id": "A1"}}, {"final": "已发货"})
        result = core.run_agent("查订单", tools, decide)
        expect(result["status"] == "done" and result["final"] == "已发货", f"应正常结束：{result}")
        expect(calls == [("lookup", "A1")], f"应调用一次 lookup：{calls}")
        expect(result["trace"][0]["result"] == {"order_id": "A1", "status": "shipped"}, "trace 应记录工具结果")
        expect(len(seen[1]) == 1, "第二次决策时应能看到上一步的 trace")

    def unknown_tool_and_bad_args():
        tools, calls = make_tools()
        decide, _ = script({"tool": "drop_database", "args": {}}, {"tool": "lookup", "args": ["A1"]}, {"final": "ok"})
        result = core.run_agent("x", tools, decide)
        expect(result["status"] == "done" and calls == [], f"未知工具与错误参数都不应执行工具：{result} {calls}")
        expect(result["trace"][0].get("error") and result["trace"][1].get("error"), f"两次失败都应记入 trace：{result['trace']}")

    def loop_is_bounded():
        tools, calls = make_tools()
        decide, _ = script(*[{"tool": "lookup", "args": {"order_id": "A1"}}] * 50)
        result = core.run_agent("x", tools, decide, max_steps=4)
        expect(result["status"] == "max_steps" and result["final"] is None, f"应因步数上限停止：{result['status']}")
        expect(len(calls) == 4 and len(result["trace"]) == 4, f"最多执行 4 步，实际 {len(calls)} 次工具调用")

    def dangerous_needs_approval():
        tools, calls = make_tools()
        dangerous = frozenset({"delete_order"})
        decide, _ = script({"tool": "delete_order", "args": {"order_id": "A1"}}, {"final": "x"})
        result = core.run_agent("x", tools, decide, dangerous=dangerous)
        expect(calls == [] and result["trace"][0].get("blocked") is True, f"没有审批函数时危险工具不得执行并应标记 blocked：{calls} {result['trace']}")
        decide, _ = script({"tool": "delete_order", "args": {"order_id": "A1"}}, {"final": "x"})
        core.run_agent("x", tools, decide, dangerous=dangerous, approve_fn=lambda name, args: False)
        expect(calls == [], "审批拒绝时不得执行")
        decide, _ = script({"tool": "delete_order", "args": {"order_id": "A1"}}, {"final": "x"})
        approvals: list[tuple] = []
        result = core.run_agent("x", tools, decide, dangerous=dangerous,
                                approve_fn=lambda name, args: approvals.append((name, args)) or True)
        expect(calls == [("delete_order", "A1")] and approvals == [("delete_order", {"order_id": "A1"})], f"审批通过才执行，且审批函数应收到工具名与参数：{calls} {approvals}")

    def safe_tool_does_not_ask():
        tools, calls = make_tools()
        decide, _ = script({"tool": "lookup", "args": {"order_id": "A1"}}, {"final": "x"})
        asked: list = []
        core.run_agent("x", tools, decide, dangerous=frozenset({"delete_order"}), approve_fn=lambda *a: asked.append(a) or True)
        expect(calls == [("lookup", "A1")] and asked == [], "非危险工具不需要审批")

    def tool_failure_is_fed_back():
        tools, calls = make_tools()
        decide, seen = script({"tool": "explode", "args": {}}, {"final": "已降级"})
        result = core.run_agent("x", tools, decide)
        expect(result["status"] == "done" and result["trace"][0].get("error") == "RuntimeError", f"工具异常应记入 trace 并继续：{result}")
        expect(seen[1][0].get("error") == "RuntimeError", "下一次决策应能看到工具的错误")

    def decision_failure():
        tools, _ = make_tools()
        decide, _ = script(ValueError("model down"))
        result = core.run_agent("x", tools, decide)
        expect(result["status"] == "error", f"决策函数异常应返回 status=error 而不是抛出：{result}")

    checker.check("01 正常流程：调用工具、结果进入 trace、下一步可见", normal_flow)
    checker.check("02 未知工具与错误参数不执行", unknown_tool_and_bad_args)
    checker.check("03 循环有步数上限", loop_is_bounded)
    checker.check("04 危险工具必须审批通过才执行", dangerous_needs_approval)
    checker.check("05 非危险工具不触发审批", safe_tool_does_not_ask)
    checker.check("06 工具异常进入 trace 并让下一步可见", tool_failure_is_fed_back)
    checker.check("07 决策函数异常不会抛出", decision_failure)
    return checker.report()


if __name__ == "__main__":
    raise SystemExit(main())
