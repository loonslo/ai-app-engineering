# L3.7 追踪与评测平台 · 练习记录

本章验收要求见 [gate/CHECKLIST.md](gate/CHECKLIST.md)。请在此记录你的执行观察与思考（待填写项留空供练习填写）。

## 1. 本地 OTel 追踪运行记录

- 执行命令：`python tools/run_chapter.py 3.6 otel_tracing_eval.py`
- 控制台输出的 Span 结构观察：
  - 根 Span 名称与 SpanKind：待填写
  - 子 Span 名称与顺序：
    1. 检索 Span（名称与 SpanKind）：待填写
    2. 上下文拼装 Span（名称与 SpanKind）：待填写
    3. 模型推理 Span（名称与 SpanKind）：待填写
- 观察到的核心 `gen_ai.*` 规范属性：
  - `gen_ai.provider.name`: 待填写
  - `gen_ai.operation.name`: 待填写
  - `gen_ai.request.model`: 待填写
  - `gen_ai.usage.input_tokens`: 待填写
  - `gen_ai.usage.output_tokens`: 待填写
  - `gen_ai.response.finish_reasons`: 待填写
- 自定义属性（app.*）观察：
  - `app.pipeline.type`: 待填写
  - `app.privacy.placeholder`: 待填写

## 2. 评测后端平台观察（可选）

- 选择的后端（Langfuse / LangSmith / Phoenix / 未配置外部后端）：待填写
- 观察记录（若未配置，请写“未配置外部服务，通过本地 ConsoleSpanExporter 离线核对”）：
  - 待填写

## 3. 项目必追 5 个核心字段及设计原因

请为你负责的项目（如企业知识库 RAG、客服 Copilot）设计必追的 5 个关键字段：

1. **字段 1**：待填写
   - 原因：待填写
2. **字段 2**：待填写
   - 原因：待填写
3. **字段 3**：待填写
   - 原因：待填写
4. **字段 4**：待填写
   - 原因：待填写
5. **字段 5**：待填写
   - 原因：待填写

## 4. 隐私防线：哪些内容不应直接采集？

- **不应直接采集的内容**：
  1. 待填写
  2. 待填写
  3. 待填写
- **生产推荐的脱敏与保护策略**：
  - 待填写
