# 简历项目描述与证据边界（里程碑 7.5 / step3）

> 求职定位：复合型 AI 应用开发工程师（测试/质量工程转型）。核心壁垒不是“调过模型 API 或套用框架模板”，而是能把大模型放进可测试、可观测、多租户安全的工程边界：原生 SDK 调用、Pydantic 类型契约、检索前 ACL 与质量门禁，每一项都能指向代码、测试或报告。

## 当前可直接写进简历的版本（STAR 结构精修版）

**企业知识库问答与质量门禁平台｜个人核心项目**

基于 Python、FastAPI、Pydantic 与 DeepSeek 构建多租户文档问答与 Agent 审批原型。主问答链路使用原生 openai SDK、chromadb 与自写的文本切分器，不依赖 LangChain/LangGraph（`capstone/` 目录内已无相关导入；`flagship-project/` 是冻结的历史快照，另当别论），围绕检索权限、增量一致性、回归评测、并发稳定性和可观测性建立可测试的工程边界。

- **检索前 ACL 注入与增量一致性**：支持 TXT、Markdown、PDF 解析与向量/BM25 混合检索；在向向量库发起检索前直接注入租户与角色元数据 Filter，BM25 仅在授权子集构建索引，杜绝“授权空窗”与越权泄露；基于 SHA-256 和确定性 Chunk ID 实现增量同步与旧块准确追踪。
- **质量门禁与低成本 CI 拦截**：针对大模型输出随机性搭建分层质量金字塔；在 CI 阶段采用规则断言执行黄金用例集回归（资料外超纲问题必须精准拒答且无引用，事实问题断言核心关键词与真实召回来源），零外部 LLM 成本实现秒级 PR 拦截；建立 Earliest-Fail-First 七阶段归因漏斗，将线上 Bad Case 转化为版本化回归用例。
- **高并发稳定性与多维感知缓存**：设计身份与知识版本感知的短期 TTL 缓存，缓存键绑定租户、角色、部门、模型与知识库版本号，解决横向越权与陈旧脏读；将多租户 Registry 粗粒度全局锁重构为**分租户条带锁（Per-tenant Locks）与双重检查**，使文档构建并行化；BM25 引入 LRU 控顶（Cap 256）与版本驱逐，SQLite 监控指标消除重复 DDL/WAL 损耗，2026-10-26 的优化记录中 34 项离线生产测试全绿、耗时 10.14s 降至 6.62s（数据见 `docs/capstone-optimization-validation.md`；此后测试已增加，数字以重新运行为准）。
- **有界 Agent 与持久化一次性审批（HITL）**：基于原生 Python 状态流转落地读写分离；只读查询走白名单受控调度（本项目没有接入 MCP，见下文“Agent 能力的准确说法”）；高危业务操作（如公开回复、退款）强制中断生成幂等持久化草稿；审批状态持久化到 SQLite，并校验租户隔离、主管角色、超时机制与一次性状态机，杜绝重放与越权。
- **部署与上线边界说明**：提供 Dockerfile、健康检查与部署说明，但本机尚未进行生产 Docker 集群验证或公网部署，因此按工程诚实原则表述为“具备部署准备”，不包装“已上线”。

## 只按真实熟练度写关键词

- **可深入追问（核心交付）**：RAG、混合检索、Pre-filtering ACL、多租户隔离、JWT、确定性增量同步、自动化评测与 CI 门禁、pytest、FastAPI、分租户条带锁、LRU 缓存控制、OpenTelemetry 打点（默认不采集正文）、HITL 审批、原生 openai 客户端的超时与重试、Pydantic 类型契约。
- **有代码练习但不是毕业项目核心交付**：MCP（章节 1.6、4.21）、A2A 跨 Agent 委托、RAGAS、LangSmith、ReAct、Plan-and-Execute、pgvector 迁移脚本。
- **了解级（不放进项目成果）**：LoRA 微调、LlamaIndex、AutoGen。

## Agent 能力的准确说法

`capstone/service.py` 只允许白名单动作进入 `capstone/approval.py`。审批状态持久化到 SQLite，并校验租户、审批角色、过期和一次性决策；当前仍缺少真实外部副作用执行器、取消/撤销流程和加密状态存储。MCP 与 A2A 练习存在于章节 1.6 与 10.1–10.4，不在当前 capstone 默认运行链路中。

## 作品证据清单

- 入口与运行说明：`capstone/README.md`
- 评测集与最新报告：`capstone/data/eval_set.json`、`capstone/data/eval_report.md`
- 生产边界与并发测试：`capstone/test_production.py`
- CI 门禁：`.github/workflows/eval-gate.yml`
- 本地压测报告：`reports/loadtest_*.json`
- 稳定性优化验证：`docs/capstone-optimization-validation.md`
- MCP 与 A2A 协议解耦代码：`chapters/part10-mcp-a2a-optional/`

`python -m capstone.evidence_audit` 与 `python -m capstone.interview_evidence --strict-evidence` 会自动校验上述证据链是否真实存在。

## 面试表达纪律（四层回答框架）

回答任何硬核问题，统一遵循“**风险（Risk）— 实现（Implementation）— 证据（Evidence）— 剩余边界（Boundary）**”四层结构：
- **风险**：讲清楚不这么做会有什么不可承受的生产后果（如授权空窗、脏读、CI 成本失控、死锁、Agent 失控、框架过度封装导致的维护灾难）；
- **实现**：讲清楚自己的算法、锁机制、缓存键或架构解耦设计；
- **证据**：直接报出代码模块、测试用例名称、命令与具体数据；
- **边界**：主动交代当前实现的约束条件（如单机 vs 分布式、小样本 vs 全量），展现高级工程师的成熟度。
