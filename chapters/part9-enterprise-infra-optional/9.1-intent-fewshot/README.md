# L9 Few-shot 意图识别 · Gate（原 9.1）

[全书目录](../../README.md) · [上一章 8.10](../../part8-ai-quality-optional/8.10-production-feedback-loop/README.md) · [下一章 9.2](../9.2-slot-filling/README.md)

- **能力**：构造 few-shot 意图提示词；严格解析 intent/confidence，非法值不进业务分支。
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：1.3（结构化输出）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/intent.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.1-intent-fewshot/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

意图识别最容易出这些错：

- 类别不统一，下游分支接不住；
- 模型返回 `refund`，代码却只认 `refund_status`；
- confidence 缺失/越界仍继续；
- 坏 JSON 直接崩；
- 示例太少，模型自由发挥。

这个 gate 用固定 payload 验证提示词契约和解析边界。

## 任务

实现 `build_intent_prompt` 和 `parse_intent_payload`：

| 函数 | 你要交付的行为 |
|---|---|
| `build_intent_prompt` | 含五类意图、JSON 契约、≥3 示例、用户问题；空问题报错 |
| `parse_intent_payload` | 解析 str/dict；校验 intent/confidence |

关键口径：

- 五类：refund_status/order_status/shipping/human_handoff/unknown。
- confidence 必须在 [0,1]。
- 缺字段/非对象/坏 JSON -> `ValueError`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 正常问题 | 提示词含五类/示例/问题 |
| 2 | 空问题 | `ValueError` |
| 3 | 合法 dict/字符串 | 解析成功 |
| 4 | 非法 intent/缺字段 | `ValueError` |
| 5 | confidence -0.1/1.1/"high" | `ValueError` |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- gate 不调用模型，只验证提示词/解析。
- 真实分类准确率需评测集验证。
