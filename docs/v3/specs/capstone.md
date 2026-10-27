# V3-9 capstone 细则

目标：让 capstone 与 v3 路线和求职叙事一致——主链路去掉 LangChain 胶水、接入 OpenTelemetry、提供零依赖的演示前端，并让简历文档的措辞与代码对齐。对外行为与 API 契约不变。

前置批次：V3-2（原生 RAG 写法）、V3-6（OTel 写法）。只改 `capstone/`、`.github/workflows/eval-gate.yml`（如有需要）和本批次验证记录；不改 `flagship-project/`。

## 任务 1：去掉 LangChain

2026-10-27 的核对结果：capstone 不使用 LangGraph；LangChain 出现在下列位置。

| 文件 | 现状 | 改法 |
|---|---|---|
| `knowledge_base.py` | LCEL 链（`ChatPromptTemplate`、`RunnableLambda`、`RunnablePassthrough`、`StrOutputParser`）、`langchain_chroma.Chroma`、`RecursiveCharacterTextSplitter`、`Document` | 消息组装与调用改为原生 openai 客户端（经 `common.get_openai_client()`）；重试与降级保留现有语义；向量库改用 `chromadb` 原生客户端；切分器改为原生实现 |
| `connector.py` | `langchain_chroma.Chroma`、`RecursiveCharacterTextSplitter` | 同上 |
| `context.py`、`permissions.py`、`vector_store_pg.py`、`test_production.py` | `langchain_core.documents.Document`；`permissions.py` 另有 `RunnableLambda` | `Document` 换成 capstone 自己的 dataclass（优先放进现有的 `contracts.py`）；`RunnableLambda` 换成普通函数 |
| `vector_store_pg.py` | 在函数内导入 `langchain_postgres.PGVector` | 改为 psycopg 直接执行 SQL（pgvector 扩展），测试用假连接；工作量明显超出时，先在提交里说明，由审核者决定 |

要求：

- `common.get_llm()` 与 `common.get_reliable_llm()` 不再被 capstone 调用；原有的超时、重试、主备模型语义用原生实现保留（可以参照 L5.1）。
- 完成后 `grep -rnE "^\s*(from|import) (langchain|langgraph)" capstone` 无输出，包括函数内的延迟导入。
- 公共函数与 HTTP 接口的签名、返回结构不变；`capstone/README.md` 中的运行命令照常可用。

## 任务 2：接入 OpenTelemetry

- 复用 L5.6 的写法：问答主链路的模型调用、检索、工具调用各一个 span；记录 usage 与错误；默认不采集正文。
- 默认导出到控制台或关闭；设置了 OTLP 端点环境变量时发送到后端。
- 新增离线测试：用内存导出器断言主链路产生了预期的 span 与属性。

## 任务 3：演示前端

- capstone 已有 `app_streamlit.py`（Streamlit 开发演示）。另按 P5 的要求，提供零依赖的静态前端（HTML 加原生 JS），由 FastAPI 的静态文件服务提供，用于公开演示。
- 功能：提问、展示引用、展示降级与“需要人工”状态、反馈按钮、错误提示。
- README 写明两个界面各自的用途。

## 任务 4：简历文档与代码对齐

- 逐条核对 `capstone/docs/portfolio/` 下的文档（尤其是 `resume_evidence.md`、`project_pitch.md`）：
  - 每个技术声明都要能对上代码或证据文件；对不上的改写或删除；
  - 去掉没有来源的数字（例如“调用栈从 15 层降到 2 层”之类）；
  - 仍未完成的事项（公网部署、真实用户）保持“尚未”的表述。
- 更新 `capstone/docs/adr/`：新增一条记录，说明去掉 LangChain 的原因、代价与回退方式。

## 验收命令

```bash
python -m pytest capstone/test_production.py -q        # 现有 34 项加新增测试，全部通过
python -m capstone.milestones --strict-evidence
python -m capstone.project_baseline --json
python -m capstone.evidence_audit
python -m capstone.interview_evidence --strict-evidence
python -m capstone.load_test --fake --users 2 --spawn-rate 2 --time 5s --upstream-ms 50
python -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
python -m ruff check --target-version py311 capstone
```

- 会调用真实模型的回归测试 `python -m pytest capstone/test_regression.py -v` 为可选项；运行前确认密钥与费用，结果写进验证记录，并注明日期与模型 ID。
- 验证记录：`docs/gate-v3-9-validation.md`。

## 审核重点

- 行为不变：离线评测结果与改动前一致；API 契约不变。
- 没有残留的 LangChain 导入（包括延迟导入）。
- OTel 默认不采集正文。
- 简历文档里没有代码不支持的说法。
