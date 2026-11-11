# L4.3 状态与 Reducer · Gate（原 4.4）

[全书目录](../../README.md) · [上一章 L4.9（4.3）](../4.3-branch-loop/README.md) · [下一章 L4.9（4.6）](../4.6-node-reliability/README.md)

- **能力**：理解节点返回值如何合并进 state；用 reducer 处理累加、fan-out 和滑动窗口。
- **v3 路径**：L4.9 / 核心（Gate；状态 Reducer）
- **前置**：4.3（分支与循环）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `state_reducer.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.4-state-reducer/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

本章只新增“字段怎样合并”：顺序写入默认覆盖；需要累积时给字段声明 reducer（旧值与增量合成新值的函数）。同一步多分支写入同一普通字段会抛 `InvalidUpdateError`，不能把它误解成“最后完成者覆盖其他分支”。稳定业务顺序应显式带序号，再在消费端排序。

是否需要图及版本边界见 [4.2](../4.2-langgraph-basics/README.md#什么时候需要图)。本仓库锁定 `langgraph==1.2.8`；细则的本机历史记录是 2026-10-27 的 `1.2.10`，不等于当前安装值（读取于 2026-10-31）。

## 任务

实现 `gate/starter.py` 的五个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `merge_lists` | 拼接 old+new，不修改输入 |
| `keep_last_n` | 合并后保留最近 n 条；n<1 报错 |
| `build_accumulate_graph` | log 用 `operator.add`，两步都保留 |
| `build_fanout_graph` | results 用 `operator.add`，三分支都保留 |
| `build_fanout_no_reducer` | results 不写 reducer，invoke 抛 `InvalidUpdateError` |

关键口径：

- reducer 返回新列表，不原地修改。
- `keep_last_n` 的 n 必须 >=1。
- 累加图：`log == ["A","B"]`。
- fan-out 图：3 条结果都保留。
- 无 reducer 的 fan-out：抛 `InvalidUpdateError`，不是静默覆盖。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | merge_lists(["a"],["b"]) | ["a","b"]，输入不变 |
| 2 | keep_last_n 3 保留最近 | ["2","3","4"] |
| 3 | n=0 | `ValueError` |
| 4 | 累加图 | 两条 log |
| 5 | fan-out | 三条 results |
| 6 | 无 reducer fan-out | `InvalidUpdateError` |

## 验收标准

`gate_check.py` 的 5 项全部 PASS：

- merge_lists、滑动窗口、累加图、fan-out、无 reducer 报错。

通过后，在 [workbook.md](workbook.md) 写：

1. 覆盖和累加分别适合什么字段？
2. 为什么 fan-out 写同一字段必须用 reducer？
3. reducer 保证“不丢”但不保证“有序”，怎么补顺序？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（5/5）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.4
```

`state_reducer.py` 全程离线。保留的历史示例中，`FanStateNoReducer` 的行内“最后写入胜出”注释不适用于同一步 fan-out，以实际的 `InvalidUpdateError` 演示为准；`keep_last_n` 示例也未校验 n，闭卷实现仍必须满足本页 n<1 报错的契约。

对照时只回答：

1. 参考实现的 `AccumulateState` 和 `FanState` 用了什么 reducer？
2. 参考实现为什么说无 reducer 的 fan-out 是“图跑不起来”而不是“静默丢数据”？
3. 参考实现的有序 fan-out 用什么办法补顺序？

## 概念地图

- **reducer**：`Annotated[类型, 合并函数]`；旧值 + 新值 -> 新值。
- **覆盖**：默认规则；后写胜出。
- **operator.add**：列表拼接/数字相加。
- **fan-out**：同一步多节点写同一字段，必须有 reducer。
- **顺序**：reducer 不保证顺序；带序号、消费端排序。

## 边界

- gate 只验证合并规则，不涉及真实并发时序。
- 通过 gate 只证明 reducer/图结构正确。
- 4.5 的 MessagesState、4.14 的并行分支会复用本 gate 的规则。
