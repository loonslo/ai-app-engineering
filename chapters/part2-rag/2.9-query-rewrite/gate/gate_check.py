"""L2.6 查询改写与 Agentic Retrieval · 离线 gate 验收。"""

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
    spec = importlib.util.spec_from_file_location("candidate_l29b", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_l29b"] = module
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
            "gate": "L2.6-query-rewrite",
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

    def test_prompt():
        prompt = core.build_rewrite_prompt("向量怎么存", [{"role": "user", "content": "你好"}])
        expect("向量怎么存" in prompt, "prompt 缺原问题")
        expect("你好" in prompt, "prompt 缺历史")
        expect("一行一条" in prompt or "每行一条" in prompt, "prompt 应要求一行一条")

    def test_parse():
        text = "1. 如何存储向量\n2) 向量持久化\n- 向量库落盘\n2) 向量持久化\n\n"
        rows = core.parse_rewrites(text, max_queries=5)
        expect(rows == ["如何存储向量", "向量持久化", "向量库落盘"], f"解析不对：{rows}")

    def test_parse_limit():
        rows = core.parse_rewrites("1. a\n2. b\n3. c", max_queries=2)
        expect(rows == ["a", "b"], f"max_queries 未生效：{rows}")
        for max_queries in (0, -1):
            try:
                core.parse_rewrites("a", max_queries=max_queries)
            except ValueError:
                continue
            raise AssertionError("max_queries<1 应抛 ValueError")

    def test_rewrite_ok():
        result = core.rewrite_query("向量怎么存", lambda prompt: "1. 如何存储向量\n2. 向量持久化")
        expect(result["queries"] == ["向量怎么存", "如何存储向量", "向量持久化"], f"改写结果不对：{result}")
        expect(result["error"] is None, f"error 应为 None：{result}")

    def test_rewrite_max_queries():
        result = core.rewrite_query("向量怎么存", lambda prompt: "1. a\n2. b", max_queries=2)
        expect(result["queries"] == ["向量怎么存", "a"], f"应截断到 2 条：{result}")

    def test_rewrite_empty():
        result = core.rewrite_query("向量怎么存", lambda prompt: "   ")
        expect(result["queries"] == ["向量怎么存"], f"空输出应回退原问题：{result}")
        expect(result["error"] == "empty_rewrite", f"error 不对：{result}")

    def test_rewrite_no_new_query():
        result = core.rewrite_query("向量怎么存", lambda prompt: "1. 向量怎么存")
        expect(result["queries"] == ["向量怎么存"], f"重复原问题应回退：{result}")
        expect(result["error"] == "empty_rewrite", f"error 不对：{result}")

    def test_rewrite_model_error():
        def boom(prompt):
            raise TimeoutError("timeout")

        result = core.rewrite_query("向量怎么存", boom)
        expect(result["queries"] == ["向量怎么存"], f"异常应回退原问题：{result}")
        expect(result["error"] == "model_error", f"error 不对：{result}")

    def test_rewrite_validation():
        for args, kwargs in ((("  ", lambda p: "x"), {}), (("q", lambda p: "x"), {"max_queries": 0})):
            try:
                core.rewrite_query(*args, **kwargs)
            except ValueError:
                continue
            raise AssertionError("非法参数应抛 ValueError")

    # 追加检查 10~16：Agentic Retrieval
    def test_agentic_round1_enough():
        def fake_search(q):
            return [
                core.Hit(source="doc1", index=1, score=0.9, text="hit1"),
                core.Hit(source="doc2", index=2, score=0.8, text="hit2"),
            ]
        res = core.agentic_retrieve("问题", fake_search, lambda q, hits: "q2", min_hits=2, max_rounds=3)
        expect(res.rounds == 1, f"第1轮命中足够应只有1轮：{res.rounds}")
        expect(res.stopped_reason == "enough", f"停止原因应为 enough：{res.stopped_reason}")
        expect(res.queries == ("问题",), f"queries 不对：{res.queries}")
        expect(len(res.hits) == 2, f"命中数不对：{len(res.hits)}")

    def test_agentic_rewrite_once_enough():
        calls = []
        def fake_search(q):
            calls.append(q)
            if q == "问题":
                return [core.Hit(source="doc1", index=1, score=0.5, text="hit1")]
            return [core.Hit(source="doc2", index=2, score=0.85, text="hit2")]
        def fake_rewrite(q, hits):
            return "改写问题"
        res = core.agentic_retrieve("问题", fake_search, fake_rewrite, min_hits=2, max_rounds=3)
        expect(res.rounds == 2, f"应进行2轮：{res.rounds}")
        expect(res.stopped_reason == "enough", f"停止原因应为 enough：{res.stopped_reason}")
        expect(res.queries == ("问题", "改写问题"), f"queries 不对：{res.queries}")
        expect(len(res.hits) == 2, f"命中数不对：{len(res.hits)}")

    def test_agentic_rewrite_returns_none():
        def fake_search(q):
            return [core.Hit(source="doc1", index=1, score=0.5, text="hit1")]
        def fake_rewrite(q, hits):
            return None
        res = core.agentic_retrieve("问题", fake_search, fake_rewrite, min_hits=3, max_rounds=3)
        expect(res.rounds == 1, f"改写返回None应在第1轮停止：{res.rounds}")
        expect(res.stopped_reason == "no_rewrite", f"停止原因应为 no_rewrite：{res.stopped_reason}")
        expect(res.queries == ("问题",), f"queries 不对：{res.queries}")

    def test_agentic_max_rounds():
        counter = {"rounds": 0}
        def fake_search(q):
            counter["rounds"] += 1
            return []
        def fake_rewrite(q, hits):
            return f"改写_{len(hits)}"
        res = core.agentic_retrieve("问题", fake_search, fake_rewrite, min_hits=2, max_rounds=3)
        expect(res.rounds == 3, f"达到最大轮数应为3：{res.rounds}")
        expect(res.stopped_reason == "max_rounds", f"停止原因应为 max_rounds：{res.stopped_reason}")
        expect(len(res.queries) == 3, f"queries 数量应为3：{len(res.queries)}")

    def test_agentic_dedupe_across_rounds():
        def fake_search(q):
            if q == "q1":
                return [core.Hit(source="doc1", index=1, score=0.7, text="t1")]
            return [
                core.Hit(source="doc1", index=1, score=0.9, text="t1"),
                core.Hit(source="doc2", index=2, score=0.6, text="t2"),
            ]
        res = core.agentic_retrieve("q1", fake_search, lambda q, hits: "q2", min_hits=3, max_rounds=2)
        expect(len(res.hits) == 2, f"跨轮重复 source#index 应去重：{len(res.hits)}")
        expect([h.source for h in res.hits] == ["doc1", "doc2"], f"命中列表不对：{res.hits}")

    def test_agentic_sort_by_score():
        def fake_search(q):
            return [
                core.Hit(source="doc1", index=1, score=0.3, text="low"),
                core.Hit(source="doc2", index=2, score=0.9, text="high"),
                core.Hit(source="doc3", index=3, score=0.6, text="mid"),
            ]
        res = core.agentic_retrieve("q", fake_search, lambda q, h: None, min_hits=2)
        scores = [h.score for h in res.hits]
        expect(scores == sorted(scores, reverse=True), f"hits 应按 score 降序：{scores}")

    def test_agentic_param_validation():
        for bad_max in (0, -1):
            try:
                core.agentic_retrieve("q", lambda q: [], lambda q, h: None, max_rounds=bad_max)
            except ValueError:
                continue
            raise AssertionError(f"max_rounds={bad_max} 应抛 ValueError")
        for bad_min in (0, -1):
            try:
                core.agentic_retrieve("q", lambda q: [], lambda q, h: None, min_hits=bad_min)
            except ValueError:
                continue
            raise AssertionError(f"min_hits={bad_min} 应抛 ValueError")

    gate.check("01 改写 prompt", test_prompt)
    gate.check("02 解析编号/去重", test_parse)
    gate.check("03 max_queries 解析限制", test_parse_limit)
    gate.check("04 正常改写", test_rewrite_ok)
    gate.check("05 改写条数限制", test_rewrite_max_queries)
    gate.check("06 空输出回退", test_rewrite_empty)
    gate.check("07 无新查询回退", test_rewrite_no_new_query)
    gate.check("08 模型异常回退", test_rewrite_model_error)
    gate.check("09 参数校验", test_rewrite_validation)
    # 新增项
    gate.check("10 Agentic 第1轮命中足够停止", test_agentic_round1_enough)
    gate.check("11 Agentic 改写后命中足够停止", test_agentic_rewrite_once_enough)
    gate.check("12 Agentic 改写返回None停止", test_agentic_rewrite_returns_none)
    gate.check("13 Agentic 达到最大轮数停止", test_agentic_max_rounds)
    gate.check("14 Agentic 跨轮去重", test_agentic_dedupe_across_rounds)
    gate.check("15 Agentic 最终按分数降序", test_agentic_sort_by_score)
    gate.check("16 Agentic 参数校验", test_agentic_param_validation)
    return gate.report(module_path)


if __name__ == "__main__":
    raise SystemExit(main())
