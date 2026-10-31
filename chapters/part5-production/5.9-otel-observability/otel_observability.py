"""
章节 5.9（L5.6）· 可观测性：用 OpenTelemetry 给模型调用和工具调用打点
==========================================================
一次脚本化的 RAG + 工具调用，打成这样一棵 trace：

    handle_request                      （INTERNAL，业务入口）
    ├── chat demo-model                 （CLIENT，模型调用：usage、可选的正文）
    │   └── execute_tool lookup_order   （INTERNAL，工具调用）
    └── chat demo-model                 （第二次模型调用：脚本里让它失败一次，演示错误怎么记）

属性名来自 OpenTelemetry GenAI 语义约定（独立仓库 open-telemetry/semantic-conventions-genai，
提交 3fe84604a5，读取于 2026-10-31；约定仍处于 Development 状态，升级后要重新核对）。

默认输出到控制台，不联网、不需要密钥。设置了 OTEL_EXPORTER_OTLP_ENDPOINT 时发送到后端
（Langfuse、Phoenix、LangSmith、Datadog 等都能接收 OTLP）；这需要额外安装
opentelemetry-exporter-otlp-proto-http，课程依赖里没有锁定它，所以是可选的。

运行：python tools/run_chapter.py 5.9
      python tools/run_chapter.py 5.9 --capture-content   （采集正文：先脱敏，仅用于排查）
==========================================================
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, Status, StatusCode


@dataclass(frozen=True)
class Usage:
    input_tokens: int            # 总输入 token，已经包含命中缓存的部分
    output_tokens: int
    cached_input_tokens: int = 0


@contextmanager
def llm_span(tracer, *, operation: str, model: str, provider: str):
    """模型调用 span：名字 "{operation} {model}"，CLIENT。start_as_current_span 让里面的 span 自动成为子 span。"""
    with tracer.start_as_current_span(f"{operation} {model}", kind=SpanKind.CLIENT, record_exception=False,
                                      set_status_on_exception=False) as span:
        span.set_attribute("gen_ai.operation.name", operation)
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("gen_ai.provider.name", provider)
        yield span


@contextmanager
def tool_span(tracer, *, tool_name: str, call_id: str):
    """工具调用 span：名字 "execute_tool {tool_name}"，INTERNAL。"""
    with tracer.start_as_current_span(f"execute_tool {tool_name}", kind=SpanKind.INTERNAL, record_exception=False,
                                      set_status_on_exception=False) as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", tool_name)
        span.set_attribute("gen_ai.tool.call.id", call_id)
        yield span


def record_usage(span, usage: Usage) -> None:
    """input_tokens 已包含命中缓存的部分；命中缓存的 token 用标准属性 cache_read 单独标出来。"""
    span.set_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", usage.output_tokens)
    if usage.cached_input_tokens > 0:
        span.set_attribute("gen_ai.usage.cache_read.input_tokens", usage.cached_input_tokens)


def record_error(span, exc: BaseException) -> None:
    """只记类型，不记消息和堆栈：消息里可能有 prompt，堆栈里可能有本机路径。

    这就是为什么上面创建 span 时要关掉 record_exception 和 set_status_on_exception：
    SDK 默认会把 exception.message / exception.stacktrace 都写进事件。
    """
    type_name = type(exc).__qualname__
    span.set_status(Status(StatusCode.ERROR))
    span.set_attribute("error.type", type_name)
    span.add_event("exception", {"exception.type": type_name})


def maybe_capture_content(span, prompt: str, completion: str, *, capture: bool, redact: Callable[[str], str]) -> None:
    """正文默认不采集；要采集时先脱敏，并按语义约定的 role + parts 结构写成 JSON 字符串。"""
    if not capture:
        return
    span.set_attribute("gen_ai.input.messages", json.dumps(
        [{"role": "user", "parts": [{"type": "text", "content": redact(prompt)}]}], ensure_ascii=False))
    span.set_attribute("gen_ai.output.messages", json.dumps(
        [{"role": "assistant", "parts": [{"type": "text", "content": redact(completion)}]}], ensure_ascii=False))


_HEX = re.compile(r"[0-9a-f]+")


def _valid_id(value: str, length: int) -> bool:
    return len(value) == length and _HEX.fullmatch(value) is not None and set(value) != {"0"}


def inject_traceparent(headers: dict, trace_id: str, span_id: str, sampled: bool) -> dict:
    """W3C Trace Context：traceparent = version-trace_id-parent_id-flags。"""
    if not _valid_id(trace_id, 32) or not _valid_id(span_id, 16):
        raise ValueError("trace_id 须为 32 位、span_id 须为 16 位小写十六进制，且不能全为 0")
    return {**headers, "traceparent": f"00-{trace_id}-{span_id}-{'01' if sampled else '00'}"}


def extract_traceparent(headers: dict) -> tuple[str, str, bool] | None:
    value = next((v for k, v in headers.items() if k.lower() == "traceparent"), None)
    if not isinstance(value, str):
        return None
    parts = value.split("-")
    if len(parts) != 4 or parts[0] != "00":
        return None
    _, trace_id, span_id, flags = parts
    if not _valid_id(trace_id, 32) or not _valid_id(span_id, 16) or len(flags) != 2 or not _HEX.fullmatch(flags):
        return None
    return trace_id, span_id, bool(int(flags, 16) & 1)


def summarize_trace(spans: list) -> dict:
    """从一批已结束的 span 里读出排查需要的几个数：多慢、几次模型调用、几次工具、多少 token、谁出错。"""
    if not spans:
        return {"total_ms": 0, "llm_spans": 0, "tool_spans": 0, "tokens": 0, "error_spans": []}
    total_ns = max(s.end_time for s in spans) - min(s.start_time for s in spans)
    llm = [s for s in spans if s.attributes.get("gen_ai.operation.name") == "chat"]
    tools = [s for s in spans if s.attributes.get("gen_ai.operation.name") == "execute_tool"]
    tokens = sum(int(s.attributes.get("gen_ai.usage.input_tokens", 0)) + int(s.attributes.get("gen_ai.usage.output_tokens", 0))
                 for s in llm)
    errors = [s.name for s in sorted(spans, key=lambda s: s.start_time) if s.status.status_code == StatusCode.ERROR]
    return {"total_ms": round(total_ns / 1_000_000), "llm_spans": len(llm), "tool_spans": len(tools),
            "tokens": tokens, "error_spans": errors}


# ---------------------------------------------------------------- 演示 ----
def redact(text: str) -> str:
    """演示用的脱敏：手机号和邮箱。真实系统用 5.7 的 mask_pii。"""
    text = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[手机号]", text)
    return re.sub(r"[\w.\-+]+@[\w\-]+(?:\.[\w\-]+)+", "[邮箱]", text)


def _console_line(span) -> str:
    return span.to_json(indent=None) + "\n"


def build_provider() -> TracerProvider:
    provider = TracerProvider()
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # 可选依赖

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))  # 端点、头从 OTEL_* 环境变量读
        print(f"[OTel] 发送到 OTLP 端点：{endpoint}")
    else:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(formatter=_console_line)))
    return provider


def run_scripted_request(tracer, *, capture_content: bool) -> None:
    """脚本化的一次请求：模型决定调工具 → 工具 → 第二次模型调用失败。没有任何真实网络调用。"""
    question = "我的订单 A100 到哪了？我的手机号 13812345678"
    with tracer.start_as_current_span("handle_request"):
        with llm_span(tracer, operation="chat", model="demo-model", provider="custom") as span:
            with tool_span(tracer, tool_name="lookup_order", call_id="call_1"):
                pass  # 真实代码在这里查订单
            record_usage(span, Usage(input_tokens=120, output_tokens=30, cached_input_tokens=80))
            maybe_capture_content(span, question, "订单 A100 已发货。", capture=capture_content, redact=redact)
        try:
            with llm_span(tracer, operation="chat", model="demo-model", provider="custom") as span:
                try:
                    raise TimeoutError("上游超时：prompt=我的手机号 13812345678")  # 脚本化的失败
                except TimeoutError as exc:
                    record_error(span, exc)
                    raise
        except TimeoutError:
            pass  # 业务层决定降级；trace 里已经有这次失败


def main() -> int:
    parser = argparse.ArgumentParser(description="5.9 OpenTelemetry 可观测性演示")
    parser.add_argument("--capture-content", action="store_true", help="采集（脱敏后的）prompt 与回答")
    args = parser.parse_args()
    try:
        provider = build_provider()
    except ImportError:
        print("设置了 OTEL_EXPORTER_OTLP_ENDPOINT，但没有安装 opentelemetry-exporter-otlp-proto-http；"
              "先安装它，或取消该环境变量使用控制台输出。", file=sys.stderr)
        return 1
    memory = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(memory))  # 同时留一份内存副本，用来汇总
    tracer = provider.get_tracer("course.5.9")
    run_scripted_request(tracer, capture_content=args.capture_content)
    provider.force_flush()
    print("\n汇总：", summarize_trace(list(memory.get_finished_spans())))
    print("提示：error span 里只有 error.type，没有异常消息，也没有 prompt 里的手机号。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ----------------------------------------------------------
# 10 分钟定位一次故障的排查顺序：
#   1. 用户给你 trace_id（5.1 的响应头 X-Trace-Id）→ 在后端搜到整棵 trace；
#   2. 先看总耗时与最长的 span：慢在模型、检索还是工具；
#   3. 找状态为 ERROR 的 span 与 error.type：超时、429、5xx、解析失败；
#   4. 看 usage：token 是否异常膨胀、缓存是否命中（cache_read 占比）；
#   5. 需要正文时，只在能打开采集开关的环境里复现，别在线上长期开。
# ----------------------------------------------------------
