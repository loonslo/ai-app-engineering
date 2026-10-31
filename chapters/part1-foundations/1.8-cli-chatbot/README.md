# L1.7 CLI 助手 · Gate（原 1.8）

[全书目录](../../README.md) · [上一章 L1.8](../../part2-rag/2.5-raw-sdk-rag-agent-loop/README.md) · [下一章 L1.10](../1.10-embedded-llm-feature/README.md)

- **能力**：把多轮历史、工具调用、命令解析和错误出口拼成一个可测试的 CLI 循环。
- **v2 路径**：L1.7 / 核心（Gate；CLI 助手）
- **v3 路径**：L1.9 / 核心（Gate；CLI 助手）
- **前置**：1.1、1.4、1.5。
- **时间盒**：6 小时（1h 读 + 4h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `chatbot_project.py`。
- **验收命令**：

```bash
python chapters/part1-foundations/1.8-cli-chatbot/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

把零件拼起来时，最容易出现“单测都过，循环一跑就乱”：

- 历史越带越长，或者 `clear` 后还带着旧上下文；
- `quit` 之后还继续处理输入；
- 工具结果没有回灌，模型看不到事实；
- 未知工具/模型异常时直接崩，用户只看到堆栈；
- 没有轮数上限，脚本化输入可以无限跑。

这个 gate 用**脚本化输入 + 脚本化模型**，把 CLI 循环变成可重复验收的行为，而不是只能人工敲。

## 任务

实现 `gate/starter.py` 的 `run_cli`：

| 输入/状态 | 你要交付的行为 |
|---|---|
| 普通输入 | 追加 user → 调 `chat_fn` → 有工具就执行并回灌 → 追加 assistant |
| `clear` | 清空历史，保留 system；输出“记忆已清除” |
| `quit` | 停止，`exit_code=0`，后续输入不再处理 |
| 空行/空白 | 忽略，不调用模型 |
| 未知工具/工具异常 | 输出可读错误，`exit_code=1`，停止 |
| 模型异常 | 输出可读错误，`exit_code=1`，停止 |
| 超过 `max_turns` | `exit_code=2`，停止 |
| `max_turns < 1` | 抛 `CLIError` |

关键口径：

- 历史从 `{"role":"system","content":SYSTEM_PROMPT}` 开始。
- 工具结果以 `{"role":"tool","content":...,"tool_call_id":...}` 回灌。
- 返回 `{"outputs","trace","exit_code","history"}`。
- `history` 是最终消息历史；`trace` 每轮记录 `turn/input/output/tools`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 两轮普通输入 | 第二轮能看到第一轮 assistant |
| 2 | `clear` 后继续问 | 旧历史不再出现 |
| 3 | `quit` 后还有输入 | 不再调用模型 |
| 4 | 空行/空白 | 忽略 |
| 5 | 工具调用后最终回答 | 第二次调用能看到 `role="tool"` |
| 6 | 未知工具 | `exit_code=1`，输出含“工具” |
| 7 | 模型抛异常 | `exit_code=1`，输出含“模型” |
| 8 | 输入超过 `max_turns` | `exit_code=2`，提示达到上限 |
| 9 | `max_turns=0` | `CLIError` |

## 验收标准

`gate_check.py` 的 11 项全部 PASS：

- 单轮、多轮历史、clear、quit、空输入。
- 工具回灌、未知工具、模型异常、超轮数、参数校验、无输入。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么 `quit` 后必须立即停止，而不是先处理完当前缓冲？
2. `clear` 为什么要保留 system 消息？
3. CLI 的 `exit_code` 你会怎么定义？0/1/2 分别代表什么？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（11/11）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python chapters/part1-foundations/1.8-cli-chatbot/chatbot_project.py
```

参考实现改用原生的 `run_cli` 控制循环，跨章复用了 1.3 结构化校验与 1.5 工具调用体系，彻底剥离了 LangChain 框架依赖。

对照时思考并回答：

1. 为什么将命令行输入设计为 `inputs: Iterable[str]` 能够使 CLI 程序在离线状态下实现 100% 自动化单元测试？
2. clear 命令为什么必须重置为仅包含 SYSTEM_PROMPT 的初始状态？如果直接清空成空列表会丢失什么？
3. 生产环境中为什么要硬性限制 max_turns？当触发 max_turns 时，返回特定 exit_code=2 对上层容器编排或监控系统有什么意义？

## 概念地图

- **CLI 循环**：读输入 → 更新历史 → 调模型/工具 → 输出 → 下一轮。
- **命令解析**：`clear`/`quit` 是控制命令，不是普通对话。
- **历史与工具**：工具中间消息可以回灌给模型，但不必全部写入长期历史。
- **退出码**：0 正常、1 错误、2 超限；让脚本和 CI 能判断结果。
- **可测试性**：把 `input()` 换成 `inputs` 迭代器，把模型换成 `chat_fn`，循环就能离线验收。

## 边界

- gate 用脚本化输入/模型，不验证真实模型质量。
- 通过 gate 只证明 CLI 控制流正确，不证明回答正确。
- 真实交互、文件保存、角色切换在参考实现里；权限与审批见 L4.8。
