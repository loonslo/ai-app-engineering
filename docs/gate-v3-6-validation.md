# V3-6 L5 服务化与生产验证 · 2026-10-31

本批次改了什么：按 `docs/v3/specs/L5.md` 把 5.1、5.2、5.3 换成原生 openai SDK 实现；给 5.3、5.7 的 gate 追加检查；新增 5.9（OpenTelemetry）、5.10（控制面与执行面）、5.12（容量、SLO 与恢复）三个 gate 章，以及 5.11、5.13、5.14、5.15 四个清单章；给 6.1 README 增补。没改 `flagship-project/`，没改 5.1、5.2 的 gate，没改 5.4、5.5、5.6、5.8（L5.3 与 L5.8 的保留部分只待 V3-10 加标签）。

实施线程因额度用完无法继续，本批次由审核者（我）亲自实施并复跑，所以没有“实施者与审核者分离”的独立性；复核请以第 3 节命令为准。

## 1. 范围

| v3 编号 | 目录 | 类型 | 主要改动 |
|---|---|---|---|
| L5.1 | `5.1-serve-fastapi`、`5.2-reliability-retry` | 换实现 | 去掉 LangChain；`reliability.py` 重写为原生客户端 + 带抖动的退避重试（含 Retry-After、降级）；`serve_fastapi.py` 改用原生客户端并新增 SSE `/chat/stream`；README 增补限流（429）与 Datadog 数据 |
| L5.2 | `5.3-cost-cache-routing` | 换实现 + 增补 | 原生客户端；离线默认、`--live` 调真实模型；新增 `cost_with_cache`、`schedule_batch`；gate 原 4 项 + 新增 5 项；README 增补计价与低峰调度 |
| L5.4 | `5.15-auth-multitenancy` | 新增 · 清单 | README、CHECKLIST、`templates/threat-model.md`、workbook |
| L5.5 | `5.7-security-guardrails` | 增补 | 新增 `audit_record`、`label_ai_content`；gate 原 7 项 + 新增 4 项；README 增补治理；参考实现补充非字符串校验 |
| L5.6 | `5.9-otel-observability` | 新增 · gate | 13 项 gate；参考实现为脚本化的 RAG + 工具调用打点 |
| L5.7 | `5.10-control-execution-plane` | 新增 · gate | 14 项 gate；参考实现导入 4.19 执行面，线程 worker + 假 webhook |
| L5.8 | `5.11-cloud-deploy`（5.5 保留） | 新增 · 清单 | README、CHECKLIST、`templates/deploy-record.md`、workbook |
| L5.9 | `5.12-capacity-slo-recovery` | 新增 · gate | 12 项 gate；参考实现读 `reports/loadtest_*.json` |
| L5.10 | `5.13-managed-runtime-tradeoffs` | 新增 · 清单 | README（6 个运行时的核对表）、CHECKLIST、workbook |
| L5.11 | `5.14-llm-system-design` | 新增 · 清单 | README、`templates/design-doc.md`、`templates/rubric.md`、CHECKLIST、workbook |
| L5.12 | `6.1-choose-prompt-rag-finetune` | 增补 | README 增补决策顺序、各方法、小模型；gate 与参考实现不变 |

另改：`tools/course_catalog.py`（登记 5.9–5.15）、`chapters/test_v3_lessons.py`（新增 7 项离线测试）、`requirements-course.txt`（注释可选的 OTLP 导出器）。

## 2. 外部出处核对（均于 2026-10-31 读取）

| 内容 | 实际读到的 | 与细则的差异 |
|---|---|---|
| Datadog State of AI Engineering 2026 | 2026 年 2 月 5% 的 LLM span 报错，其中 60% 为限流；3 月报错占比 2%，限流近三分之一 | 细则只写“60% 由限流引起”；README 写明是 2 月数据并补充 3 月，并注明样本偏向其客户 |
| DeepSeek 官方定价页 | 区分高峰/低峰，低峰价为高峰价一半；高峰为周一至周五（不含中国法定节假日）UTC 01–04 与 06–10 | 细则写“2026-08 起实行”；官方页未写起始日期，README 没有写该日期，只写页面当前内容 |
| EU AI Act | White & Case（2026-08-04）：AI Omnibus 2026-07-27 生效；Art.50 大部分透明度义务自 2026-08-02 适用；Annex III 高风险推迟到 2027-12-02，Annex I 到 2028-08-02；已上市生成式系统的水印义务宽限到 2026-12-02 | 与细则一致，并补充了水印宽限期与 Annex I |
| 技术雷达 Vol.34 | Role-based contextual isolation in RAG：Assess；Small language models：Assess | 与细则一致 |
| RFC 8725 | `alg=none`、RS256→HS256、`aud`/`iss` 校验、弱密钥等 | 密钥轮换不在 RFC 8725 中逐条规定，README 已写明这是通行做法、以平台文档为准 |
| 托管运行时 | OpenAI Agents API：2026-09-10 公开测试版；Claude Managed Agents：2026-04-08 公开测试版；LangSmith Managed Deep Agents 文档标 BETA；Foundry、AgentCore、Vertex AI Agent Engine 只核对到文档存在与一句话定位 | 各家数据驻留、地区、价格多数“未核实”，README 逐项标注 |
| W3C Trace Context | REC 2021-11-23 | — |

## 3. 实际执行

环境：Windows，`.venv`，Python 3.14。

| # | 命令 | 结果 |
|---|---|---|
| 1 | 5.2、5.3、5.7、5.9、5.10、5.12 的 `gate_check.py`（默认骨架） | 全部退出 1，0 项通过 |
| 2 | 同上，加 `--module .tmp/gate_solutions/v3/<章>.py` | 5.2 5/5、5.3 9/9、5.7 11/11、5.9 13/13、5.10 14/14、5.12 12/12，退出 0；各连跑两次输出一致 |
| 3 | `pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py capstone/test_regression.py -q` | 110 passed |
| 4 | `tools/check_course_links.py` | 411 篇，0 断链 |
| 5 | `ruff check --target-version py311 chapters/part3-evals chapters/part4-agents-langgraph chapters/part5-production chapters/part6-model-tradeoffs common.py tools chapters/test_v3_lessons.py chapters/test_new_lessons.py` | 通过 |
| 6 | `apply_v2_map.py --check` | 111 unchanged |
| 7 | `apply_v3_map.py --check` | 5.9–5.15 均 unchanged；旧章节 inserted 属 V3-10 前的约定状态 |
| 8 | `git grep` 查 part5 与 6.1 的 LangChain 导入 | 只有 5.6 的 `langchain_ollama`（选修章，在白名单内） |
| 9 | `run_chapter.py` 离线运行 5.2、5.3、5.7、5.9（含 `--capture-content`）、5.10、5.12 | 均退出 0，无堆栈；`--capture-content` 的输出里手机号已被脱敏，默认运行没有正文属性 |
| 10 | `5.2 --live`、`5.3 --live` 模型不可达（`127.0.0.1:9`） | 均退出 1，无堆栈 |
| 11 | `5.2 --live`、`5.3 --live`（DeepSeek `deepseek-flash`，单次） | 均退出 0 |
| 12 | 5.1：用假检索器/假客户端的 TestClient 调 `/chat`、`/chat/stream`、`/stats`；再用真实 lifespan（本地 embedding + DeepSeek）调 `/ready`、`/chat`、`/chat/stream` | 假替身：`/chat` 与 SSE 事件序列 meta→delta→done 正确，数据库记录 2 条；真实栈：`/ready` 就绪、`/chat` 与 `/chat/stream` 返回内容 |

实现中发现并修复：5.7 参考实现的 `scan_input`、`mask_pii` 原先不校验非字符串输入（gate 要求 `ValueError`），已补；5.12 gate 第 4 项的期望值我最初算错（p95 应为 300 而非 5000），已按最近秩法更正。

## 4. 细则偏离

- **目录与编号**：细则中的 L5.x 与实际目录的对应按 `tools/course_catalog.py` / `docs/v3/outline.md`（5.9–5.15）。
- **5.1 的 gate 未复跑参考解**：细则要求不改 5.1 的 gate；其 gate 针对独立的 `create_app(answer_fn, store)` 接口，章节参考实现 `serve_fastapi.py` 是另一种结构（全局 `app`），本来就不互相通过。本批次没有改 gate，也没有为它补临时参考解。
- **5.2 `call_with_retry` 与 gate 的关系**：gate 只检查三个纯函数；参考实现在同名函数之外加了带抖动的重试与降级。
- **5.3 默认改为离线**：原先默认直接调真实模型；按 conventions 第 8 节改为 `--live` 才调用，离线用脚本化假回答。
- **L5.1 的“可以导入 L0.4 的 `retry_async`”没采用**：`retry_async` 没有抖动，5.2 自己实现更贴合“带抖动的退避”。
- **5.9 span 的异常处理**：为了不泄露内容，`record_error` 只记类型；与 V3-3 在 3.6 的做法一致。

## 5. 未验证

- 5.9 的 OTLP 发送路径：没有安装 `opentelemetry-exporter-otlp-proto-http`，也没有连接任何后端；GenAI 语义约定仍是 Development 状态。
- 5.10 的 worker 是同进程线程；没有验证 worker 崩溃恢复、持久队列、并发幂等、真实网络 webhook。
- 5.12 的压测数据来自本地假上游的小样本；没有真实容量数据，没有做真实的备份恢复演练。
- 5.11、5.13、5.14、5.15 是清单章：没有任何真实云部署、没有注册或调用托管运行时、没有写出设计文档；它们的“完成”只能由学习者完成。
- 5.1 的 SSE 没做并发、断线与长连接测试；`/chat/stream` 不在 gate 内。
- 各托管运行时的数据驻留、地区、价格等多数“未核实”，已在 README 中逐项标注。
- 没有在 CI 的 Python 3.11 上实际运行；只做了 `ruff --target-version py311` 静态检查。
