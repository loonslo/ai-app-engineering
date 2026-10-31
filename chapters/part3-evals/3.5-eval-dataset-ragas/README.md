# L3.5 Ragas 与指标口径 · Gate（原 3.5）

[全书目录](../../README.md) · [上一章 L3.4](../3.3-llm-judge/README.md) · [下一章 L3.6（3.7）](../3.7-eval-regression-curve/README.md)

- **能力**：合并基础集/补充集；校验拒答题；把非拒答样本整理成 RAGAS 四列。
- **v2 路径**：L3.5 / 核心（Gate；Ragas 与指标口径）
- **v3 路径**：L3.5 / 核心（Gate；指标口径）
- **前置**：3.4（schema 与基础集）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `dataset_ragas.py`。
- **验收命令**：

```bash
python chapters/part3-evals/3.5-eval-dataset-ragas/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

把两批样本合在一起，最容易破坏“单一数据源”：

- 两批 ID 重复，失败 case 无法定位；
- 拒答题没标 `should_refuse=True`，被当成应答题；
- 拒答题带关键词，指标口径混乱；
- RAGAS 行把拒答题也塞进去，指标失真；
- `ask_fn` 返回缺字段，整批评估崩。

这个 gate 用固定样本和假 `ask_fn`，验证合并、校验、RAGAS 行。

## 任务

实现 `gate/starter.py` 的三个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `merge_sets` | 合并 base/extra；不修改输入；ID 唯一；缺 id/type 报错 |
| `validate_full_set` | 校验空集/题型/ID/拒答题；返回计数 |
| `build_ragas_rows` | 跳过 refuse；校验 answer/contexts；返回四列 |

关键口径：

- 合并顺序：base 在前，extra 在后；重复 ID -> `ValueError`。
- 空集 -> `ok=False`，`errors` 含 `empty`。
- 拒答题：`should_refuse=True`，`keywords` 为空。
- RAGAS 四列：`question/answer/contexts/ground_truth`；拒答题不进入。
- `contexts` 必须是字符串列表；`ask_fn` 结果缺字段/类型错 -> `ValueError`。
- 不修改输入。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | base+extra 合并 | 顺序正确、输入不变 |
| 2 | 重复 ID | `ValueError` |
| 3 | 缺 type | `ValueError` |
| 4 | 合法全集 | `ok=True`，type_counts/refuse_count 正确 |
| 5 | 空集/拒答带关键词 | `ok=False`，有 errors |
| 6 | RAGAS 行 | 跳过 refuse，三行非拒答 |
| 7 | `ask_fn` 缺 contexts/类型错 | `ValueError` |
| 8 | 检查输入 | 未被修改 |

## 验收标准

`gate_check.py` 的 8 项全部 PASS：

- 合并/副本、重复 ID、缺字段、全集校验、空集/拒答错误、RAGAS 四列、ask_fn 校验、不修改输入。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么拒答题不进入 RAGAS？
2. 合并时最容易漏掉哪种校验？
3. RAGAS 四列缺一列会怎样？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（8/8）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 3.5
```

对照时只回答：

1. 参考实现怎么合并 base/extra？有没有校验 ID 重复？
2. 参考实现为什么跳过拒答题再喂 RAGAS？
3. RAGAS 的四个字段分别对应你的哪个输出？

## 概念地图

- **单一数据源**：`eval_set_full.json` 被 3.2/3.3/3.6/3.7 共用。
- **拒答题**：不进 RAGAS；用拒答正确率单独评。
- **引用题**：答对还不够，要标对来源。
- **RAGAS 四列**：question/answer/contexts/ground_truth；缺一列指标就失真。
- **数据契约**：ID 唯一、字段齐全、类型正确。

## 边界

- gate 不跑 RAGAS，只验证数据准备。
- 通过 gate 只证明合并/校验/四列结构正确。
- RAGAS 真实分数、模型费用、偏差见参考实现和第 3 篇后续。
