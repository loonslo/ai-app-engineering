# V3-2 阶段 2 上下文工程与检索验证 · 2026-10-28

本批次完成了 v3 课程改造的 V3-2 批次（阶段 2：上下文工程与检索），覆盖 L2.1–L2.12 共 14 个章节/练习；新建了 4 个新章节（`2.12-context-engineering`、`2.13-static-context-skills`、`2.14-memory-compaction`、`2.15-real-corpus-kb-gate`），原生重构了 9 个章节（`2.1`、`2.6`、`2.2`、`2.3`、`2.7`、`2.8`、`2.11`、`2.9`、`2.10`），在 `2.3` 和 `2.8` 保留了框架对照文件（`minimal_rag_langchain.py`、`hybrid_search_langchain.py`），并在 `2.15` 交付了包含 32 题基准评测集、公开语料清单、下载工具与多策略消融对比的真实资料知识库流水线；全过程未调用外部真实模型或公网付费网络，未改动 v2 路径标签，所有 Gate 均满足 `--module` 支持、生成 `gate_report.json`、骨架严格 0 通过（退出码 1）与临时参考解 100% 通过（退出码 0）。

## 范围

| v3 编号 | 对应目录 | 类型 | 新增 / 修改 / 删除的文件 |
|---|---|---|---|
| L2.1 | `chapters/part2-rag/2.12-context-engineering` | 新建 Gate | 新建章节目录：`README.md`、`gate/starter.py`、`gate/gate_check.py`（11 项断言）、`gate/CHECKLIST.md`、`workbook.md`、`context_engineering.py` |
| L2.2 | `chapters/part2-rag/2.1-load-split` | 换实现 | 重构：`load_split.py`（原生递归与字符切分，`ZH_SEPARATORS`）、`load_split_formats.py`（pypdf/docx2txt 原生提取）；`gate/gate_check.py`（支持 `--module` 与报告写出）；`README.md` 更新说明 |
| L2.2 | `chapters/part2-rag/2.6-pdf-sources` | 换实现 | 重构：`pdf_sources.py`（原生 `NativeRetriever` 与 `NativeRagChain`，维持下游 `3.2` 等兼容性）；`gate/gate_check.py`（支持 `--module` 与报告写出）；`README.md` 更新说明 |
| L2.3 | `chapters/part2-rag/2.2-embed-retrieve` | 换实现 | 重构：`embed_retrieve.py`（原生向量余弦与 NumPy top-k，三类检索失败注入，可选 FAISS 替身）；`gate/gate_check.py`（支持 `--module` 与报告写出）；`README.md` 更新点积前提说明 |
| L2.4 | `chapters/part2-rag/2.3-minimal-rag` | 换实现+对照 | 重命名保留：`minimal_rag_langchain.py`；重构：`minimal_rag.py`（原生提示词注入隔离、`source#index` 引用标注、无证据安全拒答）；`gate/gate_check.py`（支持 `--module` 与报告写出）；`README.md` 增补框架对照说明 |
| L2.5 | `chapters/part2-rag/2.7-chunk-strategy` | 换实现 | 重构：`chunk_strategy.py`（原生段落/标点保边界切分 `split_preserving_boundaries` 与切分统计消融）；`gate/gate_check.py`（支持 `--module` 与报告写出）；`README.md` 更新说明 |
| L2.6 | `chapters/part2-rag/2.8-hybrid-search` | 换实现+对照 | 重命名保留：`hybrid_search_langchain.py`；重构：`hybrid_search.py`（原生 `rank_bm25` + 向量检索 + `rrf_fuse` 倒数排名融合）；`gate/gate_check.py`（支持 `--module` 与报告写出）；`README.md` 增补框架对照说明 |
| L2.6 | `chapters/part2-rag/2.11-multimodal-rerank` | 换实现 | 重构：`multimodal_rerank.py`（原生 CrossEncoder 重排打分与 `recall_at_k` 计算）；`gate/gate_check.py`（支持 `--module` 与报告写出）；`README.md` 引用技术雷达 Vol.34 评级 |
| L2.7 | `chapters/part2-rag/2.9-query-rewrite` | 增补 Gate | 重构：`query_rewrite.py`（原生 Multi-Query、HyDE 与 `agentic_retrieve` 自主多轮检索）；`gate/starter.py` 增补契约；`gate/gate_check.py` 追加 7 项 Agentic 断言（共 16 项）；`README.md` 新增 Agent 直接搜索权衡 |
| L2.8 | `chapters/part2-rag/2.10-chroma-persist` | 换实现 | 重构：`chroma_persist.py`（原生 `chromadb.PersistentClient`，确定性哈希切片 ID `sha256(source + index + text)` 幂等更新）；`gate/gate_check.py`（支持 `--module` 与报告写出）；`README.md` 更新说明 |
| L2.9 | `chapters/part2-rag/2.13-static-context-skills` | 新建 Gate | 新建章节目录：`README.md`、`gate/fixtures/skills/`（3 个合法 Skill、2 个非法格式测试 Skill）、`gate/starter.py`、`gate/gate_check.py`（11 项断言）、`gate/CHECKLIST.md`、`workbook.md`、`skills_loader.py` |
| L2.10 | `chapters/part2-rag/2.14-memory-compaction` | 新建 Gate | 新建章节目录：`README.md`、`gate/starter.py`、`gate/gate_check.py`（11 项断言）、`gate/CHECKLIST.md`、`workbook.md`、`memory_compaction.py` |
| L2.11 | `chapters/part2-rag/2.4-eval-seed` | 增补更新 | 修改：`README.md` 关联 L1.10 Harness 概念（Task/Trial/Grader/Transcript），增补“从 20 条到 50 条”评测集构建哲学并引用 Anthropic《Demystifying evals for AI agents》（读取日期：2026-10-28）；保持原 gate 与参考实现 |
| L2.12 | `chapters/part2-rag/2.15-real-corpus-kb-gate` | 新建出口 Gate | 新建章节目录：`README.md`、`corpus/SOURCES.md`（22 份公开许可与公有领域语料说明）、`corpus/.gitignore`、`fetch_corpus.py`（带哈希校验的下载工具）、`gate/fixtures/`（离线合法摘录）、`gate/cases.json`（32 题 Golden Set）、`gate/starter.py`、`gate/gate_check.py`（12 项断言）、`gate/CHECKLIST.md`、`workbook.md`、`kb_pipeline.py` |
| 索引 | `tools/course_catalog.py` | 目录索引 | 修改：登记 4 个新建章节（`2.12`、`2.13`、`2.14`、`2.15`） |
| 测试 | `chapters/test_v3_lessons.py` | 离线测试 | 修改：追加 9 项 L2 纯函数单元测试，总用例数扩充至 29 项 |

## 实际执行

### 1. Gate：骨架与临时参考解

#### (1) Starter 骨架检查（验证未完成状态下全部检查失败，退出码均为 1，通过数严格为 0）

| 章节编号 | 对应目录 | 检查命令 | 骨架结果 | 退出码 |
|---|---|---|---|---|
| L2.1 | `2.12-context-engineering` | `python chapters/part2-rag/2.12-context-engineering/gate/gate_check.py` | 0/11 passed | 1 |
| L2.2 | `2.1-load-split` | `python chapters/part2-rag/2.1-load-split/gate/gate_check.py` | 0/6 passed | 1 |
| L2.2 | `2.6-pdf-sources` | `python chapters/part2-rag/2.6-pdf-sources/gate/gate_check.py` | 0/9 passed | 1 |
| L2.3 | `2.2-embed-retrieve` | `python chapters/part2-rag/2.2-embed-retrieve/gate/gate_check.py` | 0/9 passed | 1 |
| L2.4 | `2.3-minimal-rag` | `python chapters/part2-rag/2.3-minimal-rag/gate/gate_check.py` | 0/10 passed | 1 |
| L2.5 | `2.7-chunk-strategy` | `python chapters/part2-rag/2.7-chunk-strategy/gate/gate_check.py` | 0/7 passed | 1 |
| L2.6 | `2.8-hybrid-search` | `python chapters/part2-rag/2.8-hybrid-search/gate/gate_check.py` | 0/7 passed | 1 |
| L2.6 | `2.11-multimodal-rerank` | `python chapters/part2-rag/2.11-multimodal-rerank/gate/gate_check.py` | 0/8 passed | 1 |
| L2.7 | `2.9-query-rewrite` | `python chapters/part2-rag/2.9-query-rewrite/gate/gate_check.py` | 0/16 passed | 1 |
| L2.8 | `2.10-chroma-persist` | `python chapters/part2-rag/2.10-chroma-persist/gate/gate_check.py` | 0/9 passed | 1 |
| L2.9 | `2.13-static-context-skills` | `python chapters/part2-rag/2.13-static-context-skills/gate/gate_check.py` | 0/11 passed | 1 |
| L2.10 | `2.14-memory-compaction` | `python chapters/part2-rag/2.14-memory-compaction/gate/gate_check.py` | 0/11 passed | 1 |
| L2.11 | `2.4-eval-seed` | `python chapters/part2-rag/2.4-eval-seed/gate/gate_check.py` | 0/14 passed | 1 |
| L2.12 | `2.15-real-corpus-kb-gate` | `python chapters/part2-rag/2.15-real-corpus-kb-gate/gate/gate_check.py` | 0/12 passed | 1 |

#### (2) 临时参考解验证（验证参考解全部通过，退出码均为 0）

| 章节编号 | 对应目录 | 检查命令 | 参考解结果 | 退出码 |
|---|---|---|---|---|
| L2.1 | `2.12-context-engineering` | `python chapters/part2-rag/2.12-context-engineering/gate/gate_check.py --module .tmp/gate_solutions/v3/2.12.py` | 11/11 passed | 0 |
| L2.2 | `2.1-load-split` | `python chapters/part2-rag/2.1-load-split/gate/gate_check.py --module .tmp/gate_solutions/v3/2.1.py` | 6/6 passed | 0 |
| L2.2 | `2.6-pdf-sources` | `python chapters/part2-rag/2.6-pdf-sources/gate/gate_check.py --module .tmp/gate_solutions/v3/2.6.py` | 9/9 passed | 0 |
| L2.3 | `2.2-embed-retrieve` | `python chapters/part2-rag/2.2-embed-retrieve/gate/gate_check.py --module .tmp/gate_solutions/v3/2.2.py` | 9/9 passed | 0 |
| L2.4 | `2.3-minimal-rag` | `python chapters/part2-rag/2.3-minimal-rag/gate/gate_check.py --module .tmp/gate_solutions/v3/2.3.py` | 10/10 passed | 0 |
| L2.5 | `2.7-chunk-strategy` | `python chapters/part2-rag/2.7-chunk-strategy/gate/gate_check.py --module .tmp/gate_solutions/v3/2.7.py` | 7/7 passed | 0 |
| L2.6 | `2.8-hybrid-search` | `python chapters/part2-rag/2.8-hybrid-search/gate/gate_check.py --module .tmp/gate_solutions/v3/2.8.py` | 7/7 passed | 0 |
| L2.6 | `2.11-multimodal-rerank` | `python chapters/part2-rag/2.11-multimodal-rerank/gate/gate_check.py --module .tmp/gate_solutions/v3/2.11.py` | 8/8 passed | 0 |
| L2.7 | `2.9-query-rewrite` | `python chapters/part2-rag/2.9-query-rewrite/gate/gate_check.py --module .tmp/gate_solutions/v3/2.9.py` | 16/16 passed | 0 |
| L2.8 | `2.10-chroma-persist` | `python chapters/part2-rag/2.10-chroma-persist/gate/gate_check.py --module .tmp/gate_solutions/v3/2.10.py` | 9/9 passed | 0 |
| L2.9 | `2.13-static-context-skills` | `python chapters/part2-rag/2.13-static-context-skills/gate/gate_check.py --module .tmp/gate_solutions/v3/2.13.py` | 11/11 passed | 0 |
| L2.10 | `2.14-memory-compaction` | `python chapters/part2-rag/2.14-memory-compaction/gate/gate_check.py --module .tmp/gate_solutions/v3/2.14.py` | 11/11 passed | 0 |
| L2.12 | `2.15-real-corpus-kb-gate` | `python chapters/part2-rag/2.15-real-corpus-kb-gate/gate/gate_check.py --module .tmp/gate_solutions/v3/2.15.py` | 12/12 passed | 0 |

### 2. 测试

执行命令：
```bash
.\.venv\Scripts\python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
```
执行结果：
```text
63 passed, 1 warning in 11.49s (退出码 0)
```
其中 `chapters/test_v3_lessons.py` 包含 29 项单元测试（涵盖 V3-0、V3-1 与 V3-2 新增的 9 项 L2 纯函数断言）。

### 3. 断链与静态检查

- **断链检查**：
  ```bash
  .\.venv\Scripts\python.exe tools/check_course_links.py
  ```
  结果：350 份 Markdown 文件，0 断链（退出码 0）。
- **Ruff 静态代码检查**：
  ```bash
  .\.venv\Scripts\python.exe -m ruff check --target-version py311 chapters/part2-rag/ common.py chapters/test_v3_lessons.py
  ```
  结果：`All checks passed!`（退出码 0）。

### 4. LangChain 边界与标签检查

- **LangChain 边界检查**：
  对 `chapters/part2-rag/` 目录下全部非 `_langchain.py` 脚本执行正则表达式排查，0 个违规导入。
- **v2 映射检查**：
  ```bash
  .\.venv\Scripts\python.exe tools/apply_v2_map.py --check
  ```
  结果：`合计：111 份 README：inserted=0 updated=0 unchanged=111`（退出码 0）。
- **v3 映射检查**：
  ```bash
  .\.venv\Scripts\python.exe tools/apply_v3_map.py --check
  ```
  结果：本批次新建的 4 个章节（`2.12`、`2.13`、`2.14`、`2.15`）全部为 `[unchanged]`。

### 5. 参考实现启动运行检查

使用 `tools/run_chapter.py` 对本阶段全部 14 个参考实现进行执行验证：
```text
OK: 2.12 (context_engineering.py)
OK: 2.1 load_split.py
OK: 2.6 pdf_sources.py
OK: 2.2 embed_retrieve.py
OK: 2.3 minimal_rag.py
OK: 2.7 chunk_strategy.py
OK: 2.8 hybrid_search.py
OK: 2.11 multimodal_rerank.py
OK: 2.9 query_rewrite.py
OK: 2.10 chroma_persist.py
OK: 2.13 skills_loader.py
OK: 2.14 memory_compaction.py
OK: 2.4 eval_seed.py
OK: 2.15 kb_pipeline.py
ALL 14 REFERENCE IMPLEMENTATIONS RUN SUCCESSFULLY VIA RUN_CHAPTER! (退出码 0)
```

## 细则偏离

无。严格遵循 `docs/v3/specs/L2.md` 与 `docs/v3/conventions.md`。

## 未验证

1. 真实大模型在线 API 调用（如 `--live` 模式需配置外部商用密钥 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`，受限于零成本与离线隔离约束，未在本次本地测试中触发外部扣费调用）。
2. `fetch_corpus.py` 完整下载百兆公网大文件（受限于离线环境与网络波动，测试通过 `--dry-run` 验证清单元数据完整性，Gate 与本地流水线运行均基于 `gate/fixtures/` 离线确定性样本）。

## 复现方式

在仓库根目录下激活 `.venv` 虚拟环境后执行：
```bash
# 验证全部 gate 骨架与临时解
.\.venv\Scripts\python.exe chapters/part2-rag/2.15-real-corpus-kb-gate/gate/gate_check.py
.\.venv\Scripts\python.exe chapters/part2-rag/2.15-real-corpus-kb-gate/gate/gate_check.py --module .tmp/gate_solutions/v3/2.15.py

# 运行回归测试套件
.\.venv\Scripts\python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q

# 检查链接与静态规范
.\.venv\Scripts\python.exe tools/check_course_links.py
.\.venv\Scripts\python.exe -m ruff check --target-version py311 chapters/part2-rag/ common.py chapters/test_v3_lessons.py
.\.venv\Scripts\python.exe tools/apply_v2_map.py --check
```

## 边界

- `flagship-project/` 保持历史冻结快照，未作任何改动。
- 本批次所有改动均在 `wip-v3-2` 分支完成，未合入 `master`。
