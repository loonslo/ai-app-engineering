# V3-9 capstone 验证 · 2026-10-31

本批次改了什么：`capstone/` 主链路去掉 LangChain；接入 OpenTelemetry；新增零依赖静态演示前端与反馈接口；简历与面试文档的措辞对齐代码；新增 ADR-002。对外行为与 HTTP 契约不变，响应新增可选字段 `degraded`（默认 `false`）。没改 `flagship-project/`，没改 `.github/workflows/eval-gate.yml`。

实施线程额度用完，由审核者亲自实施并复跑，没有实施与审核的分离。

## 范围

| 文件 | 改动 |
|---|---|
| `contracts.py` | 新增 `Document` dataclass；`AssistResult` 增加 `degraded` |
| `text_split.py`（新） | 原生递归字符切分 |
| `embedding.py`（新） | 对 `common.embed_texts` 的薄封装 |
| `vector_store.py`（新） | 原生 Chroma 封装（`add_documents` / `similarity_search` / `delete` / `reset`） |
| `llm.py`（新） | `ChatClient`：原生 openai 客户端、20 秒超时、4 次带抖动重试、可选备用模型（`degraded`） |
| `telemetry.py`（新） | 检索、模型调用、工具调用 span；usage 与错误类型；不采集正文；`configure_tracing()` |
| `knowledge_base.py` | 去掉 LCEL、`langchain_chroma`、切分器与 `Document`；`chain()` 改为返回普通函数；`SOURCE_VERSION_SCHEMA` 升到 `source-v3` |
| `connector.py`、`context.py`、`permissions.py` | 换用原生切分、向量库与 `Document`；`permission_chain` 改为普通函数 |
| `vector_store_pg.py` | 去掉 `langchain-postgres`，改为 psycopg 直接执行 SQL（含 where→SQL 翻译与迁移模板） |
| `config.py`、`provider_contract.py` | 不再导出 `get_llm`/`get_reliable_llm`；`validate_settings` 明确报出 Bedrock 直连不再支持 |
| `service.py`、`api_enterprise.py` | 工具调用 span；降级答案不进缓存；`degraded` 字段；`POST /v1/feedback`；`/ui` 静态页；启动时 `configure_tracing()` |
| `static/index.html`、`static/app.js`（新） | 零依赖演示前端 |
| `test_production.py` | 34 → 43 项：新增切分、重试与备用模型、原生 Chroma 的 ACL 预过滤、pgvector SQL、span（含错误只记类型）、工具 span 与降级不缓存、反馈接口与静态页 |
| `docs/portfolio/*`、`README.md`、`docs/adr/002-…` | 对齐措辞；见下 |
| `requirements*.txt` | `requirements.txt` 增加 `openai`、`opentelemetry-api`（capstone 直接导入）；`requirements-pgvector.txt` 去掉 `langchain-postgres`；`requirements-bedrock.txt` 加注释 |

## 文档对齐（任务 4）

逐条核对 `docs/portfolio/` 与 `README.md`，改动如下：

- `resume_evidence.md`：去掉“去黑盒化解耦”“MCP 协议规范”等对不上代码的说法；主链路已无 LangChain 导入的措辞改为可验证的描述，并注明 `flagship-project/` 另当别论；34 项测试与 35% 的数字标注为 2026-10-26 的数据；MCP 只列为章节练习。
- `project_pitch.md`：Agent 部分原写“LangGraph 人工审批中断”，capstone 实际是 `approval.py` 状态机，已改；补充 OTel 与静态页；34 项测试的数字标注为当时的数据。
- `enterprise_interview.md`：`common.get_reliable_llm()` 改为 `ChatClient` 的实际行为；补充备用模型与 Bedrock 的变化。
- `rag_agent_interview.md`：原写“项目的 HITL 演示使用 InMemorySaver”，capstone 实际是 SQLite 持久化审批，已改并注明 `InMemorySaver` 属于冻结的 flagship 快照。
- 细则提到的“调用栈从 15 层降到 2 层”：全仓库文档里搜索不到这句话（`15 层`、`调用栈`、`去黑盒` 均无命中，仅 `resume_evidence.md` 中一处“去黑盒化解耦”已改），没有需要删除的同名数字。
- “尚未部署、没有真实用户”的表述保持原样。

## 实际执行

| # | 命令 | 结果 |
|---|---|---|
| 1 | `pytest capstone/test_production.py -q` | 43 passed（原 34 + 新增 9） |
| 2 | `pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py capstone --deselect capstone/test_regression.py -q` | 151 passed |
| 3 | `python -m capstone.milestones --strict-evidence` | 通过 |
| 4 | `python -m capstone.project_baseline --json` | 通过 |
| 5 | `python -m capstone.evidence_audit` | 无 FAIL（仍有“0 个截图/GIF 证据”的 WARN，属实） |
| 6 | `python -m capstone.interview_evidence --strict-evidence` | 通过 |
| 7 | `python -m capstone.load_test --fake --users 2 --spawn-rate 2 --time 5s --upstream-ms 50` | 压测本身正常（0 失败）；**进程以 PermissionError 退出**：Windows 上清理临时目录时 `metrics.db` 仍被占用。在 master 的干净工作树上复现同样的错误，属于既有问题，本批次没有处理 |
| 8 | `ruff check --target-version py311 capstone tools chapters/test_v3_lessons.py` | 通过 |
| 9 | `git grep -nE "^\s*(from|import) (langchain|langgraph)" -- capstone` | 无输出（含函数内延迟导入） |
| 10 | 原生切分器对照 LangChain `RecursiveCharacterTextSplitter` | 仓库 55 篇 Markdown × 3 组参数 = 165 例，逐块完全一致（一次性对比，未入库） |
| 11 | 真实栈冒烟：本地 embedding + 原生 Chroma 建库（86 个块），再次打开后数量一致；DeepSeek 回答带来源 | 通过 |
| 12 | `pytest capstone/test_regression.py -v`（DeepSeek `deepseek-flash`，2026-10-31，会产生少量费用） | 6 passed |
| 13 | `python -m capstone.main eval`（同上模型） | 拒答 2/2、关键词 4/4、引用 4/4、失败 0，与 `project_pitch.md` 里记录的 4/4、2/2、0 一致 |
| 14 | 前端：启动真实 `api_enterprise`（开发登录），无头 Chromium 里：开发登录换令牌 → 提问（真实模型）→ 引用列表 → 提交“有用” → 坏令牌得到“未登录或令牌无效”的可读错误 | 全部符合；截图已看过 |

## 细则偏离

- `vector_store_pg.py` 的改写完成，但**没有在真实 Postgres + pgvector 上运行**，只有假连接的离线测试；细则允许工作量过大时说明，这里选择了实现并如实标注。
- `chain()` 原返回 LCEL 可运行对象（有 `.invoke`），现返回普通函数 `ask(question)`；仓库里没有其他调用点，文档与 `permission_chain` 已同步。
- Bedrock 直连不再支持（OpenAI 客户端不能直连）；`validate_settings` 会明确报出，ADR-002 已写明替代方案。
- 新增 `POST /v1/feedback`：细则要求前端有“反馈按钮”，capstone 原本没有对应接口，这里补了一个只存请求 ID、评分、脱敏短评与用户指纹的最小实现。

## 未验证

- 真实 Postgres + pgvector；OTLP 后端的真实发送（只测了内存导出器，`CAPSTONE_OTEL=console` 在冒烟启动时设置过但没有检查输出）。
- 旧的本地 Chroma 目录迁移：设计上是重建，没有对“已有索引的升级”做演练。
- 备用模型路径只在假客户端上验证过，没有真实触发主模型故障。
- 静态前端没有移动端、无障碍和自动化前端测试。
- 没有部署、没有真实用户；简历文档里的“尚未”表述保持不变。
