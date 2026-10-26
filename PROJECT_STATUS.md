---
project_id: langchain-learning
updated: 2026-10-27
status: active
overview: 测试工程师转 AI 应用开发的章节课程、企业客服旗舰项目与岗位选修专项。
progress: "课件全量结构完成（82 章 + 29 步）；完成 Capstone 核心稳定性与并发性能优化；完成测试转复合型 AI 应用开发工程师求职作品集与面试攻防手册梳理（STAR 简历、5 分钟 Pitch、四层攻防卡）。离线生产测试 34 passed，章节测试 28 passed，ruff 与 milestones/baseline 全部通过。未运行真实外部模型与物理部署验收。"
next: "进入真实学习/试教：按各章任务书执行 gate 或清单并记录失败；补真实模型、数据库、Docker/GPU、远端 CI/staging 证据；核对第三方内容版权与课程时长。"
evidence:
  - README.md
  - TASKS.md
  - chapters/README.md
  - docs/curriculum-v2.md
  - docs/course-v2-structure-validation.md
  - docs/gate-samples-validation.md
  - docs/gate-b1-validation.md
  - docs/gate-b2a-validation.md
  - docs/gate-b2b-validation.md
  - docs/gate-b3a-validation.md
  - docs/gate-b3b-validation.md
  - docs/gate-b4a-validation.md
  - docs/gate-b4b-validation.md
  - docs/gate-b4c-validation.md
  - docs/gate-b4d-validation.md
  - docs/gate-b5a-validation.md
  - docs/gate-b5b-validation.md
  - docs/gate-b6a-validation.md
  - docs/gate-b6b-validation.md
  - docs/gate-b6i-validation.md
  - flagship-project/ACCEPTANCE.md
  - docs/course-restructure-validation.md
  - docs/course-book-validation.md
  - docs/course-review-validation.md
  - docs/course-book-v1-validation.md
  - docs/capstone-optimization-validation.md
  - capstone/docs/portfolio/resume_evidence.md
  - capstone/docs/portfolio/project_pitch.md
---

# LangChain 学习记录 · 项目概览与进度

本页是本项目的概览与进度摘要。更新进度时先核对证据文件及实际验收；任务细节仍以项目原有的 TASKS、ROADMAP 或验收记录为准。只根据有证据的变化修改状态与日期；未验证事项保留“待核实”，不把文件存在或 Git 改动当作完成。

2026-09-28 完成章节导航、统一还原工具、CI 路径与历史资料归档，并补齐入门章节。真实模型回归暴露拒答仍携带无关引用的问题，已记录到 TASKS；未将其写为验收通过。

同日按用户反馈改为用途文件名，所有学习目录先链接书稿正文；正文涵盖场景、概念、流程、代码导读和练习记录。最新离线结果与未验证边界见 course-book-validation，课程内容调整不表示本人已学完。

2026-09-29 按反馈继续逐个排查旧日编号内容：清理失效路径和日编号命名、更新 PDF 书稿并重建 99 页成品。仅完成静态扫描、PDF 构建检查和页面缩略图目视检查；未运行测试。生成目录和测试缓存清理受限情况见 `docs/project-cleanup-validation.md`。

2026-09-30 按七项要求审查课程：订正断链、文字与代码不符和多处实际缺陷，补充注释与测试；随后按确认清理旧环境和历史输出，并修复拒答附引用与混合检索证据门槛。命令、结果和未验证边界见 `docs/course-review-validation.md`；课程内容调整不表示本人已学完。

同日按本次修订重建 PDF 书稿并定版 v1.0（100 页、120 张图，机械与几何自检通过，书签 97 条）。订正的是与当前仓库对不上的说法：封面配套代码、环境依赖与自检命令、代码地图中的旧日编号与已删除目录、6 章两处实现的验收口径、7.7 端到端的流式表述。命令、核对结果和未做逐页目视检查的边界见 `docs/course-book-v1-validation.md`；书稿定版不表示本人已学完或真实环境验收通过。

2026-10-18 完成课程路径 v2 提案：以 5 份岗位样本和 1 份行业能力地图对照现有 82 章 + 29 步，提出核心 58 章、约 321 小时的 12 周路径与阶段出口门，并列出 5.1 前置矛盾、3.9 后移、选修线代码血缘过重等结构问题。只是设计提案，未修改章节、未运行课程测试，不代表学习完成或真实环境验收。

同日完成全量结构修复：82 章 + 29 个旗舰步骤共 111 个 README 写入 `v2 路径`；3.9 标明建议在 4.10 后学，5.2 改为 5.1 gate 之后，9.1/10.1 区分学习前置与运行代码血缘；新增映射与幂等工具，260 个 Markdown 断链 0。离线测试 28 passed，ruff 通过。未物理移动 3.9、未重排目录；命令与边界见 `docs/course-v2-structure-validation.md`。

同日把 5 个样板章改为 Gate：L1.6 / L2.9 / L3.4 / L4.4 / L5.1 对应 2.5 / 2.4 / 3.3 / 4.5 / 5.1，新增闭卷骨架、离线验收脚本、故障注入和 gate workbook，重写 README。用临时参考解跑通 16/16、14/14、14/14、14/14、17/17；默认骨架 0 通过（预期），现有离线测试 28 passed，ruff 通过。未运行真实模型、未部署、未验证真实学习者从零实现；命令、结果与边界见 `docs/gate-samples-validation.md`。

同日完成 B1 Gate 化：1.1–1.5、1.8 新增闭卷骨架与离线验收，覆盖请求/响应契约、流式收集、结构化解析、会话预算、工具回灌、CLI 控制流。临时参考解跑通 11/11、10/10、10/10、12/12、11/11、11/11；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未运行真实模型、未验证真实学习者；命令与边界见 `docs/gate-b1-validation.md`。

同日完成 B2a Gate 化：2.1–2.3 覆盖加载/切分、向量化/索引、最小 RAG 的上下文/引用/拒答。临时参考解跑通 6/6、9/9、10/10；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实 embedding/模型；命令与边界见 `docs/gate-b2a-validation.md`。

同日完成 B2b Gate 化：2.6–2.11 覆盖 PDF 溯源、切分策略、混合检索 RRF、查询改写、JSON 持久化、重排/recall@k。临时参考解跑通 9/9、7/7、7/7、9/9、9/9、8/8；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实 embedding/reranker/PDF；命令与边界见 `docs/gate-b2b-validation.md`。

同日完成 B3a Gate 化：3.1、3.2、3.4、3.5 覆盖失败定位顺序、拒答/关键词指标、评测集 schema/覆盖、评测集合并与 RAGAS 行。临时参考解跑通 8/8、6/6、7/7、8/8；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实模型/RAGAS；命令与边界见 `docs/gate-b3a-validation.md`。

同日完成 B3b：3.7 回归对比、3.10 失败诊断改为 gate，3.6 LangSmith 因外部服务改为清单验收。临时参考解跑通 8/8、5/5；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未运行真实模型/LangSmith/DeepEval；命令与边界见 `docs/gate-b3b-validation.md`。

同日完成 B4a：4.1–4.4 覆盖 Agent 有界循环、LangGraph 线性/分支、recursion_limit、状态 reducer/fan-out。临时参考解跑通 8/8、4/4、4/4、5/5；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实模型/检查点；命令与边界见 `docs/gate-b4a-validation.md`。

同日完成 B4b：4.6 节点可靠性、4.7 结构化路由改为 gate，覆盖降级/可重试/真实超时、枚举路由/意图分类。临时参考解跑通 7/7、4/4；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实模型；命令与边界见 `docs/gate-b4b-validation.md`。

同日完成 B4c：4.8 规划与执行、4.9 可观测性、4.10 检查点与上下文改为 gate，覆盖计划解析/异常/超长、轨迹记录/汇总、会话隔离/副本/裁剪。临时参考解跑通 6/6、4/4、6/6；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实模型/checkpointer；命令与边界见 `docs/gate-b4c-validation.md`。

2026-10-26 完成 Capstone 核心模块稳定性与并发性能优化：修复 BM25 缓存无界与增量版本失效风险，消除 SQLite 监控指标每次插入重复 DDL/WAL 开销，多租户 Registry 粗粒度全局锁升级为分租户细粒度锁与双重检查，并在 KnowledgeBase 内部复用可靠 LLM 链实例。34 项离线测试全部通过（耗时由 10.14s 降至 6.62s）、28 项工具链测试通过、ruff 通过、milestones 与 baseline 全部通过。未运行真实模型与远端服务；命令、结果与边界见 `docs/capstone-optimization-validation.md`。

2026-10-27 完成求职作品集与面试攻防实操手册梳理：基于测试转复合型 AI 应用开发工程师定位，提炼 STAR 项目经历与 5 分钟 Pitch 讲稿，确立“检索前 ACL + 增量确定性同步 + 身份/版本感知缓存”为第一技术卖点，整合“三层质量金字塔 CI 门禁”、“七阶段线性归因漏斗”、“分租户条带锁并发调优”与“HITL 有界 Agent”四大硬核攻防卡（风险-实现-证据-边界），并同步更新 portfolio 文档与证据链。
