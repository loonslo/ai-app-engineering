# L10 A2A 任务生命周期 · Gate（原 10.2）

[全书目录](../../README.md) · [上一章 10.1](../10.1-mcp-auth-approval/README.md) · [下一章 10.3](../10.3-a2a-protocol-bindings/README.md)

- **能力**：按 message_id 幂等提交；按状态表迁移；终态/非法迁移拒绝；未知任务 `TaskNotFound`。
- **v2 路径**：L10 / 选做（Gate；A2A 任务状态机）
- **v3 路径**：选修 / 选修（MCP 鉴权深挖与 A2A）
- **前置**：4.10（检查点/状态）。
- **时间盒**：5 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/a2a.py`。
- **验收命令**：

```bash
python chapters/part10-mcp-a2a-optional/10.2-a2a-agent-card-task/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

远端协作最容易丢状态：网络重试重复执行、submitted→completed 非法迁移、终态改回 working、未知 task_id 静默返回。

## 任务

实现 `InMemoryTaskStore`：

| 方法 | 要求 |
|---|---|
| submit | 空 message_id -> ValueError；同 id 返回已有任务 |
| get | 不存在 -> TaskNotFound |
| transition | 只允许 ALLOWED 表；终态/非法 -> TaskTransitionError |

关键口径：初始 `submitted`；`working→completed` 合法；`submitted→completed` 非法；终态无出边。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 同 message_id 两次 | 同 task id |
| 2 | 空 message_id | ValueError |
| 3 | submitted→working→completed | 成功 |
| 4 | submitted→completed | 拒绝 |
| 5 | 终态再迁移 | 拒绝 |
| 6 | 未知 task_id | TaskNotFound |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 内存 store，不验证持久化/多租户/网络。
- 真实 A2A 传输未接入。
