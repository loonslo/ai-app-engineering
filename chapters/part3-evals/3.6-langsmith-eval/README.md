# 3.6 追踪与评测平台：OpenTelemetry 与现代 AI 可观测性

[全书目录](../../README.md) · [上一章 L3.6（3.10）](../3.10-eval-report-failures/README.md) · [下一章 L4.1](../../part4-agents-langgraph/4.1-agent-patterns/README.md)

- **目标**：理解现代 AI 应用可观测性体系，使用 OpenTelemetry GenAI 语义约定为 RAG 调用链打上标准化追踪（Trace 与 Span），了解主流评测后端定位与隐私防线。
- **v2 路径**：L3.6 / 核心（清单验收；LangSmith 外部服务）
- **v3 路径**：L3.7 / 核心（清单验收）
- **岗位任务 / 面试题型**：T4、T5 / F5
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

如果在代码中手工写 `print()` 或 `logger.info()`，日志分散、缺乏层级嵌套，且难以与分布式微服务链路串联；若直接深度绑定特定商业平台私有 SDK，又会面临厂商锁定（Vendor Lock-in）风险。我们需要开放、标准化的调用链路追踪方案。

## 概念

### 1. OpenTelemetry GenAI 语义约定（Semantic Conventions）

[OpenTelemetry (OTel)](https://opentelemetry.io/) 是云原生计算基金会（CNCF）的跨语言标准化可观测性框架。

为了统一不同 LLM 框架与模型的追踪口径，OpenTelemetry 社区在独立仓库维护了专门的生成式 AI 语义约定（规范来源：[open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai)，依据 commit `3fe84604a5`，截至 2026-10-30 仍处于 Development 实验性演进状态）。它规范了生成式 AI 调用的标准命名空间 `gen_ai.*`：

- **提供商**：`gen_ai.provider.name`（在 semconv v1.37.0 中已替代旧的 `gen_ai.system`，如 `deepseek`、`openai`、`anthropic`）。取值按注册表：`azure` 记为 `azure.ai.openai`，Bedrock 记为 `aws.bedrock`；兼容网关无法从地址判断厂商时记 `custom`，不冒用 `openai`。
- **操作类型**：`gen_ai.operation.name`（如 `chat`、`text_completion`、`retrieval`）。
- **模型标识**：`gen_ai.request.model` / `gen_ai.response.model`（请求模型与实际返回模型）。
- **Token 消耗**：`gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`（约定中无 `total_tokens`，需由调用方按需计算）。
- **结束原因**：`gen_ai.response.finish_reasons`（复数，字符串数组，如 `["stop"]`）。
- **检索 Span 规范**：
  - Span 名称规范为 `retrieval {gen_ai.data_source.id}`（如 `retrieval test_doc.txt`）；
  - Span 类型 SHOULD 为 `SpanKind.CLIENT`（规范原文为 “Span kind SHOULD be `CLIENT`”，见 `gen-ai-spans.md` 的 Retrievals 一节）；
  - 属性包含 `gen_ai.operation.name = "retrieval"`、`gen_ai.data_source.id` 与 `gen_ai.retrieval.top_k`（约定中不存在 `documents_count`）；
  - 授权采集时可记录 `gen_ai.retrieval.query.text`。
- **推理 Span 规范**：
  - Span 名称规范为 `{gen_ai.operation.name} {gen_ai.request.model}`（如 `chat deepseek-flash`）；
  - 远程大模型调用设为 `SpanKind.CLIENT`。
- **Agent 与工具调用 Span 规范**（[gen-ai-agent-spans.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/3fe84604a5/docs/gen-ai/gen-ai-agent-spans.md)，读取于 2026-10-31）：
  - `invoke_agent`：远程 Agent 调用 kind 为 `CLIENT`，进程内 Agent 循环 kind 为 `INTERNAL`；span 名优先为 `invoke_agent {gen_ai.agent.name}`，取不到名称时用 `invoke_agent`；常用属性有 `gen_ai.agent.name`、`gen_ai.agent.id`、`gen_ai.agent.version`、`gen_ai.conversation.id`。
  - `execute_tool`：kind SHOULD 为 `INTERNAL`；span 名 `execute_tool {gen_ai.tool.name}`；必需属性 `gen_ai.tool.name`，条件属性 `gen_ai.tool.call.id`、`gen_ai.agent.name`，推荐属性 `gen_ai.tool.type`、`gen_ai.tool.description`。
  - 工具参数 `gen_ai.tool.call.arguments` 与结果 `gen_ai.tool.call.result` 属于 Opt-In 内容，采集时按各自 JSON schema 记录；没有真实工具调用时不要凭空造这两个属性。
- **内容属性演进**：旧版的 `gen_ai.prompt` 与 `gen_ai.completion` 已被废弃并移除，正文采集改用 `gen_ai.input.messages` 与 `gen_ai.output.messages`。两者 MUST 遵循约定的 JSON schema：消息数组，每条消息含 `role` 与 `parts`（文本部分为 `{"type": "text", "content": ...}`）；记录在 span 上时写成 JSON 字符串。
- **自定义属性原则**：凡不属于官方标准约定的私有属性（如脱敏状态、业务流水线类型），统一使用自有前缀 `app.*`（如 `app.pipeline.type`、`app.prompt.status`），避免私造 `gen_ai.*` 属性导致与未来标准冲突。

### 2. 三大主流可观测性平台定位与选型

通过 OpenTelemetry 标准协议（OTLP），同一套业务追踪代码可以无缝分流至不同后端：

| 平台 | 协议与生态 | 许可证与部署模式 | 适用场景 |
| :--- | :--- | :--- | :--- |
| **Langfuse** | 原生兼容 OTLP/HTTP，支持 SDK 接入 | **MIT 开源**，支持 Docker / K8s 完全私有化部署 | 追求数据隐私、企业合规与成本可控的团队（注：当前仅支持 OTLP/HTTP，暂不支持 gRPC） |
| **LangSmith** | LangChain / LangGraph 深度原生整合，支持 OTLP 摄取 | 商业托管 SaaS，混合部署需企业版 | 深度依赖 LangChain 生态、需要网页端多人标注与评测集管理的团队 |
| **Phoenix (Arize)** | 原生基于 OpenTelemetry 架构 | **Elastic License 2.0 (ELv2)** 源码可用（非 OSI 纯开源） | 专注于 RAG 检索深度评估、Embedding 漂移分析与可解释性的团队 |

> **行业数据参考**：Stack Overflow 2026 年开发者调查 AI 章节的 [AI agent observability and security](https://survey.stackoverflow.co/2026/ai/data/ai-obs) 数据页（读取于 2026-10-31）。样本是回答“过去一年是否用过以下 AI agent 可观测性、提示词或评测工具”这道题的 2,277 名受访者，不是“使用 AI 工具的专业开发者”总数。该样本中 LangSmith 使用率为 17.3%，Langfuse 为 15.2%，Arize AI 为 5.8%（Phoenix 未单列）。

### 3. 离线评测与在线评测在平台的哪一环

- **离线评测（Offline Evals）**：代码提交前或在 CI 流水线中运行。基于固定的测试集（如 3.4/3.5 的评测集），计算准确率、召回率、pass@k 与回归告警（3.7）。离线评测结果决定“代码能否合并或发布”。
- **在线评测（Online Evals）**：生产服务发布后，在可观测性平台中基于实时调用 Trace 构建数据集（Dataset），创建实验对比（Experiment），并通过 LLM 裁判或人工抽检持续监控质量。在线评测负责“发现线上长尾问题与模型漂移”。

### 4. 隐私防线（Privacy & Security）

在生产环境中，可观测性追踪必须严格遵守数据安全防线：
1. **默认不采集明文**：用户输入可能包含个人身份信息（PII）、敏感凭据或商业机密。追踪平台默认仅记录 Token 数量与模型元数据，对正文使用 `[REDACTED_BY_DEFAULT]` 占位掩码；代码里 `app.prompt.status`、`app.completion.status` 与 `app.privacy.placeholder` 使用同一个占位符，README、workbook 与测试不再各写一种；
2. **脱敏过滤与 schema**：即使显式开启调试采集（`--capture-content`），也必须先经过基础脱敏过滤器处理（如掩码 API Key、邮箱、手机号）。`gen_ai.input.messages` 与 `gen_ai.output.messages` 按约定 MUST 遵循的 JSON schema（`role` + `parts`）序列化后写入，不能写成 `["user: …"]` 这样的字符串列表；
3. **异常堆栈防泄漏**：Span 记录异常事件时，若直接写入包含本机文件路径的完整 stacktrace，极易泄漏内部文件系统结构和变量。本章的 span 以 `record_exception=False` 创建，异常路径只手动记录 `error.type` 与清洗后的状态描述，不写入 `exception.stacktrace`；
4. **第三方云服务边界**：使用外部 SaaS 平台（如 LangSmith 云端）会把 Prompt、上下文与回答发送至第三方服务器，处理生产或内部数据前须确认合规授权。

## 流程

1. **本地离线验证**：运行 `python tools/run_chapter.py 3.6 otel_tracing_eval.py`，观察控制台输出的根 Span 与子 Span 嵌套结构；
2. **核对属性**：对照 GenAI 规范核对 `gen_ai.provider.name`、`SpanKind.CLIENT` 等标准字段；
3. **（可选）OTLP 上报**：配置环境变量 `OTEL_EXPORTER_OTLP_ENDPOINT`（如本地部署的 Langfuse 或 Phoenix），通过 OTLP 导出器发送；
4. **（平台示例）**：若需体验商业平台专有 SDK，可运行 `langsmith_eval.py`（需配置对应密钥并加 `--live`）。

## 产物与验收

- **产物**：在 [workbook.md](workbook.md) 中记录 Span 结构观察、项目核心追踪字段设计以及隐私防线回答。
- **验收方式**：依据 [gate/CHECKLIST.md](gate/CHECKLIST.md) 的 4 项清单逐项核对。

## 代码导读

本章提供两个实现文件：
1. [otel_tracing_eval.py](otel_tracing_eval.py)（**推荐，v3 核心**）：
   - 基于原生 OpenTelemetry SDK 实现完整 RAG 链路追踪（`rag_pipeline` 根 Span -> `retrieval {data_source.id}` -> `assemble_context` -> `chat {model}`）；
   - 默认使用 `ConsoleSpanExporter` 离线向终端打印结构化 Span，零网络、零外部依赖；
   - 根据标准环境变量 `OTEL_EXPORTER_OTLP_ENDPOINT` 与 `OTEL_EXPORTER_OTLP_PROTOCOL` 自适应接入 OTLP 导出器；
   - 默认开启隐私掩码，并内置 `sanitize_text` 脱敏过滤器。
2. [langsmith_eval.py](langsmith_eval.py)（平台示例）：
   - 保留作为专有平台 SDK 接入示例，展示如何用 `langsmith` 跑在线 Dataset 与 Experiment。

## 练习

1. 运行 `otel_tracing_eval.py`，观察控制台打印的各个 Span，找出哪些是 `SpanKind.CLIENT`（检索与推理），哪些是 `SpanKind.INTERNAL`（根 Span 与上下文拼装）；
2. 检查 `chat` Span 中是否包含了 `gen_ai.provider.name`、`gen_ai.response.finish_reasons` 等标准属性；
3. 故意制造一次调用失败（如 `--live` 模式下提供无效的 API 端点），观察 Span 如何记录 `error.type` 与错误状态，同时避免泄漏本机文件路径；
4. 在 [workbook.md](workbook.md) 中记录你的观察并完成 4 项清单。

## 边界与运行

- 默认离线控制台运行不发起任何外部网络请求；
- 发送 OTLP 时须注意后端支持的协议类型：Langfuse 原生仅接收 OTLP/HTTP，需使用 HTTP 导出器或通过 OpenTelemetry Collector 进行协议转换；
- `langsmith_eval.py` 在 `--live` 模式下会向外部商业服务器发送数据，需确认数据脱敏与授权。
