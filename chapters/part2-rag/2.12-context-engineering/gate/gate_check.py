"""L2.1 上下文工程总论 · 离线 gate 验收。"""

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
    spec = importlib.util.spec_from_file_location("candidate_l21_context", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_l21_context"] = module
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
            "gate": "L2.1-context-engineering",
            "module": str(module_path),
            "passed": passed,
            "total": total,
            "ok": passed == total,
            "checks": self.rows,
        }
        (HERE / "gate_report.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return 0 if passed == total else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    args = parser.parse_args()
    module_path = Path(args.module).resolve()
    core = load_module(module_path)
    gate = Gate()

    Section = core.Section
    ContextBudgetError = core.ContextBudgetError

    def test_count_tokens():
        # CJK 字符记 1，英文片段按空白分割记 1
        text = "Hello world! 你好世界 123"
        cnt = core.count_tokens(text)
        # Hello: 1, world!: 1, 你,好,世,界: 4, 123: 1 -> 总数 7
        expect(cnt == 7, f"count_tokens 计算错误：期望 7，实际 {cnt}")

    def test_static_before_dynamic():
        s1 = Section(name="dyn1", text="动态历史", kind="dynamic", priority=5)
        s2 = Section(name="sta1", text="静态系统指令", kind="static", priority=1)
        res = core.assemble_context([s1, s2], budget=50)
        expect(res.included == ("sta1", "dyn1"), f"排序错误，static 应排在 dynamic 前：{res.included}")
        expect(res.text.startswith("静态系统指令\n\n动态历史"), f"正文组装错误：{res.text}")

    def test_required_always_included():
        s1 = Section(name="req1", text="必须条款", kind="static", priority=1, required=True)
        s2 = Section(name="opt1", text="可选提示词", kind="dynamic", priority=10, required=False)
        res = core.assemble_context([s1, s2], budget=8)
        expect("req1" in res.included, "required=True 的段落必须被包含")

    def test_required_over_budget_raises():
        s1 = Section(name="req_big", text="非常长的必须系统条款内容超过十个字符", kind="static", priority=1, required=True)
        try:
            core.assemble_context([s1], budget=3)
        except ContextBudgetError:
            pass
        else:
            raise AssertionError("仅 required 就超过 budget 时应抛出 ContextBudgetError")

    def test_priority_dropping():
        s_low = Section(name="low", text="低优段落内容", kind="dynamic", priority=1)
        s_high = Section(name="high", text="高优段落内容", kind="dynamic", priority=10)
        res = core.assemble_context([s_low, s_high], budget=8)
        expect("high" in res.included, "高优先级段落应被纳入")
        expect("low" in res.dropped, "超预算的低优先级段落应被丢弃进入 dropped")

    def test_priority_stable_order():
        s1 = Section(name="p1_a", text="第一段", kind="dynamic", priority=5)
        s2 = Section(name="p1_b", text="第二段", kind="dynamic", priority=5)
        res = core.assemble_context([s1, s2], budget=20)
        expect(res.included == ("p1_a", "p1_b"), f"同优先级应保持稳定输入顺序：{res.included}")

    def test_duplicate_section_dedup_and_warning():
        s1 = Section(name="sec1", text="相同文本内容", kind="static", priority=5)
        s2 = Section(name="sec2", text="相同文本内容", kind="static", priority=5)
        s3 = Section(name="sec1", text="不同文本内容", kind="dynamic", priority=5)
        res = core.assemble_context([s1, s2, s3], budget=50)
        expect(len(res.included) == 1 and res.included[0] == "sec1", f"同名或重复文本应去重：{res.included}")
        expect("duplicate:sec2" in res.warnings and "duplicate:sec1" in res.warnings, f"重复应同时产生同内容与同名 warning：{res.warnings}")

    def test_cache_hash_invariant_on_dynamic_change():
        s_static = Section(name="sys", text="静态系统提示词前缀", kind="static", priority=10)
        s_dyn1 = Section(name="q1", text="用户提问一", kind="dynamic", priority=5)
        s_dyn2 = Section(name="q2", text="用户完全不同的提问二", kind="dynamic", priority=5)
        res1 = core.assemble_context([s_static, s_dyn1], budget=50)
        res2 = core.assemble_context([s_static, s_dyn2], budget=50)
        expect(res1.static_prefix_hash == res2.static_prefix_hash, "仅改变 dynamic 时 static_prefix_hash 必须严格一致以命中缓存")

    def test_cache_hash_changes_on_static_change():
        s_static1 = Section(name="sys1", text="静态提示词版本A", kind="static", priority=10)
        s_static2 = Section(name="sys2", text="静态提示词版本B", kind="static", priority=10)
        res1 = core.assemble_context([s_static1], budget=50)
        res2 = core.assemble_context([s_static2], budget=50)
        expect(res1.static_prefix_hash != res2.static_prefix_hash, "改变 static 内容时 static_prefix_hash 必须改变")

    def test_lint_volatile_in_static():
        s1 = Section(name="sys_time", text="系统启动于 2026-10-28 10:30:00", kind="static", priority=10)
        s2 = Section(name="user_time", text="今天日期是 2026-10-28", kind="dynamic", priority=5)
        warnings = core.lint_context([s1, s2], budget=100)
        expect("volatile_in_static:sys_time" in warnings, f"static 中含日期时间应告警 volatile_in_static：{warnings}")
        expect("volatile_in_static:user_time" not in warnings, "dynamic 中含日期时间不应触发 volatile_in_static")

    def test_lint_oversized_section():
        s_huge = Section(name="huge_sec", text="这是一个极其巨大的段落内容", kind="dynamic", priority=10)
        # 假设 budget 很小，s_huge 超过 budget 的 50%
        warnings = core.lint_context([s_huge], budget=10)
        expect("oversized:huge_sec" in warnings, f"单段超过 budget 50% 应告警 oversized：{warnings}")

    gate.check("01 count_tokens 近似计数", test_count_tokens)
    gate.check("02 static 在前 dynamic 在后", test_static_before_dynamic)
    gate.check("03 required 段落始终保留", test_required_always_included)
    gate.check("04 required 超预算报错", test_required_over_budget_raises)
    gate.check("05 按 priority 降序丢弃", test_priority_dropping)
    gate.check("06 同 priority 顺序稳定", test_priority_stable_order)
    gate.check("07 重复段落去重与告警", test_duplicate_section_dedup_and_warning)
    gate.check("08 只改 dynamic 时哈希不变", test_cache_hash_invariant_on_dynamic_change)
    gate.check("09 改 static 时哈希改变", test_cache_hash_changes_on_static_change)
    gate.check("10 static 含时间戳 lint 告警", test_lint_volatile_in_static)
    gate.check("11 单段超过50%预算 lint 告警", test_lint_oversized_section)

    return gate.report(module_path)


if __name__ == "__main__":
    raise SystemExit(main())
