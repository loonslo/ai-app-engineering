# L10 跨 Agent 委派 · Gate（原 10.4）

[全书目录](../../README.md) · [上一章 10.3](../10.3-a2a-protocol-bindings/README.md) · [下一章 项目实战](../../../capstone/README.md)

- **能力**：订单 Agent 缺订单号追问、缺 scope 拒绝、正常读取；委托器翻译 error/input/auth/completed。
- **v3 路径**：选修 / 选修（MCP 鉴权深挖与 A2A）
- **前置**：10.1（授权）、10.2（任务）。
- **时间盒**：5 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/integration.py`。
- **验收命令**：

```bash
python chapters/part10-mcp-a2a-optional/10.4-cross-agent-delegation/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

跨 Agent 委派最容易出这些错：

- 缺订单号仍查；
- scope 不足仍调用；
- 身份/租户从请求 metadata 取，而不是构造上下文；
- error 当正常结果；
- auth-required 不翻译成用户可读提示。

## 任务

实现 `OrderAgent` 和 `SupportOrderDelegator`：

| 情况 | 返回 |
|---|---|
| 缺订单号 | input-required + 追问 |
| 无 orders.read | auth-required |
| 正常 | completed + 状态 |
| client error | 转人工提示 |
| input-required | 原样追问 |
| auth-required | 无权限提示 |

关键口径：身份/scope 来自构造 context；订单号正则提取并大写。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 无订单号 | input-required |
| 2 | 空 scopes | auth-required |
| 3 | 正常订单 | completed，含 tenant/subject/order |
| 4 | error 响应 | 转人工 |
| 5 | input/auth 响应 | 追问/无权限 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 进程内假 client/reader，不连真实 A2A/订单服务。
- 网络/超时/重试未验证。
