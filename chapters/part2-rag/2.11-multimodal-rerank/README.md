# L2.8 重排与多模态 · Gate（原 2.11）

[全书目录](../../README.md) · [上一章 L2.6（2.8）](../2.8-hybrid-search/README.md) · [下一章 L2.7](../2.9-query-rewrite/README.md)

- **能力**：对候选按外部打分重排；处理空候选、坏分数、top-k；计算 recall@k。
- **v2 路径**：L2.8 / 核心（Gate；重排（多模态选做））
- **v3 路径**：L2.6 / 核心（Gate；重排）
- **前置**：2.2（向量召回）、2.4（切分）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 对比分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `multimodal_rerank.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.11-multimodal-rerank/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

> [!IMPORTANT]
> **“混合检索 + 重排”是 2026 年文档问答的默认配置**：先用 BM25 + 向量混合检索（L2.6 / 2.8）广泛召回候选集（如 Top 15-20），再用 Cross-Encoder（如 bge-reranker-base）精排选出最相关的 Top 3-5 片段注入上下文。关于何时让 Agent 决定继续搜索还是停止的 Agentic Retrieval 见 L2.7。

> [!NOTE]
> **多模态与视觉语言模型（VLM）选做说明**：视觉语言模型（VLM）直接解析复杂版面、扫描件与图表文档在 Thoughtworks 技术雷达 Vol.34（https://www.thoughtworks.com/radar ，读取日期：2026-10-28）中被列为 **Assess（评估）**，属于前沿探索方向。本章多模态部分保持选做，主线以成熟的 Cross-Encoder 精排为核心。

## 为什么做这个 gate

重排的常见错误：

- 候选缺字段/分数不是数值，排序时崩；
- 同分顺序不稳定，结果每次不一样；
- `top_k=0` 或负数，返回空；
- 重排函数修改了传入的候选；
- 只看重排后的列表，不用 recall@k 量化有没有漏。

这个 gate 用固定候选和假打分器，验证“稳定排序 + 截断 + 指标”。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `rerank` | 校验候选/top_k/score；按分数降序稳定排序；返回带 score 的 top-k |
| `recall_at_k` | 前 k 个结果覆盖多少相关 ID；无相关 ID 返回 0 |

关键口径：

- `top_k < 1`、`k < 1` -> `ValueError`。
- 候选缺 `id/text` 或类型错 -> `ValueError`。
- `score_fn` 返回非数值或抛异常 -> `ValueError`。
- 同分保持原顺序（稳定排序）。
- 不修改输入候选。
- `recall_at_k = |前k ∩ 相关| / |相关|`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 分数 0.2/0.9/0.5 | 排序 b,c,a |
| 2 | top_k=2 | 只返回 b,c |
| 3 | 同分候选 | 保持原顺序 |
| 4 | 空候选 | `[]` |
| 5 | 候选缺 text / text 非字符串 | `ValueError` |
| 6 | top_k=0 | `ValueError` |
| 7 | score 返回字符串/抛异常 | `ValueError` |
| 8 | recall@2 只覆盖一半 | 0.5 |

## 验收标准

`gate_check.py` 的 8 项全部 PASS：

- 排序/top-k、同分稳定、空候选、非法候选/top_k、非法 score、不修改输入、recall@k、k 校验。

通过后，在 [workbook.md](workbook.md) 写：

1. 重排能补回粗召回漏掉的内容吗？为什么？
2. 同分稳定排序为什么重要？
3. recall@k 和“看起来更相关”相比，哪个更能证明重排有效？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（8/8）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 2.11
```

对照时只回答：

1. 原生参考实现用 `common.get_cross_encoder()` 打分；它和双塔向量检索在计算复杂度上有何区别？
2. 参考实现的 `top_k=3` 对应本 gate 的哪个参数？
3. 为什么说“粗召回宁多勿漏，精排宁精勿滥”？

## 概念地图

- **粗召回 + 精排**：先多召回（Bi-Encoder / BM25），再用更准但更慢的 Cross-Encoder 模型精排。
- **稳定排序**：同分保持原顺序，结果可复现。
- **top-k**：精排不是越多越好；要看 token 预算和噪声。
- **recall@k**：量化前 k 个覆盖多少相关结果；重排不能补回粗召回漏掉的。
- **多模态与 VLM**：Thoughtworks 技术雷达 Vol.34（https://www.thoughtworks.com/radar ，读取日期：2026-10-28）Assess 阶段技术，属于复杂文档解析选做方向。

## 边界

- gate 只做重排与评估指标计算，不依赖本地 reranker 模型。
- 通过 gate 只证明排序/截断/指标结构正确。
- 真实 Cross-Encoder 模型与多模态读图演示见参考实现。
