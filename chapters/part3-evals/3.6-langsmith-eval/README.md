# 3.6 追踪与评测平台：OpenTelemetry 与现代 AI 可观测性

[全书目录](../../README.md) · [上一章 3.5](../3.5-eval-dataset-ragas/README.md) · [下一章 3.7](../3.7-eval-regression-curve/README.md)

- **目标**：理解现代 AI 应用可观测性体系，使用 OpenTelemetry GenAI 语义约定为 RAG 调用链打上标准化追踪（Trace 与 Span），了解主流评测后端定位与隐私防线。
- **v2 路径**：L3.6 / 核心（清单验收；LangSmith 外部服务）
- **验收方式**：使用 [清单](gate/CHECKLIST.md) 与 [workbook](workbook.md) 核对；运行本地 `otel_tracing_eval.py` 观察 Span 属性；不提供离线 `gate_check.py`（L5.6 将用自动化 Gate 深入练习）。
- **前置**：2.6；3.4、3.5。
- **环境**：默认完全离线运行（控制台导出），不依赖任何网络与外部 API Key；若指定 `OTEL_EXPORTER_OTLP_ENDPOINT` 可上报至本地或远程后端；若带 `--live` 可调用真实模型。
- **命令**：`python tools/run_chapter.py 3.6 otel_tracing_eval.py`

> [!NOTE]
> **关于目录历史名称**：本目录命名 `3.6-langsmith-eval` 为历史遗留命名（早期版本主要介绍 LangSmith 专有平台）。在 v3 课程体系中，本章升级为基于 OpenTelemetry 开放标准的现代 AI 追踪与评测平台体系。

## 问题

RAG 或 Agent 产生错误回答时，你往往想知道：
1. 错误出在检索阶段（召回了不相关片段），还是生成阶段（检索正确但模型偏离上下文）？
2. 一次调用的端到端耗时中，向量检索、重排、拼装 Prompt、LLM 生成各占多大比例？
3. 调用的 Token 消耗量与成本随时间如何波动？

如果在代码中手工写 `print()` 或 `logger.info()`，日志分散、缺乏层级嵌套，且难以与微服务分布式追踪链路串联；若直接深度绑定特定商业平台 SDK，又会面临厂商锁定（Vendor Lock-in）风险。我们需要开放、标准化的调用链路回放方案。

## 概念

### 1. OpenTelemetry GenAI 语义约定（Semantic Conventions）

[OpenTelemetry (OTel)](https://opentelemetry.io/) 是云原生计算基金会（CNCF）的跨语言标准化可观测性框架。

为了统一不同 LLM 框架与模型的追踪口径，OpenTelemetry 制定了专门的 **GenAI Semantic Conventions**（来源：OpenTelemetry 官方规范 [Semantic Conventions for GenAI Operations](https://opentelemetry.io/docs/specs/semconv/gen-ai/)，截至 2026-10-30 仍处于 Development 实验性演进状态）。它规范了生成式 AI 调用的标准命名空间 `gen_ai.*`：

- `gen_ai.system`: 模型提供方标识（如 `openai`、`deepseek`、`anthropic`）。
- `gen_ai.operation.name`: 操作类别（如 `chat`、`text_completion`、`embeddings`）。
- `gen_ai.request.model` / `gen_ai.response.model`: 请求模型与实际返回模型。
- `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`: 消耗的 Prompt Token 与 Completion Token。
- `gen_ai.retrieval.documents_count`: 检索命中片段数。

### 2. 三大主流可观测性平台定位

通过 OpenTelemetry 标准协议（OTLP），同一份业务追踪代码可以无缝接入多种平台：

| 平台 | 协议与生态 | 开源协议与部署 | 适用场景 |
| :--- | :--- | :--- | :--- |
| **Langfuse** | 原生兼容 OTLP，支持 SDK 导入 | MIT 开源，支持 Docker / K8s 完全自托管 | 追求数据私有化、企业合规与成本可控的研发团队（Stack Overflow 2026 调查显示在自建栈中关注度迅速上升） |
| **LangSmith** | LangChain / LangGraph 深度原生整合，支持 OTLP 摄取 | 商业托管 SaaS，混合部署需企业版 | 深度使用 LangChain 全家桶、需在线标注/在线评测流水线的团队 |
| **Phoenix (Arize)** | 原生基于 OpenTelemetry 架构 | 开源，单机/集群自托管或 SaaS | 专注于 RAG 检索深度评估、Embedding 漂移分析与可解释性的团队 |

### 3. 该追踪什么（What to Trace）

生产级 AI 应用必须追踪的核心维度：
1. **LLM 调用**：使用的模型名称、温度等参数、输入/输出 Token 数量、完成原因（finish_reason）。
2. **工具调用（Tool Calls）**：调用的工具名称、输入参数结构、返回结果状态与耗时。
3. **检索操作（Retrieval）**：检索 Query、命中片段数量（`documents_count`）、召回文档的得分与元数据。
4. **延迟分布（Latency）**：整个 Pipeline 的端到端耗时，以及检索、Prompt 组装、网络等待各个子 Span 的细分耗时。
5. **异常与错误（Errors）**：网络超时、超额限流（RateLimit 429）、模型内容审核拒绝等异常堆栈。

### 4. 隐私防线（Privacy & Security）

> [!CAUTION]
> **默认不采集 Prompt 与回答明文！**
> 真实生产环境中，用户输入可能包含个人隐私（PII）、敏感商业数据或合规受限信息。
> 1. 追踪平台默认只记录 `gen_ai.*` 的元数据与 Token 统计，对具体内容做脱敏处理或占位掩码（如 `[REDACTED_BY_DEFAULT]`）。
> 2. 只有在经过合规脱敏过滤器，且明确开启调试开关时，才记录脱敏后的内容。
> 3. 严禁将 API Key、鉴权 Token 记录到 Span 属性中。

## 代码导读

本章提供两个实现文件：
1. [otel_tracing_eval.py](otel_tracing_eval.py)（**推荐，v3 核心**）：
   - 基于原生 OpenTelemetry SDK 实现完整 RAG 链路追踪（`rag_pipeline` 根 Span -> `rag_retrieval` -> `assemble_context` -> `chat_completion`）。
   - 默认使用 `ConsoleSpanExporter` 离线向终端打印结构化 Span，完全零网络、零外部依赖；
   - 若设置环境变量 `OTEL_EXPORTER_OTLP_ENDPOINT`，则自动切换为标准 OTLP 导出器发送到后台；
   - 默认开启隐私掩码，保护敏感内容。
2. [langsmith_eval.py](langsmith_eval.py)（平台示例）：
   - 保留作为平台端 SDK 接入示例，展示如何用 `langsmith` 跑在线 Dataset 与 Experiment。

## 练习与清单验收

请按照 [gate/CHECKLIST.md](gate/CHECKLIST.md) 的 4 项要点进行核对，并在 [workbook.md](workbook.md) 中记录你的回答与观察。

> [!TIP]
> 本章旨在建立标准化的可观测性认知与开发习惯；在后续阶段（L5.6），我们将结合更复杂的 Agent 多跳决策，引入自动化断言 Gate 检验 Trace 属性。
