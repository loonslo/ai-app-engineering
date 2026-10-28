# Tasks

状态核对：2026-10-28。课件全量结构完成：82 章 + 29 步均有 v2 标签与验收方式（75 章 gate + 7 章清单 + 29 步总清单）。v3 课程改造完成 V3-0 基础设施与 V3-1 批次（L0 + L1 共 15 章全量内容，5 个新建章 + 8 个原生重构章 + 1.10 原生/PAI 双解双 Gate 与离线评测 Harness）。统一入口见 `chapters/README.md`；目录与文件存在不代表本人已学完或真实环境验收通过。最新收口验证见 `docs/gate-v3-1-validation.md`；岗位对标与路径提案见 `docs/curriculum-v3.md`。

## Active

- [ ] **课件维护** - 新增/修改章节时同步更新 `course-v2-map.json`（V3-0 后另有 `course-v3-map.json`）、章节索引、README 任务书与验收记录；改 gate 后跑参考解、骨架、pytest、断链、ruff。
- [ ] **v3 改造（其他 AI 实施，Claude 审核）** - 按 `docs/v3/README.md` 的 V3-0 至 V3-10 推进：V3-0 已通过（N1 已关闭）。V3-1 已通过（M4-r 已于 2026-10-28 复核关闭），`wip-v3-1` 可以快进合入 master。合入后开始 V3-2（L2）。审核记录见 `docs/v3/reviews/`。
- [ ] **真实学习/试教** - 按各章任务书实际完成 gate 或清单并记录失败；这不是课件结构完成的前置。
- [ ] **核对 capstone 与选修阶段验收** - 按当前章节读取代码与测试，补运行证据（flagship-project 已冻结，不再补证据）；`python -m capstone.milestones --strict-evidence` 只确认所列文件存在，不等于运行验收
- [ ] **完成真实环境证据** - 依次补齐真实模型评测（含第 1–6 篇需要模型的章节，本轮审查只做了离线运行）、远端 CI、staging、容量、恢复和事故演练
- [ ] **核对第三方内容与保留的证据文件** - `面试题/` 含第三方整理内容，公开前先核对版权；`reports/` 保留了 3 个被引用的文件（见 `reports/README.md`），删除它们会让 `python -m capstone.interview_evidence --strict-evidence` 失败，并使 `capstone/docs/portfolio/` 引用的压测数字失去来源

## Waiting On

## Someday

- [ ] **求职准备** - 只从 `capstone/docs/portfolio/` 和真实报告提取可证明结论
- [ ] **Pydantic AI 升级（待 LangChain 解除 openai 3 限制后）** - 当 LangChain 依赖集允许 openai>=3 时，将 `pydantic-ai-slim` 升级至 >=2.53.0，并消除 2.31.1 的 5 条安全公告限制（PYSEC-2026-4284..4291），复核 OTel 追踪与工具支持。

## Done

- [x] **V3-1 复核 M4-r，批次通过（2026-10-28）** - 复核提交 0a444fe：0.5 README 中 4.5%（Indeed，经 Rockstar 汇总）与 12%（Axial）出处分开标注，“硬性要求”改为“提到”，5 年 / 2 年补上 Axial 职业指南页链接（已核对原文），无出处的 FDE 比例已删去。断链 0、v2 标签无变化、状态文件自检通过。V3-1 全部问题关闭，结论为通过，记录见 `docs/v3/reviews/V3-1.md`
- [x] **V3-1 复核（2026-10-28）** - 复跑提交 af1bf7e，结论为修改后通过。
  - 复跑结果：5 个 gate 统一用 `--module` 并写出报告，骨架全部 0 通过（含 Pydantic AI 0/6），参考解全过；测试 54 + 34 项通过；ruff 覆盖 35 个改动文件；断链 0；隔离运行 13 个参考实现均无堆栈。
  - B1–B3、M1–M3、M5、M6、N1 已解决；剩 M4-r：0.5 中“4.5%–12%”仍标为 Rockstar 的数据（原文只有 Indeed 的 4.5%），另有措辞与两处缺失的链接。
  - 记录见 `docs/v3/reviews/V3-1.md`
- [x] **V3-1 复核修复与全量验证（2026-10-28）** - 针对审核记录（`docs/v3/reviews/V3-1.md`）退回的 3 个阻断项（B1–B3）、6 个主要问题（M1–M6）、5 个次要问题（m1–m5）以及 V3-0 复核的 N1 规范要求，在 `wip-v3-1` 分支完成系统性修复：
  1. 阻断项清零：B1（1.10 README 验收命令改为默认检查闭卷骨架，参考解移入通过后对照）、B2（`starter_pai.py` 补齐字段契约与 DTO 说明，`gate_check_pai.py` 替换测试 6 并解决命名空间隔离，骨架 0/6 退出 1、参考解 6/6 退出 0）、B3（1.1 移除 `FinalRequestOptions` 私有类，基于标准 `httpx` 与公开异常实现 mock 与分类器，新增离线单元测试覆盖）；
  2. 主要问题到位：M1（统一 0.4/1.7/1.9/1.10 的 5 个 gate 支持 `--module`、stdout 输出与 `gate/gate_report.json` 写入）、M2（按 conventions 4.1/4.2 补齐 6 篇 README 的故障注入/闭卷规则/通过后对照等小节）、M3（2.5 清理 ruff 错误与密钥硬编码，`common.py` 新增 `deepseek_api_key()`）、M4（0.5 纠正招聘数据引用并补充官方链接与读取日期）、M5（1.10 `cases.json` 扩充订单号格式错误与超长文本至 24 条，离线评测模拟 LLM 100%、规则兜底 75%）、M6（1.10 明确写明 Pydantic AI 2.31.1 安全使用限制）；
  3. 次要与新增项：N1（`requirements-course.txt` 完整登记 2.31.1 的 5 条安全公告及课程缓解策略）、m1（starter 统一抛出 `NotImplementedError`）、m2（`FeatureDeps` 增加 `clock` 默认值）、m3（`.tmp/gate_solutions/v3` 清理与命名对齐）、m4（外部模型名称更新）、m5（2.5 README 配置说明补齐）；
  4. 全量验证通过：conventions 11 节命令 1–10 逐一验证（gate 骨架 0 通过/参考解全通、pytest 54+34 passed、断链 0、ruff 0 errors、LangChain 泄漏 0、`apply_v2_map` 111 unchanged、`apply_v3_map` 6 篇新建/改写章节全部 unchanged、13 个参考实现通过 run_chapter 正常启动、capstone baseline 100% 通过）。未运行真实外部模型与公网部署。证据见 `docs/gate-v3-1-validation.md`。
- [x] **V3-0 复核与 V3-1 审核（2026-10-28）**
  - V3-0 复核为修改后通过：全新虚拟环境中依赖解析成功（pydantic-ai-slim 2.31.1、openai 2.54.0、langchain-openai 1.3.3），其余必改项逐条确认；新发现 N1（2.31.1 的 5 条安全公告），已在 conventions.md 第 9 节写入规避规则。
  - V3-1 审核为退回。通过的部分：gate 参考解全过、骨架全挂；测试 54 + 34 项通过；断链 0；无 LangChain 泄漏。阻断项：L1.10 验收命令直接跑参考实现；Pydantic AI gate 骨架 1/6 通过且依赖参考实现的类型；L1.1 参考实现默认运行崩溃。另有 6 个主要问题。
  - 记录见 `docs/v3/reviews/V3-0.md`、`docs/v3/reviews/V3-1.md`
- [x] **v3 阶段 0 与阶段 1 V3-1 批次落地（2026-10-28；审核结论：退回，见 `docs/v3/reviews/V3-1.md`）** - 依据 `docs/v3/specs/L0.md` 与 `docs/v3/specs/L1.md` 完成 L0.1–L0.5 与 L1.1–L1.10 全量内容改造：
  1. 5 个新建章节落地：L0.3（编码 Agent 工作流与审查，包含 practice_repo 真实演练与 check_task.py 退出码验证）、L0.4（Python 工程底座，12 项工程 Gate）、L0.5（岗位地图与差距诊断，包含 3 份求职对标模板与清单）、L1.7/1.9（Provider 抽象与成本 Gate，13 项断言，多 Provider 成本追踪与超时故障转移）、L1.10（嵌入式 LLM 功能综合，原生与 Pydantic AI 双解双 Gate，20 条工单评测集与 FastAPI 工单服务）；
  2. 8 个原生章节重构：L1.1（原生 OpenAI SDK 替换 LangChain）、L1.2/1.7（改写为原理 Gate，13 项纯数学离线断言）、L1.3（原生控制输出）、L1.4（原生结构化输出与 Pydantic）、L1.5（原生消息记忆与 Token 预算）、L1.6（原生工具调用与单轮/多轮 Tool Loop，原文件保留为 `tool_calling_langchain.py` 作为框架对照）、L1.8（增补配置与测试引用）、L1.9/1.8（原生 CLI 交互智能体）；
  3. Gate 与评测验证：5 个章节的 starter 骨架在未实现状态下全部退出 1，参考解全部通过（0.3 通过、0.4 12/12、1.7 13/13、1.9 13/13、1.10 原生 16/16、1.10 PAI 6/6，退出码均为 0）；1.10 的 Golden Set 评测模拟 LLM 准确率 100%、规则兜底 75%；
  4. 质量门禁：工具与章节测试 54 passed、capstone 回归 34 passed、327 个 Markdown 文件断链 0、ruff py311 检查通过、L1 改写章节无非预期 langchain 导入泄漏（0 leaks）、`apply_v2_map --check` 保持 111 unchanged、`apply_v3_map --check` 5 个新建章节全部 unchanged。未运行真实外部模型与公网部署。证据见 `docs/gate-v3-1-validation.md`。

- [x] **v3 基础设施 V3-0 批次落地与复核修复（2026-10-28）** - 针对审核记录（`docs/v3/reviews/V3-0.md`）完成复核修复：
  1. 依赖解析与环境恢复（B1）：选方案 A 锁定 `pydantic-ai-slim[openai]==2.31.1`，在干净临时环境中验证 `pip install --dry-run` 顺利解析，本机 `.venv` 同步恢复且 `pip check` 零冲突；核对 2.31.1 `DeepSeekProvider` 尚未识别 `deepseek-flash`，后续 L1.10/L4.5 按细则显式关闭思考；
  2. OpenAI 默认模型与事实修正（B2）：核对官方弃用页，`gpt-4o-mini-2024-07-18` 已于 2026-10-14 宣布弃用、2027-01-14 停用，`common.py` 与 `.env.example` 默认模型更新为官方推荐替代型号 `gpt-6-luna`；
  3. DeepSeek 依据修正（M1）：改引官方英文文档 `https://api-docs.deepseek.com/quick_start/pricing`（读取于 2026-10-27），明确“文档已不再列出 deepseek-chat”及 `deepseek-v4-flash` 路由说明；
  4. 客户端工厂去重（M2）与延迟导入（m2）：`common.py` 抽出 `_resolve_openai_client_kwargs`，消除 50 行重复；顶层移除 `import openai` 改为延迟导入；
  5. S1 跟进与死代码清理（m1）：`tools/apply_v3_map.py` 的 v3 行改为插在 v2 行下方，多目录匹配记入 `problems`，测试同步更新（6 passed）；在副本中验证两次 `--apply` 后 `apply_v2_map --check` 保持 111 unchanged。
  工具与章节测试 45 passed、capstone 生产测试 34 passed、断链 0、ruff 通过。证据见 `docs/gate-v3-0-validation.md` 与 `docs/v3/reviews/V3-0.md`。

- [x] **v3 两项决定落地（2026-10-27）** - 用户决定：flagship-project 冻结为基于 LangChain 1.x 的历史教学快照；V3-10 保留 `v2 路径` 行、在其上方新增 `v3 路径` 行。已同步：`flagship-project/README.md` 顶部加冻结说明；`AGENTS.md` 删除 flagship 与 capstone 联动验收的约定，改为以 capstone 为准；根目录 README 课程表标注冻结；`docs/v3/` 的默认决策、V3-0 与 V3-10 细则、大纲与 `docs/curriculum-v3.md` 第 7.3 节改为已决定。CI 中 m1/step1 的基线测试保留。只改文档，未改代码
- [x] **就业视角审查并入与 v3 执行包（2026-10-27）** - 用英文资料（排除中文来源）从招聘筛选、面试形式、企业落地三方面审查 v3，结论并入 `docs/curriculum-v3.md` 第 8 节：技术覆盖够到中级 AI 应用工程师，主要缺口是真实证据、面试形式训练与岗位定位。据此新增项目主线 P（篇 11）、就业轨道 J（篇 12）与就业出口标准 E1–E4，课时由 334h 调整为 380h / 16 周。产出执行包 `docs/v3/`：大纲、编写规范、审核清单与 11 个批次的细则，供其他 AI 实施、Claude 审核。只做设计，未修改章节、未运行课程测试或真实模型；章节以 `docs/v3/outline.md` 为准
- [x] **课程路径 v3 提案（2026-10-27）** - 用英文资料调研 2026 主流 AI 应用 / Agent 技术栈（排除中文来源），并逐条取舍一份外部架构观点（嵌入式集成 vs 专项 Agent），在 v2 骨架上提出 v3：默认实现改为原生 SDK + Pydantic，核心 SDK 选 Pydantic AI，LangGraph 只负责状态与恢复，LangChain 降为框架素养一章；按两种交付形态组织 334 小时路径，新增上下文工程、执行面、沙箱、持久执行、OTel 等章节；核对仓库 LangChain 依赖分布并给出改造批次。只做设计，未修改章节、未运行课程测试或真实模型；提案见 `docs/curriculum-v3.md`
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
