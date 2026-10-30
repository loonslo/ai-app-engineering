"""L2.12 Gate：真实资料知识库 v1 · 离线 gate 验收。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(path: Path):
    if not path.exists():
        raise SystemExit(f"找不到实现文件：{path}")
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    spec = importlib.util.spec_from_file_location("candidate_l212_kb", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_l212_kb"] = module
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
            "gate": "L2.12-real-corpus-kb-gate",
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

    # 01 扫描页失败
    def test_scan_page():
        file = core.SourceFile(name="scan.pdf", pages=(None,))
        report = core.ingest([file], lambda t: [t])
        expect(len(report.failures) == 1, "未记录失败页")
        expect(report.failures[0] == ("scan.pdf", 1, "no_text_layer"), f"失败记录不对：{report.failures}")

    # 02 空白页失败
    def test_empty_page():
        file = core.SourceFile(name="empty.txt", pages=("   \n\t  ",))
        report = core.ingest([file], lambda t: [t])
        expect(len(report.failures) == 1, "未记录空白页失败")
        expect(report.failures[0] == ("empty.txt", 1, "empty_page"), f"失败记录不对：{report.failures}")

    # 03 表格行按行保留
    def test_table_preservation():
        text = "前言说明\n| col1 | col2 |\n| val1 | val2 |\n后记总结"
        file = core.SourceFile(name="table_doc", pages=(text,))
        report = core.ingest([file], lambda t: [t])
        table_chunks = [c for c in report.chunks if "|" in c.text]
        expect(len(table_chunks) == 2, f"表格行应独立切为2个chunk，实际：{len(table_chunks)}")
        expect(table_chunks[0].text == "| col1 | col2 |", f"表头行不对：{table_chunks[0].text}")
        expect(table_chunks[1].text == "| val1 | val2 |", f"数据行不对：{table_chunks[1].text}")

    # 04 Chunk 字段完整性
    def test_chunk_fields():
        file = core.SourceFile(name="docA", pages=("第一页段落一\n第一页段落二", "第二页段落一"))
        report = core.ingest([file], lambda t: [p for p in t.split("\n") if p])
        expect(len(report.chunks) == 3, f"总切片数不对：{len(report.chunks)}")
        c1, c2, c3 = report.chunks
        expect(c1.source == "docA" and c1.page == 1 and c1.index == 1, f"c1 字段不对：{c1}")
        expect(c2.source == "docA" and c2.page == 1 and c2.index == 2, f"c2 字段不对：{c2}")
        expect(c3.source == "docA" and c3.page == 2 and c3.index == 1, f"c3 字段不对：{c3}")

    # 05 无证据拒答且不得调用 chat_fn (m1)
    def test_low_score_refusal():
        chunk = core.Chunk(source="doc", page=1, index=1, text="无关内容")
        chat_called = False

        def bad_chat(m):
            nonlocal chat_called
            chat_called = True
            return "不该调用的回答"

        ans = core.answer_with_citations(
            "测试问题",
            retrieve_fn=lambda q: [(chunk, 0.3)],
            chat_fn=bad_chat,
            min_score=0.7,
        )
        expect(ans.get("refused") is True, "低分匹配应拒答")
        expect(ans.get("citations") == [], "拒答时引用必须为空列表")
        expect(chat_called is False, "拒答时不得调用 chat_fn")

    # 06 引用格式规范
    def test_citation_format():
        chunk = core.Chunk(source="manual", page=3, index=2, text="标准操作规范")
        ans = core.answer_with_citations(
            "标准操作是什么？",
            retrieve_fn=lambda q: [(chunk, 0.95)],
            chat_fn=lambda m: "参考 [manual#p3#2] 操作即可。",
            min_score=0.7,
        )
        expect(ans.get("refused") is False, "高分应当作答")
        cits = ans.get("citations", [])
        expect(len(cits) == 1, f"引用列表应包含1项：{cits}")
        expect(re.match(r"^[^#]+#p\d+#\d+$", cits[0]) is not None, f"引用格式不合规：{cits[0]}")
        expect(cits[0] == "manual#p3#2", f"引用 ID 不对：{cits[0]}")

    # 07 拦截未传给模型的幻觉引用
    def test_hallucinated_citation_rejected():
        chunk = core.Chunk(source="docA", page=1, index=1, text="这是真实资料A")
        ans = core.answer_with_citations(
            "测试幻觉引用",
            retrieve_fn=lambda q: [(chunk, 0.9)],
            chat_fn=lambda m: "根据 [docB#p9#9] 的规定说明。",
            min_score=0.7,
        )
        cits = ans.get("citations", [])
        expect("docB#p9#9" not in cits, f"未拦截幻觉引用：{cits}")

    # 08 资料装配在 user 消息分隔符内且声明为数据
    def test_prompt_isolation_delimiters():
        captured_messages = []

        def mock_chat(messages):
            captured_messages.extend(messages)
            return "根据资料 [doc#p1#1] 回答完毕。"

        chunk = core.Chunk(source="doc", page=1, index=1, text="系统操作指南数据")
        core.answer_with_citations(
            "如何操作？",
            retrieve_fn=lambda q: [(chunk, 0.85)],
            chat_fn=mock_chat,
            min_score=0.7,
        )
        expect(len(captured_messages) > 0, "未向 chat_fn 传递消息")
        user_msg = captured_messages[-1]
        expect(user_msg.get("role") == "user", "装配内容应在 user 消息中")
        content = user_msg.get("content", "")
        expect("---" in content or "===" in content or "```" in content, "资料未用明确分隔符包裹")
        expect("数据" in content or "只读" in content or "参考" in content, "未声明资料为数据或只读参考")

    # 09 固定替身指标精确计算 (仅应答题计算 citation 与 hit@5)
    def test_evaluate_metrics():
        cases = [
            # 题 1：应答题，回答正确，引用匹配
            {
                "id": "c1",
                "question": "q1",
                "should_refuse": False,
                "gold_sources": ["doc#p1"],
                "retrieved": ["doc#p1#1", "doc#p2#1"],
            },
            # 题 2：拒答题，系统拒答
            {
                "id": "c2",
                "question": "q2",
                "should_refuse": True,
                "gold_sources": [],
                "retrieved": ["doc#p9#9"],
            },
            # 题 3：应答题，但回答未召回，引用错误
            {
                "id": "c3",
                "question": "q3",
                "should_refuse": False,
                "gold_sources": ["doc#p5"],
                "retrieved": ["doc#p1#1", "doc#p2#1", "doc#p3#1", "doc#p4#1", "doc#p6#1"],
            },
        ]

        def mock_answer_fn(case):
            if case["id"] == "c1":
                return {"refused": False, "answer": "ans1", "citations": ["doc#p1#1"]}
            if case["id"] == "c2":
                return {"refused": True, "answer": "refused", "citations": []}
            return {"refused": False, "answer": "ans3", "citations": ["doc#p1#1"]}

        report = core.evaluate(cases, mock_answer_fn)
        # 应答题共有 c1, c3 (2题)：
        # citation: c1 通过, c3 失败 -> 1/2 = 0.5
        expect(abs(report["citation_accuracy"] - 0.5) < 1e-4, f"citation 不准：{report['citation_accuracy']}")
        # refusal 在全部 3 题上统计：c1, c2, c3 均符合 should_refuse -> 3/3 = 1.0
        expect(abs(report["refusal_accuracy"] - 1.0) < 1e-4, f"refusal 不准：{report['refusal_accuracy']}")
        # hit@5 仅在应答题 (c1, c3) 上统计：c1 命中, c3 未命中 -> 1/2 = 0.5
        expect(abs(report["hit_at_5"] - 0.5) < 1e-4, f"hit@5 不准：{report['hit_at_5']}")

    # 10 消融表与假时钟延迟统计
    def test_ablation_output():
        cases = [
            {"id": "c1", "question": "q1", "should_refuse": True, "gold_sources": [], "retrieved": [], "latency_ms": 15.0}
        ]
        configs = {
            "baseline": lambda c: {"refused": True, "answer": "r", "citations": []},
            "reranked": lambda c: {"refused": True, "answer": "r", "citations": []},
        }
        res = core.ablation(configs, cases, core.evaluate)
        expect(len(res) == 2, f"消融表应有2行，实际：{len(res)}")
        for row in res:
            for k in ("name", "citation_accuracy", "refusal_accuracy", "hit_at_5", "avg_latency_ms"):
                expect(k in row, f"消融表缺少字段 {k}：{row}")
            expect(abs(row["avg_latency_ms"] - 15.0) < 1e-4, f"假时钟延迟未正确统计：{row['avg_latency_ms']}")

    # 11 门禁阈值拦截器
    def test_gate_thresholds():
        passing_report = {"citation_accuracy": 0.92, "refusal_accuracy": 0.95, "hit_at_5": 0.85}
        expect(core.gate_thresholds(passing_report) == [], "达标报告应返回空列表")

        failing_report = {"citation_accuracy": 0.88, "refusal_accuracy": 0.89, "hit_at_5": 0.75}
        fails = core.gate_thresholds(failing_report)
        expect(len(fails) == 3, f"应包含3个未达标项：{fails}")

    # 12 cases.json 结构与用例完整性
    def test_cases_json():
        cases_file = HERE / "cases.json"
        expect(cases_file.exists(), "缺少 cases.json 文件")
        data = core.validate_cases(cases_file)
        expect(isinstance(data, list), "validate_cases 必须返回列表")
        expect(len(data) >= 30, f"评测样本数必须 >= 30，实际：{len(data)}")
        ids = set()
        has_refusal = False
        has_injection = False
        for c in data:
            expect("id" in c and "question" in c and "should_refuse" in c and "gold_sources" in c, f"缺少字段：{c}")
            expect(c["id"] not in ids, f"用例 ID 重复：{c['id']}")
            ids.add(c["id"])
            if c["should_refuse"]:
                has_refusal = True
            if c.get("category") == "prompt_injection" or "忽略" in c["question"]:
                has_injection = True
        expect(has_refusal, "缺少拒答用例")
        expect(has_injection, "缺少 Prompt 注入测试用例")

    gate.check("01 扫描页记失败 (reason=no_text_layer)", test_scan_page)
    gate.check("02 空白页记失败 (reason=empty_page)", test_empty_page)
    gate.check("03 表格行按行保留且不跨行合并", test_table_preservation)
    gate.check("04 Chunk 字段完整性与页内索引起始规范", test_chunk_fields)
    gate.check("05 无足够支持证据时安全拒答且不调 chat_fn", test_low_score_refusal)
    gate.check("06 引用格式严格遵循 source#p<page>#<index>", test_citation_format)
    gate.check("07 拦截引用未传给模型的幻觉片段", test_hallucinated_citation_rejected)
    gate.check("08 资料装配在 user 消息分隔符内且声明为数据", test_prompt_isolation_delimiters)
    gate.check("09 固定替身下单项指标精确计算", test_evaluate_metrics)
    gate.check("10 消融表按配置逐行输出包含延迟与指标", test_ablation_output)
    gate.check("11 门禁阈值拦截器判断全部未达标项", test_gate_thresholds)
    gate.check("12 cases.json 结构与用例完整性校验", test_cases_json)
    return gate.report(module_path)


if __name__ == "__main__":
    raise SystemExit(main())
