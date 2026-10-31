# L4.17 异步专项 Agent · Gate

[全书目录](../../README.md) · [上一章 L4.16](../4.15-framework-landscape/README.md) · [下一章 L5.1（5.1）](../../part5-production/5.1-serve-fastapi/README.md)

- **能力**：组合 Agent、持久步骤表、外置策略与审批，完成一个异步调研任务，并生成离线 pass^3 报告。
- **v3 路径**：L4.17 / 核心（Gate；异步专项 Agent）
- **岗位任务 / 面试题型**：T3、T4、T5 / F3、F4
- **前置**：L4.5、L4.11、L4.12、L4.13。
- **时间盒**：3 小时（0.5h 读 + 2h 实现与故障 + 0.5h 记录）。
- **闭卷规则**：只读本页、starter、前序公开接口与标准库文档；不允许修改 gate_check.py。
- **验收命令**：`python chapters/part4-agents-langgraph/4.23-async-agent-gate/gate/gate_check.py`。

全部 13 项 PASS 才算通过；脚本写 `gate/gate_report.json`。

## 为什么做这个 gate

模型会写“完成”并不代表任务真的发布，也不代表权限正确。本章检查实际工具轨迹、存储游标、审批决定与发布回执，把 L4.5 的阶段内 Agent 决策组合进 L4.11 的执行面，而不是另写一个状态机。

## 概念

`plan → gather → draft → approve → publish` 由可信代码固定。模型只能提出计划、选择只读工具和写草稿；审批来自调用方，发布只能在审批后由阶段推进器调用。任务的 Agent 行为通过 `agent_step(stage,task)` 注入，gate 使用脚本化替身，不请求真实模型。

gather 的工具输出作为不可信文档包装，转义防止关闭标签；这不消除提示注入。即使 draft 被恶意文档影响，产出提前发布或禁止工具请求，模型外的返回类型与权限边界也会拒绝，audit 留下原因。

## 任务

| 函数 | 输入 → 输出 |
|---|---|
| build_stages | Agent 行为、策略、可信工具 → L4.11 的五阶段列表 |
| run_e2e | 存储、ID、阶段、假时钟、回执 → Task；waiting_approval 直接返回 |
| run_trials | 新任务工厂、k → pass_at_1、pass_all_k、逐次 runs |

Agent 协议：plan/draft 返回 L4.11 `StageOutput`；gather 返回 `{'tool':名称,'args':参数}`。draft 从 task.steps 的成功 gather 记录读取资料，不从全局变量取上一轮数据。publish handler 接收 Task，只写本地演示账本。接口细节以 starter docstring 为准。

## 关键约定

- policy 包含 read_tools、command_policy、tool_commands、audit。read_tools 是应用端绑定的只读 handler 名称；tool_commands 是可信应用提供的固定命令元数据，先经 L4.12 check_command，再执行工具。它不是一个能执行任意 argv 的 shell。
- 教学只读工具绑定固定资料；不能借“已允许 reader”让模型任意读文件。若扩展为路径/URL 参数工具，还必须将实际参数交给 L4.12 路径/出网策略并隔离执行；本章没有实现通用 shell 或任意路径读取。
- timeout 转成 RetryableError；普通异常按执行面协议失败。进程崩溃用 BaseException 模拟并传播，调用方再次推进，不重跑成功 gather。
- approve 设置 needs_approval；publish 设置 side_effect，用执行面稳定回执键去重。gather 是只读阶段，不伪装成有外部副作用的写操作；成功游标同样防止重复调用。
- 独立试验每次必须新建 store、替身和回执，不能重复运行一个已成功任务。
- 本章的 pass_at_1 是 k 次独立单次试验的经验成功率；pass_all_k 是这一组 k 次是否全成功的 0/1 指示值，不把一次三连过说成真实成功概率为 100%。不是 pass@k 的“至少一次成功”，也不是一次对话的三轮。

## 故障注入（必须亲手触发）

| 故障 | 期望 | 检查 |
|---|---|---|
| 1. gather 第一次超时 | 同阶段有限重试，失败与成功都落盘 | 03 |
| 2. draft 进程崩溃 | 从 draft 续跑；gather 调用仍一次 | 04 |
| 3. 人工拒绝 | failed、可读审批原因、未发布 | 05 |
| 4. plan 用尽预算 | budget_exceeded，后续工具不执行 | 06 |
| 5. 文档要求提前发布/禁止工具 | 实际经 gather 进入上下文，draft 越阶段请求被拦截并记录 | 07 |

补充检查 09 验证禁止工具在调用前被拒；10 验证合法只读工具也不能绕过外置命令策略；11 验证执行器不自动批准。

## 验收标准

13 项：正常路径、阶段协议、五个故障、发布去重、策略拒绝、命令约束、等待审批、三连过统计、混合成功统计。骨架应 0/13。失败时先查看实际状态、步骤和 audit，再修改实现，不能删检查。

## 提交物

实现、gate_report、workbook；运行参考入口产生 `reports/offline_pass3.json`，供 P4 复用其报告结构。报告必须保留 `mode=offline-scripted` 与 evidence_scope，不能用此数据替代真实模型评测或发布证据。

## 通过后对照参考实现

`python tools/run_chapter.py 4.23 async_agent.py`

默认使用 SQLite 临时数据库、固定资料、Pydantic AI 2.31.1 的真实 Agent + FunctionModel、可信本地批准与本地发布账本，独立运行三次并输出报告。FunctionModel 只替代模型决策，阶段内结构化输出工具与校验由 SDK 执行；StageOutput.tokens 的 4/8 是教学固定值，不是真实计费量。可用 `--report <路径>` 指定报告；不写仓库根 reports，不覆盖 capstone 证据；无真实模型与 `--live` 模式。SDK 版本沿用 requirements-course.txt / requirements-dev.txt，与 L4.5 一致，不启用自带埋点。

对照：1. 把权限放在 prompt 中会少哪条强制边界？2. 三次试验复用同一个成功 Task 会怎样误报？3. 发布成功但回执未落盘如何解决，为什么需要业务端幂等？

## 概念地图

Agent 决策 → 外置策略 → 阶段记录 → 审批 → 幂等发布 → 独立试验 → 标明模式的 pass^3 报告。

## 边界

本章验证固定离线模型与五种故障，不证明真实模型抗注入能力；没有真实网络、任意命令执行、并发 worker、审批 UI、自动恢复守护进程或外部支付。gate 注入普通脚本行为；参考入口实际组合 L4.5 所用 Pydantic AI SDK 与 FunctionModel，再复用同一执行面和策略边界。
