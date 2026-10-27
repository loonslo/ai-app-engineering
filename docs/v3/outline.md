# v3 课程大纲

> 状态：提案配套大纲（2026-10-27）。章节、编号、目录、课时与批次以本文件为准；论证与依据见 [curriculum-v3.md](../curriculum-v3.md)，编写规则见 [conventions.md](conventions.md)。

## 1. 目标

学完并达到第 6 节的就业出口标准后，能以“测试/质量工程背景 + AI 评测与应用交付”的定位投递中级岗位。

| 目标岗位 | 预期匹配度 | 主要支撑 |
|---|---|---|
| AI 评测 / AI 质量工程师 | 高 | L1.10、L2.11、L3、L4.7，以及 E1 中的评测证据 |
| 中级 AI 应用工程师 | 中 | L1–L5 与 P 主线的上线证据 |
| FDE / 交付工程师 | 中低 | P1、P2、L5.8、L5.11；国内交付方向加选 5.6、9.11 |
| 大厂 AI 工程师 | 低 | 另需 J3 的算法训练与后端深度 |

匹配度是审查判断，不是统计结论。

## 2. 岗位任务与面试题型

每章细则都写明对应的岗位任务（T）与面试题型（F）。

| 代码 | 岗位任务 |
|---|---|
| T1 | 把 LLM 功能嵌入现有系统（抽取、分类、生成） |
| T2 | 基于企业资料的检索问答，带权限与引用 |
| T3 | 能执行动作的 Agent 或工作流，带审批与恢复 |
| T4 | 评测与质量改进：评测集、判分、回归、线上反馈 |
| T5 | 生产运维：部署、观测、成本、可靠性、安全与合规 |
| T6 | 需求与沟通：范围、指标、对接现有系统 |
| T7 | 用编码 Agent 开发，并验证它的输出 |

| 代码 | 面试题型 |
|---|---|
| F1 | 编码（算法） |
| F2 | AI 辅助编码：在多文件代码库里修 bug、实现、验证 |
| F3 | LLM 系统设计 |
| F4 | 动手构建 / take-home |
| F5 | 评测设计讨论 |
| F6 | 行为面：事故、取舍、协作 |

## 3. 结构与课时

- **技术阶段 L0–L5**：约束逐步递增，先练嵌入式功能（形态 A），再练专项 Agent（形态 B）。
- **项目主线 P（篇 11）**：第 5–16 周贯穿；第 6 周末前最小上线，之后持续积累真实用量。
- **就业轨道 J（篇 12）**：第 3–16 周贯穿，约占总课时 13%。

| 部分 | 课时 | 出口 |
|---|---|---|
| L0 定位与工具链 | 12h | 环境通；一次带测试、经人工复核的编码 Agent 改动；岗位自评与排期 |
| L1 模型 API 原语与嵌入式功能 | 46h | L1.9 gate 通过；L1.10 双 gate 通过并产出 golden set 报告 |
| L2 上下文工程与检索 | 60h | 真实资料知识库：30–50 题评测，引用正确率 ≥90%、拒答正确率 ≥90%、hit@5 ≥80%，附消融表 |
| L3 质量闭环 | 28h | judge 与人工一致率 ≥80%；回归门禁可在 CI 运行 |
| L4-A Agent 控制流 | 44h | 同一 Agent 的原生版与 Pydantic AI 版通过同一套 eval，含 5 个故障注入 |
| L4-B 状态、执行面与安全 | 46h | 异步专项 Agent：权限、审批、崩溃恢复、5 个故障注入、pass^3 报告 |
| L5 服务化与生产 | 58h | 部署到一个主流云或 VPS；SLO 与成本报告；一次故障演练 |
| P 项目主线 | 36h | 第 6 节 E1 |
| J 就业轨道 | 50h | 第 6 节 E3、E4 |
| **合计** | **380h** | 16 周，平均每周约 24h；第 15–16 周以求职为主 |

## 4. 章节总表

目录列省略前缀 `chapters/`。类型含义：

| 类型 | 含义 |
|---|---|
| 保留 | 内容不变，只在 V3-10 添加 v3 标签 |
| 换实现 | 参考实现去掉 LangChain，改用原生 SDK；gate 不变；README 同步改写实现相关段落 |
| 改写 | README 与参考实现按新目标重写；gate 按细则保留、追加或替换 |
| 增补 | 在原章节上补内容；细则写明是否追加 gate 检查项 |
| 新增 | 新建目录与全部文件 |
| 阅读 | 核心阅读，归入所在 v3 章节，不另设验收 |

### L0 定位与工具链（12h）

| v3 编号 | 标题 | 类型 | 目录 | 验收 | h | 批次 |
|---|---|---|---|---|---|---|
| L0.1 | 环境与最小闭环 | 保留 | `part0-setup/0.1-environment` | 清单 | 2 | — |
| L0.2 | 证据式学习法 | 增补 | `part0-setup/0.2-learning-workflow` | 清单 | 2 | V3-1 |
| L0.3 | 用编码 Agent 开发与审查 | 新增 | `part0-setup/0.3-coding-agent-workflow` | 清单 + 产物 | 3 | V3-1 |
| L0.4 | AI 应用的 Python 工程底座 | 新增 | `part0-setup/0.4-python-engineering-base` | gate | 3 | V3-1 |
| L0.5 | 岗位地图与差距诊断 | 新增 | `part0-setup/0.5-job-map-gap` | 清单 + 产物 | 2 | V3-1 |

### L1 模型 API 原语与嵌入式功能（46h）

| v3 编号 | 标题 | 类型 | 目录 | 验收 | h | 批次 |
|---|---|---|---|---|---|---|
| L1.1 | 一次调用与 LLM 边界 | 换实现 | `part1-foundations/1.1-first-call` | gate | 4 | V3-1 |
| L1.2 | LLM 工作原理 | 改写 | `part1-foundations/1.7-llm-internals` | gate + 自测清单 | 5 | V3-1 |
| L1.3 | 输出控制与流式 | 换实现 | `part1-foundations/1.2-control-output` | gate | 3 | V3-1 |
| L1.4 | 结构化输出 | 换实现 | `part1-foundations/1.3-structured-output` | gate | 5 | V3-1 |
| L1.5 | 多轮与上下文预算 | 换实现 | `part1-foundations/1.4-context-memory` | gate | 4 | V3-1 |
| L1.6 | 工具调用协议 | 换实现 | `part1-foundations/1.5-tool-calling` | gate | 5 | V3-1 |
| L1.7 | Provider 抽象、第二厂商与成本 | 新增 | `part1-foundations/1.9-provider-cost` | gate | 5 | V3-1 |
| L1.8 | 手写 Harness | 增补（README） | `part2-rag/2.5-raw-sdk-rag-agent-loop` | gate | 6 | V3-1 |
| L1.9 | Gate：CLI 助手 | 换实现 | `part1-foundations/1.8-cli-chatbot` | gate | 3 | V3-1 |
| L1.10 | 嵌入式 LLM 功能与 eval harness | 新增 | `part1-foundations/1.10-embedded-llm-feature` | 双 gate + 产物 | 6 | V3-1 |

### L2 上下文工程与检索（60h）

| v3 编号 | 标题 | 类型 | 目录 | 验收 | h | 批次 |
|---|---|---|---|---|---|---|
| L2.1 | 上下文工程总论 | 新增 | `part2-rag/2.12-context-engineering` | gate | 4 | V3-2 |
| L2.2 | 数据接入与切分 | 换实现 | `part2-rag/2.1-load-split`、`part2-rag/2.6-pdf-sources` | gate ×2 | 5 | V3-2 |
| L2.3 | 向量化与召回 | 换实现 | `part2-rag/2.2-embed-retrieve` | gate | 5 | V3-2 |
| L2.4 | 最小 RAG：引用与拒答 | 换实现 | `part2-rag/2.3-minimal-rag` | gate | 5 | V3-2 |
| L2.5 | 切分策略消融 | 换实现 | `part2-rag/2.7-chunk-strategy` | gate | 4 | V3-2 |
| L2.6 | 混合检索与重排 | 换实现 | `part2-rag/2.8-hybrid-search`、`part2-rag/2.11-multimodal-rerank` | gate ×2 | 7 | V3-2 |
| L2.7 | 查询改写与 agentic retrieval | 换实现 + 增补 | `part2-rag/2.9-query-rewrite` | gate（追加检查） | 6 | V3-2 |
| L2.8 | 持久化与增量索引 | 换实现 | `part2-rag/2.10-chroma-persist` | gate | 4 | V3-2 |
| L2.9 | 静态上下文与 Skills | 新增 | `part2-rag/2.13-static-context-skills` | gate | 4 | V3-2 |
| L2.10 | 记忆与压缩 | 新增 | `part2-rag/2.14-memory-compaction` | gate | 4 | V3-2 |
| L2.11 | RAG 评测基线 | 增补 | `part2-rag/2.4-eval-seed` | gate | 5 | V3-2 |
| L2.12 | Gate：真实资料知识库 v1 | 新增 | `part2-rag/2.15-real-corpus-kb-gate` | gate + 产物 | 7 | V3-2 |

### L3 质量闭环（28h）

| v3 编号 | 标题 | 类型 | 目录 | 验收 | h | 批次 |
|---|---|---|---|---|---|---|
| L3.1 | 失败分析 | 保留 | `part3-evals/3.1-error-analysis` | gate | 4 | — |
| L3.2 | 评测集建设 | 保留 | `part3-evals/3.4-eval-dataset-build` | gate | 4 | — |
| L3.3 | 规则评测与 pytest 回归 | 保留 | `part3-evals/3.2-eval-basics`、`part5-production/5.8-pytest-regression` | gate ×2 | 4 | — |
| L3.4 | LLM Judge 与校准 | 换实现 | `part3-evals/3.3-llm-judge`（阅读 8.5） | gate | 5 | V3-3 |
| L3.5 | 指标口径 | 保留 | `part3-evals/3.5-eval-dataset-ragas` | gate | 2 | — |
| L3.6 | 回归、A/B、pass^k 与报告 | 换实现 + 增补 | `part3-evals/3.7-eval-regression-curve`、`part3-evals/3.8-prompt-ab-judge`、`part3-evals/3.10-eval-report-failures` | gate ×3（3.7 追加检查） | 5 | V3-3 |
| L3.7 | 追踪与评测平台 | 改写 | `part3-evals/3.6-langsmith-eval` | 清单 | 2 | V3-3 |
| L3.8 | 线上反馈闭环 | 阅读 | `part8-ai-quality-optional/8.10-production-feedback-loop` | — | 2 | — |

### L4-A Agent 控制流（44h）

| v3 编号 | 标题 | 类型 | 目录 | 验收 | h | 批次 |
|---|---|---|---|---|---|---|
| L4.1 | Workflow 与 Agent | 改写 | `part4-agents-langgraph/4.1-agent-patterns` | gate（追加检查） | 5 | V3-4 |
| L4.2 | 有界 Agent 循环 | 换实现 | `part4-agents-langgraph/4.5-react-agent` | gate | 6 | V3-4 |
| L4.3 | 工具设计 | 新增 | `part4-agents-langgraph/4.18-tool-design` | gate | 6 | V3-4 |
| L4.4 | 结构化路由与规划 | 换实现 | `part4-agents-langgraph/4.7-structured-routing`、`part4-agents-langgraph/4.8-plan-and-execute` | gate ×2 | 6 | V3-4 |
| L4.5 | 用 Pydantic AI 写 Agent | 新增 | `part4-agents-langgraph/4.16-pydantic-ai-agent` | gate | 8 | V3-4 |
| L4.6 | 多 Agent 与上下文隔离 | 改写 | `part4-agents-langgraph/4.14-supervisor-fanout` | gate | 4 | V3-4 |
| L4.7 | Agent 评测 | 增补 | `part3-evals/3.9-agent-trajectory-eval`（阅读 8.6） | gate（追加检查） | 6 | V3-4 |
| L4.8 | Gate：原生版与 SDK 版 | 新增 | `part4-agents-langgraph/4.17-native-vs-sdk-gate` | gate | 3 | V3-4 |

### L4-B 状态、执行面与安全（46h）

| v3 编号 | 标题 | 类型 | 目录 | 验收 | h | 批次 |
|---|---|---|---|---|---|---|
| L4.9 | 状态图（LangGraph） | 增补 | `part4-agents-langgraph/4.2-langgraph-basics`、`4.3-branch-loop`、`4.4-state-reducer`、`4.6-node-reliability` | gate ×4 | 8 | V3-5 |
| L4.10 | 检查点、HITL 与持久执行 | 增补 | `part4-agents-langgraph/4.10-checkpoint-context`、`4.11-streaming-hitl` | gate ×2 | 7 | V3-5 |
| L4.11 | 专项 Agent 执行面 | 新增 | `part4-agents-langgraph/4.19-agent-execution-plane` | gate | 8 | V3-5 |
| L4.12 | 沙箱与最小权限 | 新增 | `part4-agents-langgraph/4.20-sandbox-least-privilege` | gate | 5 | V3-5 |
| L4.13 | Agent 安全 | 换实现 + 增补 | `part4-agents-langgraph/4.12-tool-safety-search` | gate | 5 | V3-5 |
| L4.14 | MCP 实战与取舍 | 新增 | `part4-agents-langgraph/4.21-mcp-practice` | gate | 5 | V3-5 |
| L4.15 | 复用现成 harness | 新增 | `part4-agents-langgraph/4.22-reuse-harness` | 清单（实操选做） | 2 | V3-5 |
| L4.16 | 框架素养 | 改写 | `part4-agents-langgraph/4.15-framework-landscape` | 清单 + 练习 | 3 | V3-5 |
| L4.17 | Gate：异步专项 Agent | 新增 | `part4-agents-langgraph/4.23-async-agent-gate` | gate + 产物 | 3 | V3-5 |

### L5 服务化与生产（58h）

| v3 编号 | 标题 | 类型 | 目录 | 验收 | h | 批次 |
|---|---|---|---|---|---|---|
| L5.1 | FastAPI、SSE 与可靠性 | 换实现 | `part5-production/5.1-serve-fastapi`、`part5-production/5.2-reliability-retry` | gate ×2 | 9 | V3-6 |
| L5.2 | 成本：缓存、路由、峰谷 | 换实现 + 增补 | `part5-production/5.3-cost-cache-routing` | gate（追加检查） | 4 | V3-6 |
| L5.3 | 持久化与 SQL | 保留 | `part5-production/5.4-sqlite-persistence` | gate | 4 | — |
| L5.4 | 认证、授权与多租户 | 新增 | `part5-production/5.15-auth-multitenancy`（阅读 9.5、capstone） | 清单 + 产物 | 5 | V3-6 |
| L5.5 | 护栏、红队与治理 | 增补 | `part5-production/5.7-security-guardrails`（阅读 8.8） | gate（追加检查） | 5 | V3-6 |
| L5.6 | 可观测性：OpenTelemetry | 新增 | `part5-production/5.9-otel-observability` | gate | 6 | V3-6 |
| L5.7 | 控制面与执行面集成 | 新增 | `part5-production/5.10-control-execution-plane` | gate | 5 | V3-6 |
| L5.8 | 容器、CI 评测门禁与云部署 | 保留 + 新增 | `part5-production/5.5-docker-packaging`（阅读 8.9）、`part5-production/5.11-cloud-deploy` | gate + 清单 | 8 | V3-6 |
| L5.9 | 容量、SLO 与恢复 | 新增 | `part5-production/5.12-capacity-slo-recovery` | gate | 5 | V3-6 |
| L5.10 | 托管运行时取舍 | 新增 | `part5-production/5.13-managed-runtime-tradeoffs` | 清单 | 1 | V3-6 |
| L5.11 | LLM 系统设计 | 新增 | `part5-production/5.14-llm-system-design` | 清单 + 产物 | 3 | V3-6 |
| L5.12 | 模型方案取舍 | 增补 | `part6-model-tradeoffs/6.1-choose-prompt-rag-finetune` | gate | 3 | V3-6 |

### P 项目主线（篇 11，36h）

| v3 编号 | 标题 | 类型 | 目录 | 验收 | h | 批次 |
|---|---|---|---|---|---|---|
| P1 | 需求与指标 | 新增 | `part11-project-sprint/11.1-requirements-metrics` | 清单 + 产物 | 4 | V3-7 |
| P2 | 最小上线 | 新增 | `part11-project-sprint/11.2-walking-skeleton-deploy` | 清单 + 产物 | 5 | V3-7 |
| P3 | 迭代 1：控制面加固 | 新增 | `part11-project-sprint/11.3-control-plane-hardening` | 清单 + 产物 | 10 | V3-7 |
| P4 | 迭代 2：执行面与真实证据 | 新增 | `part11-project-sprint/11.4-execution-plane-launch` | 清单 + 产物 | 10 | V3-7 |
| P5 | 可演示前端 | 新增 | `part11-project-sprint/11.5-demo-web-ui` | 清单 + 产物 | 3 | V3-7 |
| P6 | 项目叙事与证据索引 | 新增 | `part11-project-sprint/11.6-project-narrative` | 清单 + 产物 | 4 | V3-7 |

### J 就业轨道（篇 12，50h）

| v3 编号 | 标题 | 类型 | 目录 | 验收 | h | 批次 |
|---|---|---|---|---|---|---|
| J1 | 定位与三版简历 | 新增 | `part12-job-track/12.1-positioning-resume` | 清单 + 产物 | 4 | V3-8 |
| J2 | 公开作品节奏 | 新增 | `part12-job-track/12.2-public-portfolio-cadence` | 清单 | 4 | V3-8 |
| J3 | 编码面试与 AI 辅助编码 | 新增 | `part12-job-track/12.3-coding-interview` | 清单 + 演练测试 | 14 | V3-8 |
| J4 | LLM 系统设计模拟 | 新增 | `part12-job-track/12.4-llm-system-design-mock` | 清单 + 产物 | 8 | V3-8 |
| J5 | 限时 take-home 模拟 | 新增 | `part12-job-track/12.5-take-home-sim` | 任务书 + 离线检查器 | 12 | V3-8 |
| J6 | 行为面故事 | 新增 | `part12-job-track/12.6-behavioral-stories` | 清单 + 产物 | 3 | V3-8 |
| J7 | 投递与漏斗 | 新增 | `part12-job-track/12.7-applications-funnel` | 清单 + 产物 | 5 | V3-8 |

## 5. 选修与降级

| 章节 | 处置 | 原因 |
|---|---|---|
| 1.6 MCP 入门 | 选修，被 L4.14 取代 | 要点并入 4.21；旧脚本依赖 langchain-mcp-adapters |
| 4.9 可观测性 | 选修 | L5.6 用 OpenTelemetry 重做 |
| 4.13 Text2SQL | 选修 | 数据类岗位再学 |
| 5.6 Ollama 本地推理 | 选修；国内交付方向必修 | 私有化部署 |
| 6.2 LoRA 微调 | 选修 | 概念并入 L5.12 |
| 8.1–8.4、8.7 | 选修 | AI 质量工程专项，评测岗加分 |
| 8.5、8.6、8.8、8.9、8.10 | 核心阅读 | 分别归入 L3.4、L4.7、L5.5、L5.8、L3.8 |
| 9.1–9.4、9.6–9.10、9.12 | 选修 | 企业数据与推理设施 |
| 9.5 Postgres RLS | 核心阅读 | 归入 L5.4 |
| 9.11 vLLM | 选修；国内交付方向必修 | 推理服务 |
| 10.1–10.4 | 选修 | MCP 鉴权深挖与 A2A |
| flagship-project | 冻结（2026-10-27） | 基于 LangChain 1.x 的历史教学快照，不再更新；项目实践以 capstone 与 P 为准 |

## 6. 就业出口标准（E1–E4）

| 标准 | 内容 | 主要来源 |
|---|---|---|
| E1 主作品 | capstone 或自有项目：公网可访问且已运行 ≥4 周；≥5 个真实用户、≥200 次真实请求（不含自测）；真实模型评测报告（golden set ≥50 条，judge 用 ≥30 条人工标注校准并给出一致率）；≥2 份事故复盘；p95 延迟、单次请求成本、缓存命中率；`DECISIONS.md`；README 分别列出离线、真实、部署三类证据 | P1–P6、L5 |
| E2 辅助作品 | L1.10 嵌入式功能仓库（含 golden set 与 CI）；一篇评测方法文章或一个小型开源评测工具 | L1.10、J2 |
| E3 面试准备 | 3 次限时 take-home，自评 rubric 全部达标；5 次系统设计模拟（书面设计 + 复盘）；≥3 次 AI 辅助编码演练记录；目标含大厂时另有算法练习记录；6 个 STAR 故事 | J3–J6 |
| E4 求职材料 | 3 版简历与定位陈述；目标公司清单 ≥30 家，按岗位类型分组；投递漏斗记录（投递 → 回复 → 面试 → offer），每周复盘 | J1、J7 |

数值门槛是建议值，按实际记录填写，不得估算或虚构。

## 7. 16 周排期

| 周 | 技术阶段 | 项目主线 P | 就业轨道 J |
|---|---|---|---|
| 1–2 | L0、L1.1–L1.9 | — | L0.5 岗位地图（J 的起点） |
| 3–4 | L1.10、L2.1–L2.8 | — | J1；J2 起每周更新；J3 起每周 1–2h |
| 5–6 | L2.9–L2.12、L3.1–L3.2 | P1；P2（第 6 周末前最小上线） | J5 第 1 次；J4 第 1 次 |
| 7–8 | L3.3–L3.8、L4.1–L4.4 | P2 运行并收集真实请求 | J4 第 2 次；J5 第 2 次 |
| 9–10 | L4.5–L4.11 | P3 开始 | J4 第 3 次 |
| 11–12 | L4.12–L4.17、L5.1–L5.3 | P3 收尾；P5 | J4 第 4 次 |
| 13–14 | L5.4–L5.9 | P4 | J5 第 3 次；J4 第 5 次；J6 |
| 15–16 | L5.10–L5.12、复习补漏 | P6；项目持续运行 | J7 集中投递与面试 |

## 8. 关键前置

- L1.10 依赖 L1.4（结构化输出）、L1.6（工具调用）、L1.7（provider）。
- L2.12 复用 L1.10 的 eval harness，以及 L2.2–L2.8 的检索组件。
- L4.5 以 L1.10 后半的 Pydantic AI 入门为前置。
- L4.8 依赖 L4.2、L4.3、L4.5、L4.7。
- L4.17 依赖 L4.5、L4.11、L4.12、L4.13。
- L5.7 依赖 L4.11。
- P2 依赖 L1.10、L2.12；P3 依赖 L3、L5.1；P4 依赖 L4.17、L5.6、L5.7。
- J5 第 1 次在 L2 之后，第 2 次在 L4-A 之后，第 3 次在 L5 中段。
