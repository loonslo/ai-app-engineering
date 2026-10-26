# Capstone 稳定性与并发性能优化验证记录

**日期**：2026-10-26  
**环境**：Windows 11 / Python 3.14 (.venv)  
**性质**：Capstone 核心模块性能与高并发稳定性专项优化（离线测试替身环境）

---

## 1. 优化目标与修改文件

1. **BM25 缓存失效与内存容量限制**
   - 目标文件：`capstone/knowledge_base.py`
   - 改动点：
     - 使用 `collections.OrderedDict` 替换无界原生 `dict`，加入上限 256 容量控制（LRU 淘汰机制），防止长时间多用户服务内存泄露。
     - 缓存键纳入知识库版本 `self.version`，并在 `build()` 时清空 BM25 缓存与 LLM 链缓存，避免文档增量同步后返回陈旧召回结果。
     - 为 `answer_with_usage` 增加实例级 `_llm_cache`，复用可靠 LLM 管道实例。

2. **SQLite 监控指标连接与 DDL 开销消除**
   - 目标文件：`capstone/monitoring.py`
   - 改动点：
     - 增加 `_initialized_dbs` 与 `_init_lock` 机制，在进程生命周期内对同一数据库只执行一次 `CREATE TABLE IF NOT EXISTS` 和 `PRAGMA journal_mode=WAL`。
     - 保持原有连接及时关闭特性，完全兼容 Windows 下单元测试对 SQLite 文件的 `unlink()` 清理。

3. **TenantKBRegistry 多租户并发锁粒度细化**
   - 目标文件：`capstone/api_enterprise.py`
   - 改动点：
     - 由原先的单一全局 `self._lock` 升级为基于租户的条带锁 `_tenant_locks` 与双重检查机制。
     - 租户各自的 `KnowledgeBase.build()` 耗时过程在全局锁外并行执行，互不阻塞，读路径极大降低锁争用。

---

## 2. 实际执行验证与结果

### 2.1 Capstone 生产级功能与回归测试
```bash
.venv\Scripts\python.exe -m pytest capstone/test_production.py -v
```
- **执行结果**：34 passed，耗时 6.62s（优化前为 10.14s）。
- **覆盖点**：ACL 过滤、多租户隔离、JWT、速率限制、监控租户隔离、缓存隔离、审批流、增量同步确定性、拒答不带引用、内容安全等 34 项测试全部通过。

### 2.2 章节与工具链回归测试
```bash
.venv\Scripts\python.exe -m pytest tools chapters/test_new_lessons.py -q
```
- **执行结果**：28 passed，耗时 6.68s。

### 2.3 代码风格与规范自检
```bash
.venv\Scripts\python.exe -m ruff check capstone/
```
- **执行结果**：All checks passed!

### 2.4 里程碑证据与基线检查
```bash
.venv\Scripts\python.exe -m capstone.milestones --strict-evidence
.venv\Scripts\python.exe -m capstone.project_baseline --json
```
- **执行结果**：所有阶段性里程碑证据存在；项目基线 15 项（包括 walking skeleton）全部 `passed: true`。

---

## 3. 未验证边界说明

1. **测试模式为离线测试替身（Test Doubles）**：未调用真实的外部大模型（如 DeepSeek/OpenAI API）或加载真实本地 Embedding/Reranker 模型文件。
2. **多进程与物理外部服务未验证**：未启动多进程 Gunicorn / Uvicorn 真实压测，亦未连接真实的 PostgreSQL/pgvector 外部集群。
