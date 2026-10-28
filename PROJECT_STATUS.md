---
project_id: langchain-learning
updated: 2026-10-28
status: active
overview: 测试工程师转 AI 应用开发的章节课程、capstone 整合项目与岗位选修专项；企业客服旗舰项目已冻结为历史快照。
progress: "V3-0、V3-1 审核已通过并合入 master。V3-2 经首轮审核退回后，已在 wip-v3-2 分支完成 3 个阻断项、9 个主要问题与 7 个次要问题的全部修复：恢复 PROJECT_STATUS.md 真实历史记录；重构 2.15 阶段出口流水线（导入前序真实组件，杜绝读取标准答案与伪造输出，消融三种真正不同的配置，workbook 改为“待填写”）；彻底重写 2.15 语料清单与抓取脚本（24 份真实开源资料覆盖 Linux 命令、SemVer、Python 教程及真实表格/扫描 PDF，许可证逐条核实，固定 commit 并强制哈希校验）；修正 2.15 评测集与指标公式（gold 指向真实页码，指标只统计应答题，延迟取假时钟）；修复 2.6 下游兼容（轻量 Document 兼容字典与属性访问，删除伪造回答兜底）；全部参考实现真实调用改由 --live 开启，缺密钥可读提示退出不伪造输出；参考实现复用前序章节；补齐 2.14 不超预算截断保证、20 轮记忆保留检查与 --live；补齐 2.13 agentskills.io 命名约束与非法用例；纠正 2.4/2.9/2.11/2.13 引用出处；完善 README 与 workbook 模板；conventions 11 节命令 1–10 逐项通过（12 个 gate 骨架 0 通过退出 1，参考解全通退出 0；测试 63+34 passed；断链 0；ruff py311 0 errors；LangChain 泄漏 0；v2 map 111 unchanged；16 个参考实现离线 exit 0）。证据见 docs/gate-v3-2-validation.md。"
next: "通知审核者复核 V3-2 修复；审核通过后合入 master，开启 V3-3（L3 评测与错误分析）。后续学习阶段按各章任务书闭卷完成 gate 与 workbook；补真实模型、数据库、Docker/GPU、远端 CI/staging 证据；核对第三方内容版权与课程时长。"
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
  - docs/v3/reviews/V3-2.md
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

同日完成课程路径 v3 提案：用英文资料调研 2026 主流 AI 应用 / Agent 技术栈（排除中文来源），逐条取舍一份外部架构观点，在 v2 骨架上提出原语先行、按嵌入式功能与专项 Agent 两种形态组织的路径；核心 SDK 选 Pydantic AI，LangGraph 只负责状态与恢复，LangChain 降为框架素养一章。只做设计，未修改章节、未运行课程测试或真实模型；flagship 去留与章节标签切换待用户决定。依据、取舍与批次见 `docs/curriculum-v3.md`。

同日并入就业视角审查：用英文资料从招聘筛选、面试形式、企业落地三方面审查 v3，结论是技术覆盖够到中级 AI 应用工程师，主要缺口在真实证据、面试形式训练与岗位定位。据此新增项目主线 P、就业轨道 J 与就业出口标准 E1–E4，课时调整为 380h / 16 周；并产出执行包 `docs/v3/`（大纲、编写规范、审核清单、11 个批次的细则），由其他 AI 按细则实施、Claude 审核。仍只是设计，未修改章节、未运行课程测试或真实模型；国内岗位只来自英文媒体报道，定稿前需对照目标 JD。

同日用户作出两项决定：flagship-project 冻结为基于 LangChain 1.x 的历史教学快照，不再更新（快照仍可还原运行，CI 保留 m1/step1 基线测试）；V3-10 打标签时保留 `v2 路径` 行、在其上方新增 `v3 路径` 行（注：v3 行位置已于同日改为“v2 行下方”，见 `docs/v3/README.md` 第 7 节）。据此修改了 `AGENTS.md` 的联动验收约定、`flagship-project/README.md` 的冻结说明、根目录 README 的课程表，以及 `docs/v3/` 与 `docs/curriculum-v3.md` 中的相关表述。只改文档，未改代码与测试。

同日完成 v3 改造基础设施批次 V3-0：`common.py` 新增原生 OpenAI 客户端与异步工厂、模型 ID 解析函数、本地嵌入与重排模型工厂；查阅 DeepSeek 官方 API 文档将主力推荐模型默认值更新为 `deepseek-flash`（旧别名 `deepseek-chat` 已下线），OpenAI 确认为 `gpt-4o-mini` 并同步 `.env.example`；在 `requirements-course.txt` 锁定 `pydantic-ai-slim[openai]==2.62.0` 与 `opentelemetry-sdk==1.44.0`；新增覆盖 119 个条目的 `docs/course-v3-map.json` 与幂等标签工具 `tools/apply_v3_map.py`（保留 v2 行，待建章节不报错）；新增 `tools/test_apply_v3_map.py` 与 `chapters/test_v3_lessons.py` 并接入 GitHub Actions CI。工具测试与纯函数测试 44 项通过、capstone 生产测试 34 项通过、Markdown 断链 0、ruff 静态检查通过、`apply_v2_map --check` 111 项无变化。未运行真实外部模型调用与物理部署；命令、结果与边界见 `docs/gate-v3-0-validation.md`。

2026-10-28 完成 V3-0 批次的审核复核修复：针对 `docs/v3/reviews/V3-0.md` 审核退回的阻断项与主要问题，将 `pydantic-ai-slim` 锁定到兼容 `openai<3` 的最新稳定版本 `2.31.1`，在干净临时虚拟环境中通过 `pip install --dry-run` 验证完整可解析，恢复本机 `.venv` 环境且 `pip check` 零冲突；依据 OpenAI 官方弃用页更正事实并将 `OPENAI_MODEL` 默认值更新为 `gpt-6-luna`；改引 DeepSeek 官方英文定价文档；`common.py` 抽出客户端配置解析 helper 消除 50 行重复并将 `import openai` 改为延迟导入；`tools/apply_v3_map.py` 的 v3 行改为插在 v2 行下方，在临时副本中连续执行两次 `--apply` 后 `apply_v2_map --check` 保持 111 unchanged。工具与章节测试 45 项通过、capstone 生产测试 34 项通过、断链 0、ruff 通过。证据见 `docs/gate-v3-0-validation.md` 与 `docs/v3/reviews/V3-0.md`。

2026-10-28 完成 v3 课程改造阶段 0 与阶段 1（V3-1 批次）落地：覆盖 L0.1–L0.5 与 L1.1–L1.10 共 15 个章节。新建 5 个章节目录（0.3 Agent 工作流与代码审查、0.4 Python 异步重试/限流/错误工程底座、0.5 岗位地图与自评差距、1.9 多 Provider 成本追踪与超时故障转移、1.10 嵌入式 LLM 功能综合）；原生重构 8 个章节（1.1 原生调用、1.2/1.7 原理 Gate、1.3 控制输出、1.4 结构化输出、1.5 上下文预算、1.6 工具调用与多轮 Loop、1.7/1.9 Provider 成本抽象、1.9/1.8 原生 CLI 智能体）；1.6 保留 `tool_calling_langchain.py` 作为对齐框架对照；1.10 实现原生与 Pydantic AI (2.31.1) 双解、双 Gate（16 项 + 6 项）、20 条 Golden Set 离线评测 Harness（模拟 LLM 100% 通过、规则兜底 75% 准确率）及 FastAPI 服务；5 个章节 starter 骨架未实现时全部退出 1，参考解全部退出 0；单元与工具测试 54 passed、capstone 生产测试 34 passed、327 个 Markdown 文件断链 0、ruff 静态检查通过、L1 改写章节无非预期 langchain 导入泄漏、apply_v2_map 111 unchanged、新建章节 v3 标签全部 unchanged。未运行真实外部模型与公网部署。证据见 `docs/gate-v3-1-validation.md`。

2026-10-28 审核者复核 V3-0 修复并审核 V3-1。

V3-0 复核为修改后通过。原必改项经独立验证：全新虚拟环境中依赖解析成功（pydantic-ai-slim 2.31.1、openai 2.54.0、langchain-openai 1.3.3）；OpenAI 默认模型、DeepSeek 引用、工厂去重与 v3 行位置均已改好。复核新发现一个主要问题：2.31.1 登记了 5 条安全公告，其中自带 OTel 埋点泄露正文与课程原则冲突，已在 conventions.md 第 9 节写入规避规则。

V3-1 审核为退回。通过的部分：gate 参考解全过、骨架全挂、结果确定；测试 54 + 34 项通过；断链 0；V3-1 范围无 LangChain 泄漏；v2/v3 标签检查符合预期。三个阻断项：
- L1.10 README 的验收命令直接拿参考实现跑 gate；
- Pydantic AI gate 骨架 1/6 通过，且依赖参考实现中的类型；
- L1.1 参考实现默认运行即崩溃。

另有 6 个主要问题：新 gate 未用 `--module`、也不写报告；README 不符合模板；2.5 引入 ruff 错误；0.5 市场数据引用失真；golden set 缺两类用例；L1.10 未写 Pydantic AI 使用限制。

记录见 `docs/v3/reviews/V3-0.md` 与 `docs/v3/reviews/V3-1.md`。

2026-10-28 针对审核记录（`docs/v3/reviews/V3-1.md`）退回的 3 个阻断项、6 个主要问题、5 个次要问题及 V3-0 复核 N1 要求，在 `wip-v3-1` 分支完成全面复核修复与验证：
- 阻断项修复：1.10 README 验收命令改为默认检查闭卷骨架，参考解移入通过后对照；`starter_pai.py` 完整定义 DTO 与字段契约，`gate_check_pai.py` 替换测试 6 为未找到订单字段清洗断言，解决命名空间隔离，闭卷骨架 0/6 退出 1、参考解 6/6 退出 0；1.1 `first_call.py` 移除 `FinalRequestOptions` 私有类，基于标准 `httpx` 与公开 SDK 异常类重构 mock 与 `classify_api_error`，增加离线单元测试覆盖；
- 主要问题规范化：统一 0.4、1.7、1.9、1.10 的 5 个 Gate 脚本统一支持 `--module` 参数、stdout 输出与写入 `gate/gate_report.json` 报告；按 `conventions.md` 模板重写 0.3、0.4、0.5、1.7、1.9、1.10 的 README.md，补齐故障注入表、闭卷规则与通过后对照；清理 2.5 `raw_sdk_rag_agent_loop.py` 的 ruff 错误与密钥硬编码，在 `common.py` 新增 `deepseek_api_key()`；纠正 0.5 招聘市场数据引用并注明一手官方链接与读取日期；1.10 `gate/cases.json` 扩充订单号格式错误与超长文本至 24 条用例，离线评测模拟 LLM 100%、规则兜底 75% 通过；1.10 README 明确写明 Pydantic AI 2.31.1 安全使用约束；
- 依赖与次要项：在 `requirements-course.txt` 完整登记 `pydantic-ai-slim==2.31.1` 的 5 条安全公告（PYSEC-2026-4284..4291）及课程防御策略，并在 TASKS 登记升级任务；统一 starter 抛出 `NotImplementedError`；补充 `FeatureDeps.clock` 默认值；整理 `.tmp/gate_solutions/v3` 参考解并重命名对齐；核对外部模型发布日期；补齐 2.5 README 配置说明；
- 全量验证：按 `conventions.md` 第 11 节命令 1–10 逐一验证，单元与章节测试 54 passed、capstone 生产测试 34 passed、329 个 Markdown 文件断链 0、ruff 0 errors、LangChain 泄漏 0、`apply_v2_map` 111 unchanged、`apply_v3_map` 6 篇新建/改写章节全部 unchanged、13 个参考实现通过 run_chapter 正常启动、capstone baseline 100% 通过。未运行真实外部模型与公网部署。命令、结果与边界见 `docs/gate-v3-1-validation.md`。

同日审核者复核 V3-1 修复（提交 af1bf7e），结论为修改后通过。
- 复跑结果：5 个 gate 统一使用 `--module` 并写出报告；骨架全部 0 通过（含 Pydantic AI 0/6），参考解全部通过，结果确定；测试 54 + 34 项、里程碑与基线检查通过；ruff 覆盖 35 个改动文件；断链 0；在隔离副本中无密钥运行 13 个参考实现，均无堆栈。
- 三个阻断项与 M1–M3、M5、M6 均已解决，V3-0 的 N1 关闭，V3-0 至此通过。
- 剩余 M4-r：0.5 README 中“4.5%–12%”仍标注为 Rockstar 的数据（原文只有引自 Indeed 的 4.5%），另有一处措辞与两处缺失的链接。修完由审核者复核这一项，然后合入 master。

记录见 `docs/v3/reviews/V3-1.md`。

同日审核者复核 M4-r（提交 0a444fe），结论为通过。
- 修正内容：4.5% 标为 Indeed（经 Rockstar 汇总），12% 标为 Axial；“硬性要求”改为“提到”；5 年 / 2 年补上 Axial 职业指南页链接，已核对原文；无出处的 FDE 比例已删去。
- 复跑：断链 0、v2 标签无变化、状态文件自检通过。本次只改了文档，gate 与测试沿用上一轮复核的结果。
- V3-1 全部问题关闭，可以快进合入 master。

2026-10-28 审核者审核 V3-2（提交 4288317），结论为退回。
- 通过部分：13 个 gate 骨架全部 0 通过、参考解全过且结果确定；测试 63 + 34 项通过；断链 0；ruff 通过；part2 无 LangChain 泄漏；v2 标签 111 个未变。
- 3 个阻断项：① PROJECT_STATUS.md 正文历史记录被改写，多处与验证文档矛盾，冻结快照决定与 V3-0/V3-1 记录被删；② 2.15 阶段出口流水线直接读取用例标准答案，消融配置虚假且伪造“门禁通过”，workbook 预填 100%；③ 2.15 语料许可证多处标错或虚构。
- 9 个主要问题：语料清单与下载脚本不达标、缺哈希校验与表格/扫描 PDF；2.6 下游测试不兼容且伪造兜底回答；参考实现缺密钥时伪造输出或默认产生真实扣费调用；未复用前序章节；2.14 缺不超预算保证、20 轮记忆保留检查与 --live；2.13 Skill 命名规则与 agentskills.io 不一致；多章引用出处缺失或失真；验证记录与模板缺项。
- 7 个次要问题：gate 断言收紧（2.12/2.13/2.15）；新章节删除 CHECKLIST.md；2.6/2.10/2.3 README 与文风修正；2.15 导航链接与新章节标题格式统一。

记录见 `docs/v3/reviews/V3-2.md`。

2026-10-28 针对审核记录（`docs/v3/reviews/V3-2.md`）退回的 3 个阻断项、9 个主要问题与 7 个次要问题，在 `wip-v3-2` 分支完成全面复核修复与验证：
- 阻断项修复：① 以 `355ea98` 为准完整恢复 PROJECT_STATUS.md 历史条目，仅在末尾追加 V3-2 记录，用户决定段落补充 v3 标签插入位置修正说明，自检契约字段；② 重写 2.15 kb_pipeline.py，导入前序真实组件（2.7 切分、2.8 RRF 融合），彻底杜绝读取 gold 标准答案与伪造输出，消融对比三种真实不同配置（Dense Only、BM25 Only、Hybrid RRF），workbook 恢复“待填写”；③ 彻底重写 2.15 corpus/SOURCES.md，收录 24 份真实公有/宽松开源资料（Linux 命令、SemVer、Python 官方教程及真实表格/扫描 PDF），逐条核对官方许可证与依据，删除无真实来源条目。
- 主要问题修复：重构 fetch_corpus.py，支持固定 commit/tag 并强制哈希校验，不符时非 0 退出；cases.json 扩充至 32 题真实语料用例，gold 页码对齐，指标计算仅在应答题上统计，时延改取用例假时钟；2.6 pdf_sources.py 检索结果改为轻量 Document(page_content, metadata) 对象，下游测试完全兼容，删除伪造回答兜底；所有参考实现真实模型调用改由 --live 显式开启，缺密钥时给出可读提示并安全退出，不伪造生成结果，Cross-Encoder 降级打印警告，ask_image 隔离环境变量；参考实现严格复用前序章节函数；2.14 memory_compaction.py 补充压缩后不超预算截断保证、20 轮长对话关键事实保留评测与 --live；2.13 skills_loader.py 补充 agentskills.io 命名约束与非法测试用例；纠正 2.4/2.9/2.11/2.13 引用出处；完善 README 模板、概念地图与边界说明。
- 次要问题修复：收紧 2.12（双段重复断言）、2.13（多合法 fixture）、2.15（拒答不调用模型）gate 断言；删除 4 个新章节的 gate/CHECKLIST.md；修正 2.6/2.10/2.3 README 与文风；统一 2.15 导航与 4 个新章节标题。
- 全量验证：按 conventions.md 第 11 节命令 1–10 逐项验证：12 个 gate 骨架全部 0 通过（退出码 1）、临时参考解全部通过（退出码 0）且连跑结果一致（2.9 为原 9 项 + 新增 7 项）；单元与章节测试 63 passed、capstone 生产测试 34 passed；349 份 Markdown 文件断链 0；ruff py311 静态检查通过；part2 无 LangChain 导入泄漏；apply_v2_map 111 unchanged、apply_v3_map 新建章节全部 unchanged；16 个参考实现通过 run_chapter 离线正常启动退出。命令、结果与细则偏离见 `docs/gate-v3-2-validation.md`。
