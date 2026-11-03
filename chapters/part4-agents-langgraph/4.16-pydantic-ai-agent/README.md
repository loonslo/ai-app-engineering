# L4.5 用 Pydantic AI 写 Agent · Gate

[全书目录](../../README.md) · [上一章 L4.4（4.8）](../4.8-plan-and-execute/README.md) · [下一章 L4.6](../4.14-supervisor-fanout/README.md)

- **能力**：实现带依赖注入、输出校验、人工审批、用量边界和历史恢复的订单客服 Agent。
- **v3 路径**：L4.5 / 核心（Gate；Pydantic AI）
- **岗位任务 / 面试题型**：T3 / F4
- **前置**：L1.4、L4.2、L4.3、L4.4。
- **时间盒**：8 小时（2.5h 读 + 4h 实现 + 1.5h 记录）。
- **闭卷规则**：只读本页、`gate/starter.py` 和官方 SDK 文档；通过 gate 前不要打开 `pydantic_ai_agent.py`。
- **验收命令**（仓库根目录）：

```bash
python chapters/part4-agents-langgraph/4.16-pydantic-ai-agent/gate/gate_check.py
```

全部 PASS 才算通过；脚本写入 `gate/gate_report.json`，不允许修改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

本章把 L4.2 的手写循环换成真实 SDK，而不是再造一个名字相似的 Agent。SDK 负责模型往返、工具参数解析、校验反馈和暂停；租户隔离、审批人的权限和退款防重仍是应用责任。离线替换的是模型决策，不是 SDK 执行过程。

**本章基于 Pydantic AI 2.53.0**，安装项为 `pydantic-ai-slim[openai]==2.53.0`，以仓库锁定依赖为准。离线回归覆盖本章使用的 `Agent.run_sync`、`FunctionModel`、`DeferredToolResults`、`UsageLimits` 和消息适配器；在线文档持续更新，新增接口先核对锁定版。

## 概念

### 1. Agent 与依赖注入

`Agent[SupportDeps, SupportAnswer | DeferredToolRequests]` 表示“运行时需要什么、最后可能产出什么”。`SupportDeps` 是应用给本次运行的资源：当前租户、用户、订单库、退款记录。通过 `agent.run_sync(..., deps=deps)` 注入，而不是让模型在参数中选择租户。

`RunContext[SupportDeps]` 是 SDK 传给工具的运行上下文；工具从 `ctx.deps` 访问资源。依赖对象不是一段自动塞进 prompt 的 JSON，工具返回什么才决定模型能看到什么。

### 2. 带 ctx 的工具

`@agent.tool` 注册的函数首参可以是 `ctx`，其余参数生成工具 schema。`get_order(ctx, order_id)` 只访问当前租户的分区。`request_refund` 的参数中没有 `tenant_id`，因为授权身份必须来自可信调用方。查不到订单返回“未找到”，既方便模型解释，也不泄露其他租户是否拥有该订单。

### 3. 输出校验与 ModelRetry

`SupportAnswer` 用 Pydantic 检查字段类型与枚举；`@agent.output_validator` 再检查业务关系：`reply.strip()` 非空；退款动作有订单号。失败时抛 `ModelRetry("可修正的原因")`，SDK 把原因送回模型，让它重新输出。不要把它理解为程序吞掉了异常，也不要让校验器无上限重试。

结构化答案默认通过“输出工具”提交。与读订单的业务工具不同，输出工具会结束本轮运行。锁定版可以用 `ToolOutput(SupportAnswer, strict=False)` 明确关闭厂商严格 schema，但本地 Pydantic 校验仍然执行。

### 4. 历史保存与恢复

`result.all_messages()` 包括旧历史和本轮消息；下一轮把它传给 `message_history=`。使用 `ModelMessagesTypeAdapter.dump_json(...).decode("utf-8")` 和 `validate_json(text)` 做序列化往返，保留消息类型、时间、工具调用 ID 和工具结果。只保存最终回复会丢掉模型已经做过什么，更不能恢复审批。

JSON 可保存到应用自己的存储；本章只做内存中的字符串往返，不默认写磁盘。历史包含订单数据，生产系统需要按租户和用户做访问控制、保留期与加密；不要接受未经验证的客户端历史，更不要跨租户复用历史。

### 5. 用量上限

`UsageLimits(request_limit=n, tool_calls_limit=n)` 同时限制本轮的模型请求数和成功工具调用数。一个响应可能带多个工具调用，因此仅限请求数还不够。校验重试同样消耗请求预算；达到上限时 SDK 抛 `UsageLimitExceeded`，接口将它转换成 `error="usage_limit"`，保留失败轨迹。

本章每次 `run_turn` 或续跑都获得一份新预算，不声称它是跨会话累计预算或金额上限。生产系统还需在服务端累计成本，不能靠重新开始一轮就恢复额度。

### 6. Deferred tools 人工审批

Deferred tools 是“先暂停，等外部决定后再执行”的工具。流程是：

1. 把退款工具标为 `@agent.tool(requires_approval=True)`；输出类型中同时允许 `DeferredToolRequests`。
2. SDK 遇到调用后结束本轮，返回待审 `ToolCallPart`，其中有 `tool_call_id`；此时工具体还没执行。
3. 调用方保存完整历史，向可信审批人展示工具名、订单和金额。
4. 用 `DeferredToolResults(approvals={call_id: True})` 批准，或传 `ToolDenied("人工拒绝退款，未执行退款")` 拒绝。
5. 把暂停时历史和 `deferred_tool_results=` 一起交给 `run_sync`；不重发原始用户 prompt。

审批只解决“是否允许模型现在做这件事”，不提供 exactly-once。重放同一暂停历史仍可能执行工具，因此退款记录按 `(tenant_id, idempotency_key)` 防重，并在工具体内再次检查订单租户。演示只处理顺序重放；生产应在数据库用唯一约束和事务原子化防重，还要验证审批人、绑定原始参数，不能信任浏览器传来的 `True`。

### 7. 离线测试四件套

| API | 本章用途 | 不证明什么 |
|---|---|---|
| `TestModel` | 根据 schema 合成结果，做接线冒烟 | 不会理解订单业务，也不验证模型能力 |
| `FunctionModel` | 回调接收 `(messages, info)`，返回真实 `ModelResponse`；精确安排故障 | 不证明线上模型会作出相同选择 |
| `Agent.override(model=...)` | 临时替换模型，退出上下文后恢复 | 不是重新写一个执行器 |
| `models.ALLOW_MODEL_REQUESTS=False` | SDK 阻止非测试模型请求；gate 在加载候选实现前设置 | 不是操作系统防火墙，挡不住任意工具自行联网 |

FunctionModel 的回调可以返回 `ToolCallPart("get_order", {"order_id": "A100"}, tool_call_id="query-1")`。最终结构化输出则使用 `info.output_tools[0].name`，不要把输出工具名称写死。读取 `ToolReturnPart` 和 `RetryPromptPart` 可以确认工具是否真正执行、重试反馈是否进入历史。gate 还用内存 HTTP transport 确认外部模型在触达传输层之前就被阻止。

### 8. 追踪、持久执行与锁定版本安全边界

OpenTelemetry 把一次运行拆成 Agent、模型请求和工具调用的 span，便于定位失败与预算消耗。本章不启用 Pydantic AI 自带埋点，沿用 L5.6 的显式字段选择与脱敏策略，避免把订单正文和异常堆栈作为 trace 属性。

仓库当前锁定 Pydantic AI 2.53.0。PyPI 2.31.1 的五条安全公告与 `openai<3` 约束是历史情况，不应再作为当前版限制。本章不使用 `web_fetch_tool`、本地下载 `FileUrl` 或 `ConcurrencyLimitedModel`，这是示例范围，不是当前 SDK 的统一禁用要求。模型思考模式、结构化输出与工具调用的兼容性按具体端点验证；课程离线 gate 不证明真实服务行为。

持久执行引擎会记录已完成步骤，在进程中断后恢复；保存消息 JSON 并不等于具备这种能力。官方概览当前列出 Temporal、DBOS、Prefect、Restate、AWS Lambda、Absurd、pgtask、Apache Airflow。本章只讲概念，不安装这些可选集成，也不把在线文档中的所有接口视为课程锁定版已验证能力。

### 9. 与 OpenAI Agents SDK 对照

按 [课程方案 §6.1](../../../docs/curriculum-v3.md#61-pydantic-ai-与-openai-agents-sdk) 的选型维度，对照如下；不需要为本章安装另一套 SDK。

| 维度 | Pydantic AI（本章） | OpenAI Agents SDK |
|---|---|---|
| 执行入口 | 带类型的 `Agent` + `run_sync` | Agent + Runner |
| handoff（交接控制权） | 用工具委托、Python 编排；本章不做 handoff | 提供 handoff 与 agents-as-tools |
| guardrail（输入/输出安全检查） | 输出 validator、工具内授权；业务安全边界自己实现 | 提供输入/输出 guardrails；同样不能代替工具内授权 |
| session（多轮工作上下文） | 本章显式保存与传入消息历史 | 提供 sessions 持久记忆层 |
| 人工介入 | deferred requests/results + 应用幂等 | 内置 human-in-the-loop；业务幂等仍不能省 |
| 测试 | TestModel、FunctionModel、override、全局请求开关 | 本章不验证其测试 API |

## 任务

实现 `gate/starter.py` 中的五个函数，保留既定数据字段。该章的 `SupportDeps` 按细则使用可变 `@dataclass`，因为 gate 要观察共享退款记录。

| 接口 | 输入 → 输出 / 失败行为 |
|---|---|
| `build_support_agent(model)` | 注入模型 → 真实 SDK Agent；注册两个工具与输出校验 |
| `run_turn(agent, deps, prompt, history, request_limit=n)` | 新一轮 → 四键结果；待审不执行工具；超预算转 `usage_limit` |
| `resume_after_approval(agent, deps, history, approvals, request_limit=n)` | 暂停历史 + 全部待审决定 → 同结构结果；拒绝原因进入上下文 |
| `dump_history(messages)` | SDK 消息 → JSON 字符串 |
| `load_history(text)` | JSON → SDK 消息；非法格式由 Pydantic 抛校验异常 |

## 关键约定

返回值固定为 `{"output", "pending_approvals", "history", "error"}`。`output` 只能是 `SupportAnswer` 或 `None`；`pending_approvals` 只有工具调用 ID，不能把订单号当 ID；`error` 只有 `None` 或 `"usage_limit"`。预算为本轮正整数。恢复审批必须使用暂停时历史；重复续跑指重放同一暂停历史，不是对已完成历史再附加过期审批。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 / gate |
|---|---|---|
| 1 | 查询其他租户 B200 | 未找到、不泄露数据 / 03 |
| 2 | 申请退款但尚未审批 | 待审，退款记录为空 / 04 |
| 3 | 批准后再次重放同一审批 | 只登记一次 / 05、06 |
| 4 | 拒绝审批 | 不登记，回复说明人工拒绝 / 07 |
| 5 | reply 为空白 | SDK ModelRetry 后成功 / 08 |
| 6 | 退款答案缺订单号 | SDK ModelRetry 后成功 / 09 |
| 7 | 模型继续调用超过请求预算 | usage_limit，保留轨迹 / 10 |
| 8 | 一个响应带超额工具调用 | usage_limit / 11 |
| 9 | 用普通外部模型替换测试模型 | 请求开关在 HTTP transport 前阻止 / 13 |
| 10 | 批准跨租户退款 | 工具仍拒绝，不写退款 / 15 |

## 验收标准

15 项全部 PASS：真实 SDK 1 项、查询与租户 2 项、审批与幂等 4 项、校验重试 2 项、双预算 2 项、历史恢复 1 项、请求禁用 1 项、TestModel/override 1 项、审批后租户边界 1 项。骨架应为 0/15；不要给实现留只在 gate 下生效的分支。

## 提交物

实现后的 `gate/starter.py`、15/15 的 `gate/gate_report.json`、填写后的 [workbook.md](workbook.md)。记录首次失败及修正，不要把离线通过写成线上模型质量已验证。

## 通过后对照参考实现

```bash
python tools/run_chapter.py 4.16
python tools/run_chapter.py 4.16 --live
```

默认用 FunctionModel 实际走查询、退款待审、历史往返和批准续跑；`--live` 才读取 common 配置并请求模型。live 使用 `common.get_async_openai_client()` 注入 `OpenAIProvider`，模型名只取 `common.chat_model_name()`；缺钥或不可达以 1 退出，给可读提示、不打印堆栈。

DeepSeek V4 默认思考，思考模式不接受强制 `tool_choice`；本章经 OpenAI 兼容 provider 显式发送 `extra_body={"thinking":{"type":"disabled"}}`，不依赖锁定版 DeepSeekProvider 识别新模型名。工具与输出工具关闭 strict；DeepSeek 的 Chat Completions 不接受严格 JSON Schema，但本地输出校验仍存在。其他 provider 不发送 DeepSeek 专有参数。真实调用未在本章离线 gate 验证；CLI 的自动批准仅是可信本地演示，不是审批 UI。

对照问题：

1. 哪一部分由 SDK 运行，哪一部分只是 FunctionModel 脚本决定？
2. 为什么保存历史和获得人工批准，都不能替代幂等键？
3. 租户检查为什么必须在工具里，而不是只写在 instructions？

## 概念地图

依赖注入 → ctx 工具 → 输出校验 → ModelRetry；UsageLimits 给往返设界；deferred tools 暂停 → 历史保存 → 审批续跑；业务幂等负责防重；FunctionModel 替换决策而不替换执行器。

## 边界

订单与退款是合成内存数据，没有支付调用。真实模型单次运行记录见 [V3-4 验证](../../../docs/gate-v3-4-validation.md)；离线 gate 不衡量真实模型质量。未验证并发防重、审批人认证、跨进程恢复、追踪导出或持久引擎。真实系统还需订单级授权、金额/币种规则、事务与审计。gate 的 SDK 请求禁用不是工具网络沙箱；消息反序列化也不是授权或防篡改校验。

自检时把话术和状态分开看：首次 live 中，批准后退款记录已登记 1 条，但模型仍回复“等待人工审批”、`needs_human=True`。为此输出校验器增加一条规则：已有退款记录时，回复不能再说等待审批、`needs_human` 必须为 false，否则 `ModelRetry`。修复后再跑一次 live，回复为“已登记退款”。校验器只能挡住这类已知的话术冲突，仍不证明业务语义整体正确；界面状态以 `pending_approvals` 和工具记录为准。

## 官方阅读

以下页面实际读取于 **2026-10-31**；在线页面可能比锁定版新，以本机 2.53.0 依赖与离线 gate 约束已验证接口。2.31.1 链接仅作历史接口记录。

- [Deferred tools：审批、拒绝和历史续跑](https://ai.pydantic.dev/deferred-tools/)
- [Testing：TestModel、FunctionModel、override 与请求开关](https://ai.pydantic.dev/testing/)
- [Output：结构化输出与校验](https://ai.pydantic.dev/output/)
- [Message history：SDK 消息与序列化](https://ai.pydantic.dev/message-history/)
- [OpenAI：自定义异步客户端和兼容 provider](https://ai.pydantic.dev/models/openai/)
- [DeepSeek：思考模式和结构化输出限制](https://ai.pydantic.dev/models/deepseek/)
- [Durable execution：引擎概览](https://ai.pydantic.dev/durable_execution/overview/)
- [PyPI 2.31.1 元数据及历史安全公告](https://pypi.org/pypi/pydantic-ai-slim/2.31.1/json)
- [PyPI 当前锁定版 2.53.0 元数据](https://pypi.org/pypi/pydantic-ai-slim/2.53.0/json)
- [OpenAI Agents SDK：handoffs、guardrails、sessions](https://openai.github.io/openai-agents-python/)
