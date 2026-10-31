"""L5.6 可观测性 gate：用 InMemorySpanExporter 收集 span，只检查属性与计算结果，不联网。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode

HERE = Path(__file__).resolve().parent
TRACE_ID = "0af7651916cd43dd8448eb211c80319c"
SPAN_ID = "b7ad6b7169203331"


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


class Gate:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, path: Path) -> int:
        passed = sum(row["ok"] for row in self.rows)
        for row in self.rows:
            print(f"[{'PASS' if row['ok'] else 'FAIL'}] {row['name']} {row['error']}")
        print(f"{passed}/{len(self.rows)} passed")
        report = {"gate": "L5.6-otel-observability", "module": str(path), "passed": passed,
                  "total": len(self.rows), "ok": passed == len(self.rows), "checks": self.rows}
        (HERE / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if report["ok"] else 1


def new_tracer():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("gate"), exporter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    path = Path(parser.parse_args().module).resolve()
    core = load_module(path)
    gate = Gate()

    def one_llm_span(**kwargs):
        tracer, exporter = new_tracer()
        with core.llm_span(tracer, operation="chat", model="demo-model", provider="custom") as span:
            if kwargs.get("body"):
                kwargs["body"](span)
        return exporter.get_finished_spans()[0]

    def llm_basic():
        span = one_llm_span()
        expect(span.name == "chat demo-model", f"span 名应为 'chat demo-model'，实际 {span.name!r}")
        expect(span.kind == SpanKind.CLIENT, f"kind 应为 CLIENT，实际 {span.kind}")
        attrs = dict(span.attributes)
        expect(attrs.get("gen_ai.operation.name") == "chat", f"缺 gen_ai.operation.name：{attrs}")
        expect(attrs.get("gen_ai.request.model") == "demo-model", f"缺 gen_ai.request.model：{attrs}")
        expect(attrs.get("gen_ai.provider.name") == "custom", f"缺 gen_ai.provider.name：{attrs}")

    def tool_basic():
        tracer, exporter = new_tracer()
        with core.tool_span(tracer, tool_name="lookup_order", call_id="call_9"):
            pass
        span = exporter.get_finished_spans()[0]
        expect(span.name == "execute_tool lookup_order", f"span 名不对：{span.name!r}")
        expect(span.kind == SpanKind.INTERNAL, f"kind 应为 INTERNAL，实际 {span.kind}")
        attrs = dict(span.attributes)
        expect(attrs.get("gen_ai.operation.name") == "execute_tool", f"操作名不对：{attrs}")
        expect(attrs.get("gen_ai.tool.name") == "lookup_order", f"缺工具名：{attrs}")
        expect(attrs.get("gen_ai.tool.call.id") == "call_9", f"缺调用 ID：{attrs}")

    def usage_with_cache():
        span = one_llm_span(body=lambda s: core.record_usage(s, core.Usage(100, 20, cached_input_tokens=60)))
        attrs = dict(span.attributes)
        expect(attrs.get("gen_ai.usage.input_tokens") == 100, f"input_tokens 应为 100（含缓存）：{attrs}")
        expect(attrs.get("gen_ai.usage.output_tokens") == 20, f"output_tokens 应为 20：{attrs}")
        expect(attrs.get("gen_ai.usage.cache_read.input_tokens") == 60, f"应用标准属性记录命中缓存：{attrs}")

    def usage_without_cache():
        span = one_llm_span(body=lambda s: core.record_usage(s, core.Usage(10, 2)))
        expect("gen_ai.usage.cache_read.input_tokens" not in span.attributes, "没有命中缓存时不应写 cache_read 属性")

    def error_recorded():
        secret = "SECRET-PROMPT-13812345678"

        def body(span):
            core.record_error(span, ValueError(secret))

        span = one_llm_span(body=body)
        expect(span.status.status_code == StatusCode.ERROR, "状态应为 ERROR")
        expect(span.attributes.get("error.type") == "ValueError", f"error.type 应为 ValueError：{dict(span.attributes)}")
        events = [e for e in span.events if e.name == "exception"]
        expect(len(events) == 1 and events[0].attributes.get("exception.type") == "ValueError", "应有一个带 exception.type 的 exception 事件")
        dump = repr((dict(span.attributes), [(e.name, dict(e.attributes)) for e in span.events], span.status.description))
        expect(secret not in dump, "异常消息（可能含 prompt）不得写入 span")
        expect("exception.stacktrace" not in dump, "堆栈（可能含本机路径）不得写入 span")

    def content_off():
        span = one_llm_span(body=lambda s: core.maybe_capture_content(
            s, "我的手机号 13812345678", "回答", capture=False, redact=lambda t: t))
        keys = set(span.attributes)
        expect("gen_ai.input.messages" not in keys and "gen_ai.output.messages" not in keys, f"capture=False 不得写正文：{keys}")

    def content_on():
        redact = lambda t: t.replace("13812345678", "[手机号]")  # noqa: E731
        span = one_llm_span(body=lambda s: core.maybe_capture_content(
            s, "我的手机号 13812345678", "好的 13812345678", capture=True, redact=redact))
        raw_in = span.attributes.get("gen_ai.input.messages")
        raw_out = span.attributes.get("gen_ai.output.messages")
        expect(isinstance(raw_in, str) and isinstance(raw_out, str), "两个正文属性都应是 JSON 字符串")
        expect("13812345678" not in raw_in + raw_out, "写入前必须先脱敏")
        message_in = json.loads(raw_in)
        expect(message_in == [{"role": "user", "parts": [{"type": "text", "content": "我的手机号 [手机号]"}]}], f"输入结构不对：{message_in}")
        expect(json.loads(raw_out)[0]["role"] == "assistant", "输出消息 role 应为 assistant")

    def inject_ok():
        sampled = core.inject_traceparent({"x": "1"}, TRACE_ID, SPAN_ID, True)
        expect(sampled.get("traceparent") == f"00-{TRACE_ID}-{SPAN_ID}-01", f"sampled 应写 01：{sampled}")
        expect(sampled.get("x") == "1", "应保留原有头")
        expect(core.inject_traceparent({}, TRACE_ID, SPAN_ID, False)["traceparent"].endswith("-00"), "未采样应写 00")
        original = {"a": "b"}
        core.inject_traceparent(original, TRACE_ID, SPAN_ID, True)
        expect(original == {"a": "b"}, "不得修改入参")

    def inject_bad():
        for trace_id, span_id in [("abc", SPAN_ID), (TRACE_ID, "xyz"), ("0" * 32, SPAN_ID), (TRACE_ID, "0" * 16), (TRACE_ID.upper(), SPAN_ID)]:
            try:
                core.inject_traceparent({}, trace_id, span_id, True)
            except ValueError:
                continue
            raise AssertionError(f"非法 ID 应抛 ValueError：{trace_id!r}, {span_id!r}")

    def extract_ok():
        expect(core.extract_traceparent({"traceparent": f"00-{TRACE_ID}-{SPAN_ID}-01"}) == (TRACE_ID, SPAN_ID, True), "应解析出采样标志为真")
        expect(core.extract_traceparent({"Traceparent": f"00-{TRACE_ID}-{SPAN_ID}-00"}) == (TRACE_ID, SPAN_ID, False), "头名应大小写不敏感，flags=00 为未采样")

    def extract_bad():
        bad = [{}, {"traceparent": "garbage"}, {"traceparent": f"01-{TRACE_ID}-{SPAN_ID}-01"},
               {"traceparent": f"00-{'0' * 32}-{SPAN_ID}-01"}, {"traceparent": f"00-{TRACE_ID}-{'0' * 16}-01"},
               {"traceparent": f"00-{TRACE_ID.upper()}-{SPAN_ID}-01"}, {"traceparent": f"00-{TRACE_ID}-{SPAN_ID}-1"},
               {"traceparent": f"00-{TRACE_ID[:-1]}-{SPAN_ID}-01"}]
        for headers in bad:
            expect(core.extract_traceparent(headers) is None, f"应返回 None：{headers}")

    def summarize():
        tracer, exporter = new_tracer()
        ms = 1_000_000
        root = tracer.start_span("handle_request", start_time=1_000 * ms)
        chat1 = tracer.start_span("chat demo-model", start_time=1_100 * ms)
        chat1.set_attribute("gen_ai.operation.name", "chat")
        chat1.set_attribute("gen_ai.usage.input_tokens", 100)
        chat1.set_attribute("gen_ai.usage.output_tokens", 20)
        chat1.end(end_time=1_400 * ms)
        tool = tracer.start_span("execute_tool lookup_order", start_time=1_150 * ms)
        tool.set_attribute("gen_ai.operation.name", "execute_tool")
        tool.end(end_time=1_200 * ms)
        chat2 = tracer.start_span("chat demo-model", start_time=1_500 * ms)
        chat2.set_attribute("gen_ai.operation.name", "chat")
        chat2.set_attribute("gen_ai.usage.input_tokens", 50)
        core.record_error(chat2, TimeoutError("x"))
        chat2.end(end_time=1_900 * ms)
        root.end(end_time=2_000 * ms)
        result = core.summarize_trace(list(exporter.get_finished_spans()))
        expect(result == {"total_ms": 1000, "llm_spans": 2, "tool_spans": 1, "tokens": 170, "error_spans": ["chat demo-model"]},
               f"汇总不对：{result}")
        empty = core.summarize_trace([])
        expect(empty["total_ms"] == 0 and empty["error_spans"] == [], f"空列表应返回 0 与空列表：{empty}")

    def nesting():
        tracer, exporter = new_tracer()
        with core.llm_span(tracer, operation="chat", model="m", provider="custom") as parent:
            parent_id = parent.get_span_context().span_id
            with core.tool_span(tracer, tool_name="t", call_id="c1"):
                pass
        by_name = {s.name: s for s in exporter.get_finished_spans()}
        child = by_name["execute_tool t"]
        expect(child.parent is not None and child.parent.span_id == parent_id, "工具 span 的父 span 应是外层的模型调用 span")
        expect(child.context.trace_id == by_name["chat m"].context.trace_id, "同一棵 trace 的 trace_id 应相同")

    gate.check("01 模型调用 span 名称、kind 与属性", llm_basic)
    gate.check("02 工具调用 span 名称与属性", tool_basic)
    gate.check("03 usage 与标准缓存属性", usage_with_cache)
    gate.check("04 未命中缓存时不写缓存属性", usage_without_cache)
    gate.check("05 错误状态与异常事件且不泄露内容", error_recorded)
    gate.check("06 默认不采集正文", content_off)
    gate.check("07 采集时先脱敏并按 role+parts 结构写入", content_on)
    gate.check("08 traceparent 写入格式", inject_ok)
    gate.check("09 非法 ID 写入时报错", inject_bad)
    gate.check("10 解析合法头", extract_ok)
    gate.check("11 非法头与全零 ID 返回 None", extract_bad)
    gate.check("12 trace 汇总数值", summarize)
    gate.check("13 工具 span 嵌套在模型调用 span 之下", nesting)
    return gate.report(path)


if __name__ == "__main__":
    raise SystemExit(main())
