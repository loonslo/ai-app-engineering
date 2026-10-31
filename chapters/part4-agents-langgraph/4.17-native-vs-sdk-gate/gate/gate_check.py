"""完全离线的闭卷验收；默认starter必须零通过。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(path: Path):
    sys.path.insert(0, str(HERE.parent))
    spec = importlib.util.spec_from_file_location("candidate", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate"] = module
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class Gate:
    def __init__(self) -> None:
        self.rows = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, module_path: Path, gate_name: str) -> int:
        passed = sum(row["ok"] for row in self.rows)
        for row in self.rows:
            print(f"[{'PASS' if row['ok'] else 'FAIL'}] {row['name']} {row['error']}")
        print(f"{passed}/{len(self.rows)} passed")
        report = {"gate": gate_name, "module": str(module_path), "passed": passed, "total": len(self.rows), "ok": passed == len(self.rows), "checks": self.rows}
        (HERE / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if report["ok"] else 1


import pydantic_ai.models  # noqa: E402
from scenarios import make_scenarios, make_tools  # noqa: E402

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    path = Path(parser.parse_args().module).resolve()
    core = load_module(path)
    gate = Gate()
    cases = make_scenarios(core)
    def runner(fn):
        return lambda case: fn(case, make_tools(), max_steps=3)
    def check_scenario(fn, case):
        tools = make_tools()
        result = fn(case, tools, max_steps=3)
        report = core.evaluate([case], lambda _: result)
        expect(report["passed"] == [case.name] and report["failed"] == [] and report["pass_rate"] == 1, f"期望场景通过，实际{report}")
        expect(1 <= result["steps"] <= 3, f"请求数应有界，实际{result}")
        expect(tools["request_refund"].refunds == [], "本组场景不得真的执行退款")
        if case.name in {"未知工具", "工具异常", "参数非法", "模型循环超限"}:
            expect(bool(result["errors"]), f"故障必须留下errors，实际{result}")
    for index, case in enumerate(cases, 1):
        gate.check(f"{index:02} 原生 {case.name}", lambda case=case: check_scenario(core.run_native, case))
    for index, case in enumerate(cases, 9):
        gate.check(f"{index:02} SDK {case.name}", lambda case=case: check_scenario(core.run_pydantic_ai, case))
    def statistics():
        def mixed(case):
            result = core.run_native(case, make_tools(), max_steps=3)
            if case.name == "正常查询":
                result["status"] = "failed"
            return result
        report = core.evaluate(cases, mixed)
        expect(len(report["passed"]) == 7 and len(report["failed"]) == 1 and report["pass_rate"] == 7 / 8 and len(report["runs"]) == 8, f"统计不符{report}")
        expect(core.evaluate([], mixed)["pass_rate"] == 0, "空输入率应为0")
    gate.check("17 evaluate混合通过率与空集", statistics)
    def comparison():
        native = {"pass_rate": .5, "runs": [{"name": "a", "steps": 2, "tools_called": ["x"]}, {"name": "b", "steps": 3, "tools_called": []}]}
        sdk = {"pass_rate": 1., "runs": [{"name": "b", "steps": 2, "tools_called": ["x"]}, {"name": "a", "steps": 4, "tools_called": ["x", "y"]}]}
        diff = core.compare(native, sdk)
        expect(diff == {"native_pass_rate": .5, "sdk_pass_rate": 1., "differences": [{"name": "a", "steps_delta": 2, "tool_calls_delta": 1}, {"name": "b", "steps_delta": -1, "tool_calls_delta": 1}]}, f"比较应按name对齐且SDK减原生，实际{diff}")
    gate.check("18 compare字段与非零差值", comparison)
    def mutant():
        # 故意写坏：每次原生运行后偷偷多调退款；不能仅把分数改成0来假装抓变异。
        def broken_native(case):
            tools = make_tools()
            result = core.run_native(case, tools, max_steps=3)
            tools["request_refund"](order_id="A100", idempotency_key="mutant")
            expect(tools["request_refund"].refunds == ["A100"], "变异体须真的执行越权副作用")
            result["tools_called"].append("request_refund")
            return result
        report = core.evaluate(cases, broken_native)
        expect(len(report["failed"]) == 7 and report["passed"] == ["退款待审批"] and report["pass_rate"] == 1 / 8, f"变异体应被禁止工具断言抓住，实际{report}")
        expect(all("禁止" in row["reason"] for row in report["failed"]), "失败原因须定位禁止工具")
    gate.check("19 真实原生变异体被评测抓住", mutant)
    def grader_contract():
        case = core.Scenario("有序子序列", "任务", (), core.Expected("正确", ("a", "b"), ("danger",), "done"))
        def result(names, final="正确"):
            return {"status": "done", "final": final, "tools_called": names, "steps": 1, "errors": []}
        good = core.evaluate([case], lambda _: result(["a", "extra", "b"]))
        bad_order = core.evaluate([case], lambda _: result(["b", "a"]))
        bad_final = core.evaluate([case], lambda _: result(["a", "b"], "错误"))
        expect(good["pass_rate"] == 1 and bad_order["pass_rate"] == bad_final["pass_rate"] == 0, "必须检查有序子序列与最终答案")
        def raises(_):
            raise ValueError("场景运行故障")
        failed = core.evaluate([case], raises)
        expect(failed["pass_rate"] == 0 and "ValueError" in failed["failed"][0]["reason"], "异常应成为可读失败")
    gate.check("20 判分顺序最终答案与异常", grader_contract)
    def sdk_really_runs():
        from unittest.mock import patch
        from pydantic_ai import Agent
        original = Agent.run_sync
        with patch.object(Agent, "run_sync", autospec=True, side_effect=original) as spy:
            result = core.run_pydantic_ai(cases[0], make_tools(), max_steps=3)
        expect(spy.call_count == 1 and result["status"] == "done", "SDK路径必须真实执行Agent.run_sync")
    gate.check("21 SDK确实运行而非转调原生", sdk_really_runs)
    return gate.report(path, "L4.8-native-vs-sdk-gate")


if __name__ == "__main__":
    raise SystemExit(main())
