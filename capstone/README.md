# 多租户企业客服与工单 Copilot（旗舰项目整合实现）

> 从项目立项、RAG MVP、企业权限、受控工具、持久化审批和长期记忆，一直走到评测、CI、监控、迁移、压测、部署与项目交接。当前是生产导向的本地原型，没有已验证的公网部署。
>
> 产品需求见 [`docs/project_brief.md`](docs/project_brief.md)，章节与步骤见 [章节总地图](../chapters/README.md) 和 [旗舰项目路线](../flagship-project/README.md)，历史能力对照见 [`docs/project-roadmap.md`](docs/project-roadmap.md)。

## 阅读路线

这个项目把散落的客服资料变成“先找证据、再按证据回答”的服务，并把身份、审批和测试接到同一条业务链。建议按下面的顺序读文件：

1. `main.py` 与 `api_enterprise.py`：CLI / HTTP 怎样接收请求；HTTP 身份来自签名 token。
2. `contracts.py` 与 `service.py`：请求和回答的字段是什么，统一服务怎样选择知识问答、业务查询、审批或记忆。
3. `knowledge_base.py`：文档加载、切分、召回、排序、上下文与生成；回答引用怎样取自文档元数据。
4. `permissions.py` 与 `context.py`：哪些文档可见，怎样控制上下文预算，无权限或无证据时怎样拒答。
5. `connector.py`：资料变化如何触发增量同步，正文、权限与管线配置怎样影响知识版本。
6. `query_catalog.py`、`approval.py`、`memory.py`：受控查询、一次性审批与显式同意的偏好。
7. `test_production.py`：先读不调用模型的失败与隔离测试，再读 `test_regression.py` 的真实模型评测。

### 先认识六个词

- **Markdown**：用普通文本编写的文档格式，作为示例客服资料来源。
- **Document**：正文与元数据组成的片段；元数据保存来源、片段 ID 和权限。
- **向量（embedding）**：用数字表示文本，便于比较语义相似程度。
- **检索（retrieval）**：找相关片段，负责提供证据；后续上下文与生成仍可能失败。
- **LLM**：按请求、指令和证据组织回复；不能靠它补造知识库事实。
- **RRF**：融合多路排序的方法；靠前的片段获得较高分，不代表已证明答案正确。

`flagship-project/` 快照里的 `runtime.py`（LangGraph 图）与本目录的 `AssistantService` 是两套实现，分别验收，不要混用结论。

## 能力一览

| 模块 | 文件 | 当前学习对应 |
|------|------|--------|
| 稳定业务契约 + 唯一服务入口 | `contracts.py` / `service.py` | 里程碑 7.4 / step1、7.7 / step6 |
| 文档处理 + 混合检索 + 溯源 | `knowledge_base.py`（切分 `text_split.py`、向量库 `vector_store.py`、嵌入 `embedding.py`） | 章节 2.6–2.11 |
| 原生模型调用（超时、重试、可选备用模型） | `llm.py` | 章节 5.2（L5.1） |
| OpenTelemetry 打点（默认不导出、不采集正文） | `telemetry.py` | 章节 5.9（L5.6） |
| 真实数据接入 + 增量同步 | `connector.py` | 里程碑 7.4 / step4 |
| 查询前 ACL + 缺省拒绝 | `permissions.py` / `knowledge_base.py` | capstone 扩展；章节 9.5 学习租户权限 |
| 上下文预算 + 不可信资料封装 | `context.py` | 章节 4.10、里程碑 7.5 / step1 |
| JWT + 物理租户隔离 + Redis 限流 | `auth.py` | 里程碑 7.4 / step3、章节 9.7 |
| 受控业务查询 | `query_catalog.py` | 章节 4.13、里程碑 7.3 / step1 |
| 持久化高风险审批 | `approval.py` | capstone 扩展；章节 4.11 / 10.1 学习人工介入与审批 |
| 显式同意的长期偏好 | `memory.py` | capstone 扩展；章节 4.10 学习状态与上下文 |
| 输入输出内容安全 | `content_safety.py` | 里程碑 7.5 / step1 |
| 自动化评测（指标 + 报告 + 失败库） | `evaluation.py` | 第 3 篇评测与第 8 篇质量工程 |
| CI 评测门禁 | `ci_gate.py` | 里程碑 7.6 / step1 |
| p95/p99 + token/成本 + request_id | `monitoring.py` / `monitoring_cli.py` | 里程碑 7.5 / step3 |
| pgvector 迁移能力 | `vector_store_pg.py` | 里程碑 7.7 / step1 |
| 容量与 SLO 验证 | `load_test.py` | 里程碑 7.7 / step2 |
| 部署和证据审计 | `deployment_check.py` / `evidence_audit.py` | 里程碑 7.6 / step2、7.8 / step1 |
| 统一认证 HTTP 服务 | `api_enterprise.py` | 章节 5.1 / 5.4 / 5.5、里程碑 7.4 / step3 |
| 输入边界 + PII 脱敏 | `security.py` | 章节 5.7、里程碑 7.5 / step1 |
| 权限与知识版本感知缓存 | `cache.py` | 章节 5.3 |
| pytest 回归 | `test_regression.py` | 章节 5.8 |
| Web 界面：开发调试（Streamlit） | `app_streamlit.py` | — |
| Web 界面：公开演示（零依赖静态页，`/ui`） | `static/index.html` / `static/app.js` | 章节 11.5（P5） |
| CLI 入口 | `main.py` | — |

## 架构与依赖方向

```text
HTTP / CLI / Evaluation
          │
          ▼
   AssistantService  ← 唯一业务入口
     │    │    │
     │    │    └─ ApprovalWorkflow / PreferenceMemory
     │    └────── CatalogQueryTool（可信 query_id）
     └─────────── KnowledgeBase
                       │
             ACL → Hybrid Retrieval → Context Budget

横切能力：JWT、内容安全、缓存、指标、trace、CI 和部署证据
```

## 快速开始

在仓库根目录、项目虚拟环境中执行：

```bash
# 1) 安装依赖
python -m pip install -r requirements-dev.txt

# 2) 复制配置模板，只填自己的本地地址和密钥；不要提交 .env（PowerShell 用 Copy-Item）
cp .env.example .env

# 3) 建知识库：公开文档放 capstone/docs/（已带示例），私有租户文档放 capstone/data/tenants/<tenant-key>/docs/
python -m capstone.main build

# 4) 提问、跑评测（需要真实模型密钥）
python -m capstone.main ask "RAG 为什么能减少幻觉？"
python -m capstone.main eval

# 5) 先跑不调用 LLM 的生产边界测试，再按需跑真实模型回归
pytest capstone/test_production.py -q
pytest capstone/test_regression.py -v

# 6) 本地演示；登录演示需要显式设置 CAPSTONE_ENABLE_DEV_LOGIN=true
uvicorn capstone.api_enterprise:app --reload
streamlit run capstone/app_streamlit.py      # 开发调试界面
# 公开演示用的静态页由 API 服务提供：启动 uvicorn 后访问 http://127.0.0.1:8000/ui/
```

两个界面的分工：`app_streamlit.py` 面向开发调试（直接调用本地代码）；`static/` 是零依赖的静态 HTML + 原生 JS，通过 HTTP 调用 `/v1/chat` 与 `/v1/feedback`，用于公开演示，展示引用、降级（`degraded`）、需要人工审批（`status=pending_approval`）、缓存命中，提供“有用 / 没用”反馈与可读的错误提示。

可观测：设置 `CAPSTONE_OTEL=console` 把 span 打印到控制台；设置 `OTEL_EXPORTER_OTLP_ENDPOINT` 发送到 OTLP 后端（需另装 `opentelemetry-exporter-otlp-proto-http`）；默认不导出。span 只记 usage、模型 ID、request_id 与错误类型，**不记录问题、资料与回答的正文**。

可靠性：模型调用只走 OpenAI 兼容接口；配置 `CAPSTONE_BACKUP_MODEL`（同一 provider 的另一个模型 ID）后，主模型重试耗尽会改用它，响应里 `degraded=true`，且该回答不进缓存。

PyCharm 中把运行模块设为 `capstone.main`，测试目录设为 `capstone`。

统一接口 `POST /v1/chat` 默认执行知识问答，也支持显式模式：

- `mode=memory`：设置、查看或删除受控偏好；普通对话不会被静默长期保存。
- `mode=data_query` + `query_id`：只执行服务端 catalog 中的只读查询。
- `mode=action` + `action=publish_reply`：创建持久化审批，主管通过 `/v1/approvals/{id}/decision` 一次性决策。

## 与教程步骤对照

```bash
# 查看某一步在项目中的状态、证据和验收命令
python -m capstone.milestones m3-order-tool-reliability/step2
python -m capstone.milestones --json

# 汇总全部后端步骤的接入状态；partial 不包装成已交付
python -m capstone.milestones --strict-evidence

# 还原某一步的快照，并查看它相对上一步的变更
python tools/materialize.py flagship m3-order-tool-reliability/step2 --diff
```

每一步的 README 和工作簿提供阅读顺序、实验和边界。`--strict-evidence` 只检查所列文件是否存在；完成学习仍需执行验收命令，并理解失败路径。

## 检查与可选组件

```bash
# 项目基线、证据审计、监控和 provider 契约
python -m capstone.project_baseline --json
python -m capstone.evidence_audit
python -m capstone.monitoring_cli --json
python -m capstone.provider_contract

# pgvector 是可选后端：先看迁移模板，再按需安装和配置
python -m capstone.vector_store_pg migration
python -m pip install -r requirements-pgvector.txt

# Bedrock：capstone 已改用原生 OpenAI 兼容客户端，不再直连 Bedrock；
# 需要时请经 OpenAI 兼容网关接入（LLM_PROVIDER=openai_compatible）。

# 不调用 DeepSeek 的本地压测；real 模式从 LOADTEST_BEARER_TOKEN 读 token
python -m capstone.load_test --fake --users 10 --time 30s
```

内容安全已经进入真实 API 请求路径；生产必须注入外部审核器。

## 工程要点

- **检索质量**：向量召回 + BM25 关键词召回融合，专有名词不漏；metadata 溯源，答案标来源。
- **评测回归**：评测集就是回归用例库；用拒答正确率量化防幻觉；失败用例库归档错因（检索没召回，还是召回了生成错）。
- **安全**：租户物理分库、Chroma 查询前 ACL、缺 ACL 默认拒绝；输入边界和响应脱敏不替代授权。
- **认证**：开发使用短期本地 token；生产强制外部 JWT 密钥与 Redis 限流，建议接 IdP/JWKS。
- **可观测**：request_id 进入 OTel span 属性 `app.request.id`（默认不导出）；指标仅保存问题指纹，不保存明文问题。
- **可复现**：被测链 `temperature=0`，回归断言用“含关键词 / 是否拒答”的宽松匹配，避开随机性。

## 边界

证据审计会把缺少截图/GIF 报为警告。不要把 Dockerfile、迁移模板或本地演示表述成“已经公网部署”“已完成 pgvector 迁移”或“已满足全部合规要求”。`flagship-project/` 保存分步教学快照，整合实现位于 `capstone/`，两套入口分别验收。
