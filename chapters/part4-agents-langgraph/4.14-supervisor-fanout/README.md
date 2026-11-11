# L4.9 Supervisor 与并行 · Gate（原 4.14）

[全书目录](../../README.md) · [上一章 L4.5](../4.16-pydantic-ai-agent/README.md) · [下一章 L4.7](../../part3-evals/3.9-agent-trajectory-eval/README.md)

- **能力**：用原生代码拆分任务、隔离子 Agent 上下文、并行执行并保留来源；先用纯函数 gate 自检阶段推进与合并。
- **v3 路径**：L4.6 / 核心（Gate；多 Agent 隔离）
- **岗位任务 / 面试题型**：T3 / F3、F4
- **前置**：4.4（reducer）、4.5、4.8。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `supervisor_native.py` 或 `langgraph_supervisor.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.14-supervisor-fanout/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

多 Agent 最容易出这些错：

- Supervisor 阶段推进错，research 后直接 FINISH；
- 未知阶段不报错，路由到不存在的节点；
- 流水线为空，取下标崩；
- fan-out 结果直接拼接，重复/顺序乱；
- 没有去重，汇总内容重复。

这个 gate 把“阶段推进”和“结果合并”抽成纯函数，验证边界和保序。

## 什么时候分成多个 Agent

有价值的分工是**上下文隔离**与**独立任务并行**：一个子 Agent 只看功能资料，另一个只看测试资料，主管只接收摘要与来源。
把整份对话复制给每个角色，只换一个角色提示，不会自动获得隔离。原生实现用 `Assignment` 明确分支资料与独立 `request_limit`，
`ThreadPoolExecutor` 真正并行，但按分派顺序汇总，避免线程完成先后改变报告顺序。

多 Agent 也会增加协调成本、错误叠加和 token 用量：一个主管的错误拆分会影响多个执行者，合并时还可能丢来源。先证明单 Agent 不够，再比较收益。
[Datadog 2026 报告 Fact 7](https://www.datadoghq.com/state-of-ai-engineering/#7)（读取于 2026-10-31）中，59% 的 agentic application 请求只有一次**服务调用**；
这不是“一次模型调用”的占比，也不是全行业统计。
[Thoughtworks 技术雷达 Vol.34 的 coding agent swarms](https://www.thoughtworks.com/radar/techniques/coding-agent-swarms)（读取于 2026-10-31）列为 Caution：
大规模蜂群仍昂贵、未成熟，成功实验常有清晰规格与充分测试，不宜把条件直接推广到普通产品开发。
本章只是两个小分支，不把蜂群当成默认架构。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `next_stage` | 空 -> 第一阶段；最后 -> FINISH；未知/非法 pipeline -> `ValueError` |
| `fan_in` | 按输入顺序展平、去重保序；非 list -> `ValueError` |

关键口径：

- 默认流水线 `research → writing → review → FINISH`。
- 自定义 pipeline 也要支持；空/非 list -> `ValueError`。
- 未知 stage -> `ValueError`。
- fan-in 保持首次出现顺序，重复项只保留一次。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 空/research/writing/review | research/writing/review/FINISH |
| 2 | 自定义 [a,b] | a→b→FINISH |
| 3 | 未知阶段 | `ValueError` |
| 4 | 空 pipeline / 字符串 pipeline | `ValueError` |
| 5 | [["a","b"],["b","c"],["a"]] | ["a","b","c"] |
| 6 | 空输入 / 非 list | [] / `ValueError` |

## 验收标准

`gate_check.py` 的 5 项全部 PASS：

- 固定流水线、自定义流水线、未知阶段、非法 pipeline、fan-in 合并。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么 Supervisor 更适合固定流水线而不是让模型自由路由？
2. fan-in 为什么要去重保序？
3. 多 Agent 的协调成本体现在哪里？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（5/5）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.14 supervisor_native.py
```

对照时只回答：

1. `run_supervisor` 怎样保留 research → writing → review？每一步收到全量历史还是上一步摘要？
2. `run_fanout` 怎样做到真实并行、结果顺序可复现？一个分支耗尽预算会改变另一个分支吗？
3. `run_delegating_agent` 交给 writer 的资料保留了哪些来源？子 Agent 的内部消息是否泄漏给主管？

三个演示仍分别是固定流水线、并行汇聚、agent-as-tool；默认都用脚本化假模型，不联网。
要观察真实模型，显式加 `--live`。真实模型来自 `common` 配置；本章关闭 DeepSeek 思考，避免不必要的工具/结构化输出兼容差异。

## 框架对照

`langgraph_supervisor.py` 保留图节点、条件边、reducer 与共享 MessagesState 的历史演示。**学完 L4.9（目录 4.2）后再读**，不要把图 API 当作本章前置。
离线运行只给提示；`python tools/run_chapter.py 4.14 langgraph_supervisor.py --live` 才调用真实模型。

## 概念地图

- **Supervisor**：协调者按进度派活；固定流水线最可控。
- **Fan-out/Fan-in**：并行分支 + 汇聚；写同字段要 reducer。
- **去重保序**：合并结果可复现。
- **agent-as-tool**：子 Agent 独立上下文，只回摘要。
- **成本**：多 Agent 增加调用、延迟、调试成本。

## 边界

- gate 只测纯函数，不跑 LangGraph 多 Agent/真实模型。
- 通过 gate 只证明阶段推进/合并结构正确。
- 原生演示验证线程分派与摘要隔离，不模拟完整任务存储；图版的 reducer 与恢复机制留给后续章节。
