"""章节 3.6 · 追踪与评测平台：OpenTelemetry GenAI 语义约定与可观测性
==========================================================
核心能力与架构演进：
1. 为什么脱离单一厂商平台，转向 OpenTelemetry（OTel）标准化追踪？
   - 传统方案将追踪深绑定在 LangSmith、Weights & Biases 等私有 SDK 中，造成厂商锁定（Vendor Lock-in）；
   - OpenTelemetry 是 CNCF 云原生计算基金会的跨语言、开放行业标准；
   - 统一协议（OTLP）可同时将调用链路无缝分流至 Langfuse、Phoenix、Jaeger、Datadog 等任意后端。
2. OpenTelemetry GenAI Semantic Conventions（生成式 AI 语义约定，2026 开发中标准）：
   - `gen_ai.system`: 模型厂商体系标识（如 openai、deepseek、anthropic 等）；
   - `gen_ai.operation.name`: 操作类别（chat、text_completion、embeddings 等）；
   - `gen_ai.request.model` / `gen_ai.response.model`: 请求与实际响应模型标识；
   - `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`: Token 消耗量指标；
   - `gen_ai.retrieval.documents_count`: 检索命中片段数量。
3. 隐私与数据安全脱敏：
   - Prompt 与生成的回答正文属于高敏感 PII，默认不采集（或占位脱敏）；
   - 仅在明确开启授权选项并脱敏后采集。

运行模式：
  默认离线控制台导出（无需外部 API Key 与网络，输出 Span 到 Console）：
    python tools/run_chapter.py 3.6 otel_tracing_eval.py
  指定 OTLP 端点（如本地部署的 Langfuse / Phoenix）：
    $env:OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
    python tools/run_chapter.py 3.6 otel_tracing_eval.py
  真实模型调用（需配置 API Key）：
    python tools/run_chapter.py 3.6 otel_tracing_eval.py --live
==========================================================
"""

from __future__ import annotations

import argparse
import os
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
        SAMPLE_DOC,
        chat_model_name,
        get_openai_client,
    )
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from common import (
        SAMPLE_DOC,
        chat_model_name,
        get_openai_client,
    )


# --------------------------- Tracer 初始化 ---------------------------

def setup_tracer(service_name: str = "rag-eval-service") -> trace.Tracer:
    """初始化并配置 TracerProvider 与导出器。

    默认使用 ConsoleSpanExporter 输出到控制台（离线无网络）。
    当检测到环境变量 OTEL_EXPORTER_OTLP_ENDPOINT 时，尝试配置 OTLP 导出器。
    """
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": "development",
    })

    provider = TracerProvider(resource=resource)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()

    if otlp_endpoint:
        try:
            # 优先尝试 gRPC 导出器，其次 HTTP 导出器
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )
                exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
                print(f"[OTel] 成功配置 OTLP gRPC 导出器 -> {otlp_endpoint}")
            except ImportError:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
                exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                print(f"[OTel] 成功配置 OTLP HTTP 导出器 -> {otlp_endpoint}")

            provider.add_span_processor(SimpleSpanProcessor(exporter))
        except Exception as exc:
            print(f"[OTel 告警] 配置 OTLP 导出器失败 ({exc})，降级为 ConsoleSpanExporter", file=sys.stderr)
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
    """离线确定性 RAG 调用链路（完整展示三层 Span 嵌套与 GenAI 语义约定属性）。"""
    with tracer.start_as_current_span("rag_pipeline") as root_span:
        root_span.set_attribute("pipeline.type", "standard_rag")
        root_span.set_attribute("user.query", question if capture_content else "[REDACTED]")

        # 1. 检索阶段 Span
        with tracer.start_as_current_span("rag_retrieval") as ret_span:
            ret_span.set_attribute("gen_ai.operation.name", "retrieval")
            ret_span.set_attribute("gen_ai.retrieval.top_k", 3)
            ret_span.set_attribute("gen_ai.retrieval.documents_count", 2)
            ret_span.set_attribute("retrieval.source", "test_doc.txt")
            time.sleep(0.005)  # 模拟检索微量耗时
            mock_context = "RAG 是检索增强生成，先从外部知识库检索相关分块，再拼装上下文交给大模型。"

        # 2. 上下文拼装阶段 Span
        with tracer.start_as_current_span("assemble_context") as ctx_span:
            ctx_span.set_attribute("context.char_count", len(mock_context))
            ctx_span.set_attribute("context.truncated", False)

        # 3. 语言模型推理阶段 Span (严格对齐 OTel GenAI 语义约定)
        with tracer.start_as_current_span("chat_completion") as llm_span:
            llm_span.set_attribute("gen_ai.system", "openai")
            llm_span.set_attribute("gen_ai.operation.name", "chat")
            llm_span.set_attribute("gen_ai.request.model", "deepseek-flash")
            llm_span.set_attribute("gen_ai.response.model", "deepseek-flash-2026")
            llm_span.set_attribute("gen_ai.request.temperature", 0.0)
            llm_span.set_attribute("gen_ai.usage.input_tokens", 85)
            llm_span.set_attribute("gen_ai.usage.output_tokens", 36)

            # 隐私合规约定：默认不写入真实 Prompt 与 Completion 正文
            if capture_content:
                llm_span.set_attribute("gen_ai.prompt", f"问题：{question}\n上下文：{mock_context}")
                llm_span.set_attribute("gen_ai.completion", "RAG 结合了外部检索与生成模型，能有效抑制幻觉。")
            else:
                llm_span.set_attribute("gen_ai.prompt.status", "redacted_for_privacy")
                llm_span.set_attribute("gen_ai.completion.status", "redacted_for_privacy")

            time.sleep(0.010)
            mock_answer = "RAG 结合了外部检索与生成模型，能有效抑制幻觉。【来源：test_doc.txt】"

        root_span.set_attribute("pipeline.success", True)
        return {
            "question": question,
            "answer": mock_answer,
            "mode": "scripted_offline",
            "spans_generated": ["rag_pipeline", "rag_retrieval", "assemble_context", "chat_completion"],
        }


def run_live_rag_with_trace(
    tracer: trace.Tracer,
    client: Any,
    model: str,
    question: str,
    capture_content: bool = False,
) -> dict[str, Any]:
    """在线真实调用并通过 OpenTelemetry 记录真实耗时与 Token 使用。"""
    with tracer.start_as_current_span("rag_pipeline") as root_span:
        root_span.set_attribute("pipeline.type", "live_rag")
        root_span.set_attribute("user.query", question if capture_content else "[REDACTED]")

        # 1. 真实检索（读取 SAMPLE_DOC 摘录）
        with tracer.start_as_current_span("rag_retrieval") as ret_span:
            ret_span.set_attribute("gen_ai.operation.name", "retrieval")
            context = "这是本地示例文档内容：RAG 系统先从向量知识库中召回上下文片段，再生成回答。"
            if SAMPLE_DOC.exists():
                context = SAMPLE_DOC.read_text(encoding="utf-8")[:500]
            ret_span.set_attribute("gen_ai.retrieval.documents_count", 1)
            ret_span.set_attribute("retrieval.source", str(SAMPLE_DOC.name))

        # 2. 上下文拼装
        with tracer.start_as_current_span("assemble_context") as ctx_span:
            ctx_span.set_attribute("context.char_count", len(context))
            prompt = f"请根据上下文简明回答问题：\n上下文：{context}\n问题：{question}\n请在句末标注【来源：{SAMPLE_DOC.name}】。"

        # 3. 真实模型生成与 Token 记录
        with tracer.start_as_current_span("chat_completion") as llm_span:
            llm_span.set_attribute("gen_ai.system", "openai")
            llm_span.set_attribute("gen_ai.operation.name", "chat")
            llm_span.set_attribute("gen_ai.request.model", model)
            llm_span.set_attribute("gen_ai.request.temperature", 0.0)

            t0 = time.perf_counter()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            dur_ms = (time.perf_counter() - t0) * 1000.0

            ans = response.choices[0].message.content or ""
            usage = response.usage
            in_tokens = usage.prompt_tokens if usage else 0
            out_tokens = usage.completion_tokens if usage else 0

            llm_span.set_attribute("gen_ai.response.model", response.model or model)
            llm_span.set_attribute("gen_ai.usage.input_tokens", in_tokens)
            llm_span.set_attribute("gen_ai.usage.output_tokens", out_tokens)
            llm_span.set_attribute("llm.latency_ms", dur_ms)

            if capture_content:
                llm_span.set_attribute("gen_ai.prompt", prompt)
                llm_span.set_attribute("gen_ai.completion", ans)
            else:
                llm_span.set_attribute("gen_ai.prompt.status", "redacted_for_privacy")
                llm_span.set_attribute("gen_ai.completion.status", "redacted_for_privacy")

        root_span.set_attribute("pipeline.success", True)
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
    print(f"正文采集策略: {'[开启正文采集]' if args.capture_content else '[默认脱敏保护: prompt/completion 不落盘]'}")

    tracer = setup_tracer()

    if not args.live:
        print("\n[模式说明] 当前为默认【离线控制台追踪】模式（未指定 --live）。")
        print("执行一次脚本化 RAG，生成标准 OpenTelemetry Spans 并输出到控制台：\n")
        res = run_scripted_rag_with_trace(tracer, args.query, capture_content=args.capture_content)
        print("\n--- 业务执行结果 ---")
        print(f"生成回答: {res['answer']}")
        print(f"生成的链路 Span: {res['spans_generated']}")
        print("\n[离线演练完成] 控制台上方已打印各 Span 的标准属性（gen_ai.*）。")
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
