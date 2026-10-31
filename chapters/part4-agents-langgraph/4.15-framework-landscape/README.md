# 4.15 框架取舍：先写需求，再选择工具

[全书目录](../../README.md) · [上一章 L4.15](../4.22-reuse-harness/README.md) · [下一章 L4.17](../4.23-async-agent-gate/README.md)

- **目标**：根据业务约束选择编排层，把原生循环、框架 API 与仍由应用承担的责任对应起来，而不是按流行程度选工具。
- **v2 路径**：L4.1 / 核心阅读（清单验收）
- **岗位任务 / 面试题型**：T3 / F3、F6。
- **前置**：L4.2 有界循环、L4.3 工具契约、L4.5 Pydantic AI、L4.9–L4.11 状态与执行面。
- **环境**：Python 3.11+；对照练习需 `langchain` 顶层包及其锁定依赖。3 小时（1h 选型 + 1h 离线对照 + 1h 记录）。默认不联网、不读 `.env`，不需要模型密钥。

## 问题

固定检索问答、有限订单工具调用、主管审批后可恢复的工单，不需要同一种运行时。选择从流程需求出发：步骤是否固定，状态是否需要恢复，工具是否有副作用，团队能否维护依赖与迁移。

模型 SDK 负责请求；Agent 框架负责工具循环；图运行时负责显式状态与分支；harness 在循环周围加入上下文、文件、计划与委派能力。框架提供机制，业务权限、事实来源、幂等与验收仍由应用设计。MCP 是工具接入协议，A2A 是 Agent 间协作契约，不是另一种编排框架；换传输不会自动获得租户隔离或可靠性。

## 概念

### 1. 2026 年的事实，不等于选型结论

以下来源均读取于 **2026-10-31**。区分调查、官方发布、仓库锁定与本机观察；不把其中一种冒充另一种。

| 事实与口径 | 一手证据 | 如何影响选择 |
|---|---|---|
| Stack Overflow 2026 的 AIOrch 可选题，Used 回答数 n=4,400：LangChain 30.2%，OpenAI Agents SDK 23.8%，LangGraph 18.8%，Google ADK 14.0%，Pydantic AI 8.9% | [原始题目、样本数与结果](https://survey.stackoverflow.co/2026/ai/data/ai-orch)；问题是过去一年使用过什么，不是“所有开发者的市场占有率”，也不是招聘比例 | 框架素养有用；多选题不能相加为市场份额，更不能据此推断可靠性 |
| 雷达 Vol.34（2026-04）将 LangGraph 从 Adopt 移到 Trial | [Thoughtworks 原文](https://www.thoughtworks.com/en-us/radar/languages-and-frameworks/summary/langgraph)：共享大状态图并非所有 Agent 的默认解，简单 Agent 可先通过代码协作，需要时再加图 | 有明确状态、分支、恢复与人工介入时用图，不把环位当“禁止使用” |
| Microsoft Agent Framework 1.0 已面向 Python / .NET GA | [Microsoft 2026-04-29 发布记录](https://www.microsoft.com/releasecommunications/api/v2/azure/rss/560982)、[官方概览](https://learn.microsoft.com/en-us/agent-framework/overview/) | 已有 Microsoft 生态是评估理由；不能据此声称所有语言、集成和预览功能都稳定 |
| OpenAI Agents Python SDK 的可核实发布 v0.24.0，2026-10-15，仍为 0.x | [官方发布](https://github.com/openai/openai-agents-python/releases/tag/v0.24.0) | 锁版本，复核升级对已保存运行、工具错误处理的影响；不要把 `openai` 客户端包与 `openai-agents` 混为一谈 |
| 本课程基于 Pydantic AI **2.31.1**（v2），并非声称它是上游最新版 | [官方 v2.31.1 源码标签](https://github.com/pydantic/pydantic-ai/tree/v2.31.1)、[课程约束](../../../docs/v3/conventions.md#9-pydantic-ai-约定) | 保持课程锁定；不启用该版本自带遥测、web fetch、本地 FileUrl 下载或 ConcurrencyLimitedModel；不要照搬最新版 Harness 示例 |

**招聘现实如何表述？** 本次没有找到可复核的一手岗位样本、地区、时间窗口与去重口径，不能把“LangChain 出现率约 23–35%”写成 2026 招聘事实。上面的 30.2% 是开发者自报使用率，不是招聘率。练习时可自行采集一组公开 JD，记录网址、日期、岗位总数、去重规则与提及数，只对自己的样本下结论。

### 2. 把原生概念翻译成 API

API 对照的作用是读懂项目，不是承诺所有框架语义相同。下列官方页面同样读取于 2026-10-31；除本章 LangChain 对照外均为文档阅读，未逐一安装实测。

| 原生责任 | 对应 API / 机制 | 不会自动替你完成什么 |
|---|---|---|
| 模型 → 工具 → 观察 → 下一轮；前后置处理 | LangChain [`create_agent`、middleware](https://docs.langchain.com/oss/python/langchain/agents)；middleware 是模型或工具调用前后的拦截点 | 业务授权、可信身份、退款幂等；middleware 不是操作系统沙箱 |
| 显式状态、条件分支、快照、暂停 | LangGraph [`StateGraph`、checkpointer、interrupt](https://docs.langchain.com/oss/python/langgraph/overview)；分别对应图、状态保存器、暂停点 | 崩溃任务的发现与调度、外部副作用恰好一次；见 L4.10、L4.11 |
| 文件与计划、上下文卸载、子 Agent | [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview)，在 LangChain / LangGraph 之上加 harness | 虚拟文件系统不等于进程/网络隔离；复用审查见 L4.15 |
| Agent 配置、执行循环、委派、校验、会话 | OpenAI Agents SDK 的 [`Agent`、`Runner`、handoff、guardrail、session](https://openai.github.io/openai-agents-python/)；handoff 转交控制，guardrail 检查输入/输出，session 保存会话上下文 | guardrail 不取代服务端鉴权；session 不等于完整持久执行。默认 OpenAI Responses 路径不能假设所有兼容网关支持 |
| 带类型工具、宿主依赖、审批或外部执行待定 | Pydantic AI [`Agent`、`RunContext`](https://ai.pydantic.dev/agents/)、[deferred tools](https://ai.pydantic.dev/deferred-tools/)；RunContext 注入身份/资源；deferred tools 把待审批或外部结果交回宿主 | 不能信任客户端自报的租户或审批；保存历史、收集审批、续跑与幂等仍需设计；最新文档能力不代表课程 2.31.1 全部具备 |
| Agent 与工作流组合 | [Google ADK 的 Agent / LlmAgent 与 workflows](https://google.github.io/adk-docs/agents/) | 与现有平台的模型、会话、部署适配需要逐项核实，不能因名称相似就互换快照 |
| Agent、会话、工具、中间件、显式工作流 | [Microsoft Agent Framework 的 Agent / workflows](https://learn.microsoft.com/en-us/agent-framework/overview/) | 平台治理不等于应用权限；连接第三方服务的数据边界仍是自己的责任 |

## 流程：怎样做一次选择

1. 写一个可验收需求：状态字段、预算、工具读写权限、超时、审批、崩溃后恢复位置。
2. 先问普通函数是否够用。步骤固定，不为“Agent”这个名字引入模型决策。
3. 短工具循环先比较原生与带类型 SDK；需要显式状态、分支与恢复时再评估图。
4. 单独检查谁负责启动失败任务、谁负责幂等，避免把 checkpointer 当执行面。
5. 对原生、Pydantic AI、LangChain / LangGraph、OpenAI Agents SDK 填同一矩阵：控制流、可观测性、持久化/HITL、部署、学习成本、锁定风险；每个候选都写选择条件、拒绝条件和退出成本。
6. 做一次失败实验，再写结论。面试表达用“需求 → 证据 → 选择 → 拒绝理由 → 退出方案”，不说“什么都用 LangChain”。

判断示例：只读订单查询可以先用小循环；有复杂分支的审批流程值得评估 LangGraph；跨进程长业务链路还需 L4.11 执行面。它们是教学判断，不是性能排名，最后需要你自己的失败实验支持。

## 练习

### A. 同一订单任务，真正运行两种运行时

本章 [`create_agent_langchain.py`](create_agent_langchain.py) 复用 **L4.2 的原生循环**（物理目录 `4.5-react-agent/react_agent.py`）以及 **L4.3 的订单工具**（`4.18-tool-design/tool_design.py`）。不是复制业务逻辑，也不是手写一个循环冒充 LangChain。

2026-10-31 通过 `.venv` 元数据与源码检查：`langchain==1.3.14`、`langchain-core==1.4.9`、`langgraph==1.2.8`；与根 `requirements.txt` 一致。早期“顶层包缺失”“本机 LangGraph 1.2.10”不是本次机器状态。未安装时按课程锁定集安装，不执行无版本的 `pip install -U`；本章不新增依赖，也不需要安装其他候选 SDK。

```bash
.venv/Scripts/python.exe chapters/part4-agents-langgraph/4.15-framework-landscape/create_agent_langchain.py
# 查看两边真正收到的消息与工具结果
.venv/Scripts/python.exe chapters/part4-agents-langgraph/4.15-framework-landscape/create_agent_langchain.py --messages
```

脚本没有 `--live` 分支，不创建真实模型客户端、不读 `.env`，并关闭 LangChain / LangSmith 的自动追踪。CLI 失败时打印可读错误、退出 1，不输出 traceback；成功与否由实际运行结果决定，本页不预填通过记录。

运行前先预测，运行后再对照：

- 两条路径各得到新的 `shop_a` 固定订单数据，只暴露 `get_order`、`list_orders`，不暴露退款工具。
- 同一脚本依次请求查 A100、列第一页、给最终答复。LangChain 用自带 `FakeMessagesListChatModel` 生成真实 `AIMessage`；`create_agent` 实际执行工具并生成 `ToolMessage`。
- 安装版假模型继承的 `bind_tools` 抛 `NotImplementedError`，因此只在一个小子类中补绑定接口；**不重写 `_generate`、不替换 `create_agent`**。脚本已经决定工具，不能用它证明模型会正确选工具。`sleep=None`，不等待；假模型会循环响应，因此本次运行也设有 `recursion_limit`。
- 报告同时显示工具调用 ID、名字、参数、实际业务观察、是否成功、模型轮数、结束原因与答案；`equivalent` 比较这些归一化字段，不要求框架消息外壳一致。
- `line_counts` 用 `inspect.getsourcelines` 现场统计物理源码行（含空行、注释、docstring），分别列原生运行时、两边适配器、假模型适配器与共享代码。不把 SDK 内部隐藏的行数算作消失，也不拿“更短”推断更快或更可靠。原生循环还含本练习未覆盖的错误/预算/审批分支，复杂度并不对等。

### B. 选型与失败实验

从固定检索问答、有限订单查询、审批后可恢复工单中选一个。写明哪些状态可改、如何停止、如何授权与审计、恢复会重跑什么、替身如何覆盖拒答与隔离、迁移后重验哪些契约。

在 A 中把 `CALLS` 的一个订单号暂改为其他租户的 `B200`，在隔离副本里运行，记录是否只得到“未找到订单”；或者把 `recursion_limit` 降低，观察真实运行时如何有界失败。实验后恢复副本，不改共享工具或用硬编码新答案掩盖差异。把这次失败与一个“只有最终回答正确、轨迹却错误”的反例写进 workbook。

## 产物与验收

完成 [选型工作簿](workbook.md) 与 [清单](gate/CHECKLIST.md)：四类方案必须全部进入矩阵，每一行都有适用理由、不采用理由、退出成本与证据性质；附离线报告、行数口径和一次失败分析。

能够说明框架替你做了哪些工作、仍由应用负责什么，才完成本章清单。文件存在、脚本退出 0、文档里写着“durable”都不能替代故障证据。

## 边界

离线脚本验证的是固定消息下运行时的工具执行与消息连接，不验证模型质量、token 费用、真实供应商兼容、生产性能、写操作审批、持久恢复或部署。`--messages` 的 SDK 消息 ID 可能自动生成；确定性比较使用归一化轨迹，而非完整消息的逐字节相等。尚未安装或实测的框架写“文档阅读 / 未实测”。无法核实的招聘百分比不纳入教材事实。
