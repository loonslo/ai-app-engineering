# L4.2 LangGraph 基础 · Gate（原 4.2）

[全书目录](../../README.md) · [上一章 L4.8](../4.17-native-vs-sdk-gate/README.md) · [下一章 L4.9（4.3）](../4.3-branch-loop/README.md)

- **能力**：用 State/Node/Edge 搭线性图；用条件边把流程接成有出口的循环。
- **v2 路径**：L4.2 / 核心（Gate；LangGraph 基础）
- **v3 路径**：L4.9 / 核心（Gate；图结构基础）
- **前置**：4.1（Agent 模式）；已能用普通函数和循环传递状态。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `linear_graph.py` / `conditional_graph.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.2-langgraph-basics/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 什么时候需要图

当流程需要显式状态、复杂分支、检查点恢复或人工介入时，再考虑状态图。简单的“调用函数 → 传结果 → 返回”先用普通代码；有 `if` / `while` 不代表必须引入图。

Thoughtworks 雷达 Vol.34 把 LangGraph 从 Adopt 调到 Trial：不是说图无用，而是不再把“刚性图 + 巨大全局共享状态”当成所有 Agent 的默认答案。先让简单 Agent 通过代码交换所需信息，需要时才加图，通常更容易推理、测试和调试。见 [LangGraph 雷达条目](https://www.thoughtworks.com/radar/languages-and-frameworks/langgraph)（读取于 2026-10-31）。

本组四章属于 v3 L4.9，共 8h 增补阅读与练习；保留下面历史 gate 的独立时间盒与接口。仓库 [`requirements.txt`](../../../requirements.txt) 锁定 `langgraph==1.2.8`；2026-10-31 的本机包元数据核对记录也是 `1.2.8`。细则记录的 2026-10-27 本机历史值 `1.2.10` 不是当前值。锁定版本与本机版本仍可能随环境变化，复现以锁定集为准。

## 为什么做这个 gate

本章只建立 State（跨步骤数据）、Node（返回局部更新的函数）、Edge（下一步走向）三件套，再用最小循环检查状态传递与隔离。循环退出条件的设计留给 4.3，合并规则留给 4.4，不在这里重复框架选型背景。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `build_linear` | START → step_a → step_b → END；history 两条 |
| `build_conditional` | START → step_a → step_b → step_c；不通过回 step_b；attempts>=2 通过 |

关键口径：

- 线性图的 state 只需要 `history`。
- 条件图 state：`history/attempts/approved`；step_b 让 attempts+1。
- step_c 在 attempts>=2 时 approved=True，路由到 END；否则回 step_b。
- 从 attempts=1 开始，应再走一轮后通过。
- 图之间不共享状态。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 线性图初始 history=[] | 两条记录、顺序正确 |
| 2 | 条件图 attempts=0 | attempts=2、approved=True |
| 3 | 条件图 attempts=1 | 再走一轮、attempts=2 |
| 4 | 两次 invoke | 结果互不影响 |

## 验收标准

`gate_check.py` 的 4 项全部 PASS：

- 线性顺序、分支循环/审批、从中间状态继续、图之间状态隔离。

通过后，在 [workbook.md](workbook.md) 写：

1. 线性图和 LCEL 的本质差别是什么？
2. 条件边指回上游，为什么必须配计数器/退出条件？
3. 状态字段缺失时，节点应该报错还是给默认值？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（4/4）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.2 graph_basics.py
python tools/run_chapter.py 4.2 linear_graph.py
python tools/run_chapter.py 4.2 conditional_graph.py
```

以上三个脚本都离线、不调用模型。历史参考文件里把 LCEL 写成对照对象；在 v3 主线中，把它理解为“顺序函数组合”即可，不必先学 LCEL。

对照时只回答：

1. 参考实现的 `graph_basics.py` 和你的 `build_linear` 结构是否一致？
2. 参考实现的 `conditional_graph.py` 用什么防死循环？
3. 参考实现用 `history` 手动拼接，和 reducer 有什么区别？

## 概念地图

- **State**：TypedDict 声明字段；跨节点传递。
- **Node**：读 state，返回部分 dict。
- **Edge**：START/END 与普通边；顺序写死。
- **条件边**：按 state 路由；指回上游形成循环。
- **出口**：计数器/阈值/失败状态，循环必须有终止条件。

## 边界

- gate 不调用模型，只验证控制流。
- 通过 gate 只证明状态/边结构正确，不证明业务逻辑正确。
- reducer 合并规则见 4.4；检查点见 4.10。
