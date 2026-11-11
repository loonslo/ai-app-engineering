# L9 槽位填充 · Gate（原 9.2）

[全书目录](../../README.md) · [上一章 9.1](../9.1-intent-fewshot/README.md) · [下一章 9.3](../9.3-stable-json-output/README.md)

- **能力**：提取订单号；合并上一轮槽位；按意图列出缺失项；一次只追问一个槽位。
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：1.3（结构化输出）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/slots.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.2-slot-filling/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

槽位填充最容易出这些错：

- 把“我要退款”里的模糊词猜成订单号；
- 新值不覆盖旧值，用户改口无效；
- 必填项不区分意图，闲聊也追问订单号；
- 一次追问所有缺失项，用户不知道先答哪个；
- 修改上一轮 state，导致串话。

这个 gate 用固定话术验证提取、合并、缺失和追问。

## 任务

实现 `extract_slots`、`resolve_slots`、`next_question`：

| 函数 | 你要交付的行为 |
|---|---|
| `extract_slots` | 识别订单号/order id，值转大写 |
| `resolve_slots` | 合并 previous + 本轮；返回 intent/values/missing |
| `next_question` | 有缺失返回订单号追问，否则 None |

关键口径：

- 未知 intent -> `ValueError`。
- 新值覆盖旧值；不修改 previous。
- `refund_status/order_status` 必填 order_id；shipping/handoff 不追问。
- 一次只追问第一个缺失项。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 中文/英文订单号 | 提取并大写 |
| 2 | 无订单号 | {} |
| 3 | previous 有旧值+新值 | 新值覆盖 |
| 4 | “我要退款” | missing=order_id |
| 5 | shipping | 不追问 |
| 6 | 未知 intent | `ValueError` |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- gate 用正则提取，不验证模型理解。
- 真实多轮/权限/槽位校验见参考实现与 9.1。
