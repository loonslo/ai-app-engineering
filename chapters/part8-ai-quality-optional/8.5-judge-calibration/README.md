# L3.4 扩展：Judge 校准 · Gate（原 8.5）

[全书目录](../../README.md) · [上一章 8.4](../8.4-rag-layered-testing/README.md) · [下一章 8.6](../8.6-agent-trajectory-testing/README.md)

- **能力**：用人工标签校准 Judge 阈值；计算一致率、Cohen's kappa、混淆矩阵。
- **v3 路径**：L3.4 / 核心阅读（归入 L3.4）
- **前置**：3.3（LLM Judge）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/judge.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.5-judge-calibration/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

把 Judge 分数直接当真值，会把系统性偏差放大到 CI：

- 阈值拍脑袋，人工标签对不上；
- 只看一致率，不看“靠运气也会一致”；
- 混淆矩阵只有总数，分不清误报/漏报；
- 样本为空/全同类，kappa 无意义却照算。

这个 gate 用合成标签，验证阈值搜索、一致率和 kappa。

## 任务

实现 `gate/starter.py` 的 `labels_at` 和 `calibrate`：

| 函数 | 你要交付的行为 |
|---|---|
| `labels_at` | `judge_score >= threshold` -> 1/0，返回 (gold, judge) |
| `calibrate` | 候选阈值中选一致率最高（并列取小）；返回 threshold/agreement/kappa/confusion |

关键口径：

- 空样本 -> `ValueError`。
- `agreement = 一致条数 / 总数`。
- 并列一致率取较小阈值。
- `confusion` 四格 `{(0,0),(0,1),(1,0),(1,1)}` 都要有。
- `kappa = (observed-expected)/(1-expected)`；expected=1 记 1.0。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 阈值 0.5 标注 | (1,1)/(0,0) |
| 2 | 0.5/0.7 并列 | 取 0.5 |
| 3 | 完全一致 | agreement=1、kappa=1 |
| 4 | 误报/漏报混合 | 混淆矩阵四格计数正确 |
| 5 | 随机一致 | kappa=0 |
| 6 | 空样本 | `ValueError` |

## 验收标准

`gate_check.py` 的 6 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 合成分数只验证校准算法，不证明真实 Judge 可靠。
- 样本过少/分布单一时 kappa 不稳定。
