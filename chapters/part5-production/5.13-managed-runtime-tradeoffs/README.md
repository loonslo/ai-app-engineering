# L5.10 托管运行时取舍 · 清单

[全书目录](../../README.md) · [上一章 L5.9](../5.12-capacity-slo-recovery/README.md) · [下一章 L5.11](../5.14-llm-system-design/README.md)

- **目标**：了解“托管 Agent 运行时”的现状，用决策矩阵为 capstone 做一次“自建还是采购”的判断，并写出理由。
- **v3 路径**：L5.10 / 核心（清单验收）
- **岗位任务 / 面试题型**：T5 / F3
- **前置**：[4.19 执行面](../../part4-agents-langgraph/4.19-agent-execution-plane/README.md)、[5.10 控制面与执行面](../5.10-control-execution-plane/README.md)。
- **环境**：只读官方页面，不需要账号，不调用任何付费服务。
- **时间盒**：1 小时。

## 问题

前面你自己搭了执行面：任务表、worker、审批、取消、回调。现在主流模型厂商和云厂商都在提供**托管**的 Agent 运行时，把这一层打包成服务。你要能回答：什么时候自建，什么时候采购？不能只凭“省事”或“不想被锁定”这类感觉。

## 概念：现状速览

下面各条只记录我们**核对过**的内容；每条都附官方来源与读取日期（2026-10-31）。产品和定价变化很快，细节一律以官方文档为准；没有核对到的写“未核实”。

| 运行时 | 核对到的信息 | 来源 |
|---|---|---|
| OpenAI Agents API | 2026-09-10 发布，公开测试版（public beta）；托管 Codex harness，负责编排、长会话与上下文管理；执行环境可选 OpenAI 托管沙箱、自有基础设施或合作的沙箱提供商；公告称不收额外费用，只按 token 与工具用量计费。数据驻留与各地区可用性：**未核实** | [Introducing the Agents API](https://openai.com/index/introducing-the-agents-api/) |
| Claude Managed Agents | 2026-04-08 发布，Claude Platform 上的公开测试版；托管 harness 与沙箱、长会话、权限与追踪；公告价格为标准 token 价格加每会话小时 0.08 美元的活跃运行时费用；后续新增了自托管沙箱与 MCP 隧道（2026-05-19 的更新文章）。数据驻留与地区可用性：**未核实** | [发布文章](https://claude.com/resources/articles/claude-managed-agents)、[更新文章](https://claude.com/resources/articles/claude-managed-agents-updates)、[文档](https://platform.claude.com/docs/en/managed-agents/overview) |
| LangSmith Deployment 与 Managed Deep Agents | LangSmith 提供部署服务；Managed Deep Agents 的文档页标注为 BETA，部署时把代码项目编译成托管的 LangGraph 应用。具体计费、地区与数据驻留：**未核实** | [Managed Deep Agents](https://docs.langchain.com/langsmith/python/managed-deep-agents-overview)、[Deploy a Managed Deep Agent](https://docs.langchain.com/langsmith/python/managed-deep-agents-deploy)、[LangSmith Deployment](http://docs.langchain.com/langsmith/deployment.md) |
| Microsoft Foundry Agent Service | 文档描述 Foundry 的 Agent Service 支持从声明式到全代码的多种方式；“hosted agents”是在其上以托管方式部署和运行容器化的 Agent（托管、扩缩与可观测性）。正式发布状态、价格与地区：**未核实** | [Agent Service 概览](https://learn.microsoft.com/azure/ai-foundry/agents/overview)、[Hosted agents](https://learn.microsoft.com/en-ca/azure/foundry/agents/concepts/hosted-agents) |
| AWS Bedrock AgentCore | 有官方开发者指南与 AgentCore Runtime 文档，支持直接打包代码部署 Agent。隔离方式、价格、地区与数据驻留：**未核实** | [Overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)、[Direct code deployment](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy.html) |
| Google Vertex AI Agent Engine | 属于 Vertex AI Agent Builder，是用于部署和管理 Agent 的一组服务；产品页称可把 Agent 部署到全托管运行时。具体能力、价格与地区：**未核实** | [Agent Engine 概览](http://cloud.google.com/agent-builder/agent-engine/overview)、[Agent Builder](https://cloud.google.com/generative-ai-app-builder) |

读这张表时注意两点：

- 各家的 harness 是否与模型绑定、是否支持别家的模型，**没有逐项核实**，选型前要自己查；
- “公开测试版”意味着接口和计费可能变化，生产使用前要评估这一风险。

## 决策矩阵

对一个具体系统，从这六个维度比较“自建（本课程的 4.19 + 5.10 路线）”与“采购某个托管运行时”：

| 维度 | 要问的问题 |
|---|---|
| 数据驻留 | 数据和会话存在哪个地区？能否满足你的合规要求？ |
| 锁定风险 | 换供应商要重写多少？harness、会话格式、工具协议是否开放（如 MCP）？ |
| 成本 | 运行时费用 + token 费用 vs 自建的人力和基础设施？低流量与高流量时分别怎样？ |
| 控制力 | 能否自定义审批、权限、沙箱、重试、预算上限？出了问题能看到多少内部状态？ |
| 合规 | 审计日志、访问控制、证书与报告是否满足客户要求？ |
| 目标地区是否可用 | 你的用户所在地区、你的云区域是否支持？ |

## 流程

按 [CHECKLIST](gate/CHECKLIST.md) 为 capstone 填一次矩阵，写出“自建还是采购”的结论与理由；证据写在 [workbook.md](workbook.md)。

## 练习

1. 选 1–2 个你认为最相关的运行时，用上面的六个维度逐项查官方文档，查不到的写“未核实”，不要猜；
2. 为 capstone 填矩阵：自建一列、采购一列；
3. 写结论：自建还是采购，什么条件变化时你会改变结论。

## 产物与验收

- 填好的决策矩阵（自建 vs 采购，六个维度）；
- 一段结论与理由，并写明“什么条件变化会改变结论”；
- 验收看：每个维度的判断是否有来源或明确标“未核实”；结论是否同时考虑了成本与控制力，而不是只讲其中一个。

## 边界

- 本章只读官方公告与文档，没有注册、没有调用、没有实测任何托管运行时；表里的信息会过期。
- 没有比较性能、稳定性、价格的具体数字，也没有核对各地区可用性与数据驻留；这些在表里都标为“未核实”。
- “自建还是采购”没有唯一答案；课程给的是比较维度，不是推荐。
