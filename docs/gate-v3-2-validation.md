# V3-2 阶段 2 上下文工程与检索修复验证 · 2026-10-28

本批次针对首轮审核退回记录（`docs/v3/reviews/V3-2.md`）中的 3 个阻断项、9 个主要问题与 7 个次要问题进行了全面闭环修复与全量验证。修复覆盖 L2.1–L2.12 共 14 个章节/练习，包含 4 个新建章节（`2.12`、`2.13`、`2.14`、`2.15`）与 10 个既有章节，所有 Gate 均满足 `--module` 支持、生成 `gate_report.json`、骨架严格 0 通过（退出码 1）与临时参考解 100% 通过（退出码 0），所有参考实现均支持离线安全执行与 `--live` 显式开启。

## 范围与修复内容

| v3 编号 | 对应目录 | 类型 | 修复与改动内容 |
|---|---|---|---|
| 契约 | 根目录 `PROJECT_STATUS.md` | 状态同步 | **B1 阻断项修复**：以 `git show 355ea98:PROJECT_STATUS.md` 为基准恢复正文原有全部条目（含用户两项决定、v3 提案、就业审查与 V3-0/V3-1 完整审核记录），用户决定段落补充“v3 行位置同日改为 v2 行下方”说明；仅在正文末尾追加 V3-2 审核退回与修复条目，严格自检 v1 同步契约全部字段与路径。 |
| L2.12 | `chapters/part2-rag/2.15-real-corpus-kb-gate` | 出口 Gate | **B2、B3、M1、M2、M5 阻断与主要项修复**：<br>1. 重写 `corpus/SOURCES.md`，收录 24 份真实公有/宽松开源资料（Linux 命令手册、SemVer 规范、Python 中文教程、真实表格 PDF 与扫描页），官方许可证与链接逐条核实，删除虚构条目；<br>2. 重构 `fetch_corpus.py`，使用固定 commit/tag URL，下载后强制校验 sha256，不符时删除文件并退出码 1；<br>3. 评测集 `gate/cases.json` 扩充至 32 题真实语料用例（含 8 题越界拒答与 4 题注入攻击），gold 页码与分块对齐，延迟改取用例假时钟；<br>4. 重构 `kb_pipeline.py`，导入前序真实组件（2.7 切分、2.8 RRF 融合），彻底杜绝读取标准答案；消融实验对比三种真正不同配置（Dense Only、BM25 Only、Hybrid RRF）；离线安全返回，删除伪造的“门禁通过”；<br>5. 规范 `workbook.md` 为“待填写”，删除 `gate/CHECKLIST.md`（m2），统一标题与导航。 |
| L2.2 | `chapters/part2-rag/2.6-pdf-sources` | 换实现 | **M3、m3 修复**：`pdf_sources.py` 检索结果改为支持下标与属性访问的轻量原生 `Document(page_content, metadata)`，完全恢复 3.2、3.3、3.5、5.1、5.8 下游测试兼容性；删除伪造回答兜底，缺密钥可读提示退出；`README.md` 修正 `format_context` 描述。 |
| L2.4 | `chapters/part2-rag/2.3-minimal-rag` | 换实现+对照 | **M4、M5、m5 修复**：参考实现增加 `--live` 标志，复用 2.2 `VectorIndex`；离线输出明确标注 `[离线演示]`，不伪造生成；`README.md` 修正框架对照并改用“无证据时不调用模型”。 |
| L2.7 | `chapters/part2-rag/2.9-query-rewrite` | 增补 Gate | **M4、M8 修复**：参考实现增加 `--live` 标志，离线明确标注 `[离线确定性改写]` 与 `[离线确定性 HyDE 假设文本]`，不伪造模型输出；删除 README 成本表中未经核对的数字，改为定性工程权衡；Gate 严格按“原 9 项 + 新增 7 项 = 16 项”组织。 |
| L2.6 | `chapters/part2-rag/2.11-multimodal-rerank` | 换实现 | **M4、M8 修复**：Cross-Encoder 离线降级为字符重合打分时打印显式告警提示；`ask_image` 移除第三方写死默认地址与对 `DEEPSEEK_API_KEY` 的越界回退，仅从环境变量读取；README 补充技术雷达 Vol.34 官方链接。 |
| L2.1 | `chapters/part2-rag/2.12-context-engineering` | 新建 Gate | **M4、M9、m1、m2 修复**：修正 `REPO_ROOT = parents[3]`，捕获客户端初始化异常；Gate 检查 7 收紧为同时断言两个重复段落；README 补充任务与关键约定表格，删除夸张用词；workbook 改为“待填写”；删除 `CHECKLIST.md`。 |
| L2.5 | `chapters/part2-rag/2.7-chunk-strategy` | 换实现 | **M5 修复**：复用 2.2 `VectorIndex` 检索器；清理未使用导入，通过 ruff 校验。 |
| L2.10 | `chapters/part2-rag/2.14-memory-compaction` | 新建 Gate | **M6、m2 修复**：`starter.py` 与 `gate_check.py` 补充检查 7“压缩后不超预算保证”（总数 11 项）；修正 `prefix_changed`；参考实现增加 20 轮对话记忆评测与 `--live` 模式；README 补齐 ASI06、结构化笔记与写入策略，时间盒修正为 4h；workbook 恢复标准模板；删除 `CHECKLIST.md`。 |
| L2.9 | `chapters/part2-rag/2.13-static-context-skills` | 新建 Gate | **M7、M8、m1、m2、m6、m7 修复**：对齐 agentskills.io 官方规范（禁止连字符起止、禁止 `--`、强制目录名一致），Gate 增加非法测试用例与多合法 fixture 覆盖；README 补充头部字段，雷达 Vol.34 链接，改用实测 62.2% 节省比例并说明测量条件；workbook 改为“待填写”；删除 `CHECKLIST.md`。 |
| L2.11 | `chapters/part2-rag/2.4-eval-seed` | 增补更新 | **M8 修复**：忠实转述 Anthropic《Demystifying evals for AI agents》原文（“20-50 simple tasks drawn from real failures is a great start”），标注官方发布日期 2026-01-09 与读取日期 2026-10-28。 |
| L2.8 | `chapters/part2-rag/2.10-chroma-persist` | 换实现 | **m4 修复**：恢复被误删的 gate 概念（加载校验、副本、选型）与边界声明“通过 gate 只证明落盘/加载/校验结构正确”。 |

## 真实组件与测试替身（Mocks）的区别说明

为遵守离线隔离、无外部费用与确定性复现原则，本批次对参考实现与门禁中的组件边界做了严格划分：

| 模块 / 功能 | 实际运行的真实组件 | 测试替身（Mocks / 离线确定性实现） |
|---|---|---|
| **文本 Embedding** | 本地真实加载 HuggingFace `BAAI/bge-small-zh-v1.5` 模型计算 512 维稠密向量并归一化 | 离线环境且本地缺少权重时由 `common.py` 降级为确定性哈希伪向量 |
| **稀疏词法检索** | 真实 `rank_bm25.BM25Okapi` 倒排与分词打分 | 无替身，完全由真实 Python 算法库计算 |
| **向量检索与持久化** | 真实 NumPy 点积余弦检索；真实 `chromadb.PersistentClient` 写入 SQLite 与元数据过滤 | Gate 内部使用轻量 JSON 存储替身验证落盘与校验协议 |
| **重排模型** | 真实 Cross-Encoder 架构推理接口 | 离线无权重时降级为字符重合打分，**控制台打印显式降级警告**，禁止冒充精排得分 |
| **大模型问答与摘要** | **真实模型调用必须加 `--live` 参数显式开启**（读取环境变量真实密钥） | 默认离线模式使用明确标注的规则或模板替身（如 `[离线确定性改写]`、`[离线演示]`），**禁止伪造带证据的模型生成回答** |
| **评测时钟与时延** | 无外部时钟漂移 | 统一使用用例内置的假时钟字段 `latency_ms`，严禁 `time.sleep` 或 `perf_counter` 假装性能数据 |

## 实际执行与命令验证

### 1. Gate 验证：骨架 0 通过（退出码 1）与临时参考解全通（退出码 0）

在仓库根目录下运行，全部 Gate 均支持 `--module` 参数并写出 `gate_report.json`：

| 章节编号 | 目录 | Starter 骨架检查 | 参考解检查 | 结果一致性（命令 3 连跑两次） |
|---|---|---|---|---|
| L2.2 | `2.2-embed-retrieve` | 0/9 passed (exit 1) | 9/9 passed (exit 0) | 一致 |
| L2.4 | `2.3-minimal-rag` | 0/10 passed (exit 1) | 10/10 passed (exit 0) | 一致 |
| L2.2 | `2.6-pdf-sources` | 0/9 passed (exit 1) | 9/9 passed (exit 0) | 一致 |
| L2.5 | `2.7-chunk-strategy` | 0/7 passed (exit 1) | 7/7 passed (exit 0) | 一致 |
| L2.6 | `2.8-hybrid-search` | 0/7 passed (exit 1) | 7/7 passed (exit 0) | 一致 |
| L2.7 | `2.9-query-rewrite` | 0/16 passed (exit 1) | 16/16 passed (exit 0) | 一致（原 9 项 + 新增 7 项） |
| L2.8 | `2.10-chroma-persist` | 0/9 passed (exit 1) | 9/9 passed (exit 0) | 一致 |
| L2.6 | `2.11-multimodal-rerank` | 0/8 passed (exit 1) | 8/8 passed (exit 0) | 一致 |
| L2.1 | `2.12-context-engineering` | 0/11 passed (exit 1) | 11/11 passed (exit 0) | 一致 |
| L2.9 | `2.13-static-context-skills` | 0/11 passed (exit 1) | 11/11 passed (exit 0) | 一致 |
| L2.10 | `2.14-memory-compaction` | 0/11 passed (exit 1) | 11/11 passed (exit 0) | 一致（含压缩后不超预算截断保证） |
| L2.12 | `2.15-real-corpus-kb-gate` | 0/12 passed (exit 1) | 12/12 passed (exit 0) | 一致（应答题独立统计，假时钟延迟） |

### 2. 回归测试套件

执行命令：
```bash
.\.venv\Scripts\python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
.\.venv\Scripts\python.exe -m pytest capstone/test_production.py -q
```
执行结果：
- `tools` 与 `chapters/test_*.py`：**63 passed**, 1 warning (chromadb DeprecationWarning) (退出码 0)。
- `capstone/test_production.py`：**34 passed**, 1 warning (退出码 0)。

### 3. 断链检查与静态代码规范

- **链接检查**：
  ```bash
  .\.venv\Scripts\python.exe tools/check_course_links.py
  ```
  结果：扫描 349 份 Markdown 文件，**0 断链**（退出码 0）。
- **Ruff 静态检查（CI Python 3.11 目标版本）**：
  ```bash
  .\.venv\Scripts\python.exe -m ruff check --target-version py311 chapters/part2-rag/ common.py chapters/test_v3_lessons.py
  ```
  结果：`All checks passed!`（退出码 0）。

### 4. LangChain 边界与标签映射

- **LangChain 边界检查**：排查 `chapters/part2-rag/` 下全部非 `_langchain.py` 脚本，无任何未声明的 LangChain 导入。
- **v2 标签映射**：
  ```bash
  .\.venv\Scripts\python.exe tools/apply_v2_map.py --check
  ```
  结果：`合计：111 份 README：inserted=0 updated=0 unchanged=111`（退出码 0）。
- **v3 标签映射**：
  ```bash
  .\.venv\Scripts\python.exe tools/apply_v3_map.py --check
  ```
  结果：新建的 4 个章节（`2.12`、`2.13`、`2.14`、`2.15`）全部为 `[unchanged]`。

### 5. 参考实现启动与离线运行

使用 `tools/run_chapter.py` 对 Part 2 全部 16 个参考实现脚本执行离线启动验证，全部**正常退出（退出码 0）**且无异常堆栈：
- `2.1 load_split.py`：OK
- `2.1 load_split_formats.py`：OK
- `2.2 embed_retrieve.py`：OK
- `2.3 minimal_rag.py`：OK（离线演示，未伪造生成）
- `2.4 eval_seed.py`：OK
- `2.5 raw_sdk_rag_agent_loop.py`：OK
- `2.6 pdf_sources.py`：OK（轻量 Document 对象，下游兼容）
- `2.7 chunk_strategy.py`：OK（复用 2.2 VectorIndex）
- `2.8 hybrid_search.py`：OK
- `2.9 query_rewrite.py`：OK（离线确定性改写与假设文本标注）
- `2.10 chroma_persist.py`：OK
- `2.11 multimodal_rerank.py`：OK（重排降级打印警告，ask_image 环境变量隔离）
- `2.12 context_engineering.py`：OK（路径修复，异常保护）
- `2.13 skills_loader.py`：OK（agentskills.io 规范校验）
- `2.14 memory_compaction.py`：OK（20 轮记忆保留评测通过）
- `2.15 kb_pipeline.py`：OK（真实三配置消融，不读取标准答案）

## 细则偏离说明

按要求如实记录本批次对 `docs/v3/specs/L2.md` 的工程调整与偏离原因：

1. **2.6 保留轻量问答与下游兼容**：细则建议将 2.6 问答部分删去或导入 L2.4。为确保下游章节（3.2、3.3、3.5、5.1、5.8）已有测试无缝通过，2.6 将检索输出统一封装为支持属性与字典键访问的原生 `Document` dataclass，并保留了安全问答链（缺密钥时提示退出）；其中 3.7 的 LCEL 组合（`retriever | format_docs`）因下游仍为 LangChain 1.x 语法，登记为临时已知不兼容，后续由 V3-3 批次重构 3.7 时统一解决。
2. **2.9 追加检查项组织**：按照 `conventions.md` 6.4 节约定，2.9 Gate 严格维持前 9 项检查名称与顺序不变，在末尾追加 7 项 Agentic 检索与重试断言（共 16 项），并补充了 `min_hits` 阈值校验。
3. **2.14 记忆超预算保障策略**：细则要求压缩后严格不超预算。实现中约定：若 System 首条 + Pinned 固定条目 + 尾部保留条目本身已占满或超出预算，则不再插入额外摘要，直接返回固定保留消息集；仅当剩余预算 > 0 时对摘要进行截断并追加 `'...[截断]'`。时间盒统一对齐为 4h。
4. **2.15 评测集与语料方案调整**：为杜绝英文大文档版本漂移与许可模糊风险，语料清单精选 24 份真实公有/宽松开源中文资料（Linux 命令、SemVer、Python 中文教程及公开表格/扫描 PDF），使用固定 commit 保证哈希恒定；评测集指标计算调整为仅在可回答用例上统计 `hit@5` 与引用正确率，拒答率独立统计，并在流水线中增加 `validate_cases` 结构完整性校验。

## 未验证事项

1. **真实商用大模型在线 API 调用**：参考实现中的 `--live` 模式支持通过环境变量调用外部大模型，但在离线自动化验证中未注入真实商用 API Key，未产生任何实际计费调用。
2. **公网语料全量下载网络请求**：`fetch_corpus.py` 在自动化验证中通过 `--dry-run` 与哈希算法断言验证下载清单完整性；实际离线 Gate 运行基于 `gate/fixtures/` 内置的固定切片副本，未在 CI/测试流程中依赖实时公网下载。

## 复现方式

在仓库根目录下激活 `.venv` 虚拟环境后执行：
```bash
# 1. 验证 L2 全部 Gate（骨架 0 通过退出 1，参考解全通退出 0）
.\.venv\Scripts\python.exe chapters/part2-rag/2.15-real-corpus-kb-gate/gate/gate_check.py
.\.venv\Scripts\python.exe chapters/part2-rag/2.15-real-corpus-kb-gate/gate/gate_check.py --module .tmp/gate_solutions/v3/2.15.py

# 2. 运行自动化测试套件
.\.venv\Scripts\python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
.\.venv\Scripts\python.exe -m pytest capstone/test_production.py -q

# 3. 静态检查、断链与映射检查
.\.venv\Scripts\python.exe tools/check_course_links.py
.\.venv\Scripts\python.exe -m ruff check --target-version py311 chapters/part2-rag/ common.py chapters/test_v3_lessons.py
.\.venv\Scripts\python.exe tools/apply_v2_map.py --check
.\.venv\Scripts\python.exe tools/apply_v3_map.py --check
```

## 边界

- `flagship-project/` 保持历史冻结快照，未作任何改动。
- 本批次所有改动均在 `wip-v3-2` 分支完成，未合入 `master`。
