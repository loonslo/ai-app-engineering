# L3.2 评测集建设 · Gate（原 3.4）

[全书目录](../../README.md) · [上一章 L3.1](../3.1-error-analysis/README.md) · [下一章 L3.3（3.2）](../3.2-eval-basics/README.md)

- **能力**：校验评测集 schema、ID 唯一、题型覆盖；把错误一次收全，而不是第一条就中断。
- **v3 路径**：L3.2 / 核心（Gate；评测集建设）
- **前置**：3.3（基础评测）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `dataset_build.py`。
- **验收命令**：

```bash
python chapters/part3-evals/3.4-eval-dataset-build/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

评测集脏了，后面的指标全白算。常见问题：

- 样本缺 `reference/keywords/expect_source`，评测时才发现；
- ID 重复，失败 case 无法定位；
- 题型写错，覆盖统计失真；
- 只报第一条错误，修完再跑又冒出下一条；
- 空评测集被当成“全部通过”。

这个 gate 用内存里的样本，验证 schema 校验和覆盖统计。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `validate_dataset` | 校验字段/ID/类型/题型；返回 `ok/errors/type_counts`；错误一次收全 |
| `coverage` | 统计总数、各题型数量、缺失题型 |

关键口径：

- 空列表 -> `ok=False`，`errors` 含 `empty`。
- 每行含 `SCHEMA_FIELDS` 全部字段；`id` 非空唯一；`question/reference` 非空字符串。
- `keywords` 是 list；`should_refuse` 是 bool；`type` 在 `fact/multi_hop/refuse/citation`。
- 每条错误带 id 或行号；不因第一条错误中断。
- `coverage.types` 只统计合法题型；`missing_types` 是全集减已出现。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 合法 3 条 | `ok=True`，type_counts 正确 |
| 2 | 空列表 | `ok=False`，含 empty |
| 3 | 缺 `reference` | 报错并带 id |
| 4 | 重复 ID | 报 duplicate/重复 |
| 5 | 未知 type / keywords 非 list / should_refuse 非 bool | 报错 |
| 6 | 一行两个错误 | errors ≥2 |
| 7 | 覆盖缺 refuse/citation | missing_types 正确 |

## 验收标准

`gate_check.py` 的 7 项全部 PASS：

- 合法集、空集、缺字段、重复 ID、非法类型、多错误、覆盖。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么错误要一次收全，而不是遇错即停？
2. 空评测集为什么不能算“全部通过”？
3. 题型覆盖统计能发现什么“看起来样本很多”的问题？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（7/7）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 3.4
```

对照时只回答：

1. 参考实现的 `validate` 只检查字段和 ID，缺少哪些校验？
2. 参考实现遇错用 assert 立即中断；这和“收全错误”各适合什么场景？
3. 题型覆盖和样本数量，哪个更能说明评测集质量？

## 概念地图

- **schema**：字段约定；下游 3.2/3.3/3.5/5.8 都依赖它。
- **数据契约**：ID 唯一、字段齐全、类型正确；脏数据会让指标失真。
- **错误收集**：一次收全，减少来回修。
- **题型覆盖**：事实/跨段落/拒答/引用各有作用；只堆事实题会掩盖短板。
- **空集**：不能默认通过；没有样本就没有证据。

## 边界

- gate 用内存样本，不验证样本内容是否真的来自 `test_doc.txt`。
- 通过 gate 只证明 schema/覆盖校验正确，不证明评测集有代表性。
- 拒答题/引用题的补充见 3.5。
