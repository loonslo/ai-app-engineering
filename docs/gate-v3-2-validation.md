# V3-2 阶段 2 上下文工程与检索修复验证 · 2026-10-29

本验证记录对应针对第三轮复核（`docs/v3/reviews/V3-2.md` · 2026-10-29 第三次复核）的整改与实测。重点闭环 M9-r3（补全第 11 节命令 1–10 验证记录与偏离说明、将重排作用标注为推测）、N9（纠正 2.9 README 行业参考文献与成本延迟出处）、N10（2.15 严格核验 24 份语料完整性与哈希）及 N6-r（向量缓存键计入模型路径）。

---

## 一、本次整改明细

| 编号 | 涉及章节 / 文件 | 问题分类 | 整改与实现说明 |
|---|---|---|---|
| **N9** | `2.9/README.md` | 主要问题 | **文献引用真实性与出处纠正**：<br>1. 彻底删除无法查证的假想出处（“Pinecone & LlamaIndex 指南”）；<br>2. 忠实引用 Gao et al.《RAG Survey》（[arXiv:2312.10997](https://arxiv.org/abs/2312.10997)，v5 于 2024-03-27）与 Anthropic《Introducing Contextual Retrieval》（[官方博文](https://www.anthropic.com/news/contextual-retrieval)，2024-09-19），更正原题与实测结论（为分块补全上下文结合 BM25 混合检索使失败检索减少 49%，结合重排后减少 67%）；<br>3. 细则要求的 2026 年成本延迟对比，引入一手论文 [arXiv:2601.07711](https://arxiv.org/abs/2601.07711)《Is Agentic RAG worth it?》（2026-01-12；论文在 FiQA、NQ、FEVER、CQADupStack-EN 四个数据集上比较 Agentic RAG 与自带改写、路由和重排的 Enhanced RAG：意图判断在 FiQA、CQADupStack-EN 上略好但在 FEVER 上 F1 低 28.8 分；表 9 成本与延迟分析显示，设定最大轮数的 Agentic RAG 延迟平均约 1.5 倍、输入 token 平均约 3.3 倍、成本最高约 3.6 倍），为权衡表提供实验依据；全部标注官方链接与读取日期（2026-10-29）。 |
| **N10** | `2.15/kb_pipeline.py`<br>`2.15/README.md` | 主要问题 | **语料完整性与哈希严格核验**：<br>1. `KnowledgePipeline` 初始化时通过 `_verify_corpus_completeness()` 逐一核验 `fetch_corpus.py` 中登记的全部 24 份语料的文件存在性与 SHA256 校验和；<br>2. 遇到部分下载、文件缺失或损坏时，列出具体文件名、输出清晰可读指引并以退出码 1 终止，阻止非完整语料静默运行；<br>3. README 同步补充未下载或下载不完整时的强校验与退出行为说明。 |
| **M9-r3** | `docs/gate-v3-2-validation.md`<br>`TASKS.md`<br>`PROJECT_STATUS.md` | 主要问题 | **验证记录完整性与准确性重构**：<br>1. 完整记录 Section 11 命令 1–10（含命令 4 的 63 + 34 项测试、命令 7 LangChain 边界、命令 8 v2 标签 111 unchanged、命令 9 v3 标签、命令 10 全部 16 个参考实现离线启动）；<br>2. 细则偏离中如实记录 2.9 的文献出处与成本延迟权衡实验依据；<br>3. 将“重排与大模型门禁作用”严谨表述为“工程推测与判断，待有重排权重或真实模型时验证”。 |
| **N6-r** | `2.15/kb_pipeline.py` | 次要问题 | **缓存键计入模型路径**：`_build_indexes` 中将 `EMBED_MODEL_PATH` 路径与分块正文一并纳入 SHA256 哈希计算，保证切换模型或变更分块时缓存有效失效与重建。 |

---

## 二、真实组件与测试替身边界

| 模块 / 环节 | 实际运行的真实组件 | 测试替身（Mocks / 离线确定性逻辑） | 未验证 / 降级运行 |
|---|---|---|---|
| **语料接入** | 从 `corpus/downloads/` 真实读取 24 份完整公网下载文档，启动时逐一校验 SHA256；PDF 真实调用 `pypdf` 逐页抽取 | Gate 01–04 项使用内存 `SourceFile` 测试替身 | 扫描页 OCR 识别与复杂版面大模型分析未接入 |
| **文本向量化** | 真实调用本地 `BAAI/bge-small-zh-v1.5` 生成 512 维向量，结合模型路径与分块内容哈希缓存落盘 | Gate 09 项使用固定指标计算函数 | 无伪向量降级 |
| **词法检索** | 真实使用 `rank_bm25.BM25Okapi` + CJK 词面与双字 bigram 分词倒排检索 | 无替身 | 无 |
| **重排模型** | 代码包含 `common.get_cross_encoder()` 调用入口 | 权重不存在时打印降级提示，降级为 RRF 倒数排名加权融合 | **未验证**：开发与测试机器均未放置 `bge-reranker-base` 权重，重排链路未跑真实模型 |
| **大模型问答** | `--live` 显式开启时通过 `get_openai_client()` 发起真实网络调用 | 默认离线模式使用本地提取器，基于上下文装配分界符提取事实编号（未访问 gold 字段） | 未注入正式生产付费 API Key 进行全量在线问答生成 |
| **延迟测量** | 流水线实测消融评测使用 `time.perf_counter()` 动态统计端到端物理耗时 | Gate 检查（第 10 项）按约定使用 cases 中的 `latency_ms` 假时钟字段 | 无 |

---

## 三、Section 11 命令 1–10 逐项复跑验证结果

### 命令 1：Gate 默认骨架检查（全部 13 个 Gate）
运行各章 `gate/gate_check.py`，全部 13 个 Gate 骨架在未实现状态下均严格为 **0 通过（退出码 1）**：
- L2.1 `2.1-load-split/load_split.py`: 0/6 passed (exit 1)
- L2.2 `2.2-embed-retrieve/embed_retrieve.py`: 0/9 passed (exit 1)
- L2.4 `2.3-minimal-rag/minimal_rag.py`: 0/10 passed (exit 1)
- L2.2 `2.6-pdf-sources/pdf_sources.py`: 0/9 passed (exit 1)
- L2.5 `2.7-chunk-strategy/chunk_strategy.py`: 0/7 passed (exit 1)
- L2.6 `2.8-hybrid-search/hybrid_search.py`: 0/7 passed (exit 1)
- L2.7 `2.9-query-rewrite/query_rewrite.py`: 0/16 passed (exit 1)
- L2.8 `2.10-chroma-persist/chroma_persist.py`: 0/9 passed (exit 1)
- L2.6 `2.11-multimodal-rerank/multimodal_rerank.py`: 0/8 passed (exit 1)
- L2.1 `2.12-context-engineering/context_engineering.py`: 0/11 passed (exit 1)
- L2.9 `2.13-static-context-skills/skills_loader.py`: 0/11 passed (exit 1)
- L2.10 `2.14-memory-compaction/memory_compaction.py`: 0/11 passed (exit 1)
- L2.12 `2.15-real-corpus-kb-gate/kb_pipeline.py`: 0/12 passed (exit 1)

### 命令 2 & 3：Gate 临时参考解与确定性检查
运行各章 `gate/gate_check.py --module .tmp/gate_solutions/v3/<章>.py`，全部通过（退出码 0），连跑两次输出完全一致：
- 2.1: 6/6; 2.2: 9/9; 2.3: 10/10; 2.6: 9/9; 2.7: 7/7; 2.8: 7/7; 2.9: 16/16; 2.10: 9/9; 2.11: 8/8; 2.12: 11/11; 2.13: 11/11; 2.14: 11/11; 2.15: 12/12。
- 各参考实现作为 `--module` 传入对应章节 Gate，同样全部通过（退出码 0）。

### 命令 4：回归测试套件全量执行
- **课程工具与章节测试**：
  ```bash
  .venv\Scripts\python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
  ```
  实测输出：**63 passed**, 1 warning in 10.94s（退出码 0）。
- **Capstone 生产回归测试**：
  ```bash
  .venv\Scripts\python.exe -m pytest capstone/test_production.py -q
  ```
  实测输出：**34 passed**, 1 warning in 6.57s（退出码 0）。
- **小计**：测试套件 63 + 34 项全部通过，退出码 0。

### 命令 5：全书 Markdown 链接校验
```bash
.venv\Scripts\python.exe tools/check_course_links.py
```
实测输出：扫描 366 个 Markdown 文件，**0 断链**（退出码 0）。

### 命令 6：Ruff 静态代码检查（目标版本 py311）
```bash
.venv\Scripts\ruff check chapters/part2-rag/ common.py tools/
```
实测输出：`All checks passed!`（退出码 0）。

### 命令 7：LangChain 边界检查
```bash
grep -rlE "^\s*(from|import) (langchain|langgraph)" chapters --include=*.py \
  | grep "chapters/part2-rag" \
  | grep -vE "(minimal_rag_langchain|hybrid_search_langchain)\.py$"
```
实测输出：无输出（退出码 1，表示未匹配到任何非预期框架导入）。除 2.3 `minimal_rag_langchain.py` 与 2.8 `hybrid_search_langchain.py` 两份显式保留的框架对照实现外，Part 2 全部原生实现与 Gate 脚本均零导入 `langchain*` / `langgraph*`（0 泄漏）。

### 命令 8：v2 标签映射检查
```bash
.venv\Scripts\python.exe tools/apply_v2_map.py --check
```
实测输出：`合计：111 份 README：inserted=0 updated=0 unchanged=111`（退出码 0）。

### 命令 9：v3 标签映射检查
```bash
.venv\Scripts\python.exe tools/apply_v3_map.py --check
```
实测输出：本批次 4 个新建章节（`2.12`、`2.13`、`2.14`、`2.15`）全部保持 `[unchanged]`；输出包含既有章节 `inserted=81` 与待建章节 `待建=28`，符合批次推进预期。

### 命令 10：16 个参考实现离线启动与 `--live` 失败场景
1. **16 个参考实现离线启动**：
   使用 `tools/run_chapter.py` 在默认离线模式下逐一运行，全部正常启动并退出（退出码 0，无堆栈）：
   - `2.1 load_split.py` / `load_split_formats.py`: OK
   - `2.2 embed_retrieve.py`: OK
   - `2.3 minimal_rag.py`: OK
   - `2.4 eval_seed.py`: OK
   - `2.5 raw_sdk_rag_agent_loop.py`: OK
   - `2.6 pdf_sources.py`: OK
   - `2.7 chunk_strategy.py`: OK
   - `2.8 hybrid_search.py`: OK
   - `2.9 query_rewrite.py`: OK
   - `2.10 chroma_persist.py`: OK
   - `2.11 multimodal_rerank.py`: OK
   - `2.12 context_engineering.py`: OK
   - `2.13 skills_loader.py`: OK
   - `2.14 memory_compaction.py`: OK
   - `2.15 kb_pipeline.py`: OK
2. **`--live` 失败场景实测**：
   - **缺密钥场景**（`LLM_PROVIDER=openai`, `OPENAI_API_KEY=""`）：2.3、2.9、2.12、2.14、2.15 全部输出清晰可读错误提示，**退出码 1，零 Python 堆栈**；
   - **模型网络不可达场景**（`OPENAI_BASE_URL="http://127.0.0.1:9999/v1"`, `NO_PROXY="127.0.0.1,localhost"`）：2.3、2.9、2.12、2.14、2.15 均在首个在线请求失败时立即终止，输出可读连接失败提示，**退出码 1，零 Python 堆栈**，2.15 不再输出假实测消融表。

---

### 4. 2.15 真实语料流水线实测输出（离线确定性运行）

```text
=== L2.12 真实资料知识库 v1 流水线 ===
Loading weights: 100%|██████████| 71/71 [00:00<00:00, 8047.22it/s]
[降级提示] 未检测到本地 CrossEncoder 权重（bge-reranker-base），重排阶段降级为 RRF 融合分数加权。
真实语料接入完成：共生成 1019 个多页结构化分块。
加载黄金评测集：共 32 题（包含常规应答、资料外拒答与对抗性 Prompt 注入）。
[运行模式] 默认离线模式：使用本地真实检索 + 离线上下文回答提取器（未访问 gold 字段）。

--- 阈值独立校准（在留出校准集上进行网格搜索，评测集不参与调参）---
校准得出最优阈值：Dense=0.69, BM25=19.0, Hybrid=0.66

--- 启动消融对比评测 ---

消融对比表（实测物理耗时与指标）：
配置名称                      | 引用准确率      | 拒答准确率      | Hit@5      | 平均延迟 (ms) 
---------------------------------------------------------------------------
Dense_Embedding_Only      | 75.00%     | 81.25%     | 100.00%    | 93.55     
BM25_Lexical_Only         | 85.00%     | 90.62%     | 100.00%    | 4.19      
Hybrid_RRF（未启用重排）         | 100.00%    | 71.88%     | 100.00%    | 99.00     

门禁阈值检查（Hybrid_RRF（未启用重排） 生产配置）：
[FAIL] 未达标项：['refusal_accuracy < 0.9']
```

#### 指标分析与未达标归因披露
1. **Hit@5 与引用准确率**：三种检索方案均实现 100% Top-5 召回；Hybrid 配置在应答样本上引用准确率达 100%（单页文档按规范检查至文档级 `#p1`）。
2. **拒答准确率未达标（71.88% < 90%）**：
   - 黄金评测集内 8 道资料外题目均为软件与运维领域同类技术概念（如 Python GIL 细节、Docker Windows 路径、Redis 哨兵裂脑、PostgreSQL 逻辑复制等），与语料库技术词汇高度重叠；
   - 在未加载 Cross-Encoder 跨编码器权重（仅做无监督双塔稠密相似度与 RRF 加权）的情况下，同领域技术查询的倒数排名加权得分容易越过无监督校准阈值 0.66；
   - **工程判断与推测**：在当前离线配置下（缺少本地 `bge-reranker-base` 重排权重、未接入真实商用大模型），三种检索配置的拒答准确率或引用准确率均未能达到 90% 的门禁标准，这是如实测量的工程现状；关于重排模型或大模型反思门禁能否有效提升判界准确率并使系统达标，属于合理技术推测与判断，留待后续学习/试教阶段配置真实模型权重时进一步验证。

---

## 四、细则偏离说明

1. **2.6 保留轻量问答与下游兼容**：细则建议将 2.6 问答部分删去或导入 L2.4。为保证下游章节已有测试通过，2.6 切分复用 2.1，检索复用 2.2，输出保留兼容字典访问；3.7 的 LCEL 语法（`|` 管道）组合登记为已知不兼容，后续由 V3-3 批次统一处理。
2. **2.9 检查项组织、文献引用与成本延迟对比**：
   - Gate 维持前 9 项名称不变，追加 7 项 Agentic 断言（共 16 项）；
   - README 引用了 Gao et al. RAG Survey（arXiv:2312.10997）、Anthropic《Introducing Contextual Retrieval》（2024-09-19）与 arXiv:2601.07711《Is Agentic RAG worth it?》（2026-01-12）三篇一手文献出处与读取日期（2026-10-29）；
   - 细则要求引用 2026 年指南的成本延迟对比：README 中的权衡对比表参考了 arXiv:2601.07711 论文（在 FiQA、NQ、FEVER、CQADupStack-EN 四个数据集上比较 Agentic RAG 与自带改写、路由和重排的 Enhanced RAG：意图判断在 FiQA、CQADupStack-EN 上略好但在 FEVER 上 F1 低 28.8 分；表 9 成本延迟分析显示延迟平均约 1.5 倍、输入 token 平均约 3.3 倍、成本最高约 3.6 倍）；删除了此前无法查证的假想出处。
3. **2.14 记忆超预算保障策略**：若必须保留消息本身超出预算，抛出带原因的 `ValueError`；仅在剩余预算充足时对摘要二分截断；若剩余预算过小无法容纳摘要标记，安全省略摘要。
4. **2.15 跨编码器无权重降级与名称规范**：本地缺失模型权重时，打印降级提示并回退至 RRF 加权融合，消融表名称显式标注为 `Hybrid_RRF（未启用重排）`。
5. **2.15 单页文档 gold 标注粒度**：24 份语料中，单页 Markdown 手册统一以 `#p1` 标注文档来源，因此 Hit@5 与引用准确率在单页文档上检验文档级召回与引用匹配。
6. **2.15 语料完整性强校验与嵌入哈希键**：
   - 流水线启动时严格校验 `CORPUS_MANIFEST` 中 24 份语料的完整性与 SHA256，任一缺失或不符即退出（exit 1），防止部分语料静默运行；
   - 向量缓存键计入 `EMBED_MODEL_PATH` 与分块文本的联合哈希，确保更换模型时缓存自动失效。

---

## 五、未验证事项

1. **商用大模型付费 API 端到端在线调用**：虽然 `--live` 代码与所有异常失败分支均经过实测，但在离线自动化环境中未注入商业付费 API Key 进行全量在线问答生成。
2. **Cross-Encoder 真实权重在线推理**：因开发与测试机器均未挂载 `bge-reranker-base` 权重文件，重排阶段的真实模型推理效果尚未在本地闭环运行。

---

## 六、保护边界与分支说明

- `flagship-project/` 与 `capstone/` 严格受保护，未做任何改动。
- 本批次所有改动均在 `wip-v3-2` 分支完成，未合入 `master`。
