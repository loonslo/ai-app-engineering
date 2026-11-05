# Tasks

状态核对：2026-11-04。V3-0–V3-10 的实施批次均有对应验证记录；V3-4 与 V3-5 审核结论均为通过，V3-4 复核见 `docs/v3/reviews/V3-4.md`。capstone 依赖、默认语料边界、评测拒答口径与 CI 检查的本轮修复/复测见 `docs/capstone-repair-validation.md`。2026-11-04 完成旧版书籍排版工具链（pdf-course/）与临时缓存/配置清理（释放 70MB+）。尚未关闭：L2.12 拒答率未达 90% 门槛、真实学习与试教、外部生产验收、第三方内容版权确认。统一入口见 `chapters/README.md`；课件实现与 gate 通过不代表本人已学完。

## Active

- [ ] **课件维护** - 新增/修改章节时同步更新 `course-v2-map.json`（V3-0 后另有 `course-v3-map.json`）、章节索引、README 任务书与验收记录；改 gate 后跑参考解、骨架、pytest、断链、ruff。
- [ ] **V3-3 外部环境遗留** - 3.3/3.7/3.8 的 DeepSeek 单次 live 记录保留于 `docs/gate-v3-3-validation.md` 第 8 节；远端 OTLP、DeepEval 仍未验证。V3-3 已合入；用户决定不再恢复丢失的原 LangSmith 报告。
- [ ] **真实学习/试教** - 按各章任务书实际完成 gate 或清单并记录失败；这不是课件结构完成的前置。
- [ ] **核对 capstone 与选修阶段验收** - 按当前章节读取代码与测试，补运行证据（flagship-project 已冻结，不再补证据）；`python -m capstone.milestones --strict-evidence` 只确认所列文件存在，不等于运行验收
- [ ] **完成真实环境证据** - 依次补齐真实模型评测（含第 1–6 篇需要模型的章节，本轮审查只做了离线运行）、远端 CI、staging、容量、恢复和事故演练
- [ ] **L2.12 拒答质量未达门槛** - 当前历史实测 Hybrid 拒答准确率 71.88%，低于 90% 要求；不得通过降低门槛、改评测集阈值或改指标定义伪造通过。需要有代表性的离线评估和真实 reranker/model 验证后再调整。证据：`docs/gate-v3-2-validation.md`。

- [ ] **第三方内容与证据文件** - `面试题/` 含 98 道题目及答案/解析的复制内容；按用户决定暂时保留，但授权未确认前不得公开分发。公开前需核对许可证或移除复制材料。`reports/` 中的两个压测文件仍作为 portfolio 数字来源，未经迁移证据不得删除。
## Waiting On

## Someday

- [ ] **求职准备** - 只从 `capstone/docs/portfolio/` 和真实报告提取可证明结论

## Done

- [x] **v7 1.1 节文章初稿与写作规范落地（2026-11-05）** - 确立技术随笔写作（tech-article-writing）与去 AI 味（de-ai-slop-review）标准并写入 AGENTS.md；完成第 1 章 1.1 节《一个需求里，哪些步骤适合交给模型》图文样稿及 Task Spec 契约（`docs/articles/1.1-task-decomposition.md`），绘制纯矢量白底架构图 `shots/feedback-pipeline-division.svg`；全面排查清除“不是……而是……”等套路对仗句式。代码包含行内中文注释与下游使用、故障排查说明，未调用线上付费 API。

- [x] **v7 AI 应用开发主线重排（2026-11-05）** - 根据联网对照重新编排为 8 章 51 篇主线与 12 篇选修，共 63 篇。将模型行为、提示词、评估、RAG、上下文、工具与 Agent、安全、交付作为主线；通用数据库、身份、同步、迁移、容量、备份、MCP、多 Agent 与微调实作转为独立选修。每篇均写明内容、独立入口、实验边界和依据，附录映射 v6.1 旧篇目并区分资料支持范围与课程自身决定。结构、来源编号、文风与格式检查通过，见 `docs/course-outline-v7-validation.md`。仅为写作提案，未修改现行 v3 课件、代码或外部环境，未制作 starter 包或进行试读与真实运行。

- [x] **v6.1 企业应用实践补充设计（2026-11-05）** - 新增 `docs/course-outline-v6.1.md` 完整版，保留 v6 的 55 个编号/标题，新增需求、模型选择、外部接口/同步、数据/状态兼容、提示词对照、部署/回退、容量与恢复 11 篇，合计 66 篇。附录设计 P0—P5 连续项目及 W 可选写操作，明确职责、历史数据、失败路径与证据。结构、引用和新增范围检查通过，见 `docs/course-outline-v6.1-validation.md`。仅设计完成，阶段均待实施，未修改现行课件或运行代码、外部服务与部署。

- [x] **v6 独立文章大纲（2026-11-05）** - 根据用户提供的 v5 整理为 11 章、55 篇独立文章，每篇明确问题、前置与起始材料、结果与范围；降低说教语气，将综合练习与作者备忘移入附录。新增 `docs/course-outline-v6.md`，编号、标题唯一性和逐篇字段检查通过，记录见 `docs/course-outline-v6-validation.md`。仅完成写作提案，不替换现行 v3 目录；文章正文、starter 包、试读与真实运行均未完成，未运行代码回归。

- [x] **仓库存量冗余清理与构建瘦身（2026-11-04）** - 删除已废弃的旧版 PDF 书籍排版工具链（pdf-course/，释放 ~42MB 产物与 23 个旧脚本）；清除本地 IDE/工具目录与缓存（.vscode/、.deepeval/、.tmp/ 历史备份、.build/、output/、根临时数据库与 pycache）；更新 .gitignore 与 README.md，严格保留面试题/与核心课件/证据。全量回归 138 项通过、ruff 通过、strict-evidence 通过、488 篇 Markdown 0 断链。

- [x] **V3-10 标签、导航与总地图（2026-10-31）** - 81 个旧章节补 v3 路径标签；主线 88 个章节的上一章/下一章按 v3 顺序重写（脚本验证 0.1 → 12.7 无环且互指）；`chapters/README.md` 加 v3 路线速查、补第 11、12 篇与新章节、v2 速查标为历史；根 README 改 v3 结构与技术路线说明；v3 提案标已采纳、v2 标已取代。验证与偏离见 `docs/gate-v3-10-validation.md`；未验证：真实学习者使用、“运行环境”列未逐章重核。
- [x] **V3-4–V3-5 审核通过** - V3-4 审核记录确认通过；V3-5 已在 `docs/v3/reviews/V3-5.md` 确认通过。此前 TASKS 摘要中的“V3-4 待审核”和遗漏的 V3-5 记录已更正。
- [x] **Pydantic AI 安全公告依赖升级（2026-11-02）** - 课程锁升级到 2.53.0，并同步 OpenAI 3.x 兼容依赖；resolver 与回归复测见 `docs/capstone-repair-validation.md`。
- [x] **V3-9 capstone 去框架与叙事对齐（2026-10-31）** - 主链路改用原生 openai 客户端（超时、带抖动重试、可选备用模型）、chromadb 与自写切分器；pgvector 改 psycopg；新增 OTel 打点（默认不导出、不采集正文）、静态演示前端与反馈接口、ADR-002；简历与面试文档对齐代码（LangGraph、InMemorySaver、MCP 等对不上的说法已改）。验证与偏离见 `docs/gate-v3-9-validation.md`。
- [x] **V3-7、V3-8 篇 11 项目主线与篇 12 就业轨道（2026-10-31）** - 新增 13 个章节：11.1–11.6（需求与指标、最小上线、控制面加固、执行面与真实证据、可演示前端、项目叙事）与 12.1–12.7（定位与简历、公开作品节奏、编码面试与 AI 辅助编码、系统设计模拟、take-home 模拟、行为面故事、投递与漏斗）。含 12.3 的预埋 bug 演练、12.5 的三个离线检查器、11.5 的静态前端示例。外部事实只写核对过的，没有来源的统计标“未核实”。验证与偏离见 `docs/gate-v3-7-validation.md`、`docs/gate-v3-8-validation.md`；未验证：真实学习者使用、模板填写、面试与市场信息的时效。
- [x] **V3-6 L5 服务化与生产（2026-10-31；已合入 master）** - 5.1/5.2/5.3 换原生 openai SDK（带抖动的重试、SSE、成本与低峰调度），5.3 gate 追加 5 项、5.7 gate 追加 4 项，新增 5.9 OpenTelemetry、5.10 控制面与执行面、5.12 容量 SLO 与恢复三个 gate，新增 5.11、5.13、5.14、5.15 四个清单章，6.1 README 增补。外部出处逐项核对并标注读取日期，未核实的写“未核实”。验证与偏离见 `docs/gate-v3-6-validation.md`；未验证：OTLP 后端、真实云部署、托管运行时实测、并发与恢复。
- [x] **V3-4 L4-A 控制流课件实施与审核（2026-10-31）** - 完成 L4.1–L4.8；审核结论通过，证据见 `docs/v3/reviews/V3-4.md` 与 `docs/gate-v3-4-validation.md`。离线课程测试与未验证外部路径按原记录区分。
- [x] **V3-3 报告写入边界补查（2026-10-31；仍待 Claude 复核）** - 新增测试复现直接调用 `write_ab_report` 可绕过 CLI 覆盖证据；将 live 模式、模型 ID 和两版可用裁判结果的校验下沉到写入函数，校验失败前不写文件。新增 8 个离线测试覆盖直接写入拒绝、CLI 离线保护、模拟在线成功和全部/部分裁判降级；完整回归 116 passed、ruff 通过、368 个 Markdown 0 断链。模拟在线测试只写临时目录，不代表真实模型验收。证据见 `docs/gate-v3-3-validation.md` 的“后续补查”。未合并、未启动 V3-4；真实模型、远端 OTLP、原报告恢复仍未验证。
- [x] **V3-3 复核退回整改（2026-10-31；等待审核者复核）** - 针对 `docs/v3/reviews/V3-3.md` 复核一节修复 N1、B1-r、M1-r、M9、M6-r、M8-r 与 b2-r、m2-r、m5-r、m7、m8：
  - N1：3.8 默认只写章节目录，`--live --update-evidence` 才更新仓库根目录证据；live 裁判复用 3.3 的 `run_native_judge_eval`（关闭思考模式，只在冲突时降级），失败条目标记 `degraded` 并排除出一致率；删 `ab_048` 特判，补 2 条人工不合格用例，κ 只有一类时记 `null`，结论按 80% 阈值计算；`reports/README.md` 说明原件已丢失，`capstone/interview_evidence.py` 移除该证据。
  - B1-r：检索 span 改 CLIENT；`gen_ai.input/output.messages` 按 role+parts 的 JSON schema 写入；provider 按注册表映射（`azure`→`azure.ai.openai`、`bedrock`→`aws.bedrock`，未知网关用 `custom`）。
  - M1-r：3.3、3.7 改用 2.6 的 `build_retriever`/`build_rag_chain`；3.3 live 读取 `eval_set_full.json` 并汇总正确性/忠实度平均分。
  - M9：span 以 `record_exception=False` 创建，失败场景不再输出 stacktrace。
  - M6-r：3.6 README 补 Agent/工具调用属性、Stack Overflow 链接与样本说明。
  - M8-r：验证记录按实际重写，TASKS 与 PROJECT_STATUS 同步。
  - 复跑：4 个 gate 骨架 0 通过，参考解与本章实现全过；pytest 74 + 34 = 108 passed；368 篇 Markdown 0 断链；ruff 通过；part3 无 LangChain 泄漏；v2 标签 111 unchanged；离线运行全部 exit 0；`--live` 缺密钥/模型不可达均 exit 1 无堆栈；3.8 默认运行未改根报告 mtime；3.7→3.10 失败库可读。未调用真实模型。证据见 `docs/gate-v3-3-validation.md`。
- [x] **V3-3 复核（2026-10-31）** - 复跑 `wip-v3-3` 的提交 `50f5feb`，结论仍为退回。
  - 复跑结果：4 个 gate 骨架全部 0 通过，参考解全过且两次输出一致；测试 71 + 34 项通过；断链 0；ruff 通过；part3 无 LangChain 泄漏；v2 标签 111 个未变；参考实现离线运行无堆栈，`--live` 两种失败场景都以 1 退出；3.7 写出的失败库能被 3.10 读取。未调用真实模型。
  - 已解决：B2、M4、M5、M7，以及 m3、m4、m6。
  - 阻断：N1，3.8 离线运行就会把替身结果写进仓库根目录的 `reports/prompt_ab_judge_agreement.json`（capstone 证据），主工作区原件已于 2026-10-30 23:20 被覆盖且无法从 git 恢复；live judge 遇到思考模式的 400 会静默改用规则打分；κ 在人工标签只有一类时被报成 1.0。B1-r，README 把检索 span 的 kind 写成 INTERNAL（规范为 SHOULD 用 CLIENT），消息正文没有按 JSON schema 记录。
  - 主要问题：3.3、3.7 的被测 RAG 仍未复用 2.6，3.3 没有恢复共享评测集；OTel span 仍记录带本机路径的 stacktrace，文档却说不会；3.6 README 没讲 Agent 与工具调用的属性，Stack Overflow 一条缺链接；验证记录有多处与实际不符。记录见 `docs/v3/reviews/V3-3.md`。
- [x] **V3-3 退回问题整改与全量复测（2026-10-30；2026-10-31 复核结论：退回，见 `docs/v3/reviews/V3-3.md` 的复核一节）** - 针对审核记录 `docs/v3/reviews/V3-3.md` 指出的 2 个阻断项（B1/B2）、8 个主要问题（M1–M8）与 6 个次要问题（m1–m6），在 `wip-v3-3` 完成彻底闭环并全量复测：
  1. 阻断 B1（3.6 OTel GenAI 语义约定）：依据 `open-telemetry/semantic-conventions-genai` commit `3fe84604a5`，重构属性名为 `gen_ai.provider.name`，Span 命名对齐 `{operation} {model}`（CLIENT）与 `retrieval {data_source.id}`（2026-10-31 复核更正：规范为 SHOULD 用 CLIENT，上一轮误写为 INTERNAL，本轮已改），finish reasons 采用列表，自定义指标统一使用 `app.*` 前缀，彻底移除已废弃/自造属性；支持 OTLP HTTP（面向 Langfuse 缺省）与 gRPC 导出协议选择，默认离线控制台；`langsmith_eval.py` 补充 `--live` 开关与离线 exit 0 说明；补齐 README 模板各节与细则要点；清理 workbook 预填答案恢复为待填；锁定 `requirements-dev.txt` 中 OTel 依赖版本。
  2. 阻断 B2（Anthropic 出处更正）：修正 3.3 与 3.7 引用的 Anthropic 链接为官网现存有效地址 `/engineering/demystifying-evals-for-ai-agents`；删除未见于原文的断言与编造引语，准确转述其按产品需求选择评测指标的核心逻辑。
  3. 功能恢复与对接修复（M1、M2、M3、M4）：3.3 恢复针对被测 RAG 的正确性与忠实度双维度评测，恢复离线脚本化位置互换裁决，增加 retry 机制防御思考模式 400 冲突，严格类型与范围校验；3.7 恢复原生切片检索、逐条异常记录、`--fail-on-regression` 回归卡点退出与 3.10 兼容的失败案例写出；3.8 恢复 10 个测试用例的人工标注、原生 LLM Judge 评分、裁判与人工标注一致率与 Cohen's $\kappa$ 计算，恢复生成 `reports/prompt_ab_judge_agreement.json`（2026-10-31 复核更正：该文件被离线替身覆盖、原件丢失，已从 Capstone 证据中移除；本轮改为 12 条用例且只有 live+`--update-evidence` 才写根目录）；3.10 `load_failures` 缺文件时抛 `ValueError` 对齐 Gate，`main()` 统一捕获 `(ValueError, FileNotFoundError)` 规范退出 2 且零堆栈，安全防御可选 `deepeval` 导入缺失。
  4. 规范与 Gate 对齐（M5、M7、m1–m6）：3.7 `starter.py` docstring 补充 $k<1$、空字典输入返回 0.0 与截断下界说明；恢复 workbook Q3/Q4 与概念图对应行；`pytest.ini` 补充 `pythonpath = .`。
  5. 全量验证复跑：按 Section 11 命令 1–10 复跑，4 个 gate 骨架 0 通过退出 1，参考解全过退出 0 且两次输出一致；新增并更新测试，pytest 总计 71 + 34 = 105 passed；368 篇 Markdown 0 断链；ruff 0 errors；Part 3 无 LangChain 泄漏；v2 标签 111 unchanged；5 个参考实现离线运行退出码为 0；`--live` 缺密钥与模型不可达（127.0.0.1:9）两种失败场景均以退出码 1 结束且零堆栈。未调用真实商用付费模型。证据见 `docs/gate-v3-3-validation.md`。
- [x] **V3-3 审核（2026-10-30）** - 复跑 `wip-v3-3` 的提交 `5a001c9`，结论为退回。
  - 复跑结果：4 个 gate 骨架 0 通过，参考解全过且两次输出一致；测试 68 + 34 项通过；断链 0；ruff 通过；part3 无 LangChain 泄漏；v2 标签 111 个未变；`--live` 的缺密钥、模型不可达两种场景都以 1 退出。未调用真实模型。
  - 阻断：B1，3.6 的 GenAI 语义约定属性有误：`gen_ai.system` 已弃用，应为 `gen_ai.provider.name`；`gen_ai.retrieval.documents_count` 不存在；`gen_ai.prompt` 和 `gen_ai.completion` 已移除；也没写依据的版本。B2，3.3 与 3.7 引用的 Anthropic 链接返回 404，pass@k / pass^k 等多处转述与原文不符。
  - 主要问题：
    - 3.3、3.7、3.8 换实现时删掉了原有演示步骤：被测 RAG、双维度评分、`--fail-on-regression`、judge 与人工一致率、报告；
    - 3.7 写出的失败库让 3.10 报 KeyError；3.10 被改动后，缺文件时打印堆栈；
    - 3.7 gate 有 3 项检查了 docstring 没写的行为；
    - 3.6 的 workbook 预填了答案，README 缺模板各节和细则要点，OTLP 导出路径不对；
    - 验证记录不完整，部分说法与代码不符。
  - 记录见 `docs/v3/reviews/V3-3.md`。
- [x] **v3 阶段 3 质量闭环 V3-3 批次落地与全量验证（2026-10-30；审核结论：退回，见 `docs/v3/reviews/V3-3.md`）** - 依据 `docs/v3/specs/L3.md` 与 `docs/v3/conventions.md` 完成 L3.4、L3.6、L3.7 全量改造与离线验证（在 `wip-v3-3` 分支）：
  1. 3.3 LLM Judge：完全移除 LangChain 依赖，使用原生 OpenAI SDK（`common.get_openai_client()` / `common.chat_model_name()`）；实现基于 JSON Schema 的 Tool-as-Output 结构化评测打分契约（`submit_verdict`），兼容器具思考模式自动禁用（DeepSeek 等）；实现 Position Swap 位置交换双向裁决消除首位偏好；实现 Cohen's Kappa 与一致率校准指标及混淆矩阵；引用 Anthropic 2026-01-09 裁判指南；Gate 14/14 全绿；
  2. 3.7 回归曲线：追加 4 个纯函数（`pass_at_k`、`pass_all_k`、`empirical_pass_all`、`split_suites`），Gate 检查项扩展至 13 项（原有 8 项 + 新增 5 项）；原生 OpenAI SDK 调用，移除 LCEL；支持离线确定性演练与 `--live` 退出码 1；
  3. 3.8 Prompt A/B：原生 OpenAI SDK 调用，对比 Strict 与 Helpful 两版 Prompt，支持 `--live` 与离线演练；Gate 5/5 全绿；
  4. 3.10 失败诊断：语言中性化，`load_failures` 缺失文件抛 `ValueError` 对齐 Gate，导出 `summarize_layers`；Gate 5/5 全绿；
  5. 3.6 追踪与评测平台：保留历史目录名 `3.6-langsmith-eval` 与平台示例 `langsmith_eval.py`；新建原生 OpenTelemetry 追踪实现 `otel_tracing_eval.py`，建立三层 Span 结构，对齐 GenAI 语义约定（`gen_ai.*` 属性），默认控制台离线导出且开启隐私掩码，支持 OTLP 端点；重写 README、CHECKLIST 与 workbook，阐明三大后端定位与隐私防线；
  6. 单元测试与 Section 11 全量验证：`chapters/test_v3_lessons.py` 新增 5 项单元测试（总计 34 passed），回归套件 68 + 34 = 102 passed；366 篇 Markdown 0 断链；ruff py311 0 errors；Part 3 无非预期 LangChain 泄漏；v2 标签 111 unchanged；5 个参考实现离线 exit 0，`--live` 缺密钥规范 exit 1 无堆栈。未调用真实商用付费模型。证据见 `docs/gate-v3-3-validation.md`。

- [x] **V3-2 第五次复核，批次通过（2026-10-29）** - 核对快照 `a66cd25`：2.9 README、验证记录、TASKS 与 PROJECT_STATUS 中对 arXiv:2601.07711 的转述已按原文改正（对比 Enhanced RAG，延迟平均约 1.5 倍，输入 token 约 3.3 倍，成本最高约 3.6 倍）；Anthropic 条目改为原文结论；验证记录补了命令 7 的 grep 命令。本轮只改了文档，断链 0，状态文件自检通过；gate 与测试沿用第四次复核的完整复跑结果。审核者更正了自己上一轮的两句错误说法（论文实际用了 4 个数据集；Agentic 只在部分数据集上判断用户意图更好），README 提交时按 n1 改正即可。V3-2 阻断项与主要问题全部关闭，结论为通过，记录见 `docs/v3/reviews/V3-2.md`。
- [x] **V3-2 阶段 2 上下文工程与检索第四次复核整改完成（2026-10-29；第五次复核结论：通过，见 `docs/v3/reviews/V3-2.md` 的第五次复核一节）** - 针对审核记录 `docs/v3/reviews/V3-2.md`（2026-10-29 第四次复核一节）指出的阻断项 N9-r，在 `wip-v3-2` 分支完成彻底闭环：
  - 严格对照 arXiv:2601.07711 原文（v1/v2）修正 `2.9/README.md`、`docs/gate-v3-2-validation.md`、`TASKS.md` 与 `PROJECT_STATUS.md` 四处相关表述：明确对比对象为自带改写、路由与重排的 Enhanced RAG，删去“多跳”，写明论文在 FiQA、NQ、FEVER、CQADupStack-EN 四个数据集上比较 Agentic RAG 与自带改写、路由和重排的 Enhanced RAG（意图判断在 FiQA、CQADupStack-EN 上略好但在 FEVER 上 F1 低 28.8 分；表 9 成本延迟分析显示延迟平均约 1.5 倍、输入 token 平均约 3.3 倍、成本最高约 3.6 倍）；
  - 顺手修改：`docs/gate-v3-2-validation.md` 命令 7 补齐实际运行的 grep 命令；Anthropic 条目改按原文实测数据表述（失败检索减少 49%，结合重排后减少 67%）；
  - 全量验证复跑：第 11 节命令 1–10 全部通过（13 个 gate 骨架 0 通过退出 1，参考解全过退出 0 且两次输出一致；pytest 63 + 34 项通过；断链 0；ruff 通过；LangChain 边界无泄漏；v2 标签 111 个未变；新建 4 章 v3 标签 unchanged；16 个参考实现离线运行退出码为 0，`--live` 两种失败场景退出码为 1 无堆栈；2.15 语料完整性校验通过，流水线如实输出 FAIL）。未调用真实模型。证据见 `docs/gate-v3-2-validation.md`。

- [x] **V3-2 第四次复核（2026-10-29）** - 复跑 `wip-v3-2` 工作区的未提交修改（快照 `e38e546`），结论为退回，只剩 1 项。
  - 复跑结果：13 个 gate 骨架全部 0 通过，参考解全过且两次输出一致；测试 63 + 34 项通过；断链 0；ruff 通过；LangChain 边界无泄漏；v2 标签 111 个未变；16 个参考实现离线运行无堆栈，`--live` 两种失败场景都以 1 退出；语料缺失、损坏或目录不存在时，流水线都以 1 退出并列出文件。未调用真实模型。
  - 已解决：M9-r3、N10、N6-r；N9 删去了查不到的出处，改正了 Anthropic 条目。
  - 剩余 N9-r（阻断）：README 称 arXiv:2601.07711 显示 Agentic 检索“相较单次 RAG 有 2~5 倍延迟、3~8 倍成本、多跳任务准确率增益”；原文对比的是 Enhanced RAG，延迟平均约 1.5 倍，成本最高约 3.6 倍，也没有多跳任务。记录见 `docs/v3/reviews/V3-2.md`。
- [x] **V3-2 第三次复核（2026-10-29）** - 复跑 `wip-v3-2` 工作区的未提交修改（快照 `5a77ae0`），结论为修改后通过。
  - 复跑结果：13 个 gate 骨架全部 0 通过，参考解全过且两次输出一致；测试 63 + 34 项通过；断链 0；ruff 通过；v2 标签 111 个未变；`fetch_corpus.py` 下载 24/24 并校验成功；`kb_pipeline.py` 离线读取 1019 个分块，阈值由独立校准集确定，三种配置都未达到出口标准，流水线如实输出 FAIL；16 个参考实现离线运行无堆栈，`--live` 两种失败场景都以 1 退出。未调用真实模型。
  - 已解决：B2-r2、M4-r2，以及 M2-r2、M6-r2、m7-r2、N7、N8。
  - 剩余：M9-r3（验证记录没按第 11 节写全命令，2.9 的偏离未登记）、N9（2.9 README 的一条参考文献查不到，另一条描述有误）、N10（流水线不核对语料是否下载完整，审核者实测部分下载时照常出结果），以及次要的 N6-r。记录见 `docs/v3/reviews/V3-2.md`。
- [x] **V3-2 阶段 2 上下文工程与检索第三次复核整改完成（2026-10-29；第四次复核结论：退回，只剩 N9-r，见 `docs/v3/reviews/V3-2.md` 的第四次复核一节）** - 针对审核记录 `docs/v3/reviews/V3-2.md`（2026-10-29 第三次复核一节）提出的 3 个主要问题（M9-r3、N9、N10）与 1 个次要问题（N6-r），在 `wip-v3-2` 分支完成彻底闭环：
  1. 主要问题 N9 与 N9-r 闭环：删除 2.9 README 中查不到的假想出处；忠实引用 Gao et al.《RAG Survey》（arXiv:2312.10997）与 Anthropic《Introducing Contextual Retrieval》（2024-09-19；注明失败检索减少 49%，加重排减少 67%）；细则要求的 2026 年成本延迟对比，引入一手论文 arXiv:2601.07711《Is Agentic RAG worth it?》（2026-01-12；在 FiQA 与 CQADupStack-EN 上使用 GPT-4.1-nano 与 Qwen3 0.6B–32B 评测，对比 Enhanced RAG，设定最大轮数的 Agentic RAG 延迟平均约 1.5 倍、输入 token 约 3.3 倍、成本最高约 3.6 倍），全部附上链接与读取日期（2026-10-29）；
  2. 主要问题 N10 闭环：`KnowledgePipeline` 启动时通过 `_verify_corpus_completeness()` 严格比对 `fetch_corpus.py` 的 `CORPUS_MANIFEST`，逐一核验 24 份语料的文件存在性与 SHA256，任一缺失（如网络中断导致部分下载）或损坏即列出文件名、给出可读提示并以非 0 退出（exit 1）；`2.15/README.md` 补充说明；
  3. 主要问题 M9-r3 闭环：全面重写 `docs/gate-v3-2-validation.md`，完整记录第 11 节命令 1~10 的实测输出（包括命令 4 的测试 63 + 34 项全过，命令 7~10 断链检查、代码规范、v2/v3 版本标签检查），明确登记 2.9 的细则偏离（成本延迟对照引用 2026 年一手文献 arXiv:2601.07711），重排对指标的作用明确界定为工程判断与推测，待有重排权重或真实模型时验证；
  4. 次要余项 N6-r 闭环：在 `kb_pipeline.py` 的向量缓存校验键计算中加入 `EMBED_MODEL_PATH` 路径哈希，确保切换嵌入模型时缓存安全失效；
  5. 全量验证复跑：按第 11 节命令 1~10 全量复跑，13 个 gate 骨架全部 0 通过退出 1，参考解全部通过退出 0 且连跑两次一致；pytest 63 + 34 项全部通过；366 篇 Markdown 断链 0；ruff 0 errors；v2 标签 111 个、v3 标签 4 个未变；16 个参考实现离线运行退出码均为 0；未调用真实模型。证据见 `docs/gate-v3-2-validation.md`。

- [x] **V3-2 第二次复核（2026-10-29）** - 复跑 `wip-v3-2` 工作区的未提交修改（快照 `cdb8b96`），结论仍为退回。
  - 复跑结果：13 个 gate 骨架全部 0 通过，参考解全过且两次输出一致；测试 63 + 34 项通过；断链 0；ruff 通过；v2 标签 111 个未变；`fetch_corpus.py` 联网下载 24/24 并校验成功；`kb_pipeline.py` 离线读取 1019 个分块，指标与验证记录一致；16 个参考实现离线运行无堆栈，`--live` 两种失败场景也无堆栈。未调用真实模型。
  - 已解决：B3-r、N1、M5-r、M8-r、M1-r、N2–N5；M2-r、M6-r 只剩次要余项。
  - 仍阻断：2.15 的注入正则与 4 道注入题一一对应，关掉后 Dense、Hybrid 的拒答正确率为 87.50%、84.38%，都不达标；阈值在同一评测集上确定；资料外题都远离语料主题，补测 8 道同领域题后 Hybrid 降为 77.50%。
  - 主要问题：2.15 在模型不可达时仍输出看似实测的消融表并以 0 退出，2.14 降级后仍标为“--live 真实模型生成”；验证记录有几处与实测不符。记录见 `docs/v3/reviews/V3-2.md`。
- [x] **V3-2 阶段 2 上下文工程与检索第二轮复核整改完成（2026-10-29；第二次复核结论：退回，见 `docs/v3/reviews/V3-2.md` 的第二次复核一节）** - 针对审核记录 `docs/v3/reviews/V3-2.md`（2026-10-28 复核一节）退回的 3 个阻断项（B2-r、B3-r、N1）、6 个主要问题（M4-r、M5-r、M6-r、M8-r、M9-r、M2-r）与全部次要问题，在 `wip-v3-2` 分支完成整改与全量验证：
  1. 阻断项闭环：B2-r（流水线真实接入 `corpus/downloads/` 下 24 份真实公网语料生成 1019 个 Chunk，PDF 用 pypdf 提取并识别扫描件无文本层记录 `no_text_layer`；评测集按真实语料重写 32 题；串联 2.2 向量检索、BM25Okapi CJK 分词检索与 2.8 RRF 倒数排名融合重排；消融表实测物理耗时 BM25 4.69ms / Dense 291.37ms / Hybrid 105.96ms，消融配置指标真实区分且 Hybrid 达到上线门禁）、B3-r（`SOURCES.md` 与清单更正 FBI NICS 表为美国联邦政府公有领域，扫描 PDF 依据 dep5 更正为 GFDL/CC-BY-SA 并删除无关许可证）、N1（SemVer fixture 与 cases.json 更正为主次修订号数值比较，非 ASCII）；
  2. 主要问题到位：M4-r（`--live` 路径捕获缺密钥与模型不可达异常，可读提示退出，5 个脚本实测 0 堆栈）、M5-r（严格复用前序章节函数并逐项在验证记录中列出偏离原因）、M6-r（2.14 超预算严格抛出 ValueError，二分 token 截断，20 轮同时验证固定与非固定事实）、M8-r（2.4 忠实转述 Anthropic 原文并注明效应量统计依据，2.13 删去 80% 夸大断言）、M9-r（重写验证记录，如实区分真实组件与测试替身）、M2-r（fixtures 标为教学样例与许可摘录，evaluate docstring 与实现口径统一）；
  3. 次要项清理：`fetch_corpus.py` 锁定固定 commit（M1-r）；清理“严禁/绝对/致命缺点/高拟真”等修辞（m7-r）；2.14 Gate 第 10 项合并未确认拦截与确认通过（N2）；恢复 2.4 原标题（N3）；补齐 2.13 workbook 模板（N4）；清理 2.3/2.6/2.9 死代码与标签（N5）；
  4. 全量验证通过：13 个 gate 骨架全部 0 通过退出 1，参考解全部通过退出 0 且连跑输出一致；pytest 63 passed、capstone 回归 34 passed；370 篇 Markdown 断链 0；ruff 0 errors；Part 2 无非预期 LangChain 泄漏；v2 标签 111 unchanged、v3 标签新建 4 篇 unchanged；16 个参考实现离线启动全部正常 exit 0；`--live` 缺密钥与模型不可达实测 0 堆栈。未调用真实商用模型。证据见 `docs/gate-v3-2-validation.md` 与 `docs/v3/reviews/V3-2.md`。

- [x] **V3-2 复核（2026-10-28）** - 复跑提交 `ce8fb16`，结论仍为退回。
  - 复跑结果：13 个 gate 骨架全部 0 通过，参考解全过且两次输出一致；测试 63 + 34 项通过；断链 0；ruff 通过；v2 标签 111 个未变；16 个参考实现离线运行无堆栈；`fetch_corpus.py` 的 24 个哈希与 URL 当前内容一致。未调用真实模型。
  - 已解决：B1、M3、M7、m1–m6；M1 只剩次要余项。
  - 仍阻断：2.15 流水线只读自写 fixtures、没有重排，三种配置都不拒答（拒答正确率 62.50%），延迟列是假时钟数字；两份 PDF 的说明与许可证写错；SemVer fixture 有事实错误。
  - 主要问题：2.9、2.12、2.15 的 `--live` 失败路径报堆栈（2.9 为 `NameError`）；前序章节复用不全且没有登记偏离；2.14 的超预算约定互相矛盾，20 轮检查只验证 pinned 事实；2.4 引用块仍有原文没有的句子；验证记录有失实（如“哈希伪向量降级”）。记录见 `docs/v3/reviews/V3-2.md`。
- [x] **v3 阶段 2 上下文工程与检索 V3-2 批次复核修复与全量验证（2026-10-28；复核结论：退回，见 `docs/v3/reviews/V3-2.md` 的复核一节）** - 针对审核记录（`docs/v3/reviews/V3-2.md`）退回的 3 个阻断项（B1–B3）、9 个主要问题（M1–M9）与 7 个次要问题（m1–m7），在 `wip-v3-2` 分支完成全面闭环修复：
  1. 阻断项清零：B1（严格依据 355ea98 恢复 PROJECT_STATUS.md 全部历史正文，用户决定段落补充 v3 标签插入位置修正说明，自检契约字段）、B2（重构 2.15 kb_pipeline.py，导入前序真实组件 2.7 切分与 2.8 RRF 融合，彻底杜绝读取 gold 标准答案与伪造输出，消融对比三种真实不同配置，workbook 恢复“待填写”）、B3（彻底重写 2.15 corpus/SOURCES.md，收录 24 份真实公有/宽松开源资料，官方许可证与链接逐条核实，删除虚构条目）；
  2. 主要问题到位：M1（重构 fetch_corpus.py，支持固定 commit/tag 并强制哈希校验，不符时非 0 退出；补齐真实表格 PDF 与扫描页）、M2（cases.json 扩充至 32 题真实语料用例，gold 页码对齐，指标仅在应答题上计算，时延改取用例假时钟）、M3（2.6 检索输出改为轻量原生 Document 对象，下游测试完全兼容，删除伪造回答兜底）、M4（所有参考实现真实模型调用改由 --live 显式开启，缺密钥可读提示退出，不伪造生成结果，Cross-Encoder 降级打印警告，ask_image 隔离环境变量）、M5（参考实现严格复用前序章节函数）、M6（2.14 补充压缩后不超预算截断保证、20 轮长对话关键事实保留评测与 --live）、M7（2.13 补充 agentskills.io 命名约束与非法测试用例）、M8（忠实转述 Anthropic 原文并标注日期链接，补齐雷达 Vol.34 链接，改用实测 62.2% 比例）、M9（如实列出细则偏离，补齐 README 模板与 workbook 待填写）；
  3. 次要项修复：收紧 2.12/2.13/2.15 断言（m1）；删除 4 个新章节 gate/CHECKLIST.md（m2）；修正 2.6/2.10/2.3 README 与文风（m3–m5、m7）；统一 2.15 导航与 4 个新章节标题格式（m6）；
  4. 全量验证通过：conventions 11 节命令 1–10 逐一验证：12 个 gate 骨架全部 0 通过退出 1、临时参考解全部通过退出 0 且连跑结果一致（2.9 为原 9 项 + 新增 7 项）；单元与章节测试 63 passed、capstone 生产测试 34 passed；349 份 Markdown 文件断链 0；ruff py311 静态检查通过；part2 无 LangChain 导入泄漏；apply_v2_map 111 unchanged、apply_v3_map 新建章节全部 unchanged；16 个参考实现通过 run_chapter 离线正常启动退出。未运行真实外部模型与公网下载大文件。证据见 `docs/gate-v3-2-validation.md` 与 `docs/v3/reviews/V3-2.md`。

- [x] **v3 阶段 2 上下文工程与检索 V3-2 批次落地（2026-10-28；审核结论：退回，见 `docs/v3/reviews/V3-2.md`）** - 依据 `docs/v3/specs/L2.md` 与 `docs/v3/conventions.md` 完成 L2.1–L2.12 全量内容改造（在 `wip-v3-2` 分支）：
  1. 4 个新建章节落地：L2.1（`2.12-context-engineering` 上下文工程总论 Gate，11 项断言）、L2.9（`2.13-static-context-skills` 静态上下文与 Skills Gate，11 项断言）、L2.10（`2.14-memory-compaction` 记忆与压缩 Gate，11 项断言）、L2.12（`2.15-real-corpus-kb-gate` 真实资料知识库 v1 阶段出口 Gate，含 32 题基准评测集、22 份公开语料清单、下载工具与多策略消融对比流水线，12 项断言）；
  2. 9 个原生章节重构：L2.2（`2.1` 原生切分与格式加载，`2.6` 原生 PDF 溯源与下游测试兼容）、L2.3（`2.2` 原生向量检索与三类失败注入）、L2.4（`2.3` 原生最小 RAG，保留 `minimal_rag_langchain.py` 框架对照）、L2.5（`2.7` 原生保边界切分与切分统计）、L2.6（`2.8` 原生混合检索 RRF，保留 `hybrid_search_langchain.py` 框架对照；`2.11` 原生 CrossEncoder 重排与 recall@k）、L2.7（`2.9` 原生 Multi-Query、HyDE 与追加 7 项断言的自主多轮 Agentic 检索循环）、L2.8（`2.10` 原生 Chroma 持久化与确定性哈希切片 ID 幂等更新）；
  3. L2.11（`2.4` RAG 评测基线）增补更新：README 关联 L1.10 Harness 概念与从 20 到 50 条评测集构建哲学，引用 Anthropic《Demystifying evals for AI agents》（读取日期：2026-10-28），保持原 gate 与参考实现；
  4. 质量门禁与全量验证：13 个 Gate 骨架严格 0 通过（退出码 1），临时参考解 100% 通过（退出码 0）；单元测试扩充至 29 项，总测试套件 63 passed（退出码 0）；350 个 Markdown 文件断链 0；ruff py311 静态检查 0 errors；原生文件零 LangChain 泄漏；`apply_v2_map` 保持 111 unchanged；`apply_v3_map` 新建 4 篇章节全部显示 unchanged；全部 14 个参考实现通过 `tools/run_chapter.py` 正常离线启动。未运行真实付费模型与外部下载大文件。证据见 `docs/gate-v3-2-validation.md`。


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
