# P 项目主线细则（篇 11，V3-7）

阶段目标：从第 5 周起，把各阶段的产出持续并入同一个公开项目：第 6 周末前最小上线，之后两次迭代，持续积累真实用量与证据，最后整理成作品叙事。

出口：[outline.md](../outline.md) 第 6 节 E1。

“你的项目”指本仓库的 `capstone/`，或学习者自己的公开仓库。项目章以指南、清单与模板为主，不设 gate；涉及 capstone 代码的改动由 V3-9 完成（[capstone.md](capstone.md)）。

## 篇首

- 新建 `chapters/part11-project-sprint/README.md`，写明：
  - 篇目标与 E1 的完整内容；
  - 6 章的排期（对应 outline.md 第 7 节）；
  - 与 capstone 的关系；
  - “离线 / 真实 / 部署”三类证据的记录方式（链接 L0.2）。
- 每章使用 [conventions.md 4.4](../conventions.md#44-项目章与就业章) 的结构，模板放在各章的 `templates/` 下。

---

## P1 需求与指标

- **目录**：`chapters/part11-project-sprint/11.1-requirements-metrics/`
- **课时 / 节奏**：4h，第 5 周
- **岗位任务 / 面试题型**：T6 / F3、F6
- **README 必讲**：
  1. 先定义问题与成功标准，再写代码；企业 AI 项目常见的失败原因是没有和工作流结合、上线成本没有预估（引用 MIT NANDA 与 Anthropic 和 Material 的调查结论，注明读取日期与“厂商调查”属性）。
  2. 指标分四类：质量（引用正确率、拒答正确率、字段准确率）、延迟（p95）、成本（单次请求）、采用（真实用户数、请求数）。
  3. 怎样找真实用户：同事、测试团队、社区；访谈问什么。
- **模板**：
  - `templates/prd-1page.md`：问题、用户、范围与非目标、成功指标、约束、风险；
  - `templates/stakeholder-interview.md`：访谈提纲与记录；
  - `templates/metrics-definition.md`：指标名、计算方式、数据来源、门槛、采集频率。
- **CHECKLIST**：
  - [ ] 至少访谈 2 位潜在真实用户并记录；
  - [ ] 写完 1 页 PRD；
  - [ ] 定义 golden set 的来源（真实问题、真实失败）；
  - [ ] 把 E1 的目标数写进指标定义。
- **常见失败**：没有用户就开始写代码；指标没有采集方式。

---

## P2 最小上线

- **目录**：`chapters/part11-project-sprint/11.2-walking-skeleton-deploy/`
- **课时 / 节奏**：5h，第 6 周末前完成
- **前置**：L1.10、L2.12
- **岗位任务 / 面试题型**：T5、T6 / F4
- **README 必讲**：
  1. 为什么要尽早上线：真实用量需要时间积累；E1 要求项目已运行 ≥4 周。
  2. 最小上线包含什么：知识库 v1（L2.12）加嵌入式功能（L1.10）；HTTPS；简单鉴权（API key 或基础认证）；不含个人信息的请求日志；费用上限；用户反馈入口。
  3. 不包含什么：高可用、多租户、执行面（后续迭代再做）。
  4. 部署方式：一台 VPS 加 Docker Compose 是最便宜的通用方案；也可以用 L5.8 介绍的托管服务（目录 `5.11-cloud-deploy`，届时尚未学到，按其 README 操作即可）。
- **模板**：
  - `templates/deploy-record.md`：地址（可以只记私有地址）、上线日期、版本、邀请的用户、请求计数方式、费用上限；
  - `templates/feedback-log.md`。
- **CHECKLIST**：
  - [ ] 服务可从外网访问，并启用 HTTPS 与鉴权；
  - [ ] 日志不记录个人信息；
  - [ ] 设好费用上限；
  - [ ] 至少邀请 3 位真实用户；
  - [ ] 每周记录一次请求数与反馈。
- **边界**：只是最小可用，不代表生产级安全。

---

## P3 迭代 1：控制面加固

- **目录**：`chapters/part11-project-sprint/11.3-control-plane-hardening/`
- **课时 / 节奏**：10h，第 9–12 周
- **前置**：L2、L3、L5.1
- **岗位任务 / 面试题型**：T1、T2、T4、T5 / F3、F4、F5
- **README 必讲**：
  1. 原生 RAG 核心：去掉框架胶水，接口清晰可测。
  2. 边界上的 Pydantic 契约。
  3. 把评测接进 CI 门禁（L3）。
  4. 可靠性：超时、重试、降级（L5.1）。
  5. 每个关键决定写进 `DECISIONS.md`。
- **CHECKLIST**（每项写验收命令或证据路径）：
  - [ ] 主链路不再依赖框架胶水（本仓库对应 V3-9 的 capstone 改动）；
  - [ ] 边界契约有测试；
  - [ ] 评测门禁在 CI 中运行，阈值写明；
  - [ ] 依赖故障时不返回 500；
  - [ ] `DECISIONS.md` 至少 3 条。
- **模板**：`templates/decision-record.md`（背景、选项、决定、代价、复审时间）。

---

## P4 迭代 2：执行面与真实证据

- **目录**：`chapters/part11-project-sprint/11.4-execution-plane-launch/`
- **课时 / 节奏**：10h，第 13–14 周
- **前置**：L4.17、L5.4、L5.6、L5.7、L5.9
- **岗位任务 / 面试题型**：T3、T4、T5 / F3、F5、F6
- **README 必讲**：
  1. 把一个长任务改成执行面（L4.11、L5.7），例如批量工单分诊或周报生成。
  2. 审批与幂等。
  3. 认证与多租户检查（L5.4）。
  4. OpenTelemetry（L5.6）。
  5. 真实模型评测：golden set ≥50 条；judge 用 ≥30 条人工标注校准，并报告一致率。
  6. 事故复盘：真实发生的问题怎样检测、止损、定位根因、预防。
  7. SLO 与成本报告（L5.9）。
- **模板**：
  - `templates/eval-report.md`（数据集、模型 ID、日期、指标、失败分类、与上次对比）；
  - `templates/postmortem.md`；
  - `templates/slo-report.md`。
- **CHECKLIST**：
  - [ ] 执行面上线；
  - [ ] 真实模型评测报告；
  - [ ] judge 校准报告；
  - [ ] ≥2 份事故复盘（必须是真实发生的，不得虚构）；
  - [ ] p95 延迟、单次请求成本、缓存命中率；
  - [ ] SLO 报告。

---

## P5 可演示前端

- **目录**：`chapters/part11-project-sprint/11.5-demo-web-ui/`
- **课时 / 节奏**：3h，第 11–12 周
- **岗位任务 / 面试题型**：T6 / F4
- **README 必讲**：面试官更愿意点开一个能用的页面；最小前端需要的功能——提问、展示引用、展示降级与“需要人工”状态、反馈按钮（“有用 / 没用”）、错误提示。
- **实现方式**：默认是零依赖的静态 HTML 加原生 JS，由 FastAPI 的静态文件服务提供；不引入前端框架。偏全栈方向的学习者可以另用 TypeScript 重写（选修）。
- **文件**：`templates/ui-checklist.md`，以及一个最小示例 `example_static/`（`index.html`、`app.js`），调用约定的 API。
- **CHECKLIST**：
  - [ ] 5 个功能齐全；
  - [ ] 错误状态可读；
  - [ ] 录制 1 分钟演示视频或截图，登记到证据索引。

---

## P6 项目叙事与证据索引

- **目录**：`chapters/part11-project-sprint/11.6-project-narrative/`
- **课时 / 节奏**：4h，第 15–16 周
- **岗位任务 / 面试题型**：T6 / F6
- **README 必讲**：
  1. 招聘方看什么：真实上线、用量数字、事故、评测证据、取舍理由（引用招聘方文章，注明这些是行业经验而非研究结论）。
  2. 常见减分项：只有 notebook、没有用量数字、评测靠目测、说不出事故、“什么都用 LangChain”。
  3. 每一个声明都要能对上代码或证据。
- **模板**：
  - `templates/portfolio-readme.md`：问题 → 架构 → 评测 → 事故 → 数字 → 下次会怎么改；
  - `templates/decisions-index.md`；
  - `templates/demo-script-10min.md`；
  - `templates/evidence-index.md`：声明 → 证据文件或命令 → 日期 → 类型；
  - `templates/resume-bullets.md`：按三类目标岗位分别写，数字只取自证据。
- **CHECKLIST**：
  - [ ] 作品 README 完成；
  - [ ] 证据索引中的每一条都可以打开或复现；
  - [ ] 简历中没有代码不支持的说法（例如仍有框架胶水时，不写“完全去框架”）；
  - [ ] 10 分钟演示稿演练 2 次。

## 审核重点（全篇）

- 模板可以直接复用；清单项可判定。
- 不鼓励、不示范任何虚构的用户、数字或事故。
- 与 V3-9、L5 的分工清楚，不重复要求同一件事。
