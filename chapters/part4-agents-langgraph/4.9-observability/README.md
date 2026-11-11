# L4.6 可观测性 · Gate（原 4.9）

[全书目录](../../README.md) · [上一章 4.8](../4.8-plan-and-execute/README.md) · [下一章 4.10](../4.10-checkpoint-context/README.md)

- **能力**：把每一步运行留成结构化轨迹；按节点/耗时/错误汇总，定位最慢和失败步骤。
- **v3 路径**：选修 / 选修（被 L5.6 取代）
- **前置**：4.8（规划与执行）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `observability.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.9-observability/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

Agent 答错时，最怕“不知道错在哪一步”。轨迹最容易出这些错：

- 记录缺节点/耗时，无法定位；
- preview 存全量内容，日志爆炸/泄露隐私；
- 只 print 不落盘，不能 grep/diff；
- 汇总只算总数，不找最慢/失败步骤；
- 空轨迹/异常记录让汇总崩。

这个 gate 用内存记录，验证轨迹结构和汇总。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `make_trace_record` | 生成 `ts/node/update_keys/preview`；preview 截断 40；非法报错 |
| `summarize_trace` | total/nodes/slowest/errors；空列表有默认值 |

关键口径：

- `node` 非空、`ts>=0`、`update` 是 dict，否则 `ValueError`。
- `update_keys` 保持 update 的键顺序。
- `preview` 把值转字符串并截断到 40 字符。
- `slowest` 是 ts 最大的 node；空 -> None。
- `errors` 收集 `error` 非空的记录。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 长文本 update | preview 截断 40 |
| 2 | 非 dict update | `ValueError` |
| 3 | 空 node / 负 ts | `ValueError` |
| 4 | 3 条记录含 1 条 error | total/nodes/slowest/errors 正确 |
| 5 | 空列表 | 全默认值 |

## 验收标准

`gate_check.py` 的 4 项全部 PASS：

- 轨迹记录、非法记录、轨迹汇总、空轨迹。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么轨迹只存摘要，不存全量内容？
2. `slowest` 和 `errors` 分别回答什么问题？
3. 轨迹落盘后，怎么做回归 diff？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（4/4）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.9
```

对照时只回答：

1. 参考实现的 `run_with_trace` 每条记录有哪些字段？
2. 参考实现怎么算相对耗时？
3. `stream_mode` 的 updates/values/debug 各适合什么调试场景？

## 概念地图

- **可观测**：每一步可看见、可复盘。
- **结构化轨迹**：JSONL 一行一步；可 grep/diff。
- **preview**：摘要而非全量；控制日志体积与隐私。
- **slowest/errors**：定位慢步骤和失败步骤。
- **stream_mode**：updates/values/messages/debug。

## 边界

- gate 用内存记录，不跑真实图/LangSmith。
- 通过 gate 只证明轨迹结构/汇总正确。
- 真实耗时、隐私脱敏、LangSmith 见参考实现与 3.6。
