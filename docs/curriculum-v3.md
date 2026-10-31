# AI 应用 / Agent 开发学习路径 v3（提案）

> **状态**：提案（2026-10-27）。同日并入就业视角审查，并产出执行包 [docs/v3/](v3/README.md)（大纲、编写规范、审核清单、分批细则）。只做调研与设计，未修改章节、未运行课程测试或真实模型；不代表本人已学完或真实环境验收通过。
>
> **与 v2 的关系**：沿用 [v2](curriculum-v2.md) 的六层能力模型、闭卷 gate 与出口门，改四件事：
> 1. 默认实现从 LangChain 换成“原生 SDK + Pydantic”；
> 2. 按“嵌入式功能 / 专项 Agent”两种交付形态组织内容；
> 3. 补齐 2026 年进入主流的上下文工程、MCP 取舍、持久执行、执行面、沙箱、OpenTelemetry 追踪、Agent 评测与 Agent 安全；
> 4. 以就业证据为出口：新增项目主线 P 与就业轨道 J，用就业出口标准 E1–E4 判断是否可以投递。
>
> **依据**：2026-10-27 的英文资料调研（按要求排除中文来源）、一份外部架构观点的逐条取舍（第 3 节）、就业视角审查（第 8 节），以及对本仓库 LangChain 依赖分布的核对（第 7 节）。
>
> **章节以 [docs/v3/outline.md](v3/outline.md) 为准**；本文件只写论证与依据。

---

## 0. 结论

1. **LangChain 没有退出主流，但不再是骨架。** Stack Overflow 2026 调查中，使用编排框架的开发者（n=4,400）里 LangChain 占 30.2%、OpenAI Agents SDK 23.8%、直接用代码或终端编排的 “Terminal Use” 18.9%、LangGraph 18.8%。Thoughtworks 技术雷达 2026-04 把 LangGraph 从 Adopt 降到 Trial，理由是“更偏好用代码传递信息的简单 Agent，需要时才加图”。课程把 LangChain 降为“框架素养”一章，LangGraph 只负责显式状态、恢复和人工介入。
2. **生产中的主要问题是质量、状态和成本，不是会不会用框架。** LangChain 调查中首要障碍是质量（32%），Temporal 调查中是状态跟踪（35.7%）；Datadog 遥测显示 59% 的 Agent 请求只有一次服务调用。
3. **按两种交付形态组织**：形态 A 是嵌入现有系统的 LLM 功能（同步、控制面），形态 B 是独立执行的专项 Agent（异步、执行面）。先练 A，再练 B，最后在项目里组合。
4. **核心 SDK 选 Pydantic AI，OpenAI Agents SDK 作对照**；每个概念先用原生 SDK 写一遍，再引入 SDK。
5. **评测贯穿全程**：L1 搭好 eval harness，之后每个 gate 都往同一套 harness 里加用例。这是测试背景的护城河。
6. **技术覆盖够到中级 AI 应用工程师，但就业还要过三关**：真实证据、面试形式、岗位定位。入门岗位稀缺（美国 AI 工程岗中初级约占 12%，中位要求 5 年经验）。因此 v3 让项目在第 6 周末前最小上线并持续积累真实用量，让就业轨道从第 3 周起贯穿，并以 E1–E4 作为投递门槛（第 8 节）。

---

## 1. 2026 主流技术栈

| 层 | 主流做法 | 依据 |
|---|---|---|
| 模型接入 | 厂商原生 API；多模型加网关；原生结构化输出；prompt caching | OpenAI Assistants API 已于 2026-08-26 下线，新项目推荐 Responses API；超过 70% 的组织同时使用 ≥3 个模型；system prompt 占输入 token 的 69%，可缓存调用只有 28% 命中缓存；雷达把 Structured output 列为 Adopt |
| Agent 编排 | 普通代码循环 → 薄 SDK（OpenAI Agents SDK、Pydantic AI、Google ADK、Claude Agent SDK、Microsoft Agent Framework）→ 需要持久状态时才用图（LangGraph） | Microsoft Agent Framework 1.0（2026-04）取代 AutoGen 与 Semantic Kernel |
| 上下文工程 | 指令、知识、工具、记忆、历史统一按预算管理；渐进披露、压缩、子 Agent 隔离；AGENTS.md、Agent Skills | 雷达：Context engineering 为 Adopt，Agent Skills、Progressive context disclosure 为 Trial，Agent instruction bloat 为 Caution |
| 检索 | 文档问答默认 BM25 + 向量混合检索 + 重排 + 引用；多跳问题用 agentic retrieval；代码与高频变化数据让 Agent 直接搜索 | 多篇 2026 生产指南的共识（多为厂商博客，数字未独立验证） |
| 工具协议 | MCP 是事实标准；A2A v1.0 用于 Agent 间协作 | MCP 已捐给 Linux 基金会下的 AAIF，2026-07-28 版规范转向无状态；Agent 岗位中 MCP 与各框架的共现率为 17–24%；雷达把 “MCP by default” 列为 Caution |
| 状态与持久执行 | checkpoint、人工介入、持久执行引擎（Temporal、DBOS 等）；副作用幂等 | 雷达把 “Ignoring durability in agent workflows” 列为 Caution；Temporal × OpenAI Agents SDK 集成 2026-03 GA |
| 评测 | 代码判分优先，LLM judge 经人工校准；从 20–50 个真实失败任务起步；能力评测与回归评测分开；区分 pass@k 与 pass^k；读 transcript | Anthropic《Demystifying evals for AI agents》（2026-01）；只有 52.4% 的团队做离线评测 |
| 可观测性 | OpenTelemetry GenAI 语义约定，后端任选 Langfuse、LangSmith、Phoenix、MLflow | SO 2026：Sentry 26.0%、LangSmith 17.3%、MLflow 15.2%、Langfuse 15.2%；GenAI 约定尚未进入 Stable |
| 安全 | OWASP Agentic Top 10；间接提示注入；在模型之外强制最小权限；沙箱执行；高风险操作审批 | OWASP LLM Top 10 2026：提示注入仍居第 1，Excessive Agency 升至第 3 |
| 托管运行时 | OpenAI Agents API（2026-09 公测）、Claude Managed Agents（2026-04）、LangSmith Deployment、Microsoft Foundry、Bedrock AgentCore | 厂商把 harness、沙箱和会话打包成服务 |
| 开发方式 | 编码 Agent 是默认工具 | SO 2026：Claude Code 65.5%、GitHub Copilot 58.7%、Codex 29.5%；雷达把 Claude Code 列为 Adopt |
| 语言 | Python 为主，TypeScript 多用于全栈岗 | Agent 岗位中 Python 91–96%，TypeScript 18–26% |

招聘侧：AI/Agent 岗位中 LangChain 出现率约 23–35%；一份 1,135 个 Agent 岗位的样本里，过半职位不点名任何框架，不同框架岗位的薪资中位数相差约 4k 美元。

---

## 2. 两种交付形态

外部观点把 AI 应用分成“嵌入现有系统的 LLM 功能”和“独立的专项 Agent”。这个划分成立，也与数据一致：多数生产调用是单次调用的嵌入式功能；Anthropic 同样建议先用 workflow，确有需要再上自治 Agent。

| | 形态 A：嵌入式 LLM 功能（控制面） | 形态 B：专项 Agent（执行面） |
|---|---|---|
| 典型场景 | 打标签、字段抽取、审核建议、检索问答 | 长链路处理、批量分析、代码与脚本自动化 |
| 调用方式 | 同步，在请求链路内，受延迟预算约束 | 异步，提交后返回 task_id，由 worker 执行 |
| 控制权 | 代码决定流程，模型只产出“提议” | 阶段内模型自主循环，阶段之间由状态机推进 |
| 主要风险 | 输出错误、超时、成本、越权 | 失控循环、副作用重复执行、沙箱逃逸、注入 |
| 默认实现 | Service 层模块：原生 SDK 或 Pydantic AI | 外部状态机（DB 步骤表 / LangGraph / Temporal）+ 阶段内 Pydantic AI |
| 课程位置 | L1.10、L2、L3、L5.1 | L4.9–L4.17、L5.7 |

### 2.1 形态 A 的工程规则

1. **契约先行，LLM 输出 schema 与领域 DTO 分开。** 模型输出先过 schema，再映射到 DTO 并做业务校验。schema 通过只说明格式对，字段值仍可能是编的。
2. **LLM 提议，代码裁决。** 写操作留在 Service 层，由确定性代码校验后执行。
3. **身份与租户只从依赖注入取**（如 Pydantic AI 的 `RunContext`），不从模型生成的参数里取。
4. **超时按延迟预算定。** 先测 p95，再定超时与重试上限。推理模型更慢（DeepSeek V4 默认开启思考），抽取、分类类任务可关闭思考。
5. **降级分两种。** 低风险功能 fail-open：回退规则或默认值，不阻断主流程。高风险功能（审核、风控、退款）fail-closed：转人工，不能静默放行。
6. **可观测字段**：token、耗时、模型与版本、prompt 版本、重试次数、是否降级、校验失败原因、脱敏后的用户 ID；prompt 与回答正文默认不采集。
7. **评测**：每个功能一份 golden set，按字段计算准确率，进入 CI 回归。

### 2.2 形态 B 的工程规则

1. **异步化**：提交即返回 task_id；状态从状态存储读取，不从队列读取；结果通过带幂等键的 webhook 投递。
2. **阶段化**：把任务拆成确定性阶段，由外部状态机推进；阶段内由 Pydantic AI 做结构化工具调用。Celery 只是任务队列，重试会整段重跑；步骤级续跑需要步骤表或持久执行引擎。
3. **断点与幂等**：每步落盘。从旧快照恢复可能让工具再执行一次，OpenAI Agents SDK 的人工审批文档明确写明不保证只执行一次。有副作用的步骤要带幂等键；结果不明时记为 unknown，不自动重放。
4. **沙箱在 harness 之外实现**：容器或 VM、出网白名单、临时最小权限凭据、禁止写生产库。harness 自带的沙箱不够，例如 DeepSeek Harness 的沙箱只覆盖文件系统，不管网络与进程。
5. **预算与终止**：限制步数、token 和墙钟时间，支持取消。
6. **人工审批**：合并、部署、对外发送、破坏性命令必须审批。
7. **缓存友好**：system prompt 与工具定义放在前面且保持不变，历史只追加；压缩会破坏前缀，要在节省上下文与保住缓存之间取舍，并监控命中率。DeepSeek 自 2026-08-16 起按峰谷计价，低峰价为高峰的一半，执行面的批量任务可排到低峰。
8. **评测**：轨迹与结果分开判分，报告 pass^k。

### 2.3 现成 harness：可以复用，需受控试用

代码、脚本类专项 Agent 优先复用现成 harness，不必从零写 shell 与文件工具。

| Harness | 现状（2026-10） | 适用 |
|---|---|---|
| DeepSeek Harness（dsh） | v0.1 开发者预览（2026-08-13 发布），MIT，插件化，模型无关，有 Python SDK；无独立安全审计；沙箱只覆盖文件系统；声明会有破坏性变更 | 一次性工作区里的受控试用 |
| Pi | TypeScript，0.x；默认只有 read、write、edit、bash 四个工具；刻意不内置 MCP、子 Agent 与权限确认 | 研究最小 harness 设计；可经 RPC 模式嵌入 |
| Claude Agent SDK、OpenAI Agents SDK 的沙箱 Agent、Pydantic AI Harness、LangChain Deep Agents | 厂商或框架提供的 harness 库 | 已选定对应模型或框架时 |

---

## 3. 外部观点的取舍

| 观点 | 判断 | 处理 |
|---|---|---|
| 分成嵌入式功能与专项 Agent 两种形态 | 采纳 | 作为 v3 的组织维度 |
| 嵌入式功能用 Pydantic AI 或“轻量 SDK + Instructor” | 采纳并细化 | 单次调用用原生 SDK + Pydantic；需要依赖注入、工具或离线测试时用 Pydantic AI；不为 Instructor 新增依赖 |
| 模型输出直接对齐 DTO，无需二次校验 | 修正 | schema 与 DTO 分开，必须做业务校验 |
| `RunContext` 注入连接池、Redis、当前用户 | 采纳 | 补充：身份只从依赖注入取 |
| 超时 3–5 秒，失败回退原有逻辑、不阻断主流程 | 修正 | 超时按 p95 预算定；区分 fail-open 与 fail-closed |
| 接入 OTel、Logfire 或 Langfuse，记录 token、耗时、prompt 版本、用户 ID | 采纳 | 补充降级标记、校验失败原因；用户 ID 脱敏 |
| 专项 Agent 首选 Pi 或 DeepSeek Harness，“成熟、自带沙箱” | 部分采纳 | 复用 harness 的思路采纳；两者为预览版或 0.x，沙箱不完整，只做受控试用（L4.15） |
| Pydantic AI + 异步状态机（Celery / Temporal / 任务表） | 采纳并修正 | Celery 只是队列；状态机用步骤表、LangGraph 或 Temporal |
| 沙箱隔离，禁止写生产库 | 采纳 | 沙箱放在 harness 之外 |
| 异步任务返回 task_id，每步 checkpoint | 采纳 | 补充幂等键与“不保证只执行一次” |
| 上下文压缩与 prompt caching，针对 DeepSeek R1/V3 调优 | 修正 | 模型名已过时（现为 V4）；缓存靠前缀稳定，压缩与缓存需取舍 |
| 控制面 / 执行面分层；先改造 1–2 个接口，再建专项 Agent | 采纳 | 对应 L1→L4 的顺序与项目主线的结构 |
| 未涉及评测、注入防护、审批、预算 | 补充 | 两种形态都配评测与安全规则 |

---

## 4. 路线原则

1. **原语先行，框架后置**：每个概念先用原生 SDK + Pydantic 实现，遇到框架真正解决的问题（依赖注入、持久状态、追踪、交接）再引入框架。
2. **评测贯穿**：L1 建立 eval harness（task / trial / grader / transcript），后续 gate 共用。
3. **上下文工程统领 RAG、记忆与 Skills**：RAG 是上下文供给的一种方式，不是全部。
4. **先嵌入式功能，后专项 Agent**：先在请求链路内交付可靠的单次调用，再处理异步、自主、长任务。
5. **协议、持久执行、沙箱与安全进入核心**；托管运行时、A2A、多 Agent 只讲判断或放入选修。
6. **以就业证据为出口**：尽早上线、持续积累真实用量；面试形式从第 3 周起贯穿训练；是否可以投递看 E1–E4，不看课时。

---

## 5. 阶段概览

| 部分 | 课时 | 出口 |
|---|---|---|
| L0 定位与工具链 | 12h | 环境通；一次带测试、经人工复核的编码 Agent 改动；岗位自评与排期 |
| L1 模型 API 原语与嵌入式功能 | 46h | CLI 助手 gate 通过；嵌入式功能双 gate 通过并产出 golden set 报告 |
| L2 上下文工程与检索 | 60h | 真实资料知识库：引用正确率 ≥90%、拒答正确率 ≥90%、hit@5 ≥80%，附消融表 |
| L3 质量闭环 | 28h | judge 与人工一致率 ≥80%；回归门禁可在 CI 运行 |
| L4-A Agent 控制流 | 44h | 原生版与 Pydantic AI 版通过同一套 eval，含 5 个故障注入 |
| L4-B 状态、执行面与安全 | 46h | 异步专项 Agent：权限、审批、崩溃恢复、5 个故障注入、pass^3 报告 |
| L5 服务化与生产 | 58h | 部署到一个主流云或 VPS；SLO 与成本报告；一次故障演练 |
| P 项目主线（篇 11） | 36h | E1 |
| J 就业轨道（篇 12） | 50h | E3、E4 |
| **合计** | **380h** | 16 周，平均每周约 24h；第 15–16 周以求职为主 |

章节、目录、课时、批次、16 周排期见 [outline.md](v3/outline.md)；逐章细则见 [docs/v3/specs/](v3/specs/)。

与本文件早先草稿相比，并入就业审查后的主要变化：

- 恢复 L1.2“LLM 工作原理”为核心章，应对面试原理题；
- L1.7 加入第二家模型的对比评测；
- L1.10 嵌入式功能的后半部分引入 Pydantic AI；
- L2.12 改用真实公开资料（含表格页与扫描页）；
- 新增 L5.4 认证与多租户章；L5.5 补治理与审计；L5.8 加云部署；
- 原 L6 拆为项目主线 P 与就业轨道 J，并加入可演示前端（P5）。

---

## 6. 框架与 SDK

### 6.1 Pydantic AI 与 OpenAI Agents SDK

| 维度 | Pydantic AI | OpenAI Agents SDK |
|---|---|---|
| 设计取向 | Agent 是带类型契约的 Python 组件：`Agent[依赖, 输出]` + `RunContext` | Agent 由 Runner 驱动；handoff、guardrail、session 内置 |
| 版本 | 1.0（2025-09）、2.0（2026-06），当前 2.61.0；发版快，需锁版本 | 仍为 0.x（0.24.0，2026-10-15） |
| 模型 | 原生多厂商，有 `DeepSeekProvider` | 默认 Responses API；其他厂商走 Chat Completions 或 beta 适配器 |
| 结构化输出 | 默认“输出工具”，校验失败自动重试 | `output_type` 依赖 JSON Schema，厂商不支持时报 400 |
| 多 Agent | 委托、代码编排、图；无专门的 handoff 原语 | handoff 与 agents-as-tools 内置 |
| 人工审批 | deferred tools | `needs_approval` + RunState 序列化；不保证只执行一次 |
| 持久执行 | 内置 8 种引擎接入（Temporal、DBOS、Prefect、Restate 等） | 文档列出 Temporal、Restate、DBOS、Dapr |
| 追踪 | 标准 OpenTelemetry | 默认上传 OpenAI；使用非 OpenAI 模型时需关闭或改用第三方处理器 |
| 测试 | TestModel、FunctionModel，可全局禁止真实请求 | `agents.testing.ScriptedModel`，无全局禁网开关 |
| 生态 | 配套 Pydantic Evals；仅 Python | 实时语音、沙箱 Agent；Python 与 TypeScript |
| 使用率（SO 2026） | 8.9% | 23.8% |

**选 Pydantic AI 作核心**：
- 接 DeepSeek 最顺：有专门 provider；结构化输出默认走工具，不依赖 DeepSeek Chat Completions 不接受的严格 JSON Schema。
- 追踪是标准 OTel，与 L3.7、L5.6 共用一套。
- TestModel 加全局禁止真实请求，符合仓库“离线替身优先”的约定。
- 有正式主版本。

**改选 OpenAI Agents SDK 的条件**：需要 handoff 式多 Agent、实时语音、以 OpenAI 模型为主、需要 TypeScript，或更看重社区热度。只影响 L1.10 后半、L4.5 与 L4.8。

**DeepSeek 注意事项**（据 Pydantic AI 文档，未实测）：
- V4 默认开启思考，思考模式下拒绝强制 tool_choice；需要稳定结构化输出时设 `thinking=False`。
- Chat Completions 不接受严格 JSON Schema，Responses 端点接受。

### 6.2 LangChain 与 LangGraph 的去留

- **LangGraph 留在核心**：只负责显式状态、恢复与人工介入（L4.9、L4.10）。4.2–4.4、4.6、4.10、4.11 的 gate 继续有效，篇幅压缩，补“何时不需要图”。
- **LangChain 降为一章**：L4.16 框架素养，讲 `create_agent`、middleware、Deep Agents、LangSmith，并配一个用 `create_agent` 重写工具循环的练习，保证招聘关键词有实操支撑。
- **保留框架对照**：1.5、2.3、2.8、4.5 的旧 LangChain 版本改名为 `*_langchain.py` 保留；4.14 的 `langgraph_supervisor.py` 保留为 LangGraph 对照版。
- **移出主线**：LCEL / Runnable 链作为主实现、`langchain_classic` 旧检索器、`langchain_community` 集成、AutoGen（已进入维护模式）、OpenAI Assistants API（已下线）。
- **仓库名**：目录名与 project_id 为 `ai-app-engineering`（工作区状态契约依赖它）；README 标题已与内容一致。

### 6.3 依赖变化

- **L1、L2 不新增依赖**：`openai`、`mcp` 已在 `requirements-course.txt`；`sentence-transformers`、`chromadb`、`rank-bm25`、`pypdf` 已在 `requirements.txt`。
- **新增**：`pydantic-ai-slim[openai]`（L1.10 起）；`opentelemetry-sdk`（L3.7、L5.6）。由 V3-0 锁定版本。
- **暂不移除** LangChain 系列包：flagship 快照、LangGraph 章节、框架对照文件与框架素养章仍需要。

---

## 7. 仓库改造面与批次

### 7.1 已核对的事实（2026-10-27）

- **gate 骨架几乎不依赖 LangChain**：只有 4.3、4.4 的 `gate_check.py` 依赖 LangGraph，这两章留在 LangGraph 模块。
- **参考实现依赖 LangChain**：
  - 第 1 篇 8 章（1.1–1.8）；
  - 第 2 篇 9 章（2.1–2.3、2.6–2.11）；
  - 第 3 篇 4 章（3.3、3.6、3.7、3.8）；
  - 第 4 篇 13 章（4.1–4.12、4.14）；
  - 第 5 篇 3 章（5.1、5.2、5.6）；
  - 第 0、6、8、9、10 篇无依赖。
- **capstone 不用 LangGraph**：LangChain 只出现在 `Document` 类型、Chroma / PGVector 包装、文本切分与 `knowledge_base.py` 的 LCEL 链（`connector.py`、`context.py`、`knowledge_base.py`、`permissions.py`、`vector_store_pg.py`、`test_production.py`）。
- **flagship-project**：124 个 Python 文件中 32 个依赖 LangChain。
- **本机环境与锁定文件有漂移**：`.venv` 缺 `langchain` 顶层包；`fastapi` 为 0.141.1，而锁定的是 0.139.2。

### 7.2 批次

共 11 批（V3-0 至 V3-10），范围、依赖与流程见 [docs/v3/README.md](v3/README.md)：

- V3-0 基础设施；
- V3-1 至 V3-6 按阶段改章节；
- V3-7、V3-8 新建篇 11、篇 12；
- V3-9 改 capstone；
- V3-10 统一打标签与更新索引。

每批由实施者按细则完成并自检，审核者按 [review-checklist.md](v3/review-checklist.md) 验收。

### 7.3 用户决定（2026-10-27）

1. **flagship-project 冻结**：作为基于 LangChain 1.x 的历史教学快照保留，不再更新；快照仍可还原运行，CI 继续跑 m1/step1 基线测试。已同步修改 `AGENTS.md` 的联动验收约定、`flagship-project/README.md` 的冻结说明，以及根目录 README 的课程表。
2. **新增 v3 路径行**：V3-10 打标签时，旧章节保留 `v2 路径` 行，在其下方新增 `v3 路径` 行；冻结的旗舰步骤不加 v3 标签。V3-0 复核时由“上方”改为“下方”，以免与 `tools/apply_v2_map.py` 冲突。

---

## 8. 就业视角审查（2026-10-27）

### 8.1 企业在买什么、怎么验证

企业买的是“把业务问题变成可靠运行、成本可控的 AI 功能”。它看不到真实能力，只能通过三道关验证：筛选（经验年限、关键词、作品）→ 面试（编码、LLM 系统设计、动手构建、评测讨论、行为面）→ 试用期交付。课程能决定第三关的能力，为第一关产出证据，为第二关提供训练。

### 8.2 市场事实

| 事实 | 数据 |
|---|---|
| 需求在涨 | LinkedIn 2026 美国增长最快职位第 1 名仍是 AI 工程师；头部公司 AI 工程岗一年增 60%，普通软件岗只增 7%；FDE 岗位从 2025-04 的 643 个涨到 2026-04 的 5,330 个 |
| 入门岗位稀缺 | 美国 43,480 个 AI 工程岗中初级约占 12%，中位要求 5 年经验；另一份 903 个岗位的样本中只有 2.5% 面向 0–2 年经验；2025-05 至 2026-05 软件岗位增量的 71% 来自高级岗；斯坦福 2026-08 的数据：AI 影响大的职业里，22–25 岁人群就业比趋势低 19% |
| 评测是强信号 | 多份面试指南与招聘方文章都把评测设计列为区分候选人的关键；take-home 中一个能打印分数的小评测脚本常是最大加分项（行业经验，非研究） |
| 面试形式在变 | 常见流程为编码 + LLM 系统设计 + 动手构建 + 评测讨论；Meta 自 2025-10 起设有允许使用 AI 的编码轮，Amazon 则要求书面承诺不用 |
| 国内（英文媒体报道） | 2026 年 1–7 月 AI 岗位发布量增长近 8 倍，需求集中在智能体应用开发与现场部署岗位；部分细节在付费墙后，未能核实 |

### 8.3 课程覆盖对照

| 企业要求 | v3 覆盖 | 判断 |
|---|---|---|
| LLM 调用、结构化输出、工具调用、RAG、Agent | L1、L2、L4 | 覆盖 |
| 评测（强信号） | 全程贯穿 | 覆盖；真实模型数据与人工校准放进 P4 |
| Python 工程、算法题 | L0.4；J3 | 补齐 |
| 云平台（AI 工程岗约 56% 要求） | L5.8 新增云部署 | 补齐 |
| 机器学习与 LLM 原理题 | L1.2 恢复为核心 | 补齐 |
| LLM 系统设计 | L5.11 + J4（5 次模拟） | 补齐 |
| 动手构建 / take-home | gate + J5（3 次限时模拟） | 补齐 |
| 作品证据：上线、用量、事故 | P2 第 6 周末前最小上线；P4 真实评测与事故复盘 | 补齐；能否达成取决于真实执行 |
| 需求与沟通、对接现有系统 | L1.10、P1 | 补齐 |
| 治理与审计 | L5.5 增补 | 补齐 |
| LangChain 关键词 | L4.16 练习 + 框架对照文件 | 保留实操 |

### 8.4 三个主要缺口与改法

1. **真实证据（影响最大）**：招聘方看已上线的系统、用量数字、事故复盘与取舍理由。原课程的 capstone 未部署、没有真实用户，且简历措辞与代码不一致（声称去框架，但 `knowledge_base.py` 仍用 LCEL）。改法：P2 在第 6 周末前最小上线并持续积累真实用量；P4 产出真实模型评测、judge 校准与事故复盘；V3-9 让简历措辞与代码对齐。
2. **面试形式**：原课程的面试准备只有 16 小时，而且排在最后。改法：J3–J6 从第 3 周起贯穿，含算法、AI 辅助编码演练、5 次系统设计模拟、3 次限时 take-home、6 个 STAR 故事。
3. **岗位定位**：不以新人身份去挤初级岗，而以“测试/质量工程背景 + AI 评测与应用交付”投中级岗。改法：L0.5 岗位地图；J1 准备三版简历，分别对应 AI 应用工程师、AI 评测与质量工程师、FDE 与交付工程师。

### 8.5 目标岗位与匹配度

| 目标岗位 | 预期匹配度 | 还差什么 |
|---|---|---|
| AI 评测 / AI 质量工程师 | 高 | 真实评测数据、人工标注校准 |
| 中级 AI 应用工程师 | 中 | 上线证据、云平台、系统设计练习 |
| FDE / 交付工程师 | 中低 | 客户沟通、对接现有系统、私有化部署；国内交付方向把 5.6、9.11 提为必修 |
| 大厂 AI 工程师 | 低 | 算法题、后端深度 |

匹配度是审查判断，不是统计结论。

### 8.6 就业出口标准

E1 主作品、E2 辅助作品、E3 面试准备、E4 求职材料，具体门槛见 [outline.md 第 6 节](v3/outline.md#6-就业出口标准e1e4)。数值门槛是建议值，按实际记录填写，不得估算或虚构。

时间预期：12 周学完技术不等于 12 周拿到 offer。全职节奏下按 16 周规划；在职学习有转岗指南估计需要 6–9 个月。

---

## 9. 局限与未核实项

- **调研范围**：只用英文资料，排除了中文来源。国内情况只来自英文媒体，部分数字出自付费墙后的 AI 摘要；v2 的 5 份 JD 中有 4 份是国内岗位，定稿前应拿 3–5 份目标 JD 对照。
- **样本偏差**：
  - LangChain、Temporal、Datadog 的报告由厂商发布，样本有偏；
  - 招聘统计来自不同求职站，口径不一（初级占比从 4.5% 到 12% 不等）；
  - 招聘方建议多来自猎头与面试辅导机构，不是研究。
- **只有二手来源的事项**：Google ADK 2.0 的 GA 日期；A2A 是否已并入 AAIF；OpenAI Agent Builder 的具体关停日期（2026-06-03 宣布弃用已由官方 changelog 证实）。
- **MCP 2026-07-28 规范**：细节来自 AAIF 按候选版写的迁移文章，落地前需对照最终规范。
- **DeepSeek 相关**：
  - V3-0 复核时核对了 DeepSeek 官方英文文档（Models & Pricing，读取于 2026-10-27）：当前模型 ID 为 `deepseek-flash`（DeepSeek-V4.1-Flash-1017）与 `deepseek-v4-pro`，默认开启思考；`deepseek-v4-flash` 仍被接受，但会路由到 V4.1-Flash。
  - `common.py` 的默认值已改为 `deepseek-flash`。
  - Chat Completions 不接受严格 JSON Schema，这一条仍只出自 Pydantic AI 文档，未实测。
- **harness 评价**：DeepSeek Harness 与 Pi 的评价来自 VentureBeat、Wavect 等二手资料，未实际运行。
- **雷达版本**：Thoughtworks 雷达 Vol.35 预计 2026-11-04 发布，环位可能变化。
- **课时与匹配度**：都是估算，未经真实学习验证。

---

## 附录：来源（读取于 2026-10-27）

- 开发者调查与遥测：[Stack Overflow 2026 AI 数据](https://survey.stackoverflow.co/2026/ai/data) · [LangChain State of Agent Engineering](https://www.langchain.com/state-of-agent-engineering) · [Temporal 2026 报告](https://temporal.io/reports/state-of-development-2026) · [Datadog State of AI Engineering](https://www.datadoghq.com/state-of-ai-engineering/)
- 招聘分析：[agentic-engineering-jobs](https://agentic-engineering-jobs.com/ai-agent-frameworks-job-market-2026) · [InterviewStack](https://interviewstack.io/blog/how-ai-is-changing-ai-engineer-2026) · [Square1AI](https://www.square1ai.com/research/what-ai-job-ads-ask-for-2026) · [Axial Search 岗位分析](https://axialsearch.com/insights/ai-engineering-job-demand) · [Axial 经验要求](https://axialsearch.com/insights/ai-engineering-careers) · [365 Data Science](https://365datascience.com/career-advice/career-guides/ai-engineer-job-outlook-2025/) · [LinkedIn 榜单（Dice）](https://www.dice.com/career-advice/ai-related-jobs-top-linkedins-fastest-growing-roles-list-for-2026) · [Pragmatic Engineer 2026 招聘市场](https://newsletter.pragmaticengineer.com/p/the-job-market-in-2026-part-2) · [入门岗位统计汇总](https://rockstardeveloperuniversity.com/entry-level-software-engineer-job-market-statistics/)
- 岗位类型：[TechCrunch：FDE](https://techcrunch.com/2026/07/30/forward-deployed-engineers-are-the-ai-industrys-latest-talent-obsession/) · [Talex：AI 评测工程师](https://www.talex.co/insights/what-is-a-ai-evaluation-engineer-and-why-companies-are-hiring-for-it-now) · [QA 岗位数据分析](https://dev.to/gnana_6392e836fd500a957dc/how-ai-is-changing-the-qa-engineer-role-in-2026-a-data-analysis-4c0o)
- 面试：[Exponent](https://www.tryexponent.com/blog/ai-engineer-interview-questions) · [techscreen](https://techscreen.app/articles/ai-engineer-llm-interview-questions-2026) · [AI 面试政策追踪](https://www.techinterview.org/post/3233474911/ai-tool-policy-tracker-tech-companies-2026/) · [招聘方视角](https://unicoconnect.com/blogs/ai-engineer-skills-when-hiring)
- 企业落地与合规：[Technology.org](https://www.technology.org/2026/10/12/how-enterprises-are-actually-building-ai-in-2026-the-engineering-realities-behind-the-boom/) · [WRITER](https://writer.com/blog/enterprise-ai-adoption-2026/) · [Jones Walker：EU AI Act](https://www.joneswalker.com/en/insights/blogs/ai-law-blog/yes-august-2-still-matters-the-eu-approved-a-high-risk-ai-delay-but-most-trans.html)
- 国内市场（英文媒体）：[财新英文版](https://www.caixinglobal.com/2026-09-18/chinas-ai-hiring-surges-as-industry-pivots-to-practical-applications-102486035.html) · [SCMP](https://www.scmp.com/tech/tech-trends/article/3371925/chinas-tech-giants-are-paying-1-million-yuan-new-kind-ai-engineer) · [Rest of World](https://restofworld.org/2026/china-tech-recruiting-teenagers-ai-shortage/)
- 技术雷达：[LangGraph](https://www.thoughtworks.com/radar/languages-and-frameworks/langgraph) · [Pydantic AI](https://www.thoughtworks.com/radar/languages-and-frameworks/pydantic-ai) · [Techniques Vol.34](https://www.thoughtworks.com/radar/techniques)
- 厂商：[OpenAI Changelog](https://developers.openai.com/api/docs/changelog) · [Anthropic Managed Agents](https://www.anthropic.com/engineering/managed-agents) · [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) · [Microsoft Agent Framework 1.0](https://visualstudiomagazine.com/articles/2026/04/06/microsoft-ships-production-ready-agent-framework-1-0-for-net-and-python.aspx)
- 协议：[MCP 加入 AAIF](https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/) · [MCP 2026-07-28 变更](https://aaif.io/blog/mcp-2026-07-28-whats-changing-and-how-to-migrate) · [A2A 一周年](https://opensource.googleblog.com/2026/04/a-year-of-open-collaboration-celebrating-the-anniversary-of-a2a.html) · [Agent Skills](https://www.firecrawl.dev/blog/agent-skills)
- SDK：[Pydantic AI 概览](https://pydantic.dev/docs/ai/overview/) · [多 Agent](https://pydantic.dev/docs/ai/guides/multi-agent-applications/) · [测试](https://pydantic.dev/docs/ai/guides/testing/) · [DeepSeek](https://pydantic.dev/docs/ai/models/deepseek/) · [PyPI](https://pypi.org/project/pydantic-ai/) · [OpenAI Agents SDK PyPI](https://pypi.org/project/openai-agents/) · [其他厂商](https://openai.github.io/openai-agents-python/models/) · [追踪](https://openai.github.io/openai-agents-python/tracing/) · [人工审批](https://openai.github.io/openai-agents-python/human_in_the_loop/) · [测试](https://openai.github.io/openai-agents-python/testing/)
- 持久执行与安全：[Temporal × OpenAI Agents SDK](https://temporal.io/blog/announcing-openai-agents-sdk-integration) · [OWASP Agentic Top 10](https://cycode.com/blog/owasp-top-10-agentic-applications/) · [CSA：OWASP LLM Top 10 2026](https://cloudsecurityalliance.org/blog/2026/10/21/the-owasp-top-10-for-llm-applications-2026-what-changed-and-why-it-matters)
- Harness：[DeepSeek Harness 发布](https://venturebeat.com/technology/deepseek-harness-launches-as-open-source-rival-to-claude-code-alongside-v4-pro-on-api-with-higher-prices) · [Wavect 生产就绪评审](https://wavect.io/blog/deepseek-harness-enterprise-review/) · [Pi 作者文章](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) · [Pydantic AI issue #5193](https://github.com/pydantic/pydantic-ai/issues/5193)
- 检索：[2026 生产 RAG](https://1337skills.com/blog/2026-06-12-production-rag-2026-hybrid-search-reranking-graphrag/)
