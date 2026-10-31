"""章节 3.6 · 追踪与评测平台：OpenTelemetry GenAI 语义约定与可观测性
==========================================================
核心能力与架构演进：
1. 为什么脱离单一厂商平台，转向 OpenTelemetry（OTel）标准化追踪？
   - 传统方案将追踪深绑定在特定平台 SDK 中，带来厂商锁定（Vendor Lock-in）风险；
   - OpenTelemetry 是 CNCF 云原生计算基金会的跨语言、开放行业标准；
   - 统一协议（OTLP）可无缝将链路数据路由至 Langfuse、Phoenix、Jaeger、Datadog 等任意后端。
2. OpenTelemetry GenAI Semantic Conventions（生成式 AI 语义约定，规范来源：
   https://github.com/open-telemetry/semantic-conventions-genai，依据 commit 3fe84604a5，
   截至 2026-10-30 处于 Development 实验演进状态）：
   - `gen_ai.provider.name`: 模型提供方标识（如 deepseek、openai、anthropic；semconv v1.37.0+ 弃用 gen_ai.system）；
   - `gen_ai.operation.name`: 操作类别（chat、text_completion、embeddings、retrieval 等）；
   - `gen_ai.request.model` / `gen_ai.response.model`: 请求与实际响应模型标识；
   - `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`: Token 消耗量指标；
   - `gen_ai.response.finish_reasons`: 结束原因列表（如 ["stop"]）；
   - 检索 Span 规范：Span 名为 `retrieval {gen_ai.data_source.id}`，SpanKind 为 CLIENT，
     属性包含 `gen_ai.data_source.id` 与 `gen_ai.retrieval.top_k`；
   - 推理 Span 规范：Span 名为 `{gen_ai.operation.name} {gen_ai.request.model}`，SpanKind 为 CLIENT；
   - Agent 与工具调用：`invoke_agent`、`execute_tool` 两类操作，工具执行 Span 的 kind 为 INTERNAL；
   - 自定义属性约定：非官方约定的项目私有属性统一使用 `app.*` 前缀。
3. 隐私与数据安全脱敏：
   - Prompt 与生成的回答正文属于高敏感数据，默认不采集（使用 [REDACTED_BY_DEFAULT] 占位）；
   - 即使显式开启采集选项（--capture-content），也须先经过基础脱敏过滤器处理；
     正文按约定要求的 JSON schema（role + parts）序列化后写入 `gen_ai.input.messages` /
     `gen_ai.output.messages`；
   - 异常发生时，仅记录 error.type 与清洗后的错误描述，不写入包含本机文件路径的原始堆栈
     （stacktrace）：span 以 record_exception=False 创建，异常信息手动记录。

运行模式：
  默认离线控制台导出（无需外部 API Key 与网络，输出 Span 到 Console）：
    python tools/run_chapter.py 3.6 otel_tracing_eval.py
  指定 OTLP 端点（由 SDK 标准环境变量解析，支持 HTTP 与 gRPC）：
    $env:OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
    python tools/run_chapter.py 3.6 otel_tracing_eval.py
  真实模型调用（需配置 API Key）：
    python tools/run_chapter.py 3.6 otel_tracing_eval.py --live
==========================================================
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# 导入 OpenTelemetry 核心库
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

# 兼容 common 导入
try:
    from common import (
        LLM_PROVIDER,
        SAMPLE_DOC,
        chat_model_name,
        get_openai_client,
    )
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from common import (
        LLM_PROVIDER,
        SAMPLE_DOC,
        chat_model_name,
        get_openai_client,
    )


# 正文未采集时的统一占位符：README、workbook、代码与测试共用这一种写法。
REDACTED_PLACEHOLDER = "[REDACTED_BY_DEFAULT]"


# --------------------------- 脱敏与隐私辅助函数 ---------------------------

def sanitize_text(text: str) -> str:
    """基础脱敏过滤器：掩码常见敏感信息（API Key、邮箱、手机号等）。"""
    if not text:
        return ""
    # 掩码类似 sk-... 的 API 密钥
    scrubbed = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "sk-***", text)
    # 掩码电子邮箱
    scrubbed = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "***@***.com", scrubbed)
    # 掩码手机号
    scrubbed = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "1**********", scrubbed)
    return scrubbed


def build_input_messages_attr(question: str, context: str) -> str:
    """按 GenAI 输入消息 JSON schema（role + parts）序列化，记录到 span 时写成 JSON 字符串。"""
    messages = [
        {
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "content": sanitize_text(f"问题：{question}\n\n上下文：\n{context}"),
                }
            ],
        }
    ]
    return json.dumps(messages, ensure_ascii=False)


def build_output_messages_attr(answer: str) -> str:
    """按 GenAI 输出消息 JSON schema（role + parts）序列化模型回答。"""
    messages = [
        {
            "role": "assistant",
            "parts": [{"type": "text", "content": sanitize_text(answer)}],
        }
    ]
    return json.dumps(messages, ensure_ascii=False)


# 注册表中的提供商标识；azure 对应 azure.ai.openai，bedrock 对应 aws.bedrock。
_PROVIDER_NAMES = {
    "deepseek": "deepseek",
    "openai": "openai",
    "anthropic": "anthropic",
    "ollama": "ollama",
    "azure": "azure.ai.openai",
    "bedrock": "aws.bedrock",
}


def resolve_provider_name() -> str:
    """根据配置解析符合 OpenTelemetry GenAI 注册表的提供商标识。

    注册表见 semantic-conventions-genai 的 `docs/registry/attributes/gen-ai.md`。
    取不到注册表值时使用 `custom`，不把未知网关冒用成 `openai`。
    """
    prov = str(LLM_PROVIDER).strip().lower()
    if prov in _PROVIDER_NAMES:
        return _PROVIDER_NAMES[prov]

    # 兼容网关：只有能从地址明确判断厂商时才写具体值，否则保留 custom。
    base_url = (
        os.getenv("OPENAI_COMPATIBLE_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
        or ""
    ).lower()
    vendor_markers = {
        "deepseek": "deepseek",
        "anthropic": "anthropic",
        "moonshot": "moonshot_ai",
        "mistral": "mistral",
        "groq": "groq",
        "x.ai": "x_ai",
        "openai": "openai",
    }
    for marker, registry_name in vendor_markers.items():
        if marker in base_url:
            return registry_name
    return "custom"


# --------------------------- Tracer 初始化 ---------------------------

def setup_tracer(service_name: str = "rag-eval-service") -> trace.Tracer:
    """初始化并配置 TracerProvider 与导出器。

    默认使用 ConsoleSpanExporter 输出到控制台（离线无网络）。
    当检测到环境变量 OTEL_EXPORTER_OTLP_ENDPOINT 时，按标准 SDK 环境变量规则接入 OTLP 导出器。
    根据 OTEL_EXPORTER_OTLP_PROTOCOL 选择导出器协议（默认为 http/protobuf，适合 Langfuse 等）：
    - 不再在代码中写死 endpoint 或 insecure，完全遵循 OpenTelemetry 标准环境变量约定。
    """
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": "development",
    })

    provider = TracerProvider(resource=resource)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()

    if otlp_endpoint:
        protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf").strip().lower()
        exporter = None
        try:
            if "grpc" in protocol:
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                        OTLPSpanExporter,
                    )
                    exporter = OTLPSpanExporter()
                    print(f"[OTel] 成功配置 OTLP gRPC 导出器 (读取标准环境变量: {otlp_endpoint})")
                except ImportError:
                    print("[OTel 提示] 未安装 opentelemetry-exporter-otlp-proto-grpc，尝试 HTTP 导出器", file=sys.stderr)

            if exporter is None:
                try:
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                        OTLPSpanExporter,
                    )
                    exporter = OTLPSpanExporter()
                    print(f"[OTel] 成功配置 OTLP HTTP 导出器 (读取标准环境变量: {otlp_endpoint})")
                except ImportError:
                    print("[OTel 提示] 未安装 opentelemetry-exporter-otlp-proto-http，无法启用 OTLP HTTP 导出", file=sys.stderr)

            if exporter is not None:
                provider.add_span_processor(SimpleSpanProcessor(exporter))
            else:
                print("[OTel 告警] 未找到可用的 OTLP 导出器包，降级为控制台输出", file=sys.stderr)
                provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        except Exception as exc:
            print(f"[OTel 告警] 初始化 OTLP 导出器失败 ({exc})，降级为 ConsoleSpanExporter", file=sys.stderr)
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        # 默认离线控制台导出
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name, "1.0.0")


# --------------------------- 模拟与真实 RAG 执行流程 ---------------------------

def run_scripted_rag_with_trace(
    tracer: trace.Tracer,
    question: str,
    capture_content: bool = False,
) -> dict[str, Any]:
    """离线确定性 RAG 调用链路（完整展示三层 Span 嵌套与 GenAI 语义约定标准属性）。"""
    with tracer.start_as_current_span("rag_pipeline", kind=trace.SpanKind.INTERNAL) as root_span:
        root_span.set_attribute("app.pipeline.type", "standard_rag")
        root_span.set_attribute(
            "app.user.query",
            sanitize_text(question) if capture_content else REDACTED_PLACEHOLDER,
        )

        data_source_id = "test_doc.txt"
        mock_context = "RAG 是检索增强生成，先从外部知识库检索相关分块，再拼装上下文交给大模型。"

        # 1. 检索阶段 Span（对齐 GenAI semconv: retrieval {gen_ai.data_source.id}，kind SHOULD 为 CLIENT）
        retrieval_span_name = f"retrieval {data_source_id}"
        with tracer.start_as_current_span(retrieval_span_name, kind=trace.SpanKind.CLIENT) as ret_span:
            ret_span.set_attribute("gen_ai.operation.name", "retrieval")
            ret_span.set_attribute("gen_ai.data_source.id", data_source_id)
            ret_span.set_attribute("gen_ai.retrieval.top_k", 3)
            # 自定义属性统一使用 app.* 前缀，避免污染 gen_ai.* 命名空间
            ret_span.set_attribute("app.retrieval.chunk_count", 2)
            ret_span.set_attribute("app.retrieval.source", data_source_id)
            if capture_content:
                ret_span.set_attribute("gen_ai.retrieval.query.text", sanitize_text(question))
            time.sleep(0.005)  # 模拟检索微量耗时

        # 2. 上下文拼装阶段 Span（内部业务阶段使用 app.*）
        with tracer.start_as_current_span("assemble_context", kind=trace.SpanKind.INTERNAL) as ctx_span:
            ctx_span.set_attribute("app.context.char_count", len(mock_context))
            ctx_span.set_attribute("app.context.truncated", False)

        # 3. 语言模型推理阶段 Span（对齐 GenAI semconv: {gen_ai.operation.name} {gen_ai.request.model}，CLIENT 类型）
        model_name = "deepseek-flash"
        inference_span_name = f"chat {model_name}"
        with tracer.start_as_current_span(inference_span_name, kind=trace.SpanKind.CLIENT) as llm_span:
            llm_span.set_attribute("gen_ai.provider.name", "deepseek")
            llm_span.set_attribute("gen_ai.operation.name", "chat")
            llm_span.set_attribute("gen_ai.request.model", model_name)
            llm_span.set_attribute("gen_ai.response.model", f"{model_name}-2026")
            llm_span.set_attribute("gen_ai.request.temperature", 0.0)
            llm_span.set_attribute("gen_ai.usage.input_tokens", 85)
            llm_span.set_attribute("gen_ai.usage.output_tokens", 36)
            llm_span.set_attribute("gen_ai.response.finish_reasons", ["stop"])

            mock_answer = "RAG 结合了外部检索与生成模型，能有效抑制幻觉。【来源：test_doc.txt】"

            # 隐私合规约定：默认不写入真实 Prompt 与 Completion 正文
            if capture_content:
                llm_span.set_attribute(
                    "gen_ai.input.messages",
                    build_input_messages_attr(question, mock_context),
                )
                llm_span.set_attribute(
                    "gen_ai.output.messages",
                    build_output_messages_attr(mock_answer),
                )
            else:
                llm_span.set_attribute("app.prompt.status", REDACTED_PLACEHOLDER)
                llm_span.set_attribute("app.completion.status", REDACTED_PLACEHOLDER)
                llm_span.set_attribute("app.privacy.placeholder", REDACTED_PLACEHOLDER)

            time.sleep(0.010)

        root_span.set_attribute("app.pipeline.success", True)
        return {
            "question": question,
            "answer": mock_answer,
            "mode": "scripted_offline",
            "spans_generated": [
                "rag_pipeline",
                retrieval_span_name,
                "assemble_context",
                inference_span_name,
            ],
        }


def run_live_rag_with_trace(
    tracer: trace.Tracer,
    client: Any,
    model: str,
    question: str,
    capture_content: bool = False,
) -> dict[str, Any]:
    """在线真实调用并通过 OpenTelemetry 记录链路属性、耗时与 Token 使用。"""
    provider_name = resolve_provider_name()
    data_source_id = str(SAMPLE_DOC.name)

    # record_exception=False：异常只手动写 error.type 与状态，不把本机路径的 stacktrace 写进 span。
    with tracer.start_as_current_span(
        "rag_pipeline", kind=trace.SpanKind.INTERNAL, record_exception=False
    ) as root_span:
        root_span.set_attribute("app.pipeline.type", "live_rag")
        root_span.set_attribute(
            "app.user.query",
            sanitize_text(question) if capture_content else REDACTED_PLACEHOLDER,
        )

        # 1. 真实检索（读取 SAMPLE_DOC 摘录；kind SHOULD 为 CLIENT）
        retrieval_span_name = f"retrieval {data_source_id}"
        with tracer.start_as_current_span(retrieval_span_name, kind=trace.SpanKind.CLIENT) as ret_span:
            ret_span.set_attribute("gen_ai.operation.name", "retrieval")
            ret_span.set_attribute("gen_ai.data_source.id", data_source_id)
            ret_span.set_attribute("gen_ai.retrieval.top_k", 1)

            context = "这是本地示例文档内容：RAG 系统先从向量知识库中召回上下文片段，再生成回答。"
            if SAMPLE_DOC.exists():
                context = SAMPLE_DOC.read_text(encoding="utf-8")[:500]

            ret_span.set_attribute("app.retrieval.chunk_count", 1)
            ret_span.set_attribute("app.retrieval.source", data_source_id)
            if capture_content:
                ret_span.set_attribute("gen_ai.retrieval.query.text", sanitize_text(question))

        # 2. 上下文拼装
        with tracer.start_as_current_span("assemble_context", kind=trace.SpanKind.INTERNAL) as ctx_span:
            ctx_span.set_attribute("app.context.char_count", len(context))
            prompt = f"请根据上下文简明回答问题：\n上下文：{context}\n问题：{question}\n请在句末标注【来源：{SAMPLE_DOC.name}】。"

        # 3. 真实模型生成与 Token 记录
        inference_span_name = f"chat {model}"
        with tracer.start_as_current_span(
            inference_span_name, kind=trace.SpanKind.CLIENT, record_exception=False
        ) as llm_span:
            llm_span.set_attribute("gen_ai.provider.name", provider_name)
            llm_span.set_attribute("gen_ai.operation.name", "chat")
            llm_span.set_attribute("gen_ai.request.model", model)
            llm_span.set_attribute("gen_ai.request.temperature", 0.0)

            t0 = time.perf_counter()
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                )
            except Exception as exc:
                dur_ms = (time.perf_counter() - t0) * 1000.0
                llm_span.set_attribute("app.latency_ms", dur_ms)
                # 隐私防线：记录错误类型与脱敏描述，不记录包含本地路径的 stacktrace
                err_type = exc.__class__.__name__
                llm_span.set_attribute("error.type", err_type)
                llm_span.set_status(trace.StatusCode.ERROR, description=sanitize_text(str(exc)[:200]))
                root_span.set_attribute("app.pipeline.success", False)
                root_span.set_attribute("error.type", err_type)
                root_span.set_status(trace.StatusCode.ERROR, description=f"LLM call failed with {err_type}")
                raise

            dur_ms = (time.perf_counter() - t0) * 1000.0
            ans = response.choices[0].message.content or ""
            usage = response.usage
            in_tokens = usage.prompt_tokens if usage else 0
            out_tokens = usage.completion_tokens if usage else 0

            finish_reason = response.choices[0].finish_reason or "stop"
            llm_span.set_attribute("gen_ai.response.model", response.model or model)
            llm_span.set_attribute("gen_ai.usage.input_tokens", in_tokens)
            llm_span.set_attribute("gen_ai.usage.output_tokens", out_tokens)
            llm_span.set_attribute("gen_ai.response.finish_reasons", [str(finish_reason)])
            llm_span.set_attribute("app.latency_ms", dur_ms)

            if capture_content:
                llm_span.set_attribute(
                    "gen_ai.input.messages",
                    build_input_messages_attr(question, context),
                )
                llm_span.set_attribute(
                    "gen_ai.output.messages",
                    build_output_messages_attr(ans),
                )
            else:
                llm_span.set_attribute("app.prompt.status", REDACTED_PLACEHOLDER)
                llm_span.set_attribute("app.completion.status", REDACTED_PLACEHOLDER)
                llm_span.set_attribute("app.privacy.placeholder", REDACTED_PLACEHOLDER)

        root_span.set_attribute("app.pipeline.success", True)
        return {
            "question": question,
            "answer": ans,
            "latency_ms": dur_ms,
            "tokens": {"input": in_tokens, "output": out_tokens},
            "mode": "live",
        }


# --------------------------- 入口函数 ---------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="L3.7 OpenTelemetry GenAI 追踪与评测平台")
    parser.add_argument("--live", action="store_true", help="显式开启真实大模型在线调用")
    parser.add_argument("--capture-content", action="store_true", help="授权采集 Prompt/Completion 正文（用于调试；生产需脱敏）")
    parser.add_argument("--query", default="RAG 的基本组成部分是什么？", help="测试提问文本")
    args = parser.parse_args()

    print("==========================================================")
    print("  L3.7 追踪与评测平台（OpenTelemetry GenAI 语义约定标准）")
    print("==========================================================")
    print(f"当前输入问题: {args.query}")
    print(f"正文采集策略: {'[开启正文脱敏采集]' if args.capture_content else '[默认脱敏保护: [REDACTED_BY_DEFAULT]]'}")

    tracer = setup_tracer()

    if not args.live:
        print("\n[模式说明] 当前为默认【离线控制台追踪】模式（未指定 --live）。")
        print("执行一次脚本化 RAG，生成标准 OpenTelemetry Spans 并输出到控制台：\n")
        res = run_scripted_rag_with_trace(tracer, args.query, capture_content=args.capture_content)
        print("\n--- 业务执行结果 ---")
        print(f"生成回答: {res['answer']}")
        print(f"生成的链路 Span: {res['spans_generated']}")
        print("\n[离线演练完成] 控制台已输出各 Span 及其标准属性（gen_ai.*）。")
        return 0

    print("\n[在线模式] 正在初始化原生 OpenAI 客户端...")
    try:
        client = get_openai_client(timeout=30.0, max_retries=1)
        model = chat_model_name()
    except Exception as exc:
        print(f"[配置错误] 无法获取模型客户端或模型名称：{exc}", file=sys.stderr)
        print("请检查环境变量或 .env 配置。", file=sys.stderr)
        return 1

    try:
        print(f"使用模型: {model}，正在发起带 OTel 追踪的在线请求...")
        res = run_live_rag_with_trace(tracer, client, model, args.query, capture_content=args.capture_content)
        print("\n--- 在线调用结果 ---")
        print(f"回答: {res['answer']}")
        print(f"模型延迟: {res['latency_ms']:.1f}ms")
        print(f"消耗 Token: 输入={res['tokens']['input']}, 输出={res['tokens']['output']}")
    except Exception as exc:
        print(f"\n[运行失败] 在线请求过程中发生网络或模型错误：{exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
