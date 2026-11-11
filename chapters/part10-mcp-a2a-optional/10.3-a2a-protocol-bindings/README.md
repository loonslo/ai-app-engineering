# L10 A2A JSON-RPC 绑定 · Gate（原 10.3）

[全书目录](../../README.md) · [上一章 10.2](../10.2-a2a-agent-card-task/README.md) · [下一章 10.4](../10.4-cross-agent-delegation/README.md)

- **能力**：校验 JSON-RPC 形状；按 method 分发；错误码 -32600/-32601/-32602/-32001；成功返回 result。
- **v3 路径**：选修 / 选修（MCP 鉴权深挖与 A2A）
- **前置**：10.2（任务状态机）。
- **时间盒**：5 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/a2a_api.py`。
- **验收命令**：

```bash
python chapters/part10-mcp-a2a-optional/10.3-a2a-protocol-bindings/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

协议边界最容易“形状对了、语义错了”：无效 jsonrpc 仍处理、未知方法静默、TaskNotFound 被 KeyError 吞掉、params 非对象崩、错误码不统一。

## 任务

实现 `A2AApplication.dispatch(payload)`：

| 情况 | 错误码 |
|---|---|
| jsonrpc≠2.0/缺 method | -32600 |
| params 非对象 | -32602 |
| 未知 method | -32601 |
| TaskNotFound | -32001 |
| 其他 KeyError/ValueError | -32602 |
| 成功 | `{"jsonrpc":"2.0","id":...,"result":...}` |

关键口径：先捕 TaskNotFound（KeyError 子类），再捕 KeyError；send/get/cancel 只做分发。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | message/send | result |
| 2 | tasks/get+cancel | result |
| 3 | jsonrpc 1.0/缺 method | -32600 |
| 4 | params 非对象/KeyError/ValueError | -32602 |
| 5 | TaskNotFound | -32001 |
| 6 | 未知方法 | -32601 |

## 验收标准

`gate_check.py` 的 6 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 不启 FastAPI/HTTP/SSE；只验证分发。
- 真实 A2A 传输未接入。
