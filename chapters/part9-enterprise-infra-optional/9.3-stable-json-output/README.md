# L9 稳定 JSON 契约 · Gate（原 9.3）

[全书目录](../../README.md) · [上一章 9.2](../9.2-slot-filling/README.md) · [下一章 9.4](../9.4-intent-workflow/README.md)

- **能力**：解析围栏 JSON；严格字段/类型校验；多余字段策略；最多 repair 一次。
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：1.3（结构化输出）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/structured_json.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.3-stable-json-output/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

“让模型输出 JSON”最常见的坑：

- 带 ```json 围栏，直接 `json.loads` 失败；
- bool 被当成 int（Python 子类）；
- 缺字段/多字段静默通过；
- 解析失败无限 repair，形成模型循环；
- repair 后不重新校验。

这个 gate 用固定文本验证契约和 repair 边界。

## 任务

实现 `parse_model_json(text, fields, allow_extra=False, repair=None)`：

| 规则 | 说明 |
|---|---|
| 围栏 | 支持 ```json ... ``` |
| 对象 | 非对象/坏 JSON -> `StructuredOutputError` |
| 字段 | 缺字段报错；默认不允许多余字段 |
| 类型 | `type(value) is expected`，bool 不能当 int |
| repair | 首次失败调一次；仍失败抛错 |
| 返回 | 只含声明字段 |

关键口径：repair 最多一次；allow_extra=True 时忽略多余字段但仍只返回声明字段。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 围栏 JSON | 正常解析 |
| 2 | bool 当 int | 报错 |
| 3 | 缺字段/多字段 | 报错/allow_extra 放行 |
| 4 | 数组/坏 JSON | 报错 |
| 5 | repair 成功 | 调一次并返回 |
| 6 | repair 仍坏 | 抛错 |

## 验收标准

`gate_check.py` 的 6 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- gate 不调用模型，只验证解析/校验。
- 真实模型输出分布、repair prompt 见参考实现。
