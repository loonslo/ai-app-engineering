# L4.3 分支与循环 · Gate（原 4.3）

[全书目录](../../README.md) · [上一章 L4.9（4.2）](../4.2-langgraph-basics/README.md) · [下一章 L4.9（4.4）](../4.4-state-reducer/README.md)

- **能力**：用条件边实现分支/循环；用达标条件终止；用 `recursion_limit` 兜底。
- **v2 路径**：L4.3 / 核心（Gate；分支与循环）
- **v3 路径**：L4.9 / 核心（Gate；分支与循环）
- **前置**：4.2（线性图）、1.5（工具循环）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `branch_loop.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.3-branch-loop/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

本章只新增两层退出机制：业务达标条件决定“该不该停”，`recursion_limit` 限制图执行步数，在路由或计数写错时抛 `GraphRecursionError`。它不是质量标准，也不是网络超时。

是否需要图及版本边界见 [4.2](../4.2-langgraph-basics/README.md#什么时候需要图)。本仓库锁定 `langgraph==1.2.8`；细则的本机历史记录是 2026-10-27 的 `1.2.10`，不等于当前安装值（读取于 2026-10-31）。

## 任务

实现 `gate/starter.py` 的三个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `improve` | quality/rounds 各 +1，返回部分 dict |
| `route` | quality>=5 -> `good_enough`，否则 `keep_going` |
| `build_loop` | START→improve；条件边指回 improve 或 END |

关键口径：

- `improve` 不修改输入 state。
- `route` 只读 state，返回字符串。
- `build_loop().invoke({"quality":0,"rounds":0})` -> `{"quality":5,"rounds":5}`。
- `recursion_limit=4` 时必须抛 `GraphRecursionError`，不能静默死循环。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | improve(1,2) | (2,3) |
| 2 | route(4) / route(5) | keep_going / good_enough |
| 3 | 从 0 分跑 | 5 轮到达标 |
| 4 | recursion_limit=4 | GraphRecursionError |

## 验收标准

`gate_check.py` 的 4 项全部 PASS：

- improve 节点、route 分支、循环到达标、recursion_limit 防护。

通过后，在 [workbook.md](workbook.md) 写：

1. 条件边指回上游，为什么必须配退出条件？
2. `recursion_limit` 和业务达标条件各防什么？
3. 节点返回整个 state 会有什么问题？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（4/4）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.3 branch_loop_examples.py
python tools/run_chapter.py 4.3 branch_loop.py
```

两个脚本默认都离线。`branch_loop.py` 后半段用 LangChain 的脚本聊天模型生成固定工具调用，实际执行 `add`，不访问模型；要运行真实工具 Agent，显式执行 `python tools/run_chapter.py 4.3 branch_loop.py --live`。真实模型经 `common.get_llm()`，不写死模型 ID；错误可读提示、退出 1，不打印 traceback。本次属于“安全入口接线改动而非图逻辑改写”，图节点、边和历史 gate 不变；离线结果不证明模型质量。

对照时只回答：

1. 参考实现的 `route` 和你的返回值一致吗？
2. 从 0 分到 5 分要 5 轮，为什么 `recursion_limit=4` 必须报错，而不是提前判为达标？
3. 参考实现后半段用 `tools_condition`/`ToolNode`，它们替手写循环做了什么？

## 概念地图

- **条件边**：路由函数返回语义名，映射到节点/END。
- **循环**：条件边指回上游；必须有退出条件。
- **达标条件**：业务退出（quality>=5）。
- **安全阀**：recursion_limit 防配置错误/意外循环。
- **harness**：工具解析、执行、记忆、中断恢复。

## 边界

- gate 只跑离线质量分循环，不调用模型。
- 通过 gate 只证明控制流正确，不证明 Agent 任务完成。
- 工具循环/记忆见参考实现后半段与 4.5/4.10。
