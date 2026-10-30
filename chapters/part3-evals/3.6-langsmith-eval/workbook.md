# L3.7 追踪与评测平台 · 练习记录

本章验收要求见 [gate/CHECKLIST.md](gate/CHECKLIST.md)。请在此记录你的执行观察与思考。

## 1. 本地 OTel 追踪运行记录

- 执行命令：`python tools/run_chapter.py 3.6 otel_tracing_eval.py`
- 控制台输出的 Span 结构观察：
  - 根 Span 名称：`rag_pipeline`
  - 子 Span 名称与顺序：
    1. `rag_retrieval`（检索阶段）
    2. `assemble_context`（上下文组装）
    3. `chat_completion`（模型推理生成）
- 观察到的核心 `gen_ai.*` 属性：
  - `gen_ai.system`: 
  - `gen_ai.operation.name`: 
  - `gen_ai.request.model`: 
  - `gen_ai.usage.input_tokens`: 
  - `gen_ai.usage.output_tokens`: 
  - `gen_ai.retrieval.documents_count`: 

## 2. 评测后端平台观察（可选）

- 选择的后端（Langfuse / LangSmith / Phoenix / 未配置外部后端）：
- 观察记录（若未配置，请写“未配置外部服务，通过本地 ConsoleSpanExporter 离线核对”）：
  - 

## 3. 项目必追 5 个核心字段及设计原因

请为你负责的项目（如企业知识库 RAG、客服 Agent）设计必追的 5 个关键字段：

1. **字段 1**：`gen_ai.usage.total_tokens` (或 input/output tokens)
   - 原因：直接关联调用成本核算、预算监控与模型配额预警。
2. **字段 2**：`gen_ai.retrieval.documents_count`
   - 原因：排查检索空召回或召回过多导致上下文窗口溢出/幻觉的问题。
3. **字段 3**：`app.latency_ms`（或各子 Span 耗时）
   - 原因：定位端到端延迟瓶颈（是向量数据库慢、网络慢还是 LLM 生成慢）。
4. **字段 4**：`error.type` / `gen_ai.response.finish_reason`
   - 原因：捕获上下文超长截断、网络异常、模型拒答或审核拦截。
5. **字段 5**：`user.tenant_id` / `session.id`
   - 原因：多租户隔离与单次对话会话级链路串联分析。

## 4. 隐私防线：哪些内容绝不应采集？

- **绝对禁止采集的内容**：
  1. 用户密码、Token、API Key、签名密钥等鉴权凭证；
  2. 手机号、身份证号、银行卡号等高危个人身份信息（PII）；
  3. 未经用户授权的私有文件正文明文。
- **默认处理策略**：
  - Prompt 与 Response 正文在 Span 中默认标记为 `[REDACTED_BY_DEFAULT]`；
  - 仅在配置脱敏流水线且明确授权开启时，才记录去除敏感实体后的文本摘要。
