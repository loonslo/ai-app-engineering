# L2.6 查询改写与 Agentic Retrieval · Gate（原 2.9）

[全书目录](../../README.md) · [上一章 L2.6（2.11）](../2.11-multimodal-rerank/README.md) · [下一章 L2.8](../2.10-chroma-persist/README.md)

- **能力**：构造改写 prompt；解析多行查询；异常回退；实现 Agentic Retrieval 多轮自主检索循环。
- **v3 路径**：L2.7 / 核心（Gate；查询改写）
- **前置**：2.4（切分策略）、2.2（召回）。
- **时间盒**：6 小时（1h 读 + 4h 实现 + 1h 评测分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `query_rewrite.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.9-query-rewrite/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

改写是“用 LLM 改善召回”，但也会引入新失败：

- 模型输出编号/解释/空行，直接拼进检索；
- 改写结果重复原问题，白多调一次模型；
- 模型超时/空输出，整条链路中断；
- 改写条数不设上限，成本和延迟失控；
- **Agentic 多轮检索失控**：Agent 在检索与改写之间死循环，没有明确的停止条件（足够命中、无新改写、最大轮数超限）。

这个 gate 用脚本化替身，把“prompt → 解析 → 回退 → 截断 → Agentic 多轮检索控制流”做成可验证链路。

## 任务

实现 `gate/starter.py` 的四个核心函数/接口：

| 函数 / 接口 | 你要交付的行为 |
|---|---|
| `build_rewrite_prompt` | 包含原问题/历史；明确要求每行一条、不要编号 |
| `parse_rewrites` | 去除编号（`1.`/`-` 等）、去空行、去重、保序、截断到 `max_queries` |
| `rewrite_query` | 调模型 → 解析 → 原问题置于首位 → 失败回退原问题 |
| `agentic_retrieve` | 多轮检索循环：每轮检索累计去重；命中满足 `min_hits` 停 ("enough")；改写返回 None 停 ("no_rewrite")；达到 `max_rounds` 停 ("max_rounds") |

关键口径：

- 空问题、`max_queries < 1`、`max_rounds < 1`、`min_hits < 1` -> 抛 `ValueError`。
- `queries[0]` 永远是原问题。
- 模型空输出/解析后没有新查询 -> `queries=[原问题]`，`error="empty_rewrite"`。
- 模型异常 -> `queries=[原问题]`，`error="model_error"`。
- Agentic 检索中：
  - 跨轮命中按 `f"{h.source}#{h.index}"` 累计去重；
  - 最终结果按 `score` 降序稳定排序；
  - 终止原因严格受限于 `"enough"`、`"no_rewrite"`、`"max_rounds"`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 模型输出带 `1.`/`2)`/`-` 编号 | 解析后去掉编号 |
| 2 | 重复行 | 去重 |
| 3 | 超过 max_queries | 截断 |
| 4 | 空输出 | 回退原问题，`empty_rewrite` |
| 5 | 只输出原问题 | 回退原问题，`empty_rewrite` |
| 6 | 模型超时 | 回退原问题，`model_error` |
| 7 | 空问题 / max_queries=0 | `ValueError` |
| 8 | 第 1 轮即命中充足 (>= min_hits) | 立即停止，`rounds=1`，`stopped_reason="enough"` |
| 9 | 改写函数返回 None | 立即停止，`stopped_reason="no_rewrite"` |
| 10 | 命中始终不足 | 达到 `max_rounds` 强制退出，`stopped_reason="max_rounds"` |

## 验收标准

`gate_check.py` 的 16 项（9 项改写基础 + 7 项 Agentic 检索循环）全部 PASS：

1. 改写 prompt
2. 解析编号/去重
3. max_queries 解析限制
4. 正常改写
5. 改写条数限制
6. 空输出回退
7. 无新查询回退
8. 模型异常回退
9. 参数校验
10. Agentic 第1轮命中足够停止
11. Agentic 改写后命中足够停止
12. Agentic 改写返回None停止
13. Agentic 达到最大轮数停止
14. Agentic 跨轮去重
15. Agentic 最终按分数降序
16. Agentic 参数校验

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么改写结果要把原问题放第一位？
2. 相比单次 Multi-Query，Agentic Retrieval 动态检索循环的核心价值与主要成本是什么？
3. Agentic 循环为什么要强制设置 `max_rounds` 硬上限？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（16/16）。
- workbook 里的失败分析与三个问题的回答。

## 什么时候让 Agent 直接搜索

在企业级 AI 系统中，检索架构存在两条路线：
1. **预建索引 RAG（Pre-indexed RAG）**：先切分、离线向量化入库，运行时只做单次或批处理检索。
2. **Agent 直接动态搜索（Agentic On-demand Retrieval）**：将搜索作为 Agent 的 Tool，模型边推理边决定搜什么、搜几次。

### 适用场景划分

- **适合 Agent 直接搜索**：
  - **代码库与开发工具**：代码高频变更（git commit 频繁），每次改动重建向量库成本高；通过 `ripgrep`、LSP 或文件目录工具让 Agent 动态搜索更实时。
  - **高频变化的工作流数据**：实时运维日志、工单变更、CRM 实时跟进记录等。
- **适合预建索引 RAG**：
  - 相对静态的产品手册、规章制度、合规标准、技术白皮书。

### 成本与延迟权衡

| 维度 | 传统预建索引 RAG | Agent 动态循环搜索 (2~3 轮) |
|---|---|---|
| **端到端延迟** | 单次网络请求与向量计算，响应迅速 | 依赖多轮大模型推理与工具往返，延迟随轮数线性增加 |
| **Token 开销** | 仅单次检索上下文与问答消耗 | 多轮重写、候选反思与累计上下文导致 Token 消耗成倍增长 |
| **数据新鲜度** | 依赖定时索引同步（存在分钟至小时级延迟） | 直读最新源头工具（秒级实时性） |
| **召回控制** | 确定性算法（BM25 + 向量 Top-K），行为可预测 | 依赖大模型意图理解与改写质量，存在波动性 |

### 行业参考与实践指南

查询改写（Query Expansion / Multi-Query）、假设性文档嵌入（HyDE）以及 Agentic 检索循环的业界参考：
1. **Gao et al.**: *Retrieval-Augmented Generation for Large Language Models: A Survey* ([arXiv:2312.10997](https://arxiv.org/abs/2312.10997)，v5 更新于 2024-03-27；读取日期：2026-10-29；系统梳理 Pre-retrieval 阶段的 Query Rewriting、Sub-Query 与 Modular RAG 架构演进)。
2. **arXiv:2601.07711**: *Is Agentic RAG worth it? An experimental comparison of RAG approaches* ([arXiv:2601.07711](https://arxiv.org/abs/2601.07711)，2026-01-12；读取日期：2026-10-29；论文在 FiQA、NQ、FEVER、CQADupStack-EN 四个数据集上比较 Agentic RAG 与自带改写、路由和重排的 Enhanced RAG：判断用户意图时，Agentic 在 FiQA、CQADupStack-EN 上略好，在 FEVER 上明显较差（F1 低 28.8 分）；Agentic 的查询改写带来更好的检索质量，Enhanced 的重排更准。成本与延迟分析（表 9：FiQA 与 CQADupStack-EN，GPT-4.1-nano 与 Qwen3 0.6B–32B，Agentic 最多 3 轮）显示，Agentic 的端到端延迟平均约 1.5 倍，输入 token 平均约 3.3 倍，成本最高约 3.6 倍。为上表的成本延迟对比提供实验依据)。
3. **Anthropic Engineering**: *Introducing Contextual Retrieval* ([Anthropic 官网](https://www.anthropic.com/news/contextual-retrieval)，2024-09-19；读取日期：2026-10-29；探讨在索引切分阶段为分块补全文档上下文并结合 BM25 混合检索，实测使失败检索减少 49%，结合重排后减少 67%)。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 2.9
```

对照时只回答：

1. 原生参考实现用 OpenAI SDK 实现了 Multi-Query、HyDE 与 Agentic Retrieval；这三者在召回广度与调用开销上有何差异？
2. HyDE 生成的“假设性答案”即使包含事实错误，为什么仍可能改善向量检索效果？
3. 参考实现里的 `agentic_retrieve` 设定了哪些终止防御机制？

## 概念地图

- **Multi-Query**：一题多问，同义词拓展，增加粗召回覆盖面。
- **HyDE**：假想正文答案，利用 Document-to-Document 相似度对齐短查询与长文档。
- **Agentic Retrieval**：模型根据中间结果自适应迭代检索，适合复杂多跳问答。
- **防御性退出**：`enough` / `no_rewrite` / `max_rounds`，彻底杜绝 Agent 检索死循环。

## 边界

- gate 只验证控制流、解析逻辑与去重排序，不消耗真实 LLM 额度。
- 生产环境使用 Agentic Retrieval 必须绑定租户级单次对话 Token 与轮数配额。
