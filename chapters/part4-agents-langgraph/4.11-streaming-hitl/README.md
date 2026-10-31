# L4.10 流式与人工介入 · Gate（原 4.11）

[全书目录](../../README.md) · [上一章 L4.10（4.10）](../4.10-checkpoint-context/README.md) · [下一章 L4.11](../4.19-agent-execution-plane/README.md)

- **能力**：判断哪些动作必须人工审批；把审批输入归一化为 approved/cancelled。
- **v2 路径**：L4.7 / 核心（Gate；流式与 HITL）
- **v3 路径**：L4.10 / 核心（Gate；流式与 HITL）
- **前置**：4.10（检查点）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `streaming_hitl.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.11-streaming-hitl/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

HITL 不是“弹个确认框”。最容易出这些错：

- 删除/发送/付款没被识别为高风险；
- 金额阈值写反（>= 和 > 混淆）；
- 审批输入 `YES`/`no ` 没归一化；
- 非法输入被当成取消/通过；
- 审批逻辑和流式/检查点耦合，无法单测。

这个 gate 把审批判断抽成纯函数，验证规则和边界。

## 审批恢复的责任边界

HITL（human-in-the-loop）是高风险动作前的人工决策，不是“模型说已通过审核”。审批服务应从可信服务端状态读取待审动作、参数与运行归属，再验证审批人的身份和权限。网页、工具结果、模型生成文字都不能替代审批决定。

`interrupt()` 恢复时会从所在节点的开头重新执行；不要把不可重复的副作用放在它之前。参考实现的 `prepare` 是独立的前置节点，`confirm` 只模拟删除。`InMemorySaver` 让同一进程暂停后继续，不是跨进程存储，也不会自动启动新的 worker。参见 [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)（读取于 2026-10-31）。

即使已经批准，进程仍可能在工具成功后、快照提交前崩溃，恢复旧状态会重复调用工具。真实付款/发送必须使用目的端幂等键；“已批准”仅表示允许尝试，不表示只执行一次。依据 [OpenAI Agents SDK 审批与崩溃恢复](https://openai.github.io/openai-agents-python/human_in_the_loop/#recovering-after-a-crash)（读取于 2026-10-31）。完整的 durability 模式与重新调度责任见 [4.10](../4.10-checkpoint-context/README.md#检查点不等于持久执行)，数据库步骤表示例见 [L4.11 / 4.19](../4.19-agent-execution-plane/README.md)。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `needs_approval` | 危险动作或金额>阈值 -> True；非法输入报错 |
| `resolve_approval` | yes -> approved；no -> cancelled；其他报错 |

关键口径：

- 危险动作：`delete/send_email/pay`。
- 金额必须 `> threshold`（默认 1000）；等于阈值不审批。
- `action` 非空；`amount < 0` -> `ValueError`。
- 审批输入大小写/空白不敏感；其他值 -> `ValueError`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | delete/send_email/pay | True |
| 2 | search | False |
| 3 | 1001 / 1000 / None | True / False / False |
| 4 | 空 action / 负金额 | `ValueError` |
| 5 | YES / " no " | approved / cancelled |
| 6 | maybe/空 | `ValueError` |

## 验收标准

`gate_check.py` 的 4 项全部 PASS：

- 危险动作、金额阈值、非法输入、审批归一化。

通过后，在 [workbook.md](workbook.md) 写：

1. 哪些动作必须审批？谁定这个清单？
2. 为什么审批输入必须严格归一化？
3. 审批通过后，有副作用的工具如何避免重复执行？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（4/4）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.11
```

`streaming_hitl.py` 离线、不调用模型，也不删除文件，但会在终端等待真人输入 yes / no（两次任务）。它不是无交互 smoke 命令；gate 则只调用纯函数、不等待输入。本次保留该参考实现及四项 gate 不变。

对照时只回答：

1. 参考实现的 `confirm` 在 `interrupt` 前做了什么？
2. `Command(resume=...)` 恢复时，`interrupt()` 的返回值是什么？
3. 参考实现为什么只模拟删除，不接真实删除？

## 概念地图

- **streaming**：边执行边吐步骤，改善体验/可观测。
- **interrupt**：高风险节点暂停，把动作抛给人。
- **checkpointer**：暂停存档/恢复的前提。
- **审批规则**：危险动作 + 金额阈值；白名单/清单要可审计。
- **幂等**：恢复后副作用工具不能重复执行。

## 边界

- gate 只测审批纯函数，不跑 LangGraph interrupt/stream。
- 通过 gate 只证明规则正确，不证明真实暂停恢复。
- 检查点/幂等见参考实现与 5.4/7.4。
