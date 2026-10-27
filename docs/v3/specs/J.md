# J 就业轨道细则（篇 12，V3-8）

阶段目标：第 3–16 周持续训练面试形式与求职材料，避免“学完才开始准备”。内容对应招聘流程的三道关：筛选（简历与作品）、面试（编码、AI 辅助编码、系统设计、take-home、评测讨论、行为面）、投递管理。

出口：[outline.md](../outline.md) 第 6 节 E3、E4。

## 篇首

- 新建 `chapters/part12-job-track/README.md`，写明：
  - 本篇目标；
  - 每周节奏（J2 每周、J3 每周 1–2h、J4 隔周、J5 三次）；
  - 与 L0.5 岗位地图的衔接；
  - 证据如何登记到 L0.2 的证据索引。
- 用 [conventions.md 4.4](../conventions.md#44-项目章与就业章) 的结构。
- 市场与面试信息会变：README 中的事实注明来源与读取日期；超过 6 个月的内容标注“请复核”。

---

## J1 定位与三版简历

- **目录**：`chapters/part12-job-track/12.1-positioning-resume/`
- **课时 / 节奏**：4h，第 3–4 周，之后每 4 周更新一次
- **岗位任务 / 面试题型**：T6 / F6
- **README 必讲**：
  1. 为什么不以“新人 AI 工程师”的身份投递：入门岗位占比低，中位要求约 5 年经验（引用 Axial Search、365 Data Science，注明读取日期）。
  2. 定位句：“X 年测试/质量工程 + AI 评测与应用交付”；怎样把测试年限写成工程经验。
  3. 三类目标岗位的简历侧重点：AI 应用工程师（交付与上线）、AI 评测与质量工程师（评测体系与指标）、FDE 与交付（需求、集成、部署、沟通）。
  4. 简历条目公式：动作 + 系统 + 数字 + 证据。
  5. 减分项：框架名堆砌、没有数字、“什么都用 LangChain”、说不出取舍。
- **模板**：
  - `templates/positioning.md`；
  - `templates/resume-ai-app.md`；
  - `templates/resume-ai-eval.md`；
  - `templates/resume-fde.md`。
- **CHECKLIST**：
  - [ ] 写好定位句；
  - [ ] 写好三版简历，每条数字都能在证据索引中找到来源；
  - [ ] 找一位同行或用 AI 做一次“招聘方视角”审阅并记录修改。

---

## J2 公开作品节奏

- **目录**：`chapters/part12-job-track/12.2-public-portfolio-cadence/`
- **课时 / 节奏**：4h，第 3–16 周，每周约 20 分钟
- **岗位任务 / 面试题型**：T6 / F6
- **README 必讲**：
  1. 每周一条公开更新：问题、做法、评测数字、失败、下一步。
  2. 发布位置：GitHub README 或 Pages、个人博客。
  3. 隐私：不公开密钥、内部数据与真实用户信息。
  4. 第 8 周与第 14 周各写一篇较完整的评测方法文章，满足 E2。
- **模板**：`templates/weekly-update.md`、`templates/eval-article-outline.md`。
- **CHECKLIST**：14 周的打卡表；2 篇评测文章的链接。

---

## J3 编码面试与 AI 辅助编码

- **目录**：`chapters/part12-job-track/12.3-coding-interview/`
- **课时 / 节奏**：14h，第 3–14 周，每周 1–2h
- **岗位任务 / 面试题型**：T7 / F1、F2
- **README 必讲**：
  1. 2026 年的编码面试形态：大厂仍考算法（常见为 LeetCode 中等难度）；AI 公司与初创更多是“用 LLM API 现场构建”；部分公司设有允许使用 AI 的编码轮（Meta 自 2025-10 起，Google 在试点），也有公司明确禁止（Amazon 要求书面承诺）。注明来源与读取日期，并说明以招聘方当次通知为准。
  2. 允许用 AI 的编码轮怎么评分：解题、代码质量、验证、沟通。测试背景的优势在“验证”。
  3. 算法练习计划（只在目标含大厂时重点投入）：数组与哈希、双指针、栈与队列、二分、树与图的 BFS / DFS、堆、区间、基础动态规划；用 Python。
- **文件**：
  - `templates/dsa-tracker.md`：题目、类型、用时、是否独立完成、复盘。
  - `drill/`：一个多文件的小服务（如工单路由，4 个模块左右），预埋 3 个 bug：分页差一、时区比较、幂等判断写反。
  - `drill/check_drill.py`：断言式检查脚本，不命名为 `test_*.py`。修复前失败、修复后通过。
  - `templates/ai-verification-log.md`：AI 给了什么建议、哪里不对、怎样验证、最终改法。
- **CHECKLIST**：
  - [ ] 用 AI 助手完成 `drill`，并填写验证记录；
  - [ ] 另外再做 2 次 AI 辅助编码演练（可以用开源仓库里的真实 issue）；
  - [ ] 目标含大厂时，按计划记录算法练习。
- **审核重点**：`check_drill.py` 在原始代码上失败、在修复版上通过；修复版放在 `.tmp/gate_solutions/v3/12.3-drill/`。

---

## J4 LLM 系统设计模拟

- **目录**：`chapters/part12-job-track/12.4-llm-system-design-mock/`
- **课时 / 节奏**：8h，第 6–14 周，隔周一次，共 5 次
- **岗位任务 / 面试题型**：T5、T6 / F3、F5
- **README 必讲**：
  1. 模拟流程：计时 45 分钟；口述或书写；之后按评分表自评；可以请同行或 AI 扮演面试官追问。
  2. 必须覆盖评测计划与成本。面试指南普遍认为评测讨论是多数候选人没准备的一轮（注明来源与“行业经验”属性）。
  3. 复用 L5.11 的设计模板与评分表。
- **题目**（`prompts.md`，每题附追问清单）：
  1. 带权限与引用的企业文档问答；
  2. 通过 3 个内部工具帮用户提交工单的 Agent：哪些操作无需确认、怎样防止循环、怎样测试；
  3. 通话摘要的评测体系：golden set 里放什么、谁来标注、什么情况阻止发布；
  4. 带成本控制与降级的多租户 LLM 网关；
  5. 异步长任务调研 Agent，需支持检查点与审批。
- **CHECKLIST**：5 份书面设计与复盘，登记到证据索引。

---

## J5 限时 take-home 模拟

- **目录**：`chapters/part12-job-track/12.5-take-home-sim/`
- **课时 / 节奏**：12h，第 5–6 周、第 7–8 周、第 13–14 周各一次
- **岗位任务 / 面试题型**：T1–T4 / F4、F5
- **README 必讲**：
  1. 企业常见的 take-home 时长为 4–8 小时，也有 60–90 分钟的现场构建。评分看可运行的代码、对坏输出的处理、测试、评测脚本、写明取舍的 README（注明来源与“面试辅导机构整理”属性）。
  2. 一个能打印分数的小评测脚本往往是最大的加分项。
- **文件**：
  - `briefs/a-doc-qa.md`：带引用与拒答的文档问答，限时 4h；
  - `briefs/b-extraction.md`：结构化抽取分类器，附评测脚本，限时 3h；
  - `briefs/c-tool-agent.md`：带安全约束与测试的工具调用 Agent，限时 4h。
  - 每份任务书写明：需求、提供的数据（`fixtures/`，小而可再分发）、接口约定（供离线检查器调用）、交付物、评分表。
  - `checkers/check_a.py`、`check_b.py`、`check_c.py`：离线检查器。用 `--module` 指定学习者的实现，以假模型运行固定用例，结构与 gate 相同。
  - `templates/self-review.md`：按评分表自评，写明用时与未完成项。
- **CHECKLIST**：3 次 take-home 都在限时内提交；检查器全部通过；自评表达标。
- **审核重点**：三个检查器在空实现上失败、在参考解上通过；参考解放在 `.tmp/gate_solutions/v3/12.5-a.py` 等。

---

## J6 行为面故事

- **目录**：`chapters/part12-job-track/12.6-behavioral-stories/`
- **课时 / 节奏**：3h，第 13–14 周
- **岗位任务 / 面试题型**：T6 / F6
- **README 必讲**：
  1. STAR 结构。
  2. 事故故事的写法：发现 → 止损 → 根因 → 预防。
  3. 6 个故事必须覆盖：2 次事故、1 次评测驱动的改进、1 次降本、1 次安全问题、1 次跨团队沟通。
  4. 减分项：只讲成功、说不出数字、把团队成果说成个人成果。
- **模板**：`templates/star-story.md`、`templates/incident-story.md`。
- **CHECKLIST**：6 个故事写完，并各口述演练 1 次；故事中的事实都能在证据索引中找到来源。

---

## J7 投递与漏斗

- **目录**：`chapters/part12-job-track/12.7-applications-funnel/`
- **课时 / 节奏**：5h，第 15–16 周集中，第 9 周起可以少量投递
- **岗位任务 / 面试题型**：T6 / F6
- **README 必讲**：
  1. 目标公司清单按岗位类型分组。
  2. 内推优先。
  3. 每周复盘漏斗转化（投递 → 回复 → 面试 → offer）。
  4. 每次面试后写复盘。
  5. offer 比较的维度。
  6. 底线：不在简历与面试中虚构经历或数字。
- **模板**：
  - `templates/target-companies.md`（≥30 家，分组）；
  - `templates/funnel-tracker.md`；
  - `templates/weekly-review.md`；
  - `templates/referral-message.md`；
  - `templates/interview-debrief.md`；
  - `templates/offer-compare.md`。
- **CHECKLIST**：目标清单完成；漏斗记录至少覆盖 2 周；每次面试都有复盘。

## 审核重点（全篇）

- 面试与市场信息有来源、日期与性质说明（研究、厂商、行业经验）。
- 演练代码与检查器符合“修复前失败、修复后通过”。
- 模板可以直接使用；不出现任何示范性的虚构经历。
