"""L4.7 Agent 轨迹评测 · 离线 gate 验收。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(path: Path):
    if not path.exists():
        raise SystemExit(f"找不到实现文件：{path}")
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("candidate_l39", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_l39"] = module
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

    def report(self, module_path: Path) -> int:
        passed = sum(row["ok"] for row in self.rows)
        total = len(self.rows)
        for row in self.rows:
            mark = "PASS" if row["ok"] else "FAIL"
            print(f"[{mark}] {row['name']}" + ("" if row["ok"] else f"  <- {row['error']}"))
        print(f"\n{passed}/{total} passed")
        if passed != total:
            print("gate 未通过：先修 FAIL 项，不要打开参考实现。")
        out = {
            "gate": "L4.7-trajectory",
            "module": str(module_path),
            "passed": passed,
            "total": total,
            "ok": passed == total,
            "checks": self.rows,
        }
        (HERE / "gate_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if passed == total else 1


CASE = {
    "id": "c1",
    "type": "agent_tool",
    "expected_tools": ["web_search"],
    "forbidden_tools": ["delete_database"],
    "max_steps": 2,
    "min_tool_calls": 1,
    "keywords": ["LangGraph", "框架"],
    "should_refuse": False,
}


def traj(*tools: str, final: str = "LangGraph 是框架") -> list[dict]:
    rows = [{"role": "ai", "tool_calls": [{"name": name} for name in tools]}] if tools else []
    rows.append({"role": "final", "content": final})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    args = parser.parse_args()
    module_path = Path(args.module).resolve()
    core = load_module(module_path)
    gate = Gate()

    def test_extract():
        names = core.extract_tool_names([
            {"role": "ai", "tool_calls": [{"name": "a"}, {"name": "b"}]},
            {"role": "tool", "content": "x"},
            {"role": "ai", "tool_calls": []},
        ])
        expect(names == ["a", "b"], f"工具提取不对：{names}")

    def test_pass():
        result = core.evaluate_trajectory(CASE, traj("web_search"))
        expect(result["passed"] is True, f"正常轨迹应通过：{result}")
        expect(result["called_tools"] == ["web_search"], f"called_tools 不对：{result}")
        expect(result["step_count"] == 1 and result["tool_call_count"] == 1, f"步数不对：{result}")
        expect(result["keyword_score"] == 1.0, f"关键词应满分：{result}")

    def test_forbidden():
        result = core.evaluate_trajectory(CASE, traj("delete_database", "web_search"))
        expect(result["forbidden_ok"] is False and result["passed"] is False, f"禁用工具应失败：{result}")

    def test_missing_expected():
        result = core.evaluate_trajectory(CASE, traj())
        expect(result["expected_ok"] is False and result["passed"] is False, f"缺期望工具应失败：{result}")

    def test_incomplete_and_steps():
        incomplete = [{"role": "ai", "tool_calls": [{"name": "web_search"}]}]
        result = core.evaluate_trajectory(CASE, incomplete)
        expect(result["completed"] is False and result["passed"] is False, f"无 final 应失败：{result}")
        looping = [
            {"role": "ai", "tool_calls": [{"name": "web_search"}]},
            {"role": "ai", "tool_calls": [{"name": "web_search"}]},
            {"role": "ai", "tool_calls": [{"name": "web_search"}]},
            {"role": "final", "content": "LangGraph 是框架"},
        ]
        result = core.evaluate_trajectory(CASE, looping)
        expect(result["max_steps_exceeded"] is True and result["passed"] is False, f"超步数应失败：{result}")

    def test_min_calls_and_keyword():
        case = dict(CASE, min_tool_calls=2, keywords=["LangGraph", "框架", "Agent"])
        result = core.evaluate_trajectory(case, traj("web_search"))
        expect(result["min_calls_met"] is False and result["passed"] is False, f"调用不足应失败：{result}")
        expect(abs(result["keyword_score"] - 2 / 3) < 1e-3, f"关键词比例不对：{result}")

    def test_summary():
        good = core.evaluate_trajectory(CASE, traj("web_search"))
        bad = core.evaluate_trajectory(CASE, traj("delete_database", "web_search"))
        summary = core.summarize_trajectories([good, bad])
        expect(summary["cases"] == 2 and summary["pass_rate"] == 0.5, f"汇总不对：{summary}")
        expect(summary["forbidden_tool_pass_rate"] == 0.5, f"禁用工具率不对：{summary}")
        expect(core.summarize_trajectories([])["cases"] == 0, "空汇总 cases 应为 0")

    gate.check("01 提取工具名", test_extract)
    gate.check("02 正常轨迹", test_pass)
    gate.check("03 禁用工具", test_forbidden)
    gate.check("04 缺期望工具", test_missing_expected)
    gate.check("05 未完成/超步数", test_incomplete_and_steps)
    gate.check("06 最少调用/关键词", test_min_calls_and_keyword)
    gate.check("07 汇总", test_summary)

    def test_outcome_and_forbidden():
        result = core.grade_run(True, traj("delete_database"), forbidden_tools={"delete_database"},
                                max_steps=3, partial_checks={})
        expect(result["score"] == 0 and result["violations"] == ["forbidden_tool"], f"禁止工具应清零：{result}")
        result = core.grade_run(False, traj(), forbidden_tools=set(), max_steps=3, partial_checks={})
        expect(result["score"] == 0, f"结果失败应清零：{result}")

    def test_step_penalty():
        result = core.grade_run(True, [{"role": "ai"}] * 3, forbidden_tools=set(),
                                max_steps=2, partial_checks={})
        expect(result == {"score": 0.8, "violations": ["max_steps"]}, f"超步扣0.2：{result}")

    def test_partial_credit():
        result = core.grade_run(True, [], forbidden_tools=set(), max_steps=2,
                                partial_checks={"查订单": True, "解释退款": False, "保留来源": True})
        expect(result == {"score": 0.67, "violations": []}, f"部分分应2/3：{result}")

    def test_consistency():
        report = core.consistency_report({"a": [{"score": 1}, {"score": 0}],
                                          "b": [{"score": 1}, {"score": 1}]}, 2)
        expect(report["tasks"]["a"] == {"pass@1": 1.0, "pass^k": 0.0}, f"任务a统计不对：{report}")
        expect(report["overall"] == {"pass@1": 1.0, "pass^k": 0.5}, f"总体统计不对：{report}")
        expect(core.consistency_report({}, 2)["overall"]["pass^k"] == 0, "空输入应0")
        expect(core.consistency_report({"a": [{"score": 1}]}, 2)["tasks"]["a"]["pass^k"] == 0, "不足k次不能全成功")
        try:
            core.consistency_report({}, 0)
        except ValueError:
            return
        raise AssertionError("k<1应ValueError")

    gate.check("08 结果失败/禁止工具清零", test_outcome_and_forbidden)
    gate.check("09 超步扣分", test_step_penalty)
    gate.check("10 多部分任务部分分", test_partial_credit)
    gate.check("11 pass^k稳定性统计", test_consistency)
    return gate.report(module_path)


if __name__ == "__main__":
    raise SystemExit(main())
