# L4.9 MCP 授权与审批 · Gate（原 10.1）

[全书目录](../../README.md) · [上一章 9.12](../../part9-enterprise-infra-optional/9.12-inference-benchmark/README.md) · [下一章 10.2](../10.2-a2a-agent-card-task/README.md)

- **能力**：校验 token audience、工具 scope、高风险审批；失败统一 `McpAuthorizationError`。
- **v3 路径**：选修 / 选修（MCP 鉴权深挖与 A2A）
- **前置**：4.11（HITL）、5.7（权限）。
- **时间盒**：5 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/mcp_auth.py`。
- **验收命令**：

```bash
python chapters/part10-mcp-a2a-optional/10.1-mcp-auth-approval/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

MCP 工具连上后，最容易把“连接成功”当“有权调用”：token 签发给别的 resource、scope 不足、高风险没审批、检查顺序错。

## 任务

实现 `authorize_tool(claims, policy, resource_audience, approved=False)`：

| 顺序 | 检查 |
|---|---|
| 1 | `resource_audience in claims.audience` |
| 2 | `policy.required_scope in claims.scopes` |
| 3 | 高风险必须 `approved=True` |

关键口径：任一失败抛 `McpAuthorizationError`；身份/租户以 claims 为准。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 合法 claims/policy | 通过 |
| 2 | audience 不匹配 | 拒绝 |
| 3 | 缺 scope | 拒绝 |
| 4 | 高风险未审批/已审批 | 拒绝/通过 |
| 5 | audience+scope 都错 | 先报 audience |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 不验证签名/真实 IdP；只做授权内核。
- 真实 MCP server 未连接。
