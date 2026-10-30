# L3.7 追踪与评测平台 · 清单验收

> 3.6 介绍现代 AI 可观测性标准（OpenTelemetry GenAI 语义约定）与主流评测平台。
> 本章采用**可核对清单**形式在 [workbook.md](../workbook.md) 中记录验收证据；L5.6 将进一步通过自动化 Gate 深入检验复杂 Trace 断言。

## 前置

- 已安装 `opentelemetry-api` 和 `opentelemetry-sdk`（本课程环境已内置）。
- 离线默认运行无需配置任何密钥或外部服务。

## 验收清单

请完成以下 4 项核对，并将结果与思考记录在 [workbook.md](../workbook.md) 中：

- [ ] **1. 运行本地 OTel 追踪**：
  - 运行 `python tools/run_chapter.py 3.6 otel_tracing_eval.py`。
  - 观察控制台输出的 Span 结构，理解根 Span `rag_pipeline` 与子 Span `rag_retrieval`、`assemble_context`、`chat_completion` 的父子嵌套关系。
  - 核对各个 Span 中符合 OpenTelemetry GenAI 规范的属性（如 `gen_ai.system`、`gen_ai.operation.name`、`gen_ai.usage.input_tokens` 等）。
- [ ] **2. 平台端 Trace 观察（可选）**：
  - 若本地部署了 Langfuse / Phoenix 或配置了远程 OTLP 端点（或使用 LangSmith 运行 `langsmith_eval.py`），观察平台 UI 中展示的 Trace 瀑布图与元数据；若未配置外部服务，明确记录“未验证（离线通过控制台验证）”。
- [ ] **3. 核心追踪字段设计**：
  - 针对你实际的业务项目或 Capstone 项目，明确写出必须采集的 5 个关键字段（如 Token 消耗、检索片段数、工具调用参数、耗时分布、错误状态码等）并说明原因。
- [ ] **4. 隐私安全与脱敏防线**：
  - 明确写出生产环境中**绝对不能采集**或**必须脱敏后才能采集**的数据内容（如未经脱敏的 Prompt/回答正文、密码/API Key、用户个人身份识别信息 PII）。

## 边界与纪律

- 默认离线控制台运行不发起任何外部网络请求。
- 平台端 UI 观察属于可选外部验证，离线控制台 Span 属性正确即可满足本章入门要求。
- 严禁将 API Key、密码或用户真实私密数据记录在 Trace 属性或提交到公开仓库。
