# L4.1 Agent 模式 · Gate（原 4.1）

[全书目录](../../README.md) · [上一章 L3.7](../../part3-evals/3.6-langsmith-eval/README.md) · [下一章 L4.2](../4.5-react-agent/README.md)

- **能力**：用原生代码实现五种 workflow 与有界 Agent 循环，区分流程由谁决定。
- **v3 路径**：L4.1 / 核心（Gate；工作流与 Agent）
- **岗位任务 / 面试题型**：T3 / F3
- **前置**：1.5（工具调用）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `agent_patterns.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.1-agent-patterns/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

Agent 不是“让模型随便调工具”。一旦把控制权交给模型，就必须回答：

- 循环怎么停？
- 工具不在白名单怎么办？
- 参数错/超时/预算耗尽怎么退出？
- 失败会不会伪装成成功？
- 状态是覆盖还是追加？

这个 gate 用脚本化决策器代替模型，只验证控制循环本身。

## 五种 workflow 与自主 Agent

[Anthropic《Building effective agents》](https://www.anthropic.com/research/building-effective-agents)（2024-12，读取于 2026-10-31）区分：
workflow 的路径由代码预先安排；Agent 根据环境反馈动态决定下一步。先画流程图：能预先写清路径时，优先 workflow，而不是先造一个循环。

| 模式 | 控制路径 | 本章怎样动手 |
|---|---|---|
| 提示链 | 固定顺序，前一步输出传给下一步 | `prompt_chain`，摘要后审核 |
| 路由 | 分类后进入固定分支 | `route`，未知标签与分类异常走默认 |
| 并行 | 独立子任务或多份答案投票 | `parallel_vote`，本章顺序模拟，失败分支单独记录 |
| 编排者-执行者 | 编排者按任务动态拆分，执行者处理并汇总 | `orchestrator_workers`，保留子任务来源 |
| 评估者-优化者 | 草稿→评价→携反馈重写 | `evaluator_optimizer`，通过或到最大轮数就停 |
| 自主 Agent | 模型读工具观察，决定调用工具还是结束 | `run_agent`，代码仍管预算、白名单与参数 |

[Datadog 2026 遥测报告 Fact 7](https://www.datadoghq.com/state-of-ai-engineering/#7)（读取于 2026-10-31）中，
59% 的 agentic application 请求只有一次服务调用。这是 Datadog 客户样本的**服务调用数**，不能改说成“一次模型调用”或全行业占比。
本章的判断是：不要因名字叫 Agent 就默认多 Agent。

课程区分[两种交付形态](../../../docs/curriculum-v3.md#2-两种交付形态)：嵌入式功能把模型提议放进已有请求流程；专项 Agent 在明确任务与预算内自主推进。两者都能用这些模式，不由框架名称决定。

## 任务

实现 `gate/starter.py` 的七个函数；提示链与编排者-执行者在通过后对照参考实现：

| 函数 | 你要交付的行为 |
|---|---|
| `fixed_workflow` | 整数校验 + 加法；bool/非整数报错 |
| `scripted_planner` | 无观察 -> add；有观察 -> finish |
| `initial_state` | 完整初始 state |
| `run_agent` | 原生有界循环：白名单、预算、失败出口 |
| `route` | 分类异常或未知标签走默认，返回实际标签与处理结果 |
| `parallel_vote` | 单个 worker 失败不中断；成功不足时 ok=False；众数并列先出现优先 |
| `evaluator_optimizer` | 首轮反馈 None，之后传评判反馈；通过或最大轮数时停止 |

关键口径：

- 只允许 `add`；未知工具 -> `status=failed`，error 含“白名单”。
- `steps >= max_steps` -> `failed`，error 含“预算”。
- planner 抛 `ValueError/TimeoutError` -> `failed`；意外异常不吞。
- 工具参数错误 -> `failed`，不追加 observation。
- 正常路径 -> `status=done`，observations 含结果。
- `max_steps < 1` -> `ValueError`。
- 默认路由必须存在，否则 `ValueError`；处理函数自身异常不吞。
- 投票无成功时 `majority=None`；评估优化的 `max_rounds<1` 抛 `ValueError`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | `fixed_workflow(2,3)` | 5 |
| 2 | bool/字符串参数 | `ValueError` |
| 3 | 正常 planner | done，observations=[5] |
| 4 | 一直 add，max_steps=2 | failed 预算，steps=2 |
| 5 | 未知工具 | failed 白名单 |
| 6 | planner 抛 ValueError | failed 记录原因 |
| 7 | add 参数是字符串 | failed，无 observation |
| 8 | max_steps=0 | `ValueError` |
| 9 | 分类得到未知标签 | 使用默认路由；默认不存在抛 ValueError |
| 10 | 分类器抛异常 | 使用默认路由 |
| 11 | 一个 worker 失败 / 众数并列 | 其他分支继续；并列取首次出现 |
| 12 | 成功数不足 min_success | ok=False |
| 13 | 第二轮草稿通过 | rounds=2，反馈传给下一轮 |
| 14 | 始终不通过 / max_rounds=0 | 最大轮停止 / ValueError |

## 验收标准

`gate_check.py` 的 14 项全部 PASS（原 8 项行为与顺序保留，追加 6 项）：

- 固定工作流、初始状态、正常循环、预算、白名单、planner 异常、参数错误、max_steps 校验；默认路由两项、分支投票两项、评估优化两项。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么 Agent 循环必须有 `max_steps`？
2. 失败时为什么不能把 `status` 写成 done？
3. 哪些错误应该向外暴露，哪些应该转成 failed？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（14/14）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.1
```

对照时只回答：

1. 原生循环在调用工具之前检查了哪几层？
2. 参考实现为什么复制传入的 observations，失败为何不能追加结果？
3. 五种 workflow 中哪些路径固定，哪些由模型产生子任务？与自主循环有什么不同？

## 概念地图

- **工作流 vs Agent**：步骤写死 vs 模型决定下一步。
- **状态**：question/steps/observations/decision/status/error。
- **控制路径**：代码分支与 while 循环不需要图框架。
- **有界循环**：max_steps + 明确失败出口。
- **失败不伪装**：参数错误/预算耗尽都写 failed，不写 done。

## 边界

- gate 用脚本化 planner，不验证真实模型规划。
- 本章不实现检查点/暂停恢复，后续 L4.9（目录 4.2）再学图，4.10 学检查点。
- 有副作用工具需要审批/幂等，见 4.18 与 4.16。
