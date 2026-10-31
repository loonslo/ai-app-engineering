# L4.11 专项 Agent 执行面 · Gate

[全书目录](../../README.md) · [上一章 L4.10](../4.11-streaming-hitl/README.md) · [下一章 L4.12](../4.20-sandbox-least-privilege/README.md)

- **能力**：将调研任务做成提交即返回、分阶段落盘、可恢复、可审批、可取消的异步任务。
- **v3 路径**：L4.11 / 核心（Gate；执行面）
- **岗位任务 / 面试题型**：T3、T5 / F3
- **前置**：L4.5、L4.9、L4.10。
- **时间盒**：8 小时（2h 读 + 4.5h 实现 + 1.5h 记录）。
- **闭卷规则**：只读本页、`gate/starter.py` 与标准库文档，通过 gate 前不要读参考实现；不允许修改 `gate_check.py`。
- **验收命令**：`python chapters/part4-agents-langgraph/4.19-agent-execution-plane/gate/gate_check.py`。

全部 16 项 PASS 才算通过，报告在 `gate/gate_report.json`。

## 为什么做这个 gate

长任务不能绑定在一次 HTTP 请求或一段聊天循环里。执行面是模型之外负责接收任务、推进阶段、保存状态和限制权限的代码；Agent 只负责阶段内的判断，不拥有整个任务的控制权。

一个可学习的最小部署是 API 进程调用 `submit` 后返回 task_id，另一个 worker 领取 task_id 后调用 `run_until_blocked`。本章演示不启动 HTTP/队列服务，而用分开的提交与运行函数验证这条边界；状态查询始终调用 store.get(task_id)，不能拿“队列已消费”冒充任务成功。

## 概念：形态 B 的八条规则

| 规则 | 为什么 | 本章怎样做 / 自检 |
|---|---|---|
| 异步化 | 连接断开不应丢任务 | submit 只落盘并返回 ID；worker 另行调用，queued 可查询 |
| 阶段化 | 模型不负责持久化状态机 | 外部 current_stage 推进，阶段函数返回摘要与 token |
| 断点与幂等 | 重启会重放未确认的动作 | 步骤表 + 稳定 task_id:stage.name 回执键 |
| 沙箱在 harness 之外 | 模型输出不能授权自己 | [L4.12](../4.20-sandbox-least-privilege/README.md) 的外置路径、命令、出网与凭据策略 |
| 预算与取消 | 无界循环消耗时间和费用 | 每次阶段尝试前读取消标志和三个预算 |
| 人工审批 | 副作用要由可信人决定 | 没有决定暂停；显式 approve 后 worker 续跑，拒绝记原因 |
| 缓存友好 | 固定上下文不应反复构造 | 固定工具契约/系统前缀在前，变化的任务与资料在后；缓存不是权限 |
| 评测 | 完成话术不等于任务完成 | 检查实际步骤、状态、调用次数；[L4.17](../4.23-async-agent-gate/README.md) 独立运行三次 |

### 为什么只用 Celery 不够

队列解决分发和重试，不自动知道业务阶段已经完成。若将“查询—扣款—写报告”放进一个任务函数，整段重试可能再次扣款。使用 Celery 仍需要步骤表、任务状态和业务幂等键；这里不是否定队列，而是区分调度与业务恢复。

| 做法 | 适用 | 要付出的成本 |
|---|---|---|
| 数据库步骤表 | 阶段少、便于 SQL 排查、已有数据库 | 自己实现领取/租约/扫描重启/并发控制 |
| LangGraph | 显式状态图、分支和 HITL | 学习图与检查点语义；还要部署运行与恢复机制 |
| Temporal 等持久执行引擎 | 长时间跨服务流程与运行调度 | 服务运维、重放约束与 SDK 的学习成本 |

本章选步骤表，是为了看清状态、回执、审批在何处保存，而不是推荐把教学 worker 直接作为生产调度器。SQLite 只用标准库，不新增依赖。

## 任务

实现 `submit`、`run_until_blocked`、`approve`、`cancel`、`deliver_result`，接口与数据结构见 starter。`Stage` 名称在任务内唯一；Task/StepRecord/Budget 可变是细则指定的状态结构，Stage/StageOutput 不可变。

| 输入 | 输出 / 失败 |
|---|---|
| 同租户与提交幂等键 | 同一个 ID；不同租户互不串用 |
| queued / running | 从 current_stage 继续，不重跑已成功阶段 |
| 未决定的审批 | waiting_approval，不调用该阶段 |
| 审批拒绝 | failed，步骤 error 写明审批原因 |
| RetryableError | 同阶段有限重试；其他 Exception 直接 failed |
| 进程消失 | 最近成功快照仍在，下一次从游标继续 |
| 终态投递 | 成功后登记 delivered；投递异常不登记，允许重试 |

## 关键约定

- store 的 get 返回独立快照；find_by_key(tenant,key) 返回 Task 或 None；put(task,idempotency_key=key) 创建，put(task) 更新。SQLite 任务快照与步骤表在同一事务保存。
- clock 返回整数毫秒，不 sleep。首次执行保存 started_ms，等待审批的时间也算墙钟。
- 每次尝试都追加步骤，包括可重试失败；attempt 从 1 递增。失败 token 在教学协议中记 0，真实模型失败也可能计费，生产计量须从 provider usage/账单补足。
- 每次尝试开始前检查：已用步数、token、墙钟任一 **达到或超过** 上限就停止；不抢占正在执行的函数，也不在最后一阶段之后追溯检查预算。真实系统还应限制单次模型与工具请求。
- side_effect_log 在任务快照前记录成功回执。真实服务必须接受相同业务幂等键；“远端已经生效，但本地回执尚未落盘”仍有窗口，本章不能证明跨系统 exactly-once。
- 普通异常是业务失败，进入终态后不自动重开。gate 的 BaseException 模拟进程退出，不被业务异常处理捕获；重启与“重试 failed 任务”不是一回事。

## 故障注入（必须亲手触发）

| 注入 | 期望 | 检查 |
|---|---|---|
| 同键重提、换租户 | 同租户去重，租户隔离 | 01 |
| draft 进程退出 | 从 draft 续跑，gather 一次 | 03 |
| 副作用已有回执而快照未写 | 复用回执，不调用函数 | 04 |
| 暂停后批准 / 拒绝 | 成功 / failed，无越权调用 | 05–06 |
| 步数 / token / 墙钟达上限 | 下一阶段不执行 | 07–09 |
| 阶段内请求取消 | 当前阶段保存，后续取消 | 10 |
| 一次超时 / 持续超时 / 非法输入 | 有限重试 / 用尽失败 / 立即失败 | 11–13 |
| worker 逐步写入 | 每步都有快照 | 14 |
| webhook 重复 / 超时 | 成功去重 / 失败可重投 | 15–16 |

## 验收标准

16 项：提交与正常路径 2；崩溃/回执 2；审批 2；预算 3；取消 1；错误 3；步骤落盘 1；投递 2。默认骨架 0/16；请先预测再实现，不更改检查脚本。

## 提交物

starter 实现、gate_report、workbook 的故障与边界记录。不得把参考 gate 结果当作本人的闭卷证据。

## 通过后对照参考实现

`python tools/run_chapter.py 4.19 execution_plane.py`

参考实现使用临时 SQLite 数据库：提交 queued → gather 落盘 → draft 模拟崩溃 → 关闭并重新打开连接 → waiting_approval → 本地批准 → succeeded → webhook 去重。全部资料、发布与 webhook 都是本地演示，不调用真实模型，无 `--live`。

对照：1. 步骤和任务快照是否一起提交？2. 副作用回执为何不能只存在 worker 内存？3. 谁在生产环境发现没有继续推进的任务并重新领取？

## 概念地图

请求 → 提交去重 → 状态存储 → worker 推进 → 策略/审批/预算 → 步骤与回执 → 终态投递 → 独立评测。

## 边界

单 worker，无并发领取、租约、崩溃自动扫描、HTTP API、真实支付和远端 webhook；delivered 的 set 是单进程教学去重，生产需 outbox 与接收方幂等。数据库事务不能和任意外部副作用组成原子事务。下一章先把权限强制执行放到模型之外，再组合异步 Agent。
