# Tasks

状态核对：2026-10-18。课件全量结构完成：82 章 + 29 步均有 v2 标签与验收方式（75 章 gate + 7 章清单 + 29 步总清单）。统一入口见 `chapters/README.md`；目录与文件存在不代表本人已学完或真实环境验收通过。最新收口验证见 `docs/gate-b6i-validation.md`；岗位对标与路径提案见 `docs/curriculum-v2.md`。

## Active

- [ ] **课件维护** - 新增/修改章节时同步更新 `course-v2-map.json`、章节索引、README 任务书与验收记录；改 gate 后跑参考解、骨架、pytest、断链、ruff。
- [ ] **真实学习/试教** - 按各章任务书实际完成 gate 或清单并记录失败；这不是课件结构完成的前置。
- [ ] **核对旗舰项目与选修阶段验收** - 按当前章节或里程碑读取代码与测试，补运行证据；`python -m capstone.milestones --strict-evidence` 只确认所列文件存在，不等于运行验收
- [ ] **完成真实环境证据** - 依次补齐真实模型评测（含第 1–6 篇需要模型的章节，本轮审查只做了离线运行）、远端 CI、staging、容量、恢复和事故演练
- [ ] **核对第三方内容与保留的证据文件** - `面试题/` 含第三方整理内容，公开前先核对版权；`reports/` 保留了 3 个被引用的文件（见 `reports/README.md`），删除它们会让 `python -m capstone.interview_evidence --strict-evidence` 失败，并使 `capstone/docs/portfolio/` 引用的压测数字失去来源

## Waiting On

## Someday

- [ ] **求职准备** - 只从 `capstone/docs/portfolio/` 和真实报告提取可证明结论

## Done

- [x] **求职作品集与面试攻防实战体系（2026-10-27）** - 完成测试转复合型 AI 应用开发工程师作品集打磨与面试攻防梳理：提炼 STAR 简历经历、5 分钟 Pitch 讲稿与四层硬核攻防卡（Pre-filtering ACL、分层 CI 质量门禁、七阶段失败归因、分租户条带锁并发优化、HITL 一次性持久化审批）；更新 `capstone/docs/portfolio/resume_evidence.md`、`capstone/docs/portfolio/project_pitch.md`。相关证据通过 strict-evidence 与 34 项离线生产测试。

- [x] **Capstone 核心稳定性与并发优化（2026-10-26）** - 修复 BM25 缓存无界与增量版本失效风险；消除 SQLite 监控指标每次插入重复 DDL/WAL 开销；多租户 Registry 粗粒度全局锁升级为分租户细粒度锁与双重检查；复用可靠 LLM 链实例。34 项离线测试全部通过（耗时由 10.14s 降至 6.62s）、28 项工具链测试通过、ruff 通过、milestones 与 baseline 全部通过。未运行真实模型与远端服务。证据见 docs/capstone-optimization-validation.md

- [x] **B6i 全量收口（2026-10-18）** - 补 3.8、4.13、8.1、8.2、8.3、8.7、8.8 七个 gate；为 0.1、0.2、1.6、1.7、4.15、5.6 增加清单；82 章 75 gate + 7 checklist，29 步总清单落地。参考解全部通过、骨架 0 通过；测试 28 passed、断链 0、v2 标签 111 unchanged、ruff 通过。证据见 `docs/gate-b6i-validation.md`

- [x] **B5b 部分（2026-10-18）** - 5.4 SQLite、5.7 安全护栏改为 gate；参考解 4/4、7/7；默认骨架 0 通过。5.3/5.5/5.8 未做。证据见 `docs/gate-b5b-validation.md`

- [x] **B5a Gate 化（2026-10-18）** - 5.2 可靠性改为 gate：指数退避/上限、可重试判断、成本估算；临时参考解 5/5，默认骨架 0 通过；测试 28 passed、断链 0、ruff 通过。证据见 `docs/gate-b5a-validation.md`

- [x] **B4d 完成（2026-10-18）** - 补 4.14 Supervisor/Fan-out gate（5/5）；B4d 四项 7/7、4/4、5/5、5/5，B4 收口。

- [x] **B4d 部分（2026-10-18）** - 3.9 Agent 轨迹评测、4.11 流式/HITL、4.12 搜索信任边界改为 gate；4.14 多 Agent 未做。临时参考解 7/7、4/4、5/5；默认骨架 0 通过；测试 28 passed、断链 0、ruff 通过。证据见 `docs/gate-b4d-validation.md`

- [x] **B4c Gate 化（2026-10-18）** - 4.8 规划与执行、4.9 可观测性、4.10 检查点与上下文改为 gate：计划解析/执行异常/超长截断、轨迹记录/汇总、会话隔离/副本/上下文裁剪；新增 `gate/starter.py`、`gate/gate_check.py`，重写 README/workbook。临时参考解跑通 6/6、4/4、6/6；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实模型/checkpointer；证据见 `docs/gate-b4c-validation.md`

- [x] **B4b Gate 化（2026-10-18）** - 4.6 节点可靠性、4.7 结构化路由改为 gate：降级/可重试/真实超时、枚举路由解析/意图分类；新增 `gate/starter.py`、`gate/gate_check.py`，重写 README/workbook。临时参考解跑通 7/7、4/4；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实模型；证据见 `docs/gate-b4b-validation.md`

- [x] **B4a Gate 化（2026-10-18）** - 4.1–4.4 改为 gate：Agent 有界循环、LangGraph 线性/分支、循环与 recursion_limit、状态 reducer/fan-out；新增 `gate/starter.py`、`gate/gate_check.py`，重写 README/workbook。临时参考解跑通 8/8、4/4、4/4、5/5；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未调用真实模型/检查点；证据见 `docs/gate-b4a-validation.md`

- [x] **B3b Gate 化（2026-10-18）** - 3.7 回归对比、3.10 失败诊断改为 gate；3.6 LangSmith 因依赖外部服务改为清单验收（`gate/CHECKLIST.md`）。临时参考解跑通 8/8、5/5；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未运行真实模型/LangSmith/DeepEval；证据见 `docs/gate-b3b-validation.md`

- [x] **B3a Gate 化（2026-10-18）** - 把 3.1、3.2、3.4、3.5 改成 gate：失败定位顺序、拒答/关键词指标、评测集 schema/覆盖、评测集合并与 RAGAS 行；新增 `gate/starter.py`、`gate/gate_check.py`，重写 README/workbook。临时参考解跑通 8/8、6/6、7/7、8/8；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未运行真实模型/RAGAS；证据见 `docs/gate-b3a-validation.md`

- [x] **B2b Gate 化（2026-10-18）** - 把 2.6–2.11 改成 gate：PDF 溯源、切分策略、混合检索 RRF、查询改写、JSON 持久化、重排/recall@k；新增 `gate/starter.py`、`gate/gate_check.py`，重写 README/workbook。临时参考解跑通 9/9、7/7、7/7、9/9、9/9、8/8；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未运行真实 embedding/reranker/PDF；证据见 `docs/gate-b2b-validation.md`

- [x] **B2a Gate 化（2026-10-18）** - 把 2.1、2.2、2.3 改成 gate：加载/切分、向量化/索引、最小 RAG；新增 `gate/starter.py`、`gate/gate_check.py`，重写 README/workbook。临时参考解跑通 6/6、9/9、10/10；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未运行真实 embedding/模型；证据见 `docs/gate-b2a-validation.md`

- [x] **B1 Gate 化（2026-10-18）** - 把 1.1–1.5、1.8 改成 gate：新增 `gate/starter.py`、`gate/gate_check.py`，重写 README/workbook，覆盖请求/响应契约、流式、结构化解析、会话预算、工具回灌、CLI 控制流。临时参考解跑通 11/11、10/10、10/10、12/12、11/11、11/11；默认骨架 0 通过；现有测试 28 passed、断链 0、ruff 通过。未运行真实模型、未验证真实学习者；证据见 `docs/gate-b1-validation.md`

- [x] **课程全量结构修复（2026-10-18）** - 给 82 章 + 29 个旗舰步骤共 111 个 README 写入 `v2 路径`（阶段/核心/选做/核心阅读/跨篇顺序）；修 3.9 后移说明、5.2 在 5.1 之后、9.1/10.1 的代码血缘前置；新增 `docs/course-v2-map.json`、幂等工具 `tools/apply_v2_map.py` 与全量链接检查 `tools/check_course_links.py`。`apply_v2_map --check` 111 unchanged；258 个 Markdown 断链 0；离线测试 28 passed；ruff 通过。未物理移动 3.9、未重排目录、其余 77 章未 gate 化；证据见 `docs/course-v2-structure-validation.md`

- [x] **5 个样板章改为 Gate（2026-10-18）** - 把 L1.6 / L2.9 / L3.4 / L4.4 / L5.1 对应到 2.5 / 2.4 / 3.3 / 4.5 / 5.1：新增 `gate/starter.py`、`gate/gate_check.py`（2.9 另有 `gate/cases.json`），重写 README 与 workbook，加入闭卷规则、故障注入和可执行验收。临时参考解离线跑通 16/16、14/14、14/14、14/14、17/17；默认骨架 0 通过（预期）；现有离线测试 28 passed；ruff 通过。未运行真实模型、未部署、未验证真实学习者从零实现；证据与边界见 `docs/gate-samples-validation.md`

- [x] **课程路径 v2 提案（2026-10-18）** - 对照 5 份岗位样本与 1 份行业能力地图，审查 82 章 + 29 步的结构：给出核心 58 章 / 约 321 小时的 12 周路径、七道阶段出口门、现有章节处置与新增章节清单。只做路径设计与岗位对照，未修改章节目录、未运行课程测试；提案见 `docs/curriculum-v2.md`，不表示本人已学完或真实环境验收通过

- [x] **PDF 书稿重建并定版 v1.0（2026-09-30）** - 把当日课程审查的修订同步进书稿：封面补版本号并改正配套代码说明；环境准备改为 `requirements-course.txt` + `python tools/run_chapter.py 0.1` 自检；代码地图去掉 `dayNN` 与已删除的 `customer_support/`；6 章改为 `flagship-project/` + `capstone/` 分别验收；7.7 端到端按 8.7 实际行为改写（当前不用流式、解析器不查结尾）；8 章还原脚本改为 `tools/materialize.py`。重建后 100 页、120 张图，机械与几何自检通过，书签 97 条。只做了构建与文本层核对，未做逐页目视检查；命令与边界见 `docs/course-book-v1-validation.md`

- [x] **清理与两项遗留修复（2026-09-30）** - 删除两个旧虚拟环境（约 1.2 GB）、`debug_weather.py`、根目录三个示例文件、`artifacts/`、整个 `archive/` 和 `reports/` 的历史输出（备份在 `.tmp/deleted-backup-20260930/`），`_capstone_driver.py` 移入 `capstone/driver.py`；修复真实模型拒答仍附引用（`capstone/knowledge_base.py` 的 `is_refusal`：真实回答是“文档中没有提到。”，旧判断只认无标点的原句），真实模型回归 6 passed；旗舰 m1/step4 关键词一路加证据门槛，m1/step1、m2/step2、m5/step1 拒答时不附来源。离线测试 201 项通过，另有一次 capstone 真实模型回归 6 项通过；未运行远端服务和浏览器。证据：`docs/course-review-validation.md`

- [x] **课程全面审查与订正（2026-09-30）** - 按精简、层次、衔接、初学者视角、订正、注释、文字七项要求审查：修复共用资料与评测集断链，补依赖清单和环境自检；82 个章节与 29 个项目步骤 README 去除重复模板并改写与代码不符的说明；订正 8.7–8.10、9.1–9.7、10.2–10.4、7.7 / step2 中的实际缺陷；补充语义型注释。3.7、3.10 的示例资产已随此项补齐（3.7 读共用评测集，3.10 自带合成样本）。证据：`docs/course-review-validation.md`

- [x] **清理旧日编号内容与产物命名** - 逐项清理旧专题、课程草稿、报告/模型输出命名和失效生成脚本；PDF 书稿已更新路径并重建，99 页目录页码收敛、机械检查通过且完成页面缩略图目视检查。源码与文档扫描无旧日编号命名匹配；`.build/` 下仍有 42 个被忽略的历史生成目录，旧 pytest 缓存也残留历史测试名；当前环境拦截了清理操作，详见 `docs/project-cleanup-validation.md`。

- [x] **课程用途命名与书稿正文** - 62 个文件改为用途名称并修复导入、命令和运行标识；82 个章节及 29 个项目步骤补写问题、概念、过程、导读、练习和边界说明，目录全部先进入文字教程。174 项离线测试通过；不代表个人学完或真实模型问题已修复。证据：`docs/course-book-validation.md`

- [x] **课程章节重构与新增入门内容** - 保留物理迁移，完成统一还原工具、CI 路径、章节总地图、历史资料归档与客服阅读入口整合，补齐七个新增 / 重写位置；离线 173 项通过，真实模型回归未通过。证据：`docs/course-restructure-validation.md`。此项表示结构与内容调整，不表示个人已学完
- [x] **里程碑 7.1–7.8 内容收敛** - 旧 Demo 已删除；阶段性业务实现统一进入 `capstone/`。这一项只表示内容整理完成，不代表真实环境验收完成

## 2026-10-06 提交与发布跟进

本次提交与推送已完成，验收结果和仍待验证事项见 docs/course-book-v1-validation.md；早期未提交记录是历史快照。
