"""OpenTelemetry 打点：检索、模型调用、工具调用各一个 span；记录 usage 与错误；不采集正文。

属性名依据 OpenTelemetry GenAI 语义约定（open-telemetry/semantic-conventions-genai，提交 3fe84604a5；
仍处于 Development 状态，升级时需重新核对）。写法与课程 5.9（L5.6）一致：
- 模型调用 span：`chat {model}`，CLIENT；usage 用 gen_ai.usage.*；
- 检索 span：`retrieval {data_source}`，CLIENT；
- 工具调用 span：`execute_tool {tool}`，INTERNAL；
- 错误只记 error.type 与 exception 事件里的类型名，不记异常消息与堆栈（可能含 prompt 或本机路径）；
- prompt 与回答从不写入 span。

默认不导出：没有配置时使用 OpenTelemetry 的 no-op tracer。CAPSTONE_OTEL=console 导出到控制台；
设置了 OTEL_EXPORTER_OTLP_ENDPOINT 时发送到 OTLP 后端（需要额外安装 opentelemetry-exporter-otlp-proto-http）。
未安装 opentelemetry-api 时本模块退化为空操作，不影响问答。
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.trace import SpanKind, Status, StatusCode
except ImportError:  # pragma: no cover - 取决于运行环境
    trace = None  # type: ignore[assignment]

TRACER_NAME = "capstone"
DATA_SOURCE_ID = "capstone-kb"
_tracer: Any = None

# gen_ai.provider.name 的注册值；未知的 OpenAI 兼容网关用 custom
_PROVIDER_NAMES = {"deepseek": "deepseek", "openai": "openai", "ollama": "ollama", "azure": "azure.ai.openai"}


class _NoopSpan:
    def set_attribute(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def set_status(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def add_event(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def use_tracer_provider(provider: Any | None) -> None:
    """显式指定 TracerProvider（测试用内存导出器）；传 None 恢复为全局 provider。"""
    global _tracer
    _tracer = provider.get_tracer(TRACER_NAME) if provider is not None else None


def _get_tracer() -> Any:
    if trace is None:
        return None
    return _tracer or trace.get_tracer(TRACER_NAME)


@contextmanager
def _span(name: str, kind_name: str) -> Iterator[Any]:
    tracer = _get_tracer()
    if tracer is None:
        yield _NoopSpan()
        return
    with tracer.start_as_current_span(
        name, kind=getattr(SpanKind, kind_name), record_exception=False, set_status_on_exception=False
    ) as span:
        yield span


def provider_name() -> str:
    return _PROVIDER_NAMES.get(os.getenv("LLM_PROVIDER", "deepseek").strip().lower(), "custom")


@contextmanager
def chat_span(model: str, request_id: str = "") -> Iterator[Any]:
    with _span(f"chat {model}", "CLIENT") as span:
        if request_id:
            span.set_attribute("app.request.id", request_id)  # 方便从 request_id 找到对应的 trace
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("gen_ai.provider.name", provider_name())
        yield span


@contextmanager
def retrieval_span(tenant_id: str, top_k: int) -> Iterator[Any]:
    with _span(f"retrieval {DATA_SOURCE_ID}", "CLIENT") as span:
        span.set_attribute("gen_ai.operation.name", "retrieval")
        span.set_attribute("gen_ai.data_source.id", DATA_SOURCE_ID)
        span.set_attribute("gen_ai.retrieval.top_k", top_k)
        span.set_attribute("app.tenant.id", tenant_id)
        yield span


@contextmanager
def tool_span(tool_name: str, call_id: str) -> Iterator[Any]:
    with _span(f"execute_tool {tool_name}", "INTERNAL") as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", tool_name)
        span.set_attribute("gen_ai.tool.call.id", call_id)
        yield span


def record_chat_reply(span: Any, reply: Any) -> None:
    span.set_attribute("gen_ai.usage.input_tokens", reply.input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", reply.output_tokens)
    if reply.model:
        span.set_attribute("gen_ai.response.model", reply.model)
    if reply.degraded:
        span.set_attribute("app.degraded", True)


def record_error(span: Any, exc: BaseException) -> None:
    type_name = type(exc).__qualname__
    if trace is not None:
        span.set_status(Status(StatusCode.ERROR))
    span.set_attribute("error.type", type_name)
    span.add_event("exception", {"exception.type": type_name})


def configure_tracing() -> str:
    """按环境变量配置导出；返回 "off" / "console" / "otlp"。重复调用无副作用。"""
    if trace is None:
        return "off"
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    mode = os.getenv("CAPSTONE_OTEL", "").strip().lower()
    if not endpoint and mode != "console":
        return "off"
    if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

        provider = TracerProvider()
        if endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        else:
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
    return "otlp" if endpoint else "console"
