# 0.5 岗位地图与差距诊断

[全书目录](../../README.md) · [上一章 L0.4](../0.4-python-engineering-base/README.md) · [下一章 L1.1](../../part1-foundations/1.1-first-call/README.md)

- **目标**：把 3 份目标 JD 拆成岗位任务、技能、证据要求与面试题型；按客观证据给自己打分诊断技能缺口；把 16 周排期落地到个人日历。
- **v3 路径**：L0.5 / 核心（清单验收）
- **岗位任务 / 面试题型**：T6 / F6
- **前置**：已完成 [L0.4 AI 应用的 Python 工程底座](../0.4-python-engineering-base/README.md)
- **环境**：具备网络浏览器查阅公开招聘 JD；Markdown 文本编辑器

---

## 问题

测试工程师向 AI 应用开发转型中最常见的两个误区：
1. **盲目刷课调包**：学完一堆开源框架，能跑通几个 Demo，但不知道目标岗位到底要求什么，简历投递石沉大海；
2. **“按感觉打分”的自我误判**：“我看过相关视频，我懂了”，把“有概念”当成“有胜任力”。结果在技术面试被深挖生产细节、故障归因和评测数据时迅速暴露。

必须通过真实招聘市场的硬性要求建立客观坐标系，用证据（代码、测试、指标报告、上线运行记录）诊断自身差距。

---

## 概念

### 1. 2026 年招聘市场的四个核心事实

根据全球主流招聘统计与行业报告，当前 AI 应用工程师市场呈现以下关键特征：

> [!NOTE]
> 以下市场统计数据摘自本课程调研报告（见 [curriculum-v3.md](../../../docs/curriculum-v3.md) 第 8 节与附录），数据由调研人员于 **2026-10-27** 读取与核对。招聘市场动态变化迅速，数据仅作为学习规划与岗位画像的宏观背景。

1. **入门级初级岗位极少（Entry-level Squeeze）**：
   - [365 Data Science 2025/2026 AI 岗位报告](https://365datascience.com/career-advice/career-guides/ai-engineer-job-outlook-2025/)（读取日期：2026-10-27）显示，0–2 年经验的初级/入门 AI 岗位在挂牌职位中仅占约 **2.5%**；
   - [Rockstar Developer University 入门岗位统计汇总](https://rockstardeveloperuniversity.com/entry-level-software-engineer-job-market-statistics/)（读取日期：2026-10-27）显示，软件工程行业整体挂牌初级职位占比在 **4.5%–12%** 区间波动。
   两项数据共同印证：纯新手、零传统工程经验的求职者直接切入面临严苛竞争。
2. **工程经验与基础设施要求高（High Engineering Bar）**：
   - 根据 [Axial Search AI 岗位需求与经验要求报告](https://axialsearch.com/insights/ai-engineering-job-demand)（读取日期：2026-10-27），AI 工程师职位中中级（Mid-level）与高级（Senior-level）合计占比约 **66%**（中位年限要求为 5 年，初级岗位中位要求约 2 年）；约 **56%** 的岗位硬性要求云平台（AWS / GCP / Azure）工程化使用经验；
   - 另据面向落地交付方向的 FDE（前置交付工程）岗位技能分析，容器化与持续交付工具同样是硬门槛：Docker 要求约占 **35%**、Kubernetes 约占 **31%**、CI/CD 流水线约占 **27%**。
   这说明大模型应用开发本质是“现代软件工程 + 模型算子能力”，企业绝不仅仅需要 Prompt 调优者，而是需要懂系统架构与交付底座的工程师。
3. **评测类岗位与前置交付工程师（FDE）高速增长**：
   随着企业私有化模型和垂直业务上线，专门负责评测集构建、LLM-as-a-Judge 调优、回归防护的“AI 评测/质量工程师”，以及深入客户现场对接的“FDE / 交付工程师”需求显著攀升（来源：[TechCrunch FDE 报道](https://techcrunch.com/2026/07/30/forward-deployed-engineers-are-the-ai-industrys-latest-talent-obsession/)、[Talex AI Evaluation 洞察](https://www.talex.co/insights/what-is-a-ai-evaluation-engineer-and-why-companies-are-hiring-for-it-now)，读取日期：2026-10-27）。
4. **评测与质量工程能力是面试中的强信号**：
   行业调研（[Anthropic Demystifying Evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)、[Datadog State of AI](https://www.datadoghq.com/state-of-ai-engineering/)，读取日期：2026-10-27）表明，能够讲清“如何量化模型幻觉、构建 Golden Set、设计校准的 Judge 机制、线上事故归因与自动化回归”的候选人，更具差异化竞争力。这正是测试工程师转型的最大护城河。

### 2. 四类目标岗位画像与预期匹配度

| 目标岗位 | 预期匹配度 | 主要技术支撑与产物 |
|---|---|---|
| **AI 评测 / AI 质量工程师** | **高** | 自动化 Eval Harness、Golden Set 构建、LLM-as-a-Judge、回归门禁与指标报告 |
| **中级 AI 应用工程师** | **中** | 基础模型 API 原语、确定性结构化抽取、企业 RAG 系统、有状态 Agent 与真实上线主作品 |
| **FDE / 交付工程师** | **中低** | 工程化交付、客户系统对接、私有化部署、Docker 容器化；国内方向结合本地模型推理能力 |
| **大厂核心算法/架构师** | **低** | 需要深厚的机器学习算法训练、预训练/大模型微调理论以及底层高并发分布式架构深度 |

---

## 流程

完成岗位差距诊断的标准流程分为三步：
1. **收集与结构化拆解 JD**：收集 3 份目标岗位的真实 JD，区分硬性条件与加分项，对标到岗位任务（T1–T7）与面试题型（F1–F6）；
2. **按证据自评**：严禁凭感觉打分，严格按“0分未接触、1分有概念、2分离线练习、3分真实上线证据”给自己打分；
3. **制定 16 周排期日历**：结合自身节奏，将技能缺口攻坚落实到具体学习周与里程碑。

### 按证据自评打分量规
- **0 分（未接触）**：没接触过，不清楚技术细节和底层原理；
- **1 分（有概念）**：看过文档、论文或视频讲解，能讲清概念，但没有独立动手写过代码；
- **2 分（离线练习）**：亲手写过代码，在本地通过了离线单元测试或离线 Gate 检查；
- **3 分（真实运行与上线证据）**：调用过真实大模型 API、系统公网部署运行、积累了真实流量、或有详细的真实评测报告与事故复盘记录。

---

## 练习

使用本章节提供的 3 份标准模板完成自评与规划：
1. **收集与拆解 JD**：在主流平台寻找 3 份真实 JD，记录来源链接与读取日期，使用 [templates/jd-breakdown.md](templates/jd-breakdown.md) 逐项拆解；
2. **完成差距自评**：使用 [templates/self-assessment.md](templates/self-assessment.md) 针对 T1–T7 逐项按证据客观打分，找出最大缺口；
3. **制定 16 周日历**：使用 [templates/schedule-16w.md](templates/schedule-16w.md) 制定个人执行日历，注意在第 6 周末前安排主作品 P2 的公网最小上线，以满足就业出口标准（E1 要求公网稳定运行 ≥4 周）。

---

## 产物与验收

完成本章后交付并归档以下产物：
1. **3 份 JD 拆解报告**：完成 [templates/jd-breakdown.md](templates/jd-breakdown.md) 并保留原始来源与读取日期；
2. **差距自评分数表**：完成 [templates/self-assessment.md](templates/self-assessment.md)，列出每一项打分的具体证据；
3. **个人 16 周排期表**：完成 [templates/schedule-16w.md](templates/schedule-16w.md) 并填入日历安排；
4. **清单核对**：逐项核对并勾选 [gate/CHECKLIST.md](gate/CHECKLIST.md) 的全部 7 项标准。

---

## 边界

- **市场数据时效性**：招聘市场动态变化迅速，若距离读取日期超过 6 个月，相关比例数值可能发生漂移；
- **自评结果不代表录用保证**：高匹配度代表技能画像贴合，不等于通过招聘初筛；
- **模板为离线规划工具**：本章不包含自动化运行代码，完成标准以清单与产物文档为准。
