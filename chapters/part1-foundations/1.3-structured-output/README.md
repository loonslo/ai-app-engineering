# L1.3 结构化输出 · Gate（原 1.3）

[全书目录](../../README.md) · [上一章 L1.3](../1.2-control-output/README.md) · [下一章 L1.5](../1.4-context-memory/README.md)

- **能力**：把模型输出解析成带字段的数据；校验类型与业务范围；失败时只修复一次。
- **v2 路径**：L1.3 / 核心（Gate；结构化输出）
- **v3 路径**：L1.4 / 核心（Gate；结构化输出）
- **前置**：1.1（一次调用）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `structured_output.py`。
- **验收命令**：

```bash
python chapters/part1-foundations/1.3-structured-output/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

“让模型输出 JSON”在 demo 里很顺，在生产里会遇到：

- 模型在 JSON 外面加解释文字，或者用 Markdown 围栏；
- 字段少一个、类型不对（分数变成字符串、`true` 当整数）；
- 分数越界、问题列表里混入非字符串；
- 解析失败后无限重试，成本失控。

这个 gate 让你把结构化输出做成 **解析 → 校验 → 一次修复 → 明确失败**，而不是 `json.loads` 一把梭。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `parse_model_json` | 解析纯 JSON/围栏/带说明文字；按 schema 校验字段与类型；失败只修复一次 |
| `validate_code_review` | 校验 `summary/issues/score`，返回规范化结果；非法抛 `SchemaError` |

关键口径：

- `schema` 是 `{"字段": 类型}`，例如 `{"summary": str, "issues": list, "score": int}`。
- `int` 不接受 `bool`；`list` 只校验容器，元素类型由业务函数再校验。
- 解析/校验失败时，`repair_fn` 最多调用 **一次**；没有 `repair_fn` 直接失败。
- `validate_code_review`：summary 去空白后非空；issues 全是字符串；score 是 1–10 的整数。
- 任何不合法抛 `SchemaError`，不要把底层异常直接抛给调用方。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 纯 JSON | 正常解析 |
| 2 | ```json 围栏 + 前后说明文字 | 正常解析 |
| 3 | 缺 `score` | `SchemaError` |
| 4 | `score: "8"` / `true` / `issues: "x"` | `SchemaError` |
| 5 | JSON 是数组/字符串/数字 | `SchemaError` |
| 6 | 非法 JSON + repair 返回合法 JSON | 成功，repair 只调一次 |
| 7 | 非法 JSON + repair 仍非法 | `SchemaError` |
| 8 | 非法 JSON + 无 repair | `SchemaError` |
| 9 | score 0 / 11 / True | `SchemaError` |
| 10 | issues 含非字符串 | `SchemaError` |

## 验收标准

`gate_check.py` 的 10 项全部 PASS：

- 解析：纯 JSON、围栏、说明文字、缺字段、类型错、非对象。
- 修复：成功一次、失败、无 repair。
- 业务校验：合法审查结果、6 类非法结果。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么修复只能做一次？无限修复的代价是什么？
2. 类型校验通过后，为什么还要校验 `score` 的业务范围？
3. 如果模型持续输出非法结构，服务应该返回什么、记录什么？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（10/10）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python chapters/part1-foundations/1.3-structured-output/structured_output.py
```

参考实现改用原生的客户端，完整演示了三种结构化提取路径：
1. **JSON Object 模式**（`response_format={"type": "json_object"}`）+ 运行时 Pydantic 校验与一次修复重试；
2. **工具即输出**（Tool Calling as Output）：定义工具 Schema 并强制 `tool_choice`；
3. **严格模式能力判定**：先做能力探针，而不是假设所有模型都支持严格 JSON Schema。

> [!IMPORTANT]
> **厂商生态与思考模型重要边界**：
> - 根据主流框架调研（来源：[Pydantic AI 官方文档与端点兼容性列表](https://ai.pydantic.dev/models/)，核验读取日期：**2026-10-28**），DeepSeek 官方的 Chat Completions API 端点目前**不接受严格的 JSON Schema 语法**（即 `response_format={"type": "json_schema"}` 会报错或被忽略）；在接入 DeepSeek 时应使用方式一（JSON Object + Pydantic 校验）或方式二（工具即输出）进行结构化提取。
> - 在推理模型（如官方当前主打模型 `deepseek-flash`，即 DeepSeek-V4.1-Flash-1017；来源：[DeepSeek 官方定价与模型文档](https://api-docs.deepseek.com/quick_start/pricing)，读取日期：**2026-10-28**）中，模型默认开启内部思考过程。在思考模式下，端点通常**不接受强制 `tool_choice` 参数**。在需要严格、高确定性结构化提取的业务中，必须显式关闭思考（如设置思考参数关闭）或使用非推理通用模型。

对照时思考并回答：

1. 为什么说 JSON Schema 校验通过只代表“数据类型正确”，不能代表“业务语义合法”？为什么在 DTO 映射层必须做业务二阶校验？
2. 工具即输出模式在什么情况下会失效？为什么不能依赖写死的厂商名单判断严格 Schema 支持？
3. 在重试修复提示词中，应该把前一次的错误信息以何种形式回传给模型？

## 概念地图

- **结构化输出**：字段名 + 类型 + 说明，让程序能直接使用。
- **格式 vs 语义**：类型正确不代表内容正确；业务校验要单独做。
- **一次修复**：给模型/解析器一次纠错机会；再失败就明确报错，避免成本和延迟失控。
- **SchemaError**：把解析/校验失败变成可读错误，方便上层重试或降级。
- **Pydantic 对象 vs dict**：对象有类型提示；dict 更轻、更容易跨层传递。

## 边界

- gate 用假文本，不调用真实模型；真实 function calling 的稳定性另验。
- 通过 gate 只证明解析/校验/修复结构正确，不证明字段内容正确。
- 业务规则（如严重级别枚举、复现步骤必填）要按场景继续加。
