# ADR-002：capstone 主链路去掉 LangChain

- 状态：Accepted
- 决策日期：2026-10-31

## 背景

capstone 的问答主链路原先用 LangChain：LCEL 链（提示词、可运行对象、输出解析器）、`langchain_chroma`、`RecursiveCharacterTextSplitter`、`Document`，模型经 `common.get_reliable_llm()`。课程 v3 的默认路线是原生 SDK + Pydantic，招聘叙事也要求能说清“框架替你做了什么、不用会怎样”。主链路只有一个固定流程（检索 → 拼装 → 调用模型 → 解析），并不需要框架的编排能力。

## 决策

- 消息组装与调用改用原生 openai 客户端（`capstone/llm.py` 的 `ChatClient`）：保留原有语义——单次 20 秒超时、主模型最多尝试 4 次（只重试瞬时错误，带抖动，听 `Retry-After`）、可选备用模型（`CAPSTONE_BACKUP_MODEL`，回答标为 `degraded` 且不缓存）。
- 向量库改用 `chromadb` 原生客户端（`capstone/vector_store.py`）；集合名由 `langchain` 改为 `capstone`。
- 文本切分改为 `capstone/text_split.py` 的原生实现，行为对齐递归字符切分（分隔符保留在块首、去首尾空白、带重叠合并）。
- `Document` 换成 `capstone/contracts.py` 里的 dataclass；`RunnableLambda` 换成普通函数。
- pgvector 后端改用 psycopg 直接执行 SQL（表结构由迁移模板创建），不再依赖 `langchain-postgres`。
- 嵌入通过 `capstone/embedding.py` 调 `common.embed_texts`（不再经 `langchain_huggingface`）。
- 配套新增：OpenTelemetry 打点（`telemetry.py`）、静态演示前端（`static/`）、反馈接口 `POST /v1/feedback`。
- HTTP 接口与公共函数签名不变；响应新增可选字段 `degraded`（默认 `false`）。

## 原因

- 主链路的每一步都是几行普通代码，换成原生写法后调用栈更短、错误更容易定位，测试替身也更简单（直接注入假的聊天客户端）。
- 与课程路线一致：LangChain/LangGraph 保留在需要它们的章节和冻结的 `flagship-project/` 快照里。

## 代价与风险

- **索引要重建**：集合名、切分器、嵌入封装和 `SOURCE_VERSION_SCHEMA`（`source-v3`）都变了，旧的本地 Chroma 目录里的数据不会被读取；首次 `build()` 会重新写入，增量同步会把所有文件视为已更新。旧集合 `langchain` 留在磁盘上，不自动删除。
- **切分边界与旧版一致（一次性验证）**：2026-10-31 在仓库的 55 篇 Markdown 上，用 3 组参数（默认 300/50、120/20、500/0）共 165 例对比，原生切分器与 `RecursiveCharacterTextSplitter` 的输出逐块完全一致。这是一次性对比，没有入库成测试（去框架后 CI 不再安装对照所需的包）；中英文混排、超长无分隔符文本等情形没有专门验证。
- **Bedrock 直连不再支持**：原生 OpenAI 客户端不能直连 Bedrock，需要经 OpenAI 兼容网关（`LLM_PROVIDER=openai_compatible`）；`config.validate_settings()` 会明确报出。
- **pgvector 路径未对真实 Postgres 验证**：SQL 与过滤翻译有离线测试（假连接），没有在真实的 Postgres + pgvector 上运行过。
- 失去了 LangChain 自带的重试、回调和 LangSmith 追踪；对应能力由 `llm.py` 与 `telemetry.py` 重新实现，覆盖面更小。

## 回退方式

在合并前的提交上恢复 `capstone/` 与 `requirements*.txt`（`git revert` 本次提交即可）；旧提交仍使用 LangChain 路径与旧的 Chroma 集合 `langchain`，旧的本地索引目录若未被删除可以直接继续使用。
