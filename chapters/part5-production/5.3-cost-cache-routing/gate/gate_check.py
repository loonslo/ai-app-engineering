"""L5.2 扩展 · 成本/缓存/路由 · 离线 gate 验收。"""

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
    spec = importlib.util.spec_from_file_location("candidate_l53", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_l53"] = module
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
            "gate": "L5.2-cost-cache-routing",
            "module": str(module_path),
            "passed": passed,
            "total": total,
            "ok": passed == total,
            "checks": self.rows,
        }
        (HERE / "gate_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if passed == total else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    args = parser.parse_args()
    module_path = Path(args.module).resolve()
    core = load_module(module_path)
    gate = Gate()

    def test_key():
        a = core.cache_key("  RAG   是什么 ")
        b = core.cache_key("rag 是什么")
        expect(a == b, f"归一化后应同键：{a} != {b}")
        try:
            core.cache_key("   ")
        except ValueError:
            return
        raise AssertionError("空问题应抛 ValueError")

    def test_cache():
        cache = core.TTLCache(ttl_seconds=10)
        cache.set("k", "v", now=100)
        expect(cache.get("k", now=105) == "v", "未过期应命中")
        expect(cache.get("k", now=111) is None, "过期应未命中")
        expect(cache.get("missing", now=100) is None, "不存在应 None")
        try:
            core.TTLCache(0)
        except ValueError:
            return
        raise AssertionError("ttl<=0 应抛 ValueError")

    def test_route():
        expect(core.is_simple("你好") is True, "问候应简单")
        expect(core.is_simple("如何设计多租户 RAG 权限与灰度回滚方案") is False, "长问题应复杂")
        expect(core.route("你好") == "cheap", "简单应 cheap")
        expect(core.route("如何设计多租户 RAG 权限与灰度回滚方案") == "strong", "复杂应 strong")
        try:
            core.route("")
        except ValueError:
            return
        raise AssertionError("空问题应抛 ValueError")

    def test_savings():
        expect(core.savings(0.5, 1.0, 4.0) == 0.375, "节省比例不对")
        expect(core.savings(0.0, 1.0, 4.0) == 0.0, "无简单问题应 0")
        for args in ((-0.1, 1, 4), (1.1, 1, 4), (0.5, 0, 4), (0.5, 5, 4)):
            try:
                core.savings(*args)
            except ValueError:
                continue
            raise AssertionError(f"非法参数应报错：{args}")

    gate.check("01 缓存键归一化", test_key)
    gate.check("02 TTL 缓存", test_cache)
    gate.check("03 路由", test_route)
    gate.check("04 节省估算", test_savings)

    price = {"input": 0.30, "cached_input": 0.006, "output": 1.20}

    def test_cost_cache():
        no_cache = core.cost_with_cache(10_000, 0, 500, price)
        cached = core.cost_with_cache(10_000, 8_000, 500, price)
        expect(abs(no_cache - 0.0036) < 1e-9, f"无缓存应为 0.0036，实际 {no_cache}")
        expect(abs(cached - 0.001248) < 1e-9, f"80% 命中应为 0.001248，实际 {cached}")
        expect(cached < no_cache, "命中缓存应更便宜")

    def test_cost_cache_error():
        try:
            core.cost_with_cache(100, 101, 0, price)
        except ValueError:
            return
        raise AssertionError("cached > input 应抛 ValueError")

    tasks = [{"id": "a", "urgent": True}, {"id": "b", "urgent": False}]

    def runs(now, windows):
        result = core.schedule_batch(tasks, now, windows)
        expect([r["id"] for r in result] == ["a", "b"], "顺序应与输入一致")
        return [r["run_at_hour"] for r in result]

    def test_schedule_defer():
        expect(runs(8, [(10, 18)]) == [8, 10], "非 urgent 应推迟到窗口起点，urgent 立即执行")

    def test_schedule_midnight():
        expect(runs(20, [(22, 1)]) == [20, 22], "跨零点窗口的起点是 22")
        expect(runs(0, [(22, 1)]) == [0, 0], "凌晨 0 点已在跨零点窗口内，应立即执行")

    def test_schedule_in_window():
        expect(runs(12, [(10, 18)]) == [12, 12], "当前处于低峰应立即执行")

    gate.check("05 带缓存的成本", test_cost_cache)
    gate.check("06 cached 大于 input 报错", test_cost_cache_error)
    gate.check("07 非 urgent 推迟到低峰", test_schedule_defer)
    gate.check("08 跨零点窗口", test_schedule_midnight)
    gate.check("09 当前处于低峰立即执行", test_schedule_in_window)
    return gate.report(module_path)


if __name__ == "__main__":
    raise SystemExit(main())
