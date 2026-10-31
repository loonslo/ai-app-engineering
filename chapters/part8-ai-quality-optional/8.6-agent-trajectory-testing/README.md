# L4.11 扩展：Agent 轨迹测试 · Gate（原 8.6）

[全书目录](../../README.md) · [上一章 8.5](../8.5-judge-calibration/README.md) · [下一章 8.7](../8.7-api-sse-e2e/README.md)

- **能力**：校验轨迹步数、编号、工具白名单、写工具审批、未知动作。
- **v2 路径**：L4.11 / 核心阅读（Gate；轨迹测试）
- **v3 路径**：L4.7 / 核心阅读（归入 L4.7）
- **前置**：4.9（可观测性）、3.9（轨迹评测）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/trajectory.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.6-agent-trajectory-testing/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

只看最终答案，会漏掉“答案体面但动作违规”：

- 调了未授权工具；
- 写操作没审批；
- 步数超限/编号断裂；
- 出现未知动作；
- 只报第一个错，修完再跑又冒出下一个。

这个 gate 用固定轨迹，验证全部违规一次收全。

## 任务

实现 `validate_trajectory(steps, policy)`，返回全部违规：

| 规则 | 说明 |
|---|---|
| 步数 | `len(steps) > max_steps` |
| 编号 | 必须从 1 连续递增 |
| 工具 | `action=tool` 时 tool 必须在白名单 |
| 审批 | 写工具必须 `approved=True` |
| 动作 | 只允许 tool/retrieve/respond/refuse |

关键口径：一次返回全部违规；空列表表示合规。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 合规轨迹 | [] |
| 2 | 未授权工具 | 报“工具未授权” |
| 3 | 写工具未审批 | 报“缺少审批” |
| 4 | 编号 1→3 | 报“编号不连续” |
| 5 | 步数超限 | 报“最大步骤数” |
| 6 | 未知动作 | 报“未知动作” |

## 验收标准

`gate_check.py` 的 6 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- gate 只验证策略，不执行真实 Agent/工具。
- 参数级校验、轨迹采集见 4.9/8.6 参考实现。
