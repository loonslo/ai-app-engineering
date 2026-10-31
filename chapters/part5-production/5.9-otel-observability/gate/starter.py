"""L5.6 可观测性：OpenTelemetry · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
otel_observability.py。实现下面的函数，然后运行：

    python chapters/part5-production/5.9-otel-observability/gate/gate_check.py

不允许为了通过而修改 gate_check.py。

属性名来自 OpenTelemetry GenAI 语义约定（独立仓库 open-telemetry/semantic-conventions-genai，
提交 3fe84604a5，读取于 2026-10-31；约定仍处于 Development 状态，升级时请对照官方文档重新核对）。
gate 用 opentelemetry-sdk 的 InMemorySpanExporter 收集 span，不联网。
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    input_tokens: int            # 总输入 token，已经包含命中缓存的部分
    output_tokens: int
    cached_input_tokens: int = 0


@contextmanager
def llm_span(tracer, *, operation: str, model: str, provider: str):
    """上下文管理器：创建并"进入"一个模型调用 span（嵌套在它里面的 span 会成为它的子 span），yield 该 span。

    - span 名为 f"{operation} {model}"，例如 "chat demo-model"；
    - kind 为 CLIENT；
    - 写入 gen_ai.operation.name = operation、gen_ai.request.model = model、gen_ai.provider.name = provider。
    """
    raise NotImplementedError("实现 llm_span")
    yield  # pragma: no cover


@contextmanager
def tool_span(tracer, *, tool_name: str, call_id: str):
    """上下文管理器：工具调用 span。

    - span 名为 f"execute_tool {tool_name}"，kind 为 INTERNAL；
    - 写入 gen_ai.operation.name = "execute_tool"、gen_ai.tool.name = tool_name、gen_ai.tool.call.id = call_id。
    """
    raise NotImplementedError("实现 tool_span")
    yield  # pragma: no cover


def record_usage(span, usage: Usage) -> None:
    """写入 gen_ai.usage.input_tokens 与 gen_ai.usage.output_tokens。

    cached_input_tokens > 0 时，再写标准属性 gen_ai.usage.cache_read.input_tokens（约定里它已被
    包含在 input_tokens 中，所以不要从 input_tokens 里扣）；为 0 时不写这个属性。
    """
    raise NotImplementedError("实现 record_usage")


def record_error(span, exc: BaseException) -> None:
    """把 span 标记为失败，但不泄露内容。

    - span 状态置为 ERROR（不带描述）；
    - 写 error.type = 异常类名（type(exc).__qualname__）；
    - 添加名为 "exception" 的事件，属性只有 exception.type（同样是类名）；
    - 不得写入异常消息和堆栈：消息里可能含 prompt，堆栈里可能含本机路径。
    """
    raise NotImplementedError("实现 record_error")


def maybe_capture_content(span, prompt: str, completion: str, *, capture: bool, redact: Callable[[str], str]) -> None:
    """capture 为假时什么都不写；为真时先经 redact 脱敏，再按 role + parts 的 JSON 结构写两个属性：

    - gen_ai.input.messages  = json.dumps([{"role": "user", "parts": [{"type": "text", "content": redact(prompt)}]}], ensure_ascii=False)
    - gen_ai.output.messages = json.dumps([{"role": "assistant", "parts": [{"type": "text", "content": redact(completion)}]}], ensure_ascii=False)
    """
    raise NotImplementedError("实现 maybe_capture_content")


def inject_traceparent(headers: dict, trace_id: str, span_id: str, sampled: bool) -> dict:
    """返回带 "traceparent" 头的新字典（不修改入参）：

    "00-<32 位小写十六进制 trace_id>-<16 位小写十六进制 span_id>-<01 或 00>"，sampled 为真写 01，否则 00。
    ID 长度或字符非法、或全为 0 时抛 ValueError。
    """
    raise NotImplementedError("实现 inject_traceparent")


def extract_traceparent(headers: dict) -> tuple[str, str, bool] | None:
    """解析 traceparent，返回 (trace_id, span_id, sampled)；头名按大小写不敏感查找。

    缺失、段数不是 4、版本不是 "00"、ID 长度/字符非法（含大写）、ID 全为 0、flags 不是两位十六进制时返回 None。
    sampled 取 flags 的最低位。
    """
    raise NotImplementedError("实现 extract_traceparent")


def summarize_trace(spans: list) -> dict:
    """spans 是 InMemorySpanExporter.get_finished_spans() 返回的已结束 span 列表。

    返回 {"total_ms", "llm_spans", "tool_spans", "tokens", "error_spans"}：
    - total_ms：最晚结束时间减最早开始时间，毫秒，取整数（四舍五入）；空列表为 0；
    - llm_spans：gen_ai.operation.name 为 "chat" 的 span 数；
    - tool_spans：gen_ai.operation.name 为 "execute_tool" 的 span 数；
    - tokens：所有 llm span 的 input_tokens 与 output_tokens 之和（没写的按 0）；
    - error_spans：状态为 ERROR 的 span 名字列表，按开始时间从早到晚。
    """
    raise NotImplementedError("实现 summarize_trace")
