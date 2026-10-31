"""J5 任务 B 离线检查器：假模型按脚本返回，不联网。用 --module 指定你的实现。"""
from __future__ import annotations

import argparse
import importlib.util
import json
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
    core = load_module(parse_module("solution_b.py"))
    cases = json.loads((FIXTURES / "cases_b.json").read_text(encoding="utf-8"))
    checker = Checker()
    good = '{"category": "bug", "priority": 2, "summary": "导出后白屏"}'

    def scripted(outputs):
        calls: list[list[dict]] = []

        def chat(messages):
            calls.append(messages)
            step = outputs[min(len(calls) - 1, len(outputs) - 1)]
            if isinstance(step, Exception):
                raise step
            return step

        return chat, calls

    def parses_plain_and_fenced():
        for raw in (good, "```json\n" + good + "\n```", "```\n" + good + "\n```"):
            chat, calls = scripted([raw])
            result = core.extract_ticket("导出白屏", chat)
            expect(result["ok"] is True and result["attempts"] == 1 and len(calls) == 1, f"合法输出应一次成功：{result}")
            expect(result["data"] == {"category": "bug", "priority": 2, "summary": "导出后白屏"}, f"解析结果不对：{result['data']}")

    def rejects_invalid_values():
        bad_outputs = [
            '{"category": "refund", "priority": 2, "summary": "x"}',    # 枚举不合法
            '{"category": "bug", "priority": 5, "summary": "x"}',       # 越界
            '{"category": "bug", "priority": "2", "summary": "x"}',     # 类型不对
            '{"category": "bug", "priority": true, "summary": "x"}',    # bool 不是整数
            '{"category": "bug", "priority": 2}',                       # 缺字段
            '{"category": "bug", "priority": 2, "summary": "  "}',      # 空摘要
            '{"category": "bug", "priority": 2, "summary": "' + "长" * 81 + '"}',  # 过长
            "不是 JSON", "[1, 2]",
        ]
        for raw in bad_outputs:
            chat, _ = scripted([raw])
            result = core.extract_ticket("x", chat, max_attempts=1)
            expect(result["ok"] is False and result["data"] is None and result["error"], f"应判为失败并给出原因：{raw[:30]} -> {result}")

    def retries_with_feedback():
        chat, calls = scripted(['{"category": "refund", "priority": 2, "summary": "x"}', good])
        result = core.extract_ticket("导出白屏", chat)
        expect(result["ok"] is True and result["attempts"] == 2 and len(calls) == 2, f"第二次应成功：{result}")
        first = "\n".join(m["content"] for m in calls[0])
        second = "\n".join(m["content"] for m in calls[1])
        expect(second != first and ("refund" in second or "category" in second), "重试时应把上次的问题告诉模型")

    def retry_is_bounded():
        chat, calls = scripted(["不是 JSON"])
        result = core.extract_ticket("x", chat, max_attempts=3)
        expect(result["ok"] is False and result["attempts"] == 3 and len(calls) == 3, f"最多尝试 3 次：{result}")

    def model_exception_never_escapes():
        chat, calls = scripted([TimeoutError("down"), good])
        result = core.extract_ticket("x", chat)
        expect(result["ok"] is True and result["attempts"] == 2, f"模型异常算一次失败并重试：{result}")
        chat, _ = scripted([TimeoutError("down")])
        result = core.extract_ticket("x", chat)
        expect(result["ok"] is False and "TimeoutError" in str(result["error"]), f"持续失败应返回 error 而不是抛异常：{result}")

    def evaluate_scores_correctly():
        expected = {c["id"]: c["expected"] for c in cases}

        def fake_extract(text):
            case = next(c for c in cases if c["text"] == text)
            data = dict(expected[case["id"]], summary="摘要")
            if case["id"] == "b1":          # 类别错
                data["category"] = "bug"
            if case["id"] == "b2":          # 优先级错
                data["priority"] = 3
            if case["id"] == "b3":          # 抽取失败
                return {"ok": False, "data": None, "attempts": 2, "error": "x"}
            return {"ok": True, "data": data, "attempts": 1, "error": None}

        report = core.evaluate(cases, fake_extract)
        n = len(cases)
        expect(report["n"] == n, f"n 应为 {n}")
        expect(abs(report["category_accuracy"] - (n - 2) / n) < 1e-9, f"类别准确率应为 {(n - 2) / n}（b1 错、b3 失败），实际 {report['category_accuracy']}")
        expect(abs(report["priority_accuracy"] - (n - 2) / n) < 1e-9, f"优先级准确率应为 {(n - 2) / n}（b2 错、b3 失败），实际 {report['priority_accuracy']}")
        expect(abs(report["exact_match"] - (n - 3) / n) < 1e-9, f"完全匹配率应为 {(n - 3) / n}，实际 {report['exact_match']}")
        expect(sorted(report["failures"]) == ["b1", "b2", "b3"], f"失败用例应为 b1、b2、b3，实际 {report['failures']}")
        expect(core.evaluate([], fake_extract)["n"] == 0, "空用例集不应崩溃")

    checker.check("01 解析裸 JSON 与代码块包裹的 JSON", parses_plain_and_fenced)
    checker.check("02 枚举、范围、类型、缺字段、长度都被拒绝", rejects_invalid_values)
    checker.check("03 校验失败后带着原因重试", retries_with_feedback)
    checker.check("04 重试次数有上限", retry_is_bounded)
    checker.check("05 模型异常不会抛出", model_exception_never_escapes)
    checker.check("06 评测脚本：准确率、完全匹配率与失败列表", evaluate_scores_correctly)
    return checker.report()


if __name__ == "__main__":
    raise SystemExit(main())
