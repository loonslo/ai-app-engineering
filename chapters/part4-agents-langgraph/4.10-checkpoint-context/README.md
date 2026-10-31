# L4.6 扩展：检查点与上下文 · Gate（原 4.10）

[全书目录](../../README.md) · [上一章 L4.9（4.6）](../4.6-node-reliability/README.md) · [下一章 L4.10（4.11）](../4.11-streaming-hitl/README.md)

- **能力**：按 thread_id 保存/读取状态快照；隔离会话；按条数裁剪上下文并保留 system。
- **v2 路径**：L4.6 / 核心（Gate；检查点与上下文）
- **v3 路径**：L4.10 / 核心（Gate；检查点与上下文）
- **前置**：4.9（可观测性）、1.4（会话记忆）。
- **时间盒**：6 小时（1h 读 + 4h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `checkpoint_context.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.10-checkpoint-context/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

没有检查点，图跑完 state 就没了；有了检查点，又容易出现：

- 不同用户共享状态；
- 保存的是外部引用，后续修改污染快照；
- 裁剪把 system 删了，模型行为漂移；
- 裁剪修改原列表；
- 空 thread_id/非法 max_items 不报错。

这个 gate 用内存 store 和消息列表，验证隔离、副本和裁剪边界。

## 检查点不等于持久执行

检查点回答“保存了哪些数据、从哪里继续”，不自动回答“进程死后谁发现失败、谁重新启动这次运行”。本章与 4.11 合为 v3 L4.10 的 7h 增补单元，下面各历史 gate 的时间盒与计数不变。

LangGraph 在调用 `invoke` / `stream` 等执行方法时接受 `durability`。下表假设使用能跨进程保存的 checkpointer；`InMemorySaver` 重启后全丢，选 `sync` 也不会把内存变成磁盘。

| 模式 | 何时提交检查点 | 进程突然退出的恢复边界 |
|---|---|---|
| `exit` | 正常结束、错误退出或 HITL interrupt 时保存 | 运行中没有中间快照可用；进程崩溃可能丢掉整次运行的进度 |
| `async` | 下一步执行时异步写上一快照 | 写入尚未完成的最近进度可能丢失，恢复后需要重做 |
| `sync` | 下一步开始前等待快照写完 | 已提交的步骤边界可恢复；正在执行的步骤及未提交的结果仍可能重做 |

依据：[LangGraph checkpointers / Durability modes](https://docs.langchain.com/oss/python/langgraph/checkpointers#durability-modes) 与 [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)（读取于 2026-10-31）。仓库锁定 `langgraph==1.2.8`，具体接口以锁定版本为准；本次未实测三种崩溃窗口。

持久执行还需要运行登记、失败发现、任务重新调度和 worker 重启。Temporal、DBOS、Restate 等引擎把这类职责纳入运行时；采用引擎也不免除部署、监控和副作用协调。Thoughtworks 雷达 Vol.34 的 Caution [Ignoring durability in agent workflows](https://www.thoughtworks.com/radar/techniques/ignoring-durability-in-agent-workflows) 提醒：短调用能容忍的中断，在持续多日的 Agent / 人工审批流程中会变成严重故障；先用框架的持久执行支持，再按关键性与复杂度考虑独立平台（读取于 2026-10-31）。

**审批不等于只执行一次。** 工具已付款、快照却没写入时，旧快照看起来仍像“未执行”。[OpenAI Agents SDK 的 Recovering after a crash](https://openai.github.io/openai-agents-python/human_in_the_loop/#recovering-after-a-crash) 明确说明批准不保证 exactly-once：每个逻辑动作要带稳定幂等键，由目的端原子地去重，重试复用同一键和参数。目的端不支持时先权威对账；无法确定结果就标为未知，不自动重放。单独保存“已完成”布尔值不能让外部副作用与快照成为原子操作（读取于 2026-10-31）。

继续到 [L4.11 专项 Agent 执行面（物理章 4.19）](../4.19-agent-execution-plane/README.md)：课程用数据库步骤表展示分阶段落盘、恢复、预算和审批，不把内存快照当作完整的恢复服务。

引擎例子的另一份一手资料是 [DBOS Python 编程指南](https://docs.dbos.dev/python/programming-guide)：工作流/步骤落库，程序重启后从最后完成的步骤恢复；这与“数据库文件存在便会自己启动程序”不是一回事（读取于 2026-10-31）。

## 任务

实现 `gate/starter.py` 的 `CheckpointStore` 和 `trim_history`：

| 接口 | 你要交付的行为 |
|---|---|
| `save` | 保存副本；空 thread_id -> `ValueError` |
| `load` | 返回副本；不存在 -> None |
| `clear` | 删除；不存在不报错 |
| `trim_history` | 保留 system + 最近 N；不改输入；max<1 报错 |

关键口径：

- 保存/读取都用副本，不持有外部引用。
- `thread_id` 隔离；`load` 缺失返回 None。
- `keep_system=True` 且首条是 system：保留它 + 最近 `max_items-1` 条。
- 没有 system 或 `keep_system=False`：保留最近 `max_items` 条。
- `max_items` 大于长度：返回全部。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | save/load/clear | 读写正确，clear 后 None |
| 2 | t1/t2 两会话 | 互不影响 |
| 3 | 修改外部 state | 快照不变 |
| 4 | system + 5 条，max=3 | system + 最近 2 条 |
| 5 | 无 system，max=2 | 最近 2 条 |
| 6 | max=0 / 检查输入 | `ValueError` / 未修改 |

## 验收标准

`gate_check.py` 的 6 项全部 PASS：

- 保存/读取/清除、会话隔离、副本、system 裁剪、无 system/长度不足、非法参数/不改输入。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么保存/读取都要用副本？
2. 裁剪时为什么优先保留 system？
3. 裁剪丢信息和摘要保事实，怎么选？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（6/6）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.10
```

`checkpoint_context.py` 默认用 LangChain 脚本聊天模型离线执行天气工具/多轮记忆，导入时不创建真实客户端。裁剪和摘要只演示接线，不据固定答案评价记忆质量；`langmem` 仍为可选依赖，缺失时明确跳过摘要段。真实模型须显式执行 `python tools/run_chapter.py 4.10 checkpoint_context.py --live`，经 `common.get_llm()` 读取模型配置；错误提示后退出 1，不打印 traceback。本次属于“安全入口接线改动而非图逻辑改写”，图结构、节点和历史 gate 不变。其 `InMemorySaver` 只演示同进程内的记忆，不支持进程重启恢复。

对照时只回答：

1. 参考实现用 `InMemorySaver` 按 `thread_id` 存快照；你的 store 和它对应关系是什么？
2. 参考实现虽然调用 `trim_messages` 的 token 接口，却用 `token_counter=len` 按条数演示；换成真正的 token 计数后预算口径有什么变化？
3. 摘要节点为什么需要额外一次模型调用？

## 概念地图

- **checkpoint**：每步保存 state 快照，按 thread_id 隔离。
- **多轮记忆**：同一 thread 续聊带历史。
- **中断恢复**：从上次快照继续；有副作用工具要幂等。
- **上下文裁剪**：按条数/token 保留最近；system 优先。
- **摘要**：压缩旧历史，保事实但多一次调用。

## 边界

- gate 用内存 store，不验证 LangGraph checkpointer/Sqlite/Postgres。
- 通过 gate 只证明隔离/副本/裁剪结构正确。
- 真实记忆、摘要质量、恢复副作用见参考实现与 4.11。
