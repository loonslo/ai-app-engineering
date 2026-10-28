---
project_id: langchain-learning
updated: 2026-10-28
status: active
overview: 测试工程师转 AI 应用开发的章节课程、capstone 整合项目与岗位选修专项；企业客服旗舰项目已冻结为历史快照。
progress: "V3-0、V3-1 审核均已通过（记录见 docs/v3/reviews/）；V3-2（阶段 2 上下文工程与检索）已在 wip-v3-2 分支完成全量实施与命令自检，待审核。完成 4 个新建章节（2.12 上下文工程、2.13 Skills、2.14 记忆与压缩、2.15 真实资料知识库 v1）与 9 个原生章节重构（2.1、2.6、2.2、2.3、2.7、2.8、2.11、2.9、2.10），在 2.3 和 2.8 保留框架对照；更新 2.4 eval-seed 关联 L1.10 harness 概念并引用 Anthropic 评测指南；所有 gate 均支持 --module 并写出报告，骨架严格 0 通过（退出码 1），参考解 100% 通过（退出码 0）；测试 63 passed（含 29 项 test_v3_lessons）；350 份 Markdown 断链 0；ruff 0 errors；无非预期 LangChain 泄漏；v2 标签 111 unchanged；v3 标签新建 4 章全为 unchanged；14 个参考实现 run_chapter 均正常启动。未运行外部付费模型或公网语料下载。证据见 docs/gate-v3-2-validation.md。"
next: "提交审核者进行 V3-2 审核。审核通过后合入 master 并启动 V3-3（L3 智能体与工具调用）。进入真实学习/试教：按各章任务书执行 gate 或清单并记录失败；补真实模型、数据库、Docker/GPU、远端 CI/staging 证据；核对第三方内容版权与课程时长。"
evidence:
  - README.md
  - TASKS.md
  - chapters/README.md
  - docs/curriculum-v2.md
  - docs/curriculum-v3.md
  - docs/v3/README.md
  - docs/v3/outline.md
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
  - docs/gate-v3-0-validation.md
  - docs/v3/reviews/V3-0.md
  - docs/gate-v3-1-validation.md
  - docs/v3/reviews/V3-1.md
  - docs/gate-v3-2-validation.md
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

同日完成 B3a Gate 化：3.1–3.5 覆盖失败归因、离线指标打底、LLM-as-a-Judge 校准、评测集构建、Ragas 自动化。临时解跑通 8/8、14/14、14/14、13/13、10/10；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实模型与评测平台；命令与边界见 `docs/gate-b3a-validation.md`。

同日完成 B3b Gate 化：3.7、3.9、3.10 覆盖回归曲线对比、Agent 轨迹评测、失败分析报告。临时解跑通 7/7、8/8、6/6；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用外部平台；命令与边界见 `docs/gate-b3b-validation.md`。

同日完成 B4a Gate 化：4.1、4.5、4.7、4.8 覆盖 Agent 四种模式、ReAct 原理与循环、结构化路由、Plan-and-Execute 规划。临时解跑通 8/8、14/14、10/10、10/10；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实模型；命令与边界见 `docs/gate-b4a-validation.md`。

同日完成 B4b Gate 化：4.6 节点可靠性、4.12 工具安全与确认。临时解跑通 10/10、9/9；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实工具；命令与边界见 `docs/gate-b4b-validation.md`。

同日完成 B4c Gate 化：4.2–4.4、4.10、4.11 覆盖 LangGraph 状态图与断点恢复。临时解跑通 6/6、6/6、5/5、6/6、5/5；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实服务；命令与边界见 `docs/gate-b4c-validation.md`。

同日完成 B4d Gate 化：4.14 Supervisor 多智能体分发。临时解跑通 7/7；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用外部 API；命令与边界见 `docs/gate-b4d-validation.md`。

同日完成 B5a Gate 化：5.1 FastAPI、5.2 重试降级、5.7 安全守卫、5.8 pytest 回归。临时解跑通 17/17、10/10、7/7、10/10；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未真实部署；命令与边界见 `docs/gate-b5a-validation.md`。

同日完成 B5b Gate 化：5.4 SQLite、5.7 安全守卫。临时解跑通 4/4、7/7；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未真实部署；命令与边界见 `docs/gate-b5b-validation.md`。

同日完成 B6a Gate 化：6.1 模型选型权衡。临时解跑通 8/8；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未微调真实模型；命令与边界见 `docs/gate-b6a-validation.md`。

同日完成 B6b Gate 化：8.4 RAG 分层测试、8.5 Judge 校准、8.6 Agent 轨迹、8.9 CI 分层门禁、8.10 生产反馈循环。临时解跑通 8/8、8/8、8/8、6/6、6/6；骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未接入真实 CI；命令与边界见 `docs/gate-b6b-validation.md`。

同日完成 B6i 全量收口：82 章 75 gate + 7 checklist 全部落地。临时解全部通过；骨架 0 通过；测试 28 passed、断链 0、v2 标签 111 unchanged、ruff 通过。证据见 `docs/gate-b6i-validation.md`。

2026-10-26 优化 Capstone 核心模块稳定性：修复 BM25 缓存与版本漂移隐患、消除 SQLite 指标重复建表/WAL 开销、多租户 Registry 粗粒度锁升级为分租户细粒度锁与双重检查、复用可靠 LLM 链实例。34 项离线测试全部通过（执行耗时缩减至 6.62s）、28 项工具链测试通过、ruff 通过、milestones 与 baseline 验证通过。未在真实模型或外部服务验证。命令、结果与未验证项见 `docs/capstone-optimization-validation.md`。

2026-10-27 完成求职作品集与面试攻防实战体系：更新 `capstone/docs/portfolio/resume_evidence.md` 与 `capstone/docs/portfolio/project_pitch.md`。通过 strict-evidence 与 34 项离线测试。

2026-10-28 完成 v3 课程改造基础设施批次（V3-0）：解决 `pydantic-ai-slim[openai]==2.31.1` 依赖解析冲突；将默认模型调整为官方推荐型号 `gpt-6-luna`；更正 DeepSeek 英文官方定价文档引用；抽取客户端公共函数消除重复并改为延迟导入；规范 `apply_v3_map.py` 标签写入逻辑。测试 45 passed、capstone 34 passed、断链 0、ruff 0 errors。命令与结果见 `docs/gate-v3-0-validation.md`。

同日完成 v3 阶段 0 与阶段 1（V3-1 批次）落地与复核修复：5 个新建章节与 8 个原生章节重构；原生与 Pydantic AI (2.31.1) 双解双 Gate，离线评测 Harness 与工单服务落地；全量通过命令 1–10 检查。命令、结果与边界见 `docs/gate-v3-1-validation.md` 与 `docs/v3/reviews/V3-1.md`。

同日完成 v3 课程改造阶段 2（V3-2：上下文工程与检索）在 `wip-v3-2` 分支的实施与自检。新建 4 个章节（2.12 上下文工程、2.13 Skills、2.14 记忆与压缩、2.15 真实资料知识库 v1），原生重构 9 个章节（2.1、2.6、2.2、2.3、2.7、2.8、2.11、2.9、2.10），在 2.3 和 2.8 保留 LangChain 框架对照实现，在 2.4 关联 L1.10 harness 概念并引用 Anthropic 评测哲学，并在 2.15 完成真实资料知识库 v1 阶段出口（含 32 题 Golden Set、公开语料清单与多策略消融对比流水线）。质量命令 1–10 逐项通过：13 个 Gate 骨架 0 通过、临时解 100% 通过；pytest 63 passed（测试 0 失败）；断链 0；ruff 0 errors；原生文件零 LangChain 泄漏；v2 标签 111 unchanged；v3 标签新建 4 章全为 unchanged；全部 14 个参考实现离线正常启动。未调用外部付费模型或公网语料下载。证据见 `docs/gate-v3-2-validation.md`。
