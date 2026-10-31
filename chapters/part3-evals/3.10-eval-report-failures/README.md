# L3.6 扩展：失败诊断 · Gate（原 3.10）

[全书目录](../../README.md) · [上一章 L3.6（3.8）](../3.8-prompt-ab-judge/README.md) · [下一章 L3.7](../3.6-langsmith-eval/README.md)

- **能力**：加载失败库、推断 live/offline、按硬指标分组、统计层分布。
- **v2 路径**：L3.6 / 核心（Gate；失败诊断）
- **v3 路径**：L3.6 / 核心（Gate；失败诊断）
- **前置**：3.7（可选，用来生成真实失败库）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `failure_diagnosis.py`。
- **验收命令**：

```bash
python chapters/part3-evals/3.10-eval-report-failures/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

“错了多少”不等于“错在哪”。失败诊断最容易出这些错：

- 文件缺失/损坏，脚本直接崩；
- 把已通过的 case 也当失败；
- 有真实上下文却按 offline 处理；
- 分组顺序写反（先判生成，把拒答问题归错层）；
- 只看单条，不统计层分布。

这个 gate 用临时失败库，验证加载、模式推断、分组顺序和统计。

## 任务

实现 `gate/starter.py` 的三个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `load_failures` | 读 JSON；只留 `passed=False`；有 `retrieval_context` 判 live；失败报 `ValueError` |
| `classify_by_hard_metrics` | 按拒答 → 引用 → 关键词 → 其他顺序分组 |
| `summarize_layers` | 统计各层数量；空列表返回 `{}` |

关键口径：

- 缺文件/坏 JSON -> `ValueError`。
- `passed` 缺省视为通过，过滤掉。
- 任一失败含非空 `retrieval_context` -> `live`，否则 `offline`。
- 3.7 的失败库现在带 `mode` 字段，但本 gate 的参考实现仍按 `retrieval_context` 推断；用 3.7 离线写出的失败库时，显式加 `--mode offline`，否则会被误判为 live 产物。
- 分组顺序：`refusal_ok=False` > `citation_score<0.67` > `keyword_score<0.67` > 其他。
- 统计只按 `layer_suspected` 计数。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 失败库含 1 条 passed | 只留 2 条失败 |
| 2 | 有真实上下文 | mode=live |
| 3 | 无真实上下文 | mode=offline |
| 4 | 缺文件/坏 JSON | `ValueError` |
| 5 | refusal_ok=False + citation 低 | 拒答层优先 |
| 6 | citation 低 + keyword 低 | 检索/引用层优先 |
| 7 | 全通过硬指标 | 其他/未覆盖 |
| 8 | 统计 | 层计数正确 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS：

- live/offline 加载、缺文件/坏 JSON、分组顺序、分层统计。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么 `passed` 缺省要当“通过”过滤掉？
2. 为什么拒答分组要排在引用/生成前面？
3. 一级分流和二级复核的边界在哪？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（5/5）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 3.10
```

对照时只回答：

1. 参考实现的 `load_failures` 怎么推断 live/offline？
2. 参考实现的分组阈值和你的实现一致吗？
3. 参考实现的 DeepEval 二级复核为什么不在本 gate 内？

## 概念地图

- **只诊断不判决**：诊断给证据；发布门禁在 CI/capstone。
- **一级分流**：硬指标分组，便宜但只能标“疑似”。
- **二级复核**：LLM 维度分，需真实上下文和费用。
- **失败库**：passed=False；来源优先级 --input → shared-data → 自带样本。
- **层分布**：单条看原因，分布看系统性问题。

## 边界

- gate 不跑 DeepEval，只验证加载/分组/统计。
- 通过 gate 只证明诊断结构正确，不证明根因判断准确。
- 真实失败库、私有数据、费用见参考实现。
