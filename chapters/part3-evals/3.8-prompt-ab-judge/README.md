# L3.6 扩展：Prompt A/B 指标 · Gate（原 3.8）

[全书目录](../../README.md) · [上一章 3.7](../3.7-eval-regression-curve/README.md) · [下一章 3.9](../3.9-agent-trajectory-eval/README.md)

- **能力**：归一化答案；判拒答；关键词/引用命中率；拒答一致性。
- **v2 路径**：L3.6 / 核心（Gate；Prompt A/B 指标）
- **前置**：3.2（指标）。
- **时间盒**：4 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `prompt_ab_judge.py`。
- **验收命令**：

```bash
python chapters/part3-evals/3.8-prompt-ab-judge/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

A/B 选 prompt 不能靠感觉：全角/空白导致关键词误判、拒答词漏配、无关键词/无来源时除零、误拒答被算通过。

## 任务

实现 `normalize`、`looks_refused`、`keyword_score`、`citation_score`、`refusal_alignment`：

| 指标 | 口径 |
|---|---|
| `normalize` | 转小写并去除全部空白字符 |
| `looks_refused` | 出现任一拒答提示词判定为 True |
| `keyword_score` | 命中关键词/全部；无关键词记 1.0 |
| `citation_score` | 命中来源/全部；无来源记 1.0 |
| `refusal_alignment` | 实际拒答与用例期望一致记 1.0，否则记 0.0 |

关键口径：`normalize` 小写并去所有空白。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 全角/空格 | 归一化后匹配 |
| 2 | “信息不足” | refused=True |
| 3 | 关键词 2 中 1 | 0.5 |
| 4 | 无关键词/无来源 | 1.0 |
| 5 | 误拒答/正常答案 | 0/1 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 3.8
```

对照时只回答：

1. 原生参考实现如何通过 Strict 与 Helpful 两版 Prompt 控制回答风格与来源标注？
2. 在关键词命中率与拒答一致性评测中，文本归一化（normalize）解决了什么现实问题？
3. 为什么 A/B 测试必须在同一份黄金测试集上运行才能得出科学结论？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（5/5）。
- workbook 里的失败分析与三个问题的回答。

## 边界

- 不调用模型/LangSmith，只算指标。
- 真实 A/B 结论需真实运行与评测集。
