# L1.5 工具调用 · Gate（原 1.5）

[全书目录](../../README.md) · [上一章 L1.5](../1.4-context-memory/README.md) · [下一章 L1.7](../1.9-provider-cost/README.md)

- **能力**：定义工具 schema；校验参数；执行工具并把结果回灌；未知工具/异常/超步数都有出口。
- **v3 路径**：L1.6 / 核心（Gate；工具调用）
- **前置**：1.1（一次调用）。
- **时间盒**：6 小时（1h 读 + 4h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `tool_calling.py`。
- **验收命令**：

```bash
python chapters/part1-foundations/1.5-tool-calling/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

工具调用是 Agent 的地基，也是最容易出事故的地方：

- 模型请求不存在的工具；
- 参数缺字段/类型错；
- 工具函数自己抛异常；
- 工具返回非字符串，拼接时崩；
- 模型一直请求工具，循环停不下来；
- 结果没有以 `tool` 消息回灌，模型看不到事实。

这个 gate 让你把“模型只负责请求，程序负责执行”做成可验证的循环，而不是把 `tool_calls` 直接 `eval`。

## 任务

实现 `gate/starter.py` 的三个部分：

| 部分 | 你要交付的行为 |
|---|---|
| `build_tools` | `get_weather`、`calculate` 两个工具，schema/description/handler 正确 |
| `dispatch_tool` | 未知工具、非 dict、缺参数、类型错、工具异常、非字符串结果都有可读错误 |
| `run_tool_loop` | 模型请求 → 执行 → 结果回灌 → 再请求；有界终止；异常降级 |

关键口径：

- `ToolSpec.parameters` 是 `{"参数名": 类型}`；只校验必需字段和类型。
- `dispatch_tool` 返回 `{"ok","result","error"}`；成功时 `error=None`。
- `run_tool_loop` 的 `llm_fn(messages)` 返回 `{"content","tool_calls"}`；`tool_calls` 元素含 `id/name/args`。
- 工具结果必须以 `{"role":"tool","content":...,"tool_call_id":...}` 追加回 `messages`。
- `max_steps < 1` 抛 `ValueError`；`llm_fn` 异常 -> `stopped_reason="model_error"`。
- 未知工具/参数错误/工具异常不崩，记录 `trace`，继续循环。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 请求 `nope` 工具 | `error="unknown_tool"` |
| 2 | `args` 不是 dict | `error="invalid_args"` |
| 3 | 缺 `city` / `city` 是 int | `error="invalid_args"` |
| 4 | 工具 handler 抛异常 | `error="tool_error"` |
| 5 | 工具返回非 str | `error="invalid_tool_output"` |
| 6 | 模型一直请求工具 | `stopped_reason="max_steps"` |
| 7 | 模型调用抛异常 | `stopped_reason="model_error"` |
| 8 | 工具结果回灌 | 第二次调用能看到 `role="tool"` 和 `tool_call_id` |

## 验收标准

`gate_check.py` 的 11 项全部 PASS：

- 工具表/元数据、合法分发、3 类参数错误、工具异常。
- 无工具直接回答、工具回灌后收尾、未知工具、工具异常、超步数、模型异常、`max_steps=0`。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么 `tool_calls` 不能直接 `eval` 执行？
2. 工具结果回灌时，`tool_call_id` 起什么作用？丢了会怎样？
3. 如果工具有副作用（退款/删除），这个循环还缺哪几层？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（11/11）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python chapters/part1-foundations/1.5-tool-calling/tool_calling.py
```

参考实现采用原生的 SDK 完整还原了 OpenAI 风格工具调用协议的全链路，涵盖了工具 Schema 声明、并发工具解析、基于 role="tool" + tool_call_id 的结果回灌，以及工具失败的防御性回传。

对照时思考并回答：

1. 为什么在工具调用中，工具执行抛出的异常（如参数非法、超时、网络错误）不能直接崩溃抛出，而必须作为结构化错误信息通过 role="tool" 回灌给模型？
2. 协议中的 `tool_call_id` 是如何保证模型在发起多个并行工具调用时，能准确将返回结果与各个调用上下文一一对应的？
3. 为什么必须硬性限制 `max_steps`？当达到最大循环步数时，工程上应当返回降级提示还是直接拒绝服务？

## 框架对照

同一工具调用流程在 LangChain 中通常这样实现（历史参考代码已归档至 [tool_calling_langchain.py](tool_calling_langchain.py)）：

```python
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """查询指定城市当天的实时天气。"""
    return f"{city} 晴 22℃"

llm_with_tools = llm.bind_tools([get_weather])
ai_msg = llm_with_tools.invoke("北京天气怎么样？")
# 框架将自动提取 ai_msg.tool_calls 并分发
```

### 框架省去了什么，又隐藏了什么？
1. **省去的代码**：
   - 自动通过函数签名与 Docstring 生成 JSON Schema；
   - 自动将 `tool_calls` 转换为 `ToolMessage` 并绑定 `tool_call_id`。
2. **隐藏的行为与潜在风险**：
   - **错误吞没与抛出边界**：如果工具抛出非受检异常，默认可能直接抛出崩溃，而不是把错误信息组织成观察结果（Observation）回灌给模型促使其纠偏；
   - **并发分发控制**：面对并行工具调用（Parallel Tool Calling）时，原生实现可以清晰地控制是串行还是并发执行，而框架封装容易隐藏异步并发与超时控制细节；
   - **参数防御**：直接依赖类型提示（Type Hints）自动反射生成的 Schema，对于复杂校验逻辑（如正负数、正则格式）缺乏显式防御断言。

## 概念地图

- **工具 schema**：名字、说明、参数类型；模型靠它选工具。
- **模型只请求**：执行权在程序；参数必须校验后才能进 handler。
- **结果回灌**：`role="tool"` + `tool_call_id`，模型才能把结果对上是哪次请求。
- **有界循环**：`max_steps` + 明确出口；没有上限的循环会烧钱、拖延迟。
- **可读失败**：未知工具/参数错/异常都要能解释，不能只打印堆栈。

## 边界

- gate 用脚本化模型，不调用真实模型；真实 function calling 的稳定性另验。
- 通过 gate 只证明工具循环结构正确，不证明模型选工具准确。
- 审批、权限、审计、幂等见 L4.8/L5.4。
