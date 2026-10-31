# L9 意图工作流 · Gate（原 9.4）

[全书目录](../../README.md) · [上一章 9.3](../9.3-stable-json-output/README.md) · [下一章 9.5](../9.5-postgres-rls/README.md)

- **能力**：低置信/unknown 转人工；human_handoff 转人工；缺槽位追问；补齐后 ready；会话隔离。
- **v2 路径**：L9 / 选做（Gate；意图工作流）
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：9.1（意图）、9.2（槽位）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/workflow.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.4-intent-workflow/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

把分类接到业务，最容易出这些错：

- 低置信也进入退款分支；
- unknown 当普通问答；
- 缺订单号直接执行；
- 补槽轮又调一次分类，用户改口串台；
- 会话状态不隔离。

这个 gate 用假分类器验证分流和状态机。

## 任务

实现 `ConversationState` 和 `CustomerWorkflow.handle`：

| 情况 | 动作 |
|---|---|
| 低置信/unknown | 清状态 -> handoff |
| human_handoff | 清状态 -> handoff |
| 缺必填槽位 | 保存状态 -> needs_slot + 追问 |
| 齐全 | 清状态 -> ready |

关键口径：

- `MIN_CONFIDENCE=0.75`。
- 有待补槽位时不再分类，沿用上一轮 intent。
- 会话按 session_id 隔离。
- 补槽轮的新订单号覆盖旧值。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | confidence 0.5 | handoff |
| 2 | unknown | handoff |
| 3 | human_handoff | handoff |
| 4 | 退款无订单号 | needs_slot |
| 5 | 补“订单号 A100” | ready，且不再分类 |
| 6 | s1/s2 交叉 | 互不影响 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 内存状态，不验证持久化/多租户。
- 真实分类器/订单系统未接入。
