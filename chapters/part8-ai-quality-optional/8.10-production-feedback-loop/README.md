# L3.7 反馈闭环 · Gate（原 8.10）

[全书目录](../../README.md) · [上一章 8.9](../8.9-ci-layered-gate/README.md) · [下一章 9.1](../../part9-enterprise-infra-optional/9.1-intent-fewshot/README.md)

- **能力**：反馈入队去重；只审核负反馈；人工 approve；只导出已批准样本。
- **v2 路径**：L3.7 / 核心阅读（Gate；反馈闭环）
- **v3 路径**：L3.8 / 核心阅读（归入 L3.8）
- **前置**：5.4（SQLite）、3.4（评测集）。
- **时间盒**：4 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/feedback_loop.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.10-production-feedback-loop/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

线上反馈直接进评测集，会把噪声/攻击样本当标准答案；未审核、重复、点赞样本混入都会污染回归。

## 任务

实现 `FeedbackQueue`：

| 方法 | 要求 |
|---|---|
| submit | rating -1/1；case_id/question 非空；重复返回 False |
| review_queue | 只返回 rating<0 且 pending |
| approve | 标记 approved；不存在 KeyError |
| export | 只导出 approved，字段 id/question/answer/sources/reason |

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 重复 case_id | 第二次 False |
| 2 | rating=0/空问题 | `ValueError` |
| 3 | 正反馈/已批准 | 不进审核队列 |
| 4 | approve + 导出 | 1 条 approved |
| 5 | 未审核导出 | 0 条 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 临时文件，不接真实反馈库。
- 人工审核质量/预期答案补写未覆盖。
