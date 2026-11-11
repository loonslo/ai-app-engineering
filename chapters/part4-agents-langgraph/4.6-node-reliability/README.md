# L4.3 扩展：节点可靠性 · Gate（原 4.6）

[全书目录](../../README.md) · [上一章 L4.9（4.4）](../4.4-state-reducer/README.md) · [下一章 L4.10（4.10）](../4.10-checkpoint-context/README.md)

- **能力**：节点失败降级；区分可重试/不可重试错误；给慢调用设真实超时。
- **v3 路径**：L4.9 / 核心（Gate；节点可靠性）
- **前置**：4.5（ReAct 工具循环）。
- **时间盒**：6 小时（1h 读 + 4h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `node_reliability.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.6-node-reliability/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

本章只新增失败契约：瞬时错误才重试，确定性错误快速失败；降级必须明确标注，不能把缓存或模拟结果伪装成实时数据。超时要限制等待，不是调用结束后再比较耗时。即使停止等待，后台工作仍可能继续，写操作还需要目的端幂等。

这个历史 gate 用假函数与短暂的真实 sleep 检查降级、异常分类和限时返回；它不是假时钟测试。是否需要图及版本边界见 [4.2](../4.2-langgraph-basics/README.md#什么时候需要图)。本仓库锁定 `langgraph==1.2.8`；细则的本机历史记录是 2026-10-27 的 `1.2.10`，不等于当前安装值（读取于 2026-10-31）。

## 任务

实现 `gate/starter.py` 的三个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `robust_call` | 成功返回 ok；异常返回 fallback + error，不向外抛 |
| `is_retryable` | 只把 TimeoutError/ConnectionError 判为可重试 |
| `with_timeout` | 真正限时；超时返回 on_timeout；fn 异常透传 |

关键口径：

- `robust_call` 的 `error` 是可读原因，`value=fallback`。
- `ValueError/KeyError` 不可重试。
- `seconds <= 0` -> `ValueError`。
- 超时不能无限等待；`fn` 自身异常不能被当成“超时”吞掉。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | fn 成功 | ok=True，原值 |
| 2 | fn 抛 ConnectionError | ok=False，fallback，error 含原因 |
| 3 | Timeout/Connection vs ValueError/KeyError | True / False |
| 4 | 快速 fn + 1s | 原值 |
| 5 | sleep 0.1 + 0.02s | 0.02s 左右返回 fallback |
| 6 | seconds=0/-1 | `ValueError` |
| 7 | fn 抛 ValueError | 原样抛出 |

## 验收标准

`gate_check.py` 的 7 项全部 PASS：

- 成功、降级、可重试、快速、超时、非法 seconds、异常透传。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么“参数错误”不该重试？
2. 降级结果为什么必须让用户/下游知道？
3. “跑完再看耗时”和真正超时的差别是什么？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（7/7）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.6
```

`node_reliability.py` 默认离线：固定随机种子演示降级、重试，脚本聊天模型调用 `divide(10, 0)`，把工具异常回灌；第四段仍保留先等待完成再比较耗时的**反例**，不满足本 gate 的限时契约。需要真实模型时显式执行 `python tools/run_chapter.py 4.6 node_reliability.py --live`，经 `common.get_llm()` 读取模型配置；缺配置/调用失败退出 1，无 traceback。本次是“安全入口接线改动而非图逻辑改写”，另按已读取的锁定版本源码把同一重试策略参数名对齐为 `retry_policy`，未改变重试语义；七项 gate 未改。

对照时只回答：

1. 参考实现的 `robust_node` 捕获哪些异常？会不会吞掉编程错误？
2. 参考实现的 `with_timeout` 是真超时还是“跑完再看”？
3. `RetryPolicy` 的 `retry_on` 为什么只列 Timeout/Connection？

## 概念地图

- **降级**：失败返回可用结果，图继续；但要标注“降级”。
- **可重试**：瞬时错误才重试；确定性错误快速失败。
- **超时**：必须能中断等待，不是事后统计。
- **幂等**：重试只适用于只读/幂等操作；写操作要幂等键。
- **可观测**：降级/重试要记录原因，见 4.9。

## 边界

- gate 用假函数/真 sleep，不验证 RetryPolicy/ToolNode 真实行为。
- 通过 gate 只证明降级/超时结构正确。
- 真实模型限流、工具异常回喂见参考实现与 4.9。
