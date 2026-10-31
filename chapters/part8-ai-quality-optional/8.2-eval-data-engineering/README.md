# L8 评测数据工程 · Gate（原 8.2）

[全书目录](../../README.md) · [上一章 8.1](../8.1-risk-modeling/README.md) · [下一章 8.3](../8.3-mock-contract-invariant/README.md)

- **能力**：用例校验；数据集去重；批量校验；标签筛选；带版本保存/加载。
- **v2 路径**：L8 / 选做（Gate；评测数据工程）
- **v3 路径**：选修 / 选修（AI 质量工程专项，评测岗加分）
- **前置**：3.4（评测集 schema）。
- **时间盒**：4 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/dataset.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.2-eval-data-engineering/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

评测集脏了，后面全白测：空 id/问题、应答题没关键词、重复 id、保存丢字段、加载版本丢失。

## 任务

实现 `validate_case` 与 `EvalDataset`：

| 接口 | 要求 |
|---|---|
| validate_case | id/question 非空；非拒答至少一个关键词 |
| add | 重复 case_id -> ValueError |
| validate | 只返回有问题的 {case_id: errors} |
| by_tag | 按加入顺序筛选 |
| save/load | 带 version 往返，缺省字段用默认值 |

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 空问题/无关键词 | 报错 |
| 2 | 拒答无关键词 | 合法 |
| 3 | 重复 id | `ValueError` |
| 4 | 一条坏用例 | 只报该条 |
| 5 | 保存/加载 | version、tags、case 保留 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 临时文件，不接数据库/远端数据集。
- 数据代表性/标注质量未验证。
