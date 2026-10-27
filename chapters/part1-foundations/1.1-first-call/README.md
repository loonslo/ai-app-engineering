# L1.1 一次调用 · Gate（原 1.1）

[全书目录](../../README.md) · [上一章 0.2](../../part0-setup/0.2-learning-workflow/README.md) · [下一章 1.2](../1.2-control-output/README.md)

- **能力**：看懂一次模型往返的请求、响应、token 和失败出口；把失败转成可读结果。
- **v2 路径**：L1.1 / 核心（Gate；一次调用）
- **前置**：0.1（自检通过，`.env` 里有 `DEEPSEEK_API_KEY`）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 失败分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `first_call.py`。
- **验收命令**：

```bash
python chapters/part1-foundations/1.1-first-call/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

第一次调用最容易“跑通就以为会了”。真实服务里更常见的是：密钥错、请求超时、返回空内容、usage 缺失、上游返回非预期结构。如果你只写过 `print(response.content)`，这些情况都会变成线上事故。

这个 gate 让你把一次调用拆成三层：

1. **构造请求**：system / user 角色和顺序。
2. **解析响应**：content、token、finish_reason；缺失时怎么记。
3. **失败出口**：超时、模型异常、空响应、坏结构，都返回可读结果而不是堆栈。

## 任务

实现 `gate/starter.py` 的三个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `build_messages` | 生成 system + user 两条消息；空参数抛 `ValueError` |
| `parse_response` | 提取 content / input_tokens / output_tokens / finish_reason；非法结构抛 `CallError` |
| `call_once` | 构造、调用、解析；超时/异常/空响应/坏结构都转成 `error` 字段 |

关键口径：

- `chat_fn(messages)` 是注入的模型调用；gate 不联网。
- `content` 缺失、不是字符串或只有空白 -> `CallError("empty_response")`。
- `response` 不是 dict -> `CallError("bad_response")`。
- `usage` 缺失 -> token 记 0；token 不是 int 也记 0。
- `finish_reason` 缺省为 `"stop"`。
- `call_once` 的 `error` 只能是 `timeout`、`model_error`、`empty_response`、`bad_response` 或 `None`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 空 system / 空 question | `ValueError` |
| 2 | `chat_fn` 抛 `TimeoutError` | `error="timeout"`，content 为空 |
| 3 | `chat_fn` 抛 `RuntimeError` | `error="model_error"` |
| 4 | 返回 `{"content": ""}` | `error="empty_response"` |
| 5 | 返回 `["not a dict"]` | `error="bad_response"` |
| 6 | 返回缺 `usage` | token 记 0，不崩 |
| 7 | 返回 `finish_reason=""` | 缺省为 `"stop"` |

## 验收标准

`gate_check.py` 的 11 项全部 PASS：

- 消息结构、空参数拒绝。
- 正常响应解析、缺 usage 记 0、非法响应拒绝。
- 调用成功、空问题、超时、模型异常、空响应、坏结构。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么 `content` 为空要当失败，而不是当“模型不想回答”？
2. token 缺失时记 0 有什么风险？生产里你会怎么补？
3. 如果要把 `finish_reason` 用于判断“被截断”，它应该怎么参与业务逻辑？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（11/11）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python chapters/part1-foundations/1.1-first-call/first_call.py
```

参考实现改用原生的 `common.get_openai_client()` 与 `common.chat_model_name()` 执行调用。需要认识到：框架里的聊天模型类（例如 LangChain 的 `ChatOpenAI`）在这一层本质上只是包装了同一个底层的 HTTP 请求与 JSON 往返，剥离框架后我们能更清晰地看见网络、错误捕获与 Token 计量的真实细节。

对照时思考并回答：

1. 参考实现直接通过原生 SDK 调用，并显式捕获了认证、超时、限流三类异常；如果要在生产落地，哪些属于可重试错误？
2. 原生返回中的 `usage` 包含了哪些字段？为什么不能直接把响应剥离成纯字符串而忽略 `finish_reason`？
3. 参考实现的 system prompt 和本 gate 的 `build_messages` 结构是否一致？

## 概念地图

- **一次往返**：请求（messages）→ 模型 → 响应（content + usage + finish_reason）。
- **消息角色**：system 定规则，user 提问题；顺序会影响模型行为。
- **usage**：token 计量，是成本和容量分析的数据源。
- **可读失败**：上游不可靠时，服务要能降级并留下原因，而不是抛堆栈。
- **离线替身**：`chat_fn` 注入让 gate 可重复、零费用。

## 边界

- gate 用假模型，不验证真实模型质量；真实调用见参考实现。
- 通过 gate 只证明请求/响应/失败出口结构正确，不证明回答正确。
- 认证、限流、成本预算在 L5.1 展开。
