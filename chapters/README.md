# 章节总地图

当前路线是 **v3**：L0–L5 是技术主线，P（篇 11）是持续并入同一个公开项目的项目主线，J（篇 12）是同步进行的就业轨道。第 7 篇企业客服 Copilot 是**已冻结的历史教学快照**，业务行为以 [capstone](../capstone/README.md) 为准；第 8–10 篇按岗位选学。

每章的 README 依次回答：要解决什么问题、涉及哪些概念、代码怎么运转、从哪里读代码、怎么练习、边界在哪里。
建议先读 README，再运行和阅读代码；目录存在、离线测试通过和真实环境验收是三件事，要分别记录。

> 验收方式：gate 章用 `gate/gate_check.py` 闭卷 gate（先读任务书、自己实现，全部 PASS 后再打开参考实现）；清单章用 `gate/CHECKLIST.md`；P、J 篇以清单、模板和产物为主，J3、J5 另有离线演练与检查器。项目 29 步用 [flagship-project/ACCEPTANCE.md](../flagship-project/ACCEPTANCE.md) 总清单验收（快照已冻结，不再补证据）。
>
> 本仓库的实施与验证情况是：课件结构、离线 gate 与离线测试已逐批复跑；**真实学习者的使用、真实环境（云部署、真实用户、远端 CI、真实容量与恢复）的证据尚未取得**，见 [TASKS.md](../TASKS.md) 与 `docs/gate-v3-*-validation.md`。

## v3 路线速查

v3 是当前的学习路线：L0–L5 是技术主线，P（篇 11）是持续并入同一个公开项目的项目主线，J（篇 12）是同步进行的就业轨道。目录里的章节号（如 2.5）不变，旧链接继续有效；每章标题下有一行 `v3 路径`。完整的大纲、前置关系与 16 周排期见 [docs/v3/outline.md](../docs/v3/outline.md)，第 6 节是就业出口标准（E1–E4）。

下表与 [outline.md 第 4 节](../docs/v3/outline.md#4-章节总表)一致；“阅读”表示核心阅读，归入所在 v3 章节，不另设验收。课时是建议值，不是实测。


### L0 定位与工具链（12h）

| v3 编号 | 标题 | 章节 | 验收 | 课时 |
|---|---|---|---|---|
| L0.1 | 环境与最小闭环 | [0.1](part0-setup/0.1-environment/README.md) | 清单 | 2h |
| L0.2 | 证据式学习法 | [0.2](part0-setup/0.2-learning-workflow/README.md) | 清单 | 2h |
| L0.3 | 用编码 Agent 开发与审查 | [0.3](part0-setup/0.3-coding-agent-workflow/README.md) | 清单 + 产物 | 3h |
| L0.4 | AI 应用的 Python 工程底座 | [0.4](part0-setup/0.4-python-engineering-base/README.md) | gate | 3h |
| L0.5 | 岗位地图与差距诊断 | [0.5](part0-setup/0.5-job-map-gap/README.md) | 清单 + 产物 | 2h |

### L1 模型 API 原语与嵌入式功能（46h）

| v3 编号 | 标题 | 章节 | 验收 | 课时 |
|---|---|---|---|---|
| L1.1 | 一次调用与 LLM 边界 | [1.1](part1-foundations/1.1-first-call/README.md) | gate | 4h |
| L1.2 | LLM 工作原理 | [1.7](part1-foundations/1.7-llm-internals/README.md) | gate + 自测清单 | 5h |
| L1.3 | 输出控制与流式 | [1.2](part1-foundations/1.2-control-output/README.md) | gate | 3h |
| L1.4 | 结构化输出 | [1.3](part1-foundations/1.3-structured-output/README.md) | gate | 5h |
| L1.5 | 多轮与上下文预算 | [1.4](part1-foundations/1.4-context-memory/README.md) | gate | 4h |
| L1.6 | 工具调用协议 | [1.5](part1-foundations/1.5-tool-calling/README.md) | gate | 5h |
| L1.7 | Provider 抽象、第二厂商与成本 | [1.9](part1-foundations/1.9-provider-cost/README.md) | gate | 5h |
| L1.8 | 手写 Harness | [2.5](part2-rag/2.5-raw-sdk-rag-agent-loop/README.md) | gate | 6h |
| L1.9 | Gate：CLI 助手 | [1.8](part1-foundations/1.8-cli-chatbot/README.md) | gate | 3h |
| L1.10 | 嵌入式 LLM 功能与 eval harness | [1.10](part1-foundations/1.10-embedded-llm-feature/README.md) | 双 gate + 产物 | 6h |

### L2 上下文工程与检索（60h）

| v3 编号 | 标题 | 章节 | 验收 | 课时 |
|---|---|---|---|---|
| L2.1 | 上下文工程总论 | [2.12](part2-rag/2.12-context-engineering/README.md) | gate | 4h |
| L2.2 | 数据接入与切分 | [2.1](part2-rag/2.1-load-split/README.md)、[2.6](part2-rag/2.6-pdf-sources/README.md) | gate ×2 | 5h |
| L2.3 | 向量化与召回 | [2.2](part2-rag/2.2-embed-retrieve/README.md) | gate | 5h |
| L2.4 | 最小 RAG：引用与拒答 | [2.3](part2-rag/2.3-minimal-rag/README.md) | gate | 5h |
| L2.5 | 切分策略消融 | [2.7](part2-rag/2.7-chunk-strategy/README.md) | gate | 4h |
| L2.6 | 混合检索与重排 | [2.8](part2-rag/2.8-hybrid-search/README.md)、[2.11](part2-rag/2.11-multimodal-rerank/README.md) | gate ×2 | 7h |
| L2.7 | 查询改写与 agentic retrieval | [2.9](part2-rag/2.9-query-rewrite/README.md) | gate（追加检查） | 6h |
| L2.8 | 持久化与增量索引 | [2.10](part2-rag/2.10-chroma-persist/README.md) | gate | 4h |
| L2.9 | 静态上下文与 Skills | [2.13](part2-rag/2.13-static-context-skills/README.md) | gate | 4h |
| L2.10 | 记忆与压缩 | [2.14](part2-rag/2.14-memory-compaction/README.md) | gate | 4h |
| L2.11 | RAG 评测基线 | [2.4](part2-rag/2.4-eval-seed/README.md) | gate | 5h |
| L2.12 | Gate：真实资料知识库 v1 | [2.15](part2-rag/2.15-real-corpus-kb-gate/README.md) | gate + 产物 | 7h |

### L3 质量闭环（28h）

| v3 编号 | 标题 | 章节 | 验收 | 课时 |
|---|---|---|---|---|
| L3.1 | 失败分析 | [3.1](part3-evals/3.1-error-analysis/README.md) | gate | 4h |
| L3.2 | 评测集建设 | [3.4](part3-evals/3.4-eval-dataset-build/README.md) | gate | 4h |
| L3.3 | 规则评测与 pytest 回归 | [3.2](part3-evals/3.2-eval-basics/README.md)、[5.8](part5-production/5.8-pytest-regression/README.md) | gate ×2 | 4h |
| L3.4 | LLM Judge 与校准 | [3.3](part3-evals/3.3-llm-judge/README.md) | gate | 5h |
| L3.5 | 指标口径 | [3.5](part3-evals/3.5-eval-dataset-ragas/README.md) | gate | 2h |
| L3.6 | 回归、A/B、pass^k 与报告 | [3.7](part3-evals/3.7-eval-regression-curve/README.md)、[3.8](part3-evals/3.8-prompt-ab-judge/README.md)、[3.10](part3-evals/3.10-eval-report-failures/README.md) | gate ×3（3.7 追加检查） | 5h |
| L3.7 | 追踪与评测平台 | [3.6](part3-evals/3.6-langsmith-eval/README.md) | 清单 | 2h |
| L3.8 | 线上反馈闭环 | [8.10](part8-ai-quality-optional/8.10-production-feedback-loop/README.md) | — | 2h |

### L4-A Agent 控制流（44h）

| v3 编号 | 标题 | 章节 | 验收 | 课时 |
|---|---|---|---|---|
| L4.1 | Workflow 与 Agent | [4.1](part4-agents-langgraph/4.1-agent-patterns/README.md) | gate（追加检查） | 5h |
| L4.2 | 有界 Agent 循环 | [4.5](part4-agents-langgraph/4.5-react-agent/README.md) | gate | 6h |
| L4.3 | 工具设计 | [4.18](part4-agents-langgraph/4.18-tool-design/README.md) | gate | 6h |
| L4.4 | 结构化路由与规划 | [4.7](part4-agents-langgraph/4.7-structured-routing/README.md)、[4.8](part4-agents-langgraph/4.8-plan-and-execute/README.md) | gate ×2 | 6h |
| L4.5 | 用 Pydantic AI 写 Agent | [4.16](part4-agents-langgraph/4.16-pydantic-ai-agent/README.md) | gate | 8h |
| L4.6 | 多 Agent 与上下文隔离 | [4.14](part4-agents-langgraph/4.14-supervisor-fanout/README.md) | gate | 4h |
| L4.7 | Agent 评测 | [3.9](part3-evals/3.9-agent-trajectory-eval/README.md) | gate（追加检查） | 6h |
| L4.8 | Gate：原生版与 SDK 版 | [4.17](part4-agents-langgraph/4.17-native-vs-sdk-gate/README.md) | gate | 3h |

### L4-B 状态、执行面与安全（46h）

| v3 编号 | 标题 | 章节 | 验收 | 课时 |
|---|---|---|---|---|
| L4.9 | 状态图（LangGraph） | [4.2](part4-agents-langgraph/4.2-langgraph-basics/README.md)、[4.3](part4-agents-langgraph/4.3-branch-loop/README.md)、[4.4](part4-agents-langgraph/4.4-state-reducer/README.md)、[4.6](part4-agents-langgraph/4.6-node-reliability/README.md) | gate ×4 | 8h |
| L4.10 | 检查点、HITL 与持久执行 | [4.10](part4-agents-langgraph/4.10-checkpoint-context/README.md)、[4.11](part4-agents-langgraph/4.11-streaming-hitl/README.md) | gate ×2 | 7h |
| L4.11 | 专项 Agent 执行面 | [4.19](part4-agents-langgraph/4.19-agent-execution-plane/README.md) | gate | 8h |
| L4.12 | 沙箱与最小权限 | [4.20](part4-agents-langgraph/4.20-sandbox-least-privilege/README.md) | gate | 5h |
| L4.13 | Agent 安全 | [4.12](part4-agents-langgraph/4.12-tool-safety-search/README.md) | gate | 5h |
| L4.14 | MCP 实战与取舍 | [4.21](part4-agents-langgraph/4.21-mcp-practice/README.md) | gate | 5h |
| L4.15 | 复用现成 harness | [4.22](part4-agents-langgraph/4.22-reuse-harness/README.md) | 清单（实操选做） | 2h |
| L4.16 | 框架素养 | [4.15](part4-agents-langgraph/4.15-framework-landscape/README.md) | 清单 + 练习 | 3h |
| L4.17 | Gate：异步专项 Agent | [4.23](part4-agents-langgraph/4.23-async-agent-gate/README.md) | gate + 产物 | 3h |

### L5 服务化与生产（58h）

| v3 编号 | 标题 | 章节 | 验收 | 课时 |
|---|---|---|---|---|
| L5.1 | FastAPI、SSE 与可靠性 | [5.1](part5-production/5.1-serve-fastapi/README.md)、[5.2](part5-production/5.2-reliability-retry/README.md) | gate ×2 | 9h |
| L5.2 | 成本：缓存、路由、峰谷 | [5.3](part5-production/5.3-cost-cache-routing/README.md) | gate（追加检查） | 4h |
| L5.3 | 持久化与 SQL | [5.4](part5-production/5.4-sqlite-persistence/README.md) | gate | 4h |
| L5.4 | 认证、授权与多租户 | [5.15](part5-production/5.15-auth-multitenancy/README.md) | 清单 + 产物 | 5h |
| L5.5 | 护栏、红队与治理 | [5.7](part5-production/5.7-security-guardrails/README.md) | gate（追加检查） | 5h |
| L5.6 | 可观测性：OpenTelemetry | [5.9](part5-production/5.9-otel-observability/README.md) | gate | 6h |
| L5.7 | 控制面与执行面集成 | [5.10](part5-production/5.10-control-execution-plane/README.md) | gate | 5h |
| L5.8 | 容器、CI 评测门禁与云部署 | [5.5](part5-production/5.5-docker-packaging/README.md)、[5.11](part5-production/5.11-cloud-deploy/README.md) | gate + 清单 | 8h |
| L5.9 | 容量、SLO 与恢复 | [5.12](part5-production/5.12-capacity-slo-recovery/README.md) | gate | 5h |
| L5.10 | 托管运行时取舍 | [5.13](part5-production/5.13-managed-runtime-tradeoffs/README.md) | 清单 | 1h |
| L5.11 | LLM 系统设计 | [5.14](part5-production/5.14-llm-system-design/README.md) | 清单 + 产物 | 3h |
| L5.12 | 模型方案取舍 | [6.1](part6-model-tradeoffs/6.1-choose-prompt-rag-finetune/README.md) | gate | 3h |

### P 项目主线（篇 11，36h）

| v3 编号 | 标题 | 章节 | 验收 | 课时 |
|---|---|---|---|---|
| P1 | 需求与指标 | [11.1](part11-project-sprint/11.1-requirements-metrics/README.md) | 清单 + 产物 | 4h |
| P2 | 最小上线 | [11.2](part11-project-sprint/11.2-walking-skeleton-deploy/README.md) | 清单 + 产物 | 5h |
| P3 | 迭代 1：控制面加固 | [11.3](part11-project-sprint/11.3-control-plane-hardening/README.md) | 清单 + 产物 | 10h |
| P4 | 迭代 2：执行面与真实证据 | [11.4](part11-project-sprint/11.4-execution-plane-launch/README.md) | 清单 + 产物 | 10h |
| P5 | 可演示前端 | [11.5](part11-project-sprint/11.5-demo-web-ui/README.md) | 清单 + 产物 | 3h |
| P6 | 项目叙事与证据索引 | [11.6](part11-project-sprint/11.6-project-narrative/README.md) | 清单 + 产物 | 4h |

### J 就业轨道（篇 12，50h）

| v3 编号 | 标题 | 章节 | 验收 | 课时 |
|---|---|---|---|---|
| J1 | 定位与三版简历 | [12.1](part12-job-track/12.1-positioning-resume/README.md) | 清单 + 产物 | 4h |
| J2 | 公开作品节奏 | [12.2](part12-job-track/12.2-public-portfolio-cadence/README.md) | 清单 | 4h |
| J3 | 编码面试与 AI 辅助编码 | [12.3](part12-job-track/12.3-coding-interview/README.md) | 清单 + 演练测试 | 14h |
| J4 | LLM 系统设计模拟 | [12.4](part12-job-track/12.4-llm-system-design-mock/README.md) | 清单 + 产物 | 8h |
| J5 | 限时 take-home 模拟 | [12.5](part12-job-track/12.5-take-home-sim/README.md) | 任务书 + 离线检查器 | 12h |
| J6 | 行为面故事 | [12.6](part12-job-track/12.6-behavioral-stories/README.md) | 清单 + 产物 | 3h |
| J7 | 投递与漏斗 | [12.7](part12-job-track/12.7-applications-funnel/README.md) | 清单 + 产物 | 5h |
选修与降级的章节（1.6、4.9、4.13、5.6、6.2、8.x、9.x、10.x 中未列入主线的章节）见 [outline.md 第 5 节](../docs/v3/outline.md#5-选修与降级)；它们保留原有的上一章/下一章链接，不在上表的顺序里。

## v2 路径速查（历史）

v2 路径是 v3 之前的路线，保留作历史参考。各章 README 里 `v2 路径` 与 `v3 路径` 两行并存，**以 `v3 路径` 和上面的“v3 路线速查”为准**；下表的 `v2 路径` 编号与 v3 编号不同。

| v2 阶段 | 对应章节 | 定位 |
|---|---|---|
| L0 定位与基线 | 0.1–0.2 | 核心 |
| L1 模型调用与 Harness | 1.1–1.8、2.5 | 核心；1.1–1.5、1.8、2.5 是 Gate |
| L2 RAG 与上下文 | 2.1–2.11（全部 Gate；2.5 归 L1） | 核心；2.11 多模态部分选做 |
| L3 评测与质量 | 3.1–3.10 | 核心；3.1–3.5、3.7、3.10 已 Gate，3.6 清单，3.9 建议放到 4.10 后学 |
| L4 Agent 与工作流 | 4.1–4.15、3.9 | 核心；4.1–4.12、4.14、3.9 已 Gate，4.13 选做 |
| L5 服务化与生产 | 5.1–5.8、6.1 | 核心；5.1–5.5、5.7、5.8 已 Gate，5.6 选做 |
| L6 项目与求职 | 7.8、capstone | 项目与求职 |
| 选修专项 | 6.2、8.x、9.x、10.x | 选做；8.5/8.6/8.9/9.5 可作核心阅读 |

跨篇顺序以 `v2 路径` 为准，不要只看目录号：

- **2.4 / 2.5**：先学 2.5（L1.6 手写 Harness），再做 2.4（L2.9 评测 Gate）；两者都不依赖对方。
- **3.9**：合成轨迹可先当预习，真正做轨迹评测放在 4.10/4.11 之后。
- **5.2**：先通过 5.1 的 Gate，再读 5.2 的 jitter、主备切换和真实成本。
- **9.1 / 10.1**：`前置` 里的 8.10 / 9.12 是**运行累积代码**的还原顺序，不是学习前置；不想跑整条线时，可直接读概念，不必先做完整条选修线。

## 怎样运行

从仓库根目录运行。第 0–6 篇的独立脚本统一用：

```bash
python tools/run_chapter.py 1.1                    # 章节里只有一个脚本时，只写章节号
python tools/run_chapter.py 2.1 load_split.py      # 有多个脚本时，指定文件名
python tools/run_chapter.py 3.7 --no-upload        # 章节号（和脚本名）之后的参数原样传给脚本
```

- 入口会设置共享的导入路径，并把工作目录切到本章目录：脚本生成的文件（数据库、向量库、日志）都留在本章目录。
- 多章共用的资料放在 [shared-data](shared-data/README.md)（示例文档、评测集），路径由根目录的 `common.py` 提供，与工作目录无关。
- 第 7 篇和第 8–10 篇是累积项目，用 `tools/materialize.py` 还原成完整快照再运行，见各篇 README。
- 第 11、12 篇（项目主线与就业轨道）的章节多数**没有可运行的脚本**：它们是指南、清单与模板。有脚本的只有两处：12.3 的 `drill/check_drill.py` 与 12.5 的 `checkers/check_a.py`、`check_b.py`、`check_c.py`，按各章 README 里的命令直接用 `python` 运行，不经过 `tools/run_chapter.py`。11.5 的 `example_static/` 是静态页面，由你的 FastAPI 服务提供。
- 依赖：`python -m pip install -r requirements-course.txt`；先运行 `python tools/run_chapter.py 0.1` 自检，缺哪一篇的依赖会直接列出。

“运行环境”一列说明该章需要什么（该列主要写于 v2 时期；v3 之后许多参考实现默认离线、加 `--live` 才调用真实模型，以各章 README 的运行说明为准；“v2 Lx”前缀表示该章是选修或核心阅读，沿用 v2 编号，与 v3 编号不同）：**离线**不需要密钥或模型；**真实模型**需要 `DEEPSEEK_API_KEY` 并会产生少量费用；**本地 embedding** 需要下载 BGE 模型（见根目录 README“准备本地 embedding 模型”）。

## 怎样记录

每章有一份 `workbook.md`（学习记录）：先写预测，再运行，最后填实际结果、失败情形和未验证的部分。真实模型、离线替身、远端服务和部署结果要分别记录。方法见 [0.2](part0-setup/0.2-learning-workflow/README.md)。


## 第 0 篇：启程准备

先确认环境，再建立记录问题、过程和证据的方法。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 0.1 | [环境与离线自检（清单）](part0-setup/0.1-environment/README.md) | 清单验收 |
| 0.2 | [学习方法与验收记录（清单）](part0-setup/0.2-learning-workflow/README.md) | 清单验收 |
| 0.3 | [L0.3 用编码 Agent 开发与审查（清单）](part0-setup/0.3-coding-agent-workflow/README.md) | 清单验收 |
| 0.4 | [L0.4 AI 应用的 Python 工程底座（Gate）](part0-setup/0.4-python-engineering-base/README.md) | 离线 gate |
| 0.5 | [L0.5 岗位地图与差距诊断（清单）](part0-setup/0.5-job-map-gap/README.md) | 清单验收 |

## 第 1 篇：模型调用与上下文基础

从一次请求往返出发，依次理解输出、结构、历史与工具，最后组合成对话练习。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 1.1 | [L1.1 一次调用（Gate）](part1-foundations/1.1-first-call/README.md) | 离线 gate；live 运行方式见 README |
| 1.2 | [L1.3 输出控制（Gate）](part1-foundations/1.2-control-output/README.md) | 离线 gate；live 运行方式见 README |
| 1.3 | [L1.4 结构化输出（Gate）](part1-foundations/1.3-structured-output/README.md) | 离线 gate；live 运行方式见 README |
| 1.4 | [L1.5 上下文与记忆（Gate）](part1-foundations/1.4-context-memory/README.md) | 离线 gate；live 运行方式见 README |
| 1.5 | [L1.6 工具调用（Gate）](part1-foundations/1.5-tool-calling/README.md) | 离线 gate；live 运行方式见 README |
| 1.6 | [MCP 入门（清单）](part1-foundations/1.6-mcp-intro/README.md) | 清单验收 |
| 1.7 | [LLM 原理认知（清单）](part1-foundations/1.7-llm-internals/README.md) | 清单验收 |
| 1.8 | [L1.9 CLI 助手（Gate）](part1-foundations/1.8-cli-chatbot/README.md) | 离线 gate；live 运行方式见 README |
| 1.9 | [L1.7 Provider 抽象、第二厂商与成本（Gate）](part1-foundations/1.9-provider-cost/README.md) | 离线 gate |
| 1.10 | [L1.10 嵌入式 LLM 功能与 eval harness（Gate）](part1-foundations/1.10-embedded-llm-feature/README.md) | 离线 gate |

## 第 2 篇：检索增强生成 RAG

先把资料读对并找到证据，再组织回答。每次增加切分、融合、改写或重排，都保留固定问题作比较。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 2.1 | [L2.2 加载与切分（Gate）](part2-rag/2.1-load-split/README.md) | 离线 gate；参考实现离线 |
| 2.2 | [L2.3 向量化与召回（Gate）](part2-rag/2.2-embed-retrieve/README.md) | 离线 gate；参考实现需本地 embedding |
| 2.3 | [L2.4 最小 RAG（Gate）](part2-rag/2.3-minimal-rag/README.md) | 离线 gate；live 与 embedding 运行方式见 README |
| 2.4 | [L2.11 RAG 评测基线（Gate）](part2-rag/2.4-eval-seed/README.md) | 离线 gate |
| 2.5 | [L1.8 手写 Harness（Gate）](part2-rag/2.5-raw-sdk-rag-agent-loop/README.md) | 离线 gate，参考实现可选真实模型 |
| 2.6 | [L2.2 扩展：PDF 与来源（Gate）](part2-rag/2.6-pdf-sources/README.md) | 离线 gate；live 与 embedding 运行方式见 README |
| 2.7 | [L2.5 切分策略（Gate）](part2-rag/2.7-chunk-strategy/README.md) | 离线 gate；参考实现需本地 embedding |
| 2.8 | [L2.6 混合检索（Gate）](part2-rag/2.8-hybrid-search/README.md) | 离线 gate；参考实现需本地 embedding |
| 2.9 | [L2.7 查询改写（Gate）](part2-rag/2.9-query-rewrite/README.md) | 离线 gate；live 与 embedding 运行方式见 README |
| 2.10 | [L2.8 向量库持久化（Gate）](part2-rag/2.10-chroma-persist/README.md) | 离线 gate；参考实现需本地 embedding |
| 2.11 | [L2.6 重排与多模态（Gate）](part2-rag/2.11-multimodal-rerank/README.md) | 离线 gate；参考实现需 reranker，多模态选做 |
| 2.12 | [L2.1 上下文工程总论（Gate）](part2-rag/2.12-context-engineering/README.md) | 离线 gate |
| 2.13 | [L2.9 静态上下文与 Skills（Gate）](part2-rag/2.13-static-context-skills/README.md) | 离线 gate |
| 2.14 | [L2.10 记忆与压缩（Gate）](part2-rag/2.14-memory-compaction/README.md) | 离线 gate |
| 2.15 | [L2.12 Gate：真实资料知识库 v1（Gate）](part2-rag/2.15-real-corpus-kb-gate/README.md) | 离线 gate |

## 第 3 篇：评测方法论

从失败过程与小题集出发，理解规则、模型评委、数据工程和回归对比，把分数转成有证据的改动。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 3.1 | [L3.1 失败分析（Gate）](part3-evals/3.1-error-analysis/README.md) | 离线 gate |
| 3.2 | [L3.3 基础评测（Gate）](part3-evals/3.2-eval-basics/README.md) | 离线 gate；live 运行方式见 README |
| 3.3 | [L3.4 LLM Judge 与校准（Gate）](part3-evals/3.3-llm-judge/README.md) | 离线 gate，参考实现可选真实模型 |
| 3.4 | [L3.2 评测集建设（Gate）](part3-evals/3.4-eval-dataset-build/README.md) | 离线 gate |
| 3.5 | [L3.5 Ragas 与指标口径（Gate）](part3-evals/3.5-eval-dataset-ragas/README.md) | 离线 gate；参考实现 RAGAS 需真实模型 |
| 3.6 | [L3.7 LangSmith 可观测性（清单）](part3-evals/3.6-langsmith-eval/README.md) | 外部服务，清单验收 |
| 3.7 | [L3.6 回归对比（Gate）](part3-evals/3.7-eval-regression-curve/README.md) | 离线 gate；live 运行方式见 README |
| 3.8 | [L3.6 扩展：Prompt A/B 指标（Gate）](part3-evals/3.8-prompt-ab-judge/README.md) | 离线 gate；真实 A/B 需模型 |
| 3.9 | [L4.7 Agent 轨迹评测（Gate）](part3-evals/3.9-agent-trajectory-eval/README.md) | 离线 gate |
| 3.10 | [L3.6 扩展：失败诊断（Gate）](part3-evals/3.10-eval-report-failures/README.md) | 离线 gate；live 模式需真实模型 |

## 第 4 篇：Agent 与 LangGraph

先判断是否需要模型决策，再学习状态、节点、分支、合并、恢复与协作。每个循环都要说明失败和终止。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 4.1 | [L4.1 Agent 模式（Gate）](part4-agents-langgraph/4.1-agent-patterns/README.md) | 离线 gate |
| 4.2 | [L4.9 LangGraph 基础（Gate）](part4-agents-langgraph/4.2-langgraph-basics/README.md) | 离线 gate |
| 4.3 | [L4.9 分支与循环（Gate）](part4-agents-langgraph/4.3-branch-loop/README.md) | 离线 gate；参考实现后半段需真实模型 |
| 4.4 | [L4.9 状态与 Reducer（Gate）](part4-agents-langgraph/4.4-state-reducer/README.md) | 离线 gate |
| 4.5 | [L4.2 ReAct 与工具设计（Gate）](part4-agents-langgraph/4.5-react-agent/README.md) | 离线 gate，参考实现可选真实模型 |
| 4.6 | [L4.9 扩展：节点可靠性（Gate）](part4-agents-langgraph/4.6-node-reliability/README.md) | 离线 gate；参考实现一处需真实模型 |
| 4.7 | [L4.4 结构化路由（Gate）](part4-agents-langgraph/4.7-structured-routing/README.md) | 离线 gate；live 运行方式见 README |
| 4.8 | [L4.4 扩展：规划与执行（Gate）](part4-agents-langgraph/4.8-plan-and-execute/README.md) | 离线 gate；live 运行方式见 README |
| 4.9 | [v2 L5.6 可观测性（Gate）](part4-agents-langgraph/4.9-observability/README.md) | 离线 gate |
| 4.10 | [L4.10 检查点与上下文（Gate）](part4-agents-langgraph/4.10-checkpoint-context/README.md) | 离线 gate；live 运行方式见 README |
| 4.11 | [L4.10 流式与人工介入（Gate）](part4-agents-langgraph/4.11-streaming-hitl/README.md) | 离线 gate |
| 4.12 | [L4.13 搜索信任边界（Gate）](part4-agents-langgraph/4.12-tool-safety-search/README.md) | 离线 gate；live 运行方式见 README |
| 4.13 | [v2 L4.12 Text2SQL 安全门（Gate）](part4-agents-langgraph/4.13-text2sql-agent/README.md) | 离线 gate |
| 4.14 | [L4.6 Supervisor 与并行（Gate）](part4-agents-langgraph/4.14-supervisor-fanout/README.md) | 离线 gate；live 运行方式见 README |
| 4.15 | [框架取舍（清单）](part4-agents-langgraph/4.15-framework-landscape/README.md) | 清单验收 |
| 4.16 | [L4.5 用 Pydantic AI 写 Agent（Gate）](part4-agents-langgraph/4.16-pydantic-ai-agent/README.md) | 离线 gate |
| 4.17 | [L4.8 Gate：原生版与 SDK 版（Gate）](part4-agents-langgraph/4.17-native-vs-sdk-gate/README.md) | 离线 gate |
| 4.18 | [L4.3 工具设计（Gate）](part4-agents-langgraph/4.18-tool-design/README.md) | 离线 gate |
| 4.19 | [L4.11 专项 Agent 执行面（Gate）](part4-agents-langgraph/4.19-agent-execution-plane/README.md) | 离线 gate |
| 4.20 | [L4.12 沙箱与最小权限（Gate）](part4-agents-langgraph/4.20-sandbox-least-privilege/README.md) | 离线 gate |
| 4.21 | [L4.14 MCP 实战与取舍（Gate）](part4-agents-langgraph/4.21-mcp-practice/README.md) | 离线 gate |
| 4.22 | [L4.15 复用现成 harness（清单）](part4-agents-langgraph/4.22-reuse-harness/README.md) | 清单验收 |
| 4.23 | [L4.17 Gate：异步专项 Agent（Gate）](part4-agents-langgraph/4.23-async-agent-gate/README.md) | 离线 gate |

## 第 5 篇：服务化与工程可靠性

把脚本推进到接口、持久化、可观测与回归，逐项理解真实服务需要的边界。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 5.1 | [L5.1 FastAPI 服务与可靠性（Gate）](part5-production/5.1-serve-fastapi/README.md) | 离线 gate；live 运行方式见 README |
| 5.2 | [L5.1 可靠性：退避/重试/成本（Gate）](part5-production/5.2-reliability-retry/README.md) | 离线 gate；live 运行方式见 README |
| 5.3 | [L5.2 扩展：成本/缓存/路由（Gate）](part5-production/5.3-cost-cache-routing/README.md) | 离线 gate；live 运行方式见 README |
| 5.4 | [L5.3 SQLite 持久化（Gate）](part5-production/5.4-sqlite-persistence/README.md) | 离线 gate |
| 5.5 | [L5.8 容器与配置（Gate）](part5-production/5.5-docker-packaging/README.md) | 离线 gate；真实构建需 Docker |
| 5.6 | [调用日志与 Ollama 本地推理（清单）](part5-production/5.6-ollama-inference/README.md) | 清单验收（外部服务） |
| 5.7 | [L5.5 安全护栏（Gate）](part5-production/5.7-security-guardrails/README.md) | 离线 gate |
| 5.8 | [L3.3 扩展：pytest 回归（Gate）](part5-production/5.8-pytest-regression/README.md) | 离线 gate；真实回归需模型 |
| 5.9 | [L5.6 可观测性：OpenTelemetry（Gate）](part5-production/5.9-otel-observability/README.md) | 离线 gate；可选 OTLP 后端 |
| 5.10 | [L5.7 控制面与执行面集成（Gate）](part5-production/5.10-control-execution-plane/README.md) | 离线 gate |
| 5.11 | [L5.8 容器、CI 评测门禁与云部署（清单）](part5-production/5.11-cloud-deploy/README.md) | 清单验收；需要云账号或 VPS，可能产生费用 |
| 5.12 | [L5.9 容量、SLO 与恢复（Gate）](part5-production/5.12-capacity-slo-recovery/README.md) | 离线 gate |
| 5.13 | [L5.10 托管运行时取舍（清单）](part5-production/5.13-managed-runtime-tradeoffs/README.md) | 清单验收 |
| 5.14 | [L5.11 LLM 系统设计（清单）](part5-production/5.14-llm-system-design/README.md) | 清单验收 |
| 5.15 | [L5.4 认证、授权与多租户（清单）](part5-production/5.15-auth-multitenancy/README.md) | 清单验收 |

## 第 6 篇：模型方案取舍

从问题原因选择 Prompt、RAG 或微调；LoRA 实操按硬件和数据条件选做。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 6.1 | [L5.12 方案选型（Gate）](part6-model-tradeoffs/6.1-choose-prompt-rag-finetune/README.md) | 离线 gate |
| 6.2 | [v2 L6 LoRA 质量门禁（Gate）](part6-model-tradeoffs/6.2-lora-finetune-optional/README.md) | 离线 gate；真实训练需重依赖 |

## 第 7 篇：企业客服 Copilot（已冻结，历史快照）

[进入 8 个里程碑的项目教程](../flagship-project/README.md)（基于 LangChain 1.x 的历史教学快照，2026-10-27 冻结，不再修改）。29 个步骤连续完善同一个业务：先还原完整快照，再核对累计测试。它对应的目录是仓库根目录下的 `flagship-project/`，不在 `chapters/` 里。[capstone](../capstone/README.md) 是另一个能力整合实现，两者分别验收。

## 第 8 篇：AI 质量工程专项（选修）

将测试背景转化为风险、数据、契约、检索、轨迹和发布门禁能力。这是一条独立累积的测试工具项目线。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 8.1 | [v2 L8 风险建模（Gate）](part8-ai-quality-optional/8.1-risk-modeling/README.md) | 离线 gate |
| 8.2 | [v2 L8 评测数据工程（Gate）](part8-ai-quality-optional/8.2-eval-data-engineering/README.md) | 离线 gate |
| 8.3 | [v2 L8 契约与不变量（Gate）](part8-ai-quality-optional/8.3-mock-contract-invariant/README.md) | 离线 gate |
| 8.4 | [v2 L8 RAG 分层检索评测（Gate）](part8-ai-quality-optional/8.4-rag-layered-testing/README.md) | 离线 gate |
| 8.5 | [v2 L3.4 扩展：Judge 校准（Gate）](part8-ai-quality-optional/8.5-judge-calibration/README.md) | 离线 gate |
| 8.6 | [v2 L4.11 扩展：Agent 轨迹测试（Gate）](part8-ai-quality-optional/8.6-agent-trajectory-testing/README.md) | 离线 gate |
| 8.7 | [v2 L8 API/SSE E2E（Gate）](part8-ai-quality-optional/8.7-api-sse-e2e/README.md) | 离线 gate |
| 8.8 | [v2 L8 安全/韧性/性能（Gate）](part8-ai-quality-optional/8.8-security-resilience-perf/README.md) | 离线 gate |
| 8.9 | [v2 L5.7 扩展：CI 分层门禁（Gate）](part8-ai-quality-optional/8.9-ci-layered-gate/README.md) | 离线 gate |
| 8.10 | [v2 L3.7 反馈闭环（Gate）](part8-ai-quality-optional/8.10-production-feedback-loop/README.md) | 离线 gate |

## 第 9 篇：企业数据与推理设施专项（选修）

建立意图与会话契约，再理解数据库隔离、缓存、检索后端和推理服务。外部依赖的真实验证另记。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 9.1 | [v2 L9 Few-shot 意图识别（Gate）](part9-enterprise-infra-optional/9.1-intent-fewshot/README.md) | 离线 gate |
| 9.2 | [v2 L9 槽位填充（Gate）](part9-enterprise-infra-optional/9.2-slot-filling/README.md) | 离线 gate |
| 9.3 | [v2 L9 稳定 JSON 契约（Gate）](part9-enterprise-infra-optional/9.3-stable-json-output/README.md) | 离线 gate |
| 9.4 | [v2 L9 意图工作流（Gate）](part9-enterprise-infra-optional/9.4-intent-workflow/README.md) | 离线 gate |
| 9.5 | [v2 L5.4 扩展：Postgres 与 RLS（Gate）](part9-enterprise-infra-optional/9.5-postgres-rls/README.md) | 离线 gate |
| 9.6 | [v2 L9 只读 SQL 护栏（Gate）](part9-enterprise-infra-optional/9.6-readonly-sql-explain/README.md) | 离线 gate |
| 9.7 | [v2 L5.2 扩展：Redis 缓存/限流（Gate）](part9-enterprise-infra-optional/9.7-redis-cache-ratelimit/README.md) | 离线 gate |
| 9.8 | [v2 L9 向量存储选型（Gate）](part9-enterprise-infra-optional/9.8-vectorstore-selection/README.md) | 离线 gate |
| 9.9 | [v2 L9 Compose 与运维（Gate）](part9-enterprise-infra-optional/9.9-compose-linux-ops/README.md) | 离线 gate |
| 9.10 | [v2 L5.10 兼容模型配置（Gate）](part9-enterprise-infra-optional/9.10-openai-compatible-provider/README.md) | 离线 gate |
| 9.11 | [v2 L9 vLLM 启动配置（Gate）](part9-enterprise-infra-optional/9.11-vllm-gpu/README.md) | 离线 gate |
| 9.12 | [v2 L5.8 扩展：推理基准（Gate）](part9-enterprise-infra-optional/9.12-inference-benchmark/README.md) | 离线 gate |

## 第 10 篇：MCP 鉴权与 A2A（选修）

从可信工具授权走向独立 Agent 的任务协作，区分协议模型、离线测试与真实远端互操作。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 10.1 | [v2 L4.9 MCP 授权与审批（Gate）](part10-mcp-a2a-optional/10.1-mcp-auth-approval/README.md) | 离线 gate |
| 10.2 | [v2 L10 A2A 任务生命周期（Gate）](part10-mcp-a2a-optional/10.2-a2a-agent-card-task/README.md) | 离线 gate |
| 10.3 | [v2 L10 A2A JSON-RPC 绑定（Gate）](part10-mcp-a2a-optional/10.3-a2a-protocol-bindings/README.md) | 离线 gate |
| 10.4 | [v2 L10 跨 Agent 委派（Gate）](part10-mcp-a2a-optional/10.4-cross-agent-delegation/README.md) | 离线 gate |

## 第 11 篇：项目主线（P）

从第 5 周起把各阶段产出持续并入同一个公开项目，积累真实用量与证据。指南、清单与模板为主，没有 gate。篇首 [README](part11-project-sprint/README.md) 有 E1 主作品的完整要求与排期。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 11.1 | [P1 需求与指标（清单）](part11-project-sprint/11.1-requirements-metrics/README.md) | 清单验收 |
| 11.2 | [P2 最小上线（清单）](part11-project-sprint/11.2-walking-skeleton-deploy/README.md) | 清单验收；需要 VPS 或云账号，可能产生费用 |
| 11.3 | [P3 迭代 1：控制面加固（清单）](part11-project-sprint/11.3-control-plane-hardening/README.md) | 清单验收 |
| 11.4 | [P4 迭代 2：执行面与真实证据（清单）](part11-project-sprint/11.4-execution-plane-launch/README.md) | 清单验收；真实模型评测会产生费用 |
| 11.5 | [P5 可演示前端（清单）](part11-project-sprint/11.5-demo-web-ui/README.md) | 清单验收；静态页示例 |
| 11.6 | [P6 项目叙事与证据索引（清单）](part11-project-sprint/11.6-project-narrative/README.md) | 清单验收 |

## 第 12 篇：就业轨道（J）

第 3–16 周同步训练面试形式与求职材料。篇首 [README](part12-job-track/README.md) 有每周节奏。市场与面试信息会过期，各章已注明来源、读取日期与性质。

| 章节 | 文字教程 | 运行环境 |
|---|---|---|
| 12.1 | [J1 定位与三版简历（清单）](part12-job-track/12.1-positioning-resume/README.md) | 清单验收 |
| 12.2 | [J2 公开作品节奏（清单）](part12-job-track/12.2-public-portfolio-cadence/README.md) | 清单验收 |
| 12.3 | [J3 编码面试与 AI 辅助编码（演练）](part12-job-track/12.3-coding-interview/README.md) | 清单验收；离线演练检查脚本 |
| 12.4 | [J4 LLM 系统设计模拟（清单）](part12-job-track/12.4-llm-system-design-mock/README.md) | 清单验收 |
| 12.5 | [J5 限时 take-home 模拟（演练）](part12-job-track/12.5-take-home-sim/README.md) | 离线检查器（假模型，不联网） |
| 12.6 | [J6 行为面故事（清单）](part12-job-track/12.6-behavioral-stories/README.md) | 清单验收 |
| 12.7 | [J7 投递与漏斗（清单）](part12-job-track/12.7-applications-funnel/README.md) | 清单验收 |

## 选修与后续怎么选

- 想把测试经验转成 AI 质量工程能力：第 8 篇。
- 想补企业级数据、缓存、检索后端和推理服务：第 9 篇。
- 想了解 MCP 鉴权和 Agent 之间的协作：第 10 篇。
