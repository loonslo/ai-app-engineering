# L4.8 原生版与 SDK 版 · Gate

[全书目录](../../README.md) · [上一章 L4.7](../../part3-evals/3.9-agent-trajectory-eval/README.md) · [下一章 L4.9（4.2）](../4.2-langgraph-basics/README.md)

- **能力**：用同一套订单客服场景比较原生循环与 Pydantic AI，说清框架替你做了什么。
- **v3 路径**：L4.8 / 核心（Gate；原生与 SDK）
- **岗位任务 / 面试题型**：T3、T4 / F4、F5
- **前置**：L4.2、L4.3、L4.5、L4.7。
- **时间盒**：3 小时。
- **闭卷规则**：只读本页、`gate/starter.py` 与指定 SDK 官方文档；通过前不看参考实现。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.17-native-vs-sdk-gate/gate/gate_check.py
```

全部 PASS 才算通过；写出 `gate/gate_report.json`，不允许改 gate_check.py 绕过检查。本章基于 Pydantic AI **2.31.1**，与课程锁定版本一致。

## 为什么做这个 gate

换框架不能换题目。两边都接收完全相同的模型决策脚本，运行真正的工具与审批边界，再由同一个 `evaluate` 判分。原生版复用 L4.2 循环，SDK 版真实使用 `Agent`、`FunctionModel`、`DeferredToolRequests` 和 `UsageLimits`，不把原生结果改个标签称为 SDK 结果。

`FunctionModel` 是由本地函数提供模型响应的测试模型，不请求网络；参考 [官方 FunctionModel 文档](https://ai.pydantic.dev/models/function/) 与 [v2.31.1 deferred tools 文档](https://github.com/pydantic/pydantic-ai/blob/v2.31.1/docs/deferred-tools.md)（读取于 2026-10-31）。锁定版的安全限制见 [课程约定第9节](../../../docs/v3/conventions.md#9-pydantic-ai-约定)：本章不启用 SDK 自动追踪或网页下载工具。

## 任务

| 接口 | 行为 |
|---|---|
| `run_native` | 把 ToolCall / Final 转成 gate 的 ScriptedChat，以原生循环执行 |
| `run_pydantic_ai` | 同一脚本转成 ModelResponse，由真实 Agent 负责循环、未知工具处理与待审出口 |
| `evaluate` | 每场景检查结果、状态、有序工具子序列与禁止工具；异常记失败，继续下一场景 |
| `compare` | 比较通过率与逐场景模型请求数、工具尝试次数；按场景名对齐 |

`ToolCall` 是一次工具决策，`Final` 是一次最终回答。一次脚本项对应一次模型请求，不固定要求所有正确答案走同一条完整轨迹。

## 关键约定

- tools 是 `{name: callable}`；函数带 `tool_spec`（L4.3 ToolSpec）和可选的 `requires_approval=True`。身份由宿主注入，不接受模型提交的 tenant_id。
- 每次运行重置工具与内存数据。写操作只进入待审，不能执行 handler。
- 返回 `status`（done / waiting_approval / failed）、`final`、`tools_called`、`steps`、`errors`。
- **统一计数口径**：steps 为实际模型请求次数，含最终答案；tools_called 为模型尝试调用，包含未知工具、参数非法和待审调用。原生循环底层的 handler 执行数不是此口径，适配器从 trace 转换。
- `Final("$tool")` 将最后的真实工具返回用作最终文本，避免“工具泄露了其他租户数据，但脚本仍打印安全答案”造成假通过。普通 Final 文本仍是确定性脚本，不是模型推理证据。
- 脚本耗尽后重复末项，以构造超限；max_steps 必须大于0。异常回传不意味着整个任务必须失败，模型可以给出可读收尾。
- `evaluate` 返回 passed 名称、failed 的 name/reason、pass_rate 和 runs；空集通过率为0。必需工具按有序子序列匹配，可以夹杂其他合法调用。
- `compare` 返回 native_pass_rate、sdk_pass_rate、differences（name / steps_delta / tool_calls_delta）；差值统一为 **SDK 减原生**，缺失的 SDK 场景差值为 None。

## 故障注入（必须亲手触发）

八场景包含正常查询、退款待审批及以下六类边界（不少于细则五种故障）：

| 场景 | 期望 / 检查号（原生、SDK） |
|---|---|
| 正常查询 | 工具结果包含已发货，done，01、09 |
| 退款待审批 | waiting_approval，退款记录为空，02、10 |
| 未知工具 | 错误回传且能收尾，03、11 |
| 工具抛异常 | errors 非空、可读收尾，04、12 |
| 模型循环超限 | failed、请求不超过3，05、13 |
| 参数非法 | 不执行错误参数，errors 非空，06、14 |
| 跨租户访问 | 真实工具返回未找到，07、15 |
| 工具结果夹带退款指令与结束标签 | 不调用退款、不执行副作用，08、16 |

## 验收标准

**21 项**：两边各8场景；evaluate 混合统计、compare 非零差值、原生变异体、判分顺序/最终答案/异常、SDK 实际运行，共5项。变异体真的先运行原生实现，再绕过审批调用本地退款 handler，断言副作用已发生并记录调用；相同 evaluate 必须把7个禁止退款的场景判失败，不能硬编码一个“检测成功”分数。

## 提交物

实现后的 starter、21/21 gate_report、workbook 和下表自己的结论。代码行数要注明测量范围，不能把 SDK 依赖源码算作零成本。

## 通过后对照参考实现

```bash
python tools/run_chapter.py 4.17 native_vs_sdk_gate.py
```

默认完全离线，输出两边完整 runs 与 compare。这里不提供 live 比较：同一脚本控制实验不能被两个独立真实模型回答替代；真实工具调用见 L4.2 / L4.5 的显式 `--live`。

| 维度 | 原生版参考实现 | SDK 版参考实现 | 你的观察 |
|---|---|---|---|
| 代码行数（含注释/空行） | 本章 run_native 17行 + L4.2 run_loop 88行；另复用L4.3校验 | 本章 run_pydantic_ai 45行；另复用L4.3校验，不含已安装SDK源码 | 待填写 |
| 测试方式 | ScriptedChat + 同一8场景 | FunctionModel + 同一8场景；额外断言调用Agent.run_sync | 待填写 |
| 可观测性 | 显式 messages / trace / errors | SDK消息类型与usage；本章适配为同口径runs，不启用自动埋点 | 待填写 |
| 审批支持 | 工具返回待审信号，由宿主控制 | requires_approval + DeferredToolRequests | 待填写 |
| 出错时表现 | 本地参数验证、工具异常回传、显式预算出口 | SDK处理未知工具/请求预算；业务参数校验复用L4.3 | 待填写 |

对照问题：① 同脚本为什么不能证明真实模型选择质量？② 工具尝试数为什么不同于执行次数？③ 框架是否替你实现租户权限、幂等与业务验证？

## 概念地图

同任务 → 同数据与干净环境 → 两种真实运行时 → 同一判分 → 故障与变异 → 差异解释。

## 边界

这是离线控制流对照，不是模型排行榜、延迟或 token 基准。固定脚本只能证明“安全决策被正确执行”，不能证明模型面对恶意工具输出会自主拒绝注入；权限/审批必须由代码独立执行。SDK `Tool.from_schema` 不自动验证 schema，本章明确复用 L4.3 的验证，不能据此声称框架包办业务验证。这里只验证暂停待审，审批后续跑和幂等参见 L4.5。未运行真实模型、外部审批服务或生产并发。
