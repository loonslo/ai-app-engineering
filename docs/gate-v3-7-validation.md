# V3-7 篇 11 项目主线（P）验证 · 2026-10-31

本批次改了什么：新建篇 11（`chapters/part11-project-sprint/`）：篇首 README 与 6 个项目章 11.1–11.6（README、`gate/CHECKLIST.md`、模板），11.5 另含一个零依赖的静态前端示例 `example_static/`。没改任何旧章节，没改 capstone 代码（那是 V3-9），没有 gate。

实施线程额度用完，由审核者亲自实施并复跑，没有实施与审核的分离。

## 范围

| 编号 | 目录 | 文件 |
|---|---|---|
| 篇首 | `part11-project-sprint/` | `README.md`：E1 全文、6 章排期、与 capstone 的关系、三类证据记录方式 |
| P1 | `11.1-requirements-metrics` | README、CHECKLIST、`prd-1page`、`stakeholder-interview`、`metrics-definition` |
| P2 | `11.2-walking-skeleton-deploy` | README、CHECKLIST、`deploy-record`、`feedback-log` |
| P3 | `11.3-control-plane-hardening` | README、CHECKLIST、`decision-record` |
| P4 | `11.4-execution-plane-launch` | README、CHECKLIST、`eval-report`、`postmortem`、`slo-report` |
| P5 | `11.5-demo-web-ui` | README、CHECKLIST、`ui-checklist`、`example_static/index.html`、`example_static/app.js` |
| P6 | `11.6-project-narrative` | README、CHECKLIST、`portfolio-readme`、`decisions-index`、`demo-script-10min`、`evidence-index`、`resume-bullets` |

另改 `tools/course_catalog.py`（登记 11.1–11.6）。

## 外部出处核对（2026-10-31 读取）

| 内容 | 实际读到的 | 与细则的差异 |
|---|---|---|
| MIT NANDA《The GenAI Divide》 | 2025-07，作者自述“初步发现”；回顾 300+ 公开项目、访谈 52 家组织、153 位高管问卷；认为多数企业级系统失败于脆弱的工作流、缺少上下文学习、与日常运作不匹配 | 细则写“没有和工作流结合、上线成本没有预估”；原文没有“成本没有预估”，README 只引用读到的，并写明成本一条是课程判断 |
| Anthropic 与 Material《2026 State of AI Agents Report》 | 2025 年末调查 500+ 美国技术负责人；挑战：集成 46%、数据质量 42%、变更管理 39% | 与细则一致，并标明厂商调查 |
| 招聘方文章 | 只找到博客与教育机构内容页（zalt.me 两篇、Scaler 一篇）；其观点与细则大意一致，但性质是个人博客与营销性内容 | README 明确写成“行业经验，不是研究结论”，不当统计引用 |

## 实际执行

| # | 命令 | 结果 |
|---|---|---|
| 1 | `tools/check_course_links.py` | 0 断链 |
| 2 | `apply_v3_map.py --check` | 11.1–11.6 均 unchanged |
| 3 | `ruff check --target-version py311 chapters/part11-project-sprint chapters/part12-job-track tools chapters/test_v3_lessons.py` | 通过 |
| 4 | `pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py capstone/test_regression.py -q` | 114 passed |
| 5 | LangChain 导入检查 | part11 无命中 |
| 6 | 11.5 静态页面：用一个假 FastAPI（`/chat`、`/feedback`、静态文件）在无头 Chromium 中操作 | 提问、引用、`degraded` 与 `needs_human` 徽标、反馈写回（服务端收到 `{conversation_id:1, rating:1}`）、429 的可读错误（含 trace_id）、答案里的 `<b>` 不被解析为 HTML、控制台无错误；截图已看过 |

## 细则偏离

- 招聘方文章的出处弱（博客、教育机构），已按“行业经验”降级表述。
- 11.5 的 API 约定沿用 5.1 的参考实现（`/chat`、`/feedback`），`degraded`、`needs_human` 是可选字段：5.1 目前不返回它们，页面对缺省按“否”处理。

## 未验证

- 11.5 页面没有对接真实的 5.1 或 capstone 服务；没有自动化前端测试、移动端与无障碍检查。
- 所有模板都没有被真实学习者填写；E1 的各项数值门槛没有任何真实记录。
- 没有部署、没有真实用户、没有真实评测——本批次只提供指南、清单和模板。
