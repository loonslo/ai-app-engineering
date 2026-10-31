# L5.2 可靠性 · Gate（原 5.2）

[全书目录](../../README.md) · [上一章 5.1](../5.1-serve-fastapi/README.md) · [下一章 5.3](../5.3-cost-cache-routing/README.md)

- **能力**：生成指数退避序列；区分可重试/不可重试错误；按 usage 估算成本。
- **v2 路径**：L5.1 / 核心（Gate；可靠性/退避/成本）
- **前置**：5.1 的 gate（最小超时/重试）、1.1、2.6。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `reliability.py`。
- **验收命令**：

```bash
python chapters/part5-production/5.2-reliability-retry/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

重试和成本统计最容易出这些错：

- 无差别重试，参数错/权限错也重试；
- 退避没有上限，等待时间爆炸；
- 没有 jitter，客户端同步重试打爆服务；
- `max_retries` 含义混淆（次数 vs 总尝试）；
- 成本公式除错 1000/1000000，或 usage 缺失时崩。

这个 gate 用纯函数验证退避、可重试和成本公式，不调用模型。

## 限流是最常见的错误来源

限流（HTTP 429）是生产里最常见的 LLM 调用错误来源之一。Datadog《State of AI Engineering 2026》（2026-04-21 发布，读取于 2026-10-31）的数据：2026 年 2 月，5% 的 LLM 调用 span 报错，其中 60% 由超出速率限制引起；3 月报错 span 降到 2%，限流错误仍占近三分之一。这批数据来自 Datadog 客户的遥测，样本偏向重视基础设施的团队，只能说明量级，不能当作你自己系统的比例。

对重试的含义：限流不是模型坏了，而是容量到顶；盲目快速重试会放大负载。所以要退避、加抖动、尊重 `Retry-After`，并给重试设上限。

## 任务

实现 `gate/starter.py` 的三个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `backoff_delays` | base,2base,4base...，每项截断到 max_delay；参数校验 |
| `is_retryable` | 只把 TimeoutError/ConnectionError 判为可重试 |
| `estimate_cost` | total_tokens/1000*单价；缺失/None -> 0；负单价报错 |

关键口径：

- `max_retries=0` -> []；负数/base<=0/max_delay<=0 -> `ValueError`。
- 退避序列长度等于 max_retries，每项 `min(base*2^i, max_delay)`。
- ValueError/KeyError/PermissionError 不可重试。
- 成本保留浮点，不四舍五入。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | max_retries=3 | [1,2,4] |
| 2 | 6 次，max_delay=20 | [1,2,4,8,16,20] |
| 3 | 0 次 / 负数 | [] / `ValueError` |
| 4 | base=0 / max_delay=0 | `ValueError` |
| 5 | Timeout/Connection/ValueError | True/True/False |
| 6 | 2000 tokens，0.001 | 0.002 |
| 7 | None/空 usage | 0.0 |
| 8 | 负单价 | `ValueError` |

## 验收标准

`gate_check.py` 的 5 项全部 PASS：

- 指数退避、参数校验、可重试、成本、成本参数。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么“参数错误”不该重试？
2. 退避为什么要有上限和 jitter？
3. 成本公式里最容易写错的是什么？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（5/5）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 5.2
```

对照时只回答：

1. `call_with_retry` 为什么用"全抖动"而不是固定的 1/2/4 秒？
2. 为什么 `run_live` 里要把 SDK 自带的 `max_retries` 设成 0？
3. 响应的 `usage` 里哪个字段用于成本？

## 概念地图

- **超时**：单次调用上限。
- **指数退避**：1/2/4…，加 jitter 防同步风暴。
- **可重试**：瞬时错误才重试；确定性错误快速失败。
- **成本**：tokens/1000*单价；usage 缺失要能降级。
- **缓存边界**：评测可缓存；生产问答要防过期/失效。

## 边界

- gate 用纯函数，不调用真实模型/缓存。
- 通过 gate 只证明退避/重试/成本逻辑正确。
- 真实限流、主备切换、缓存失效见参考实现。
- 参考实现用原生 openai SDK：默认离线演示（脚本化假客户端，不联网）；`--live` 调用真实模型，缺密钥或不可达时退出码 1。
- 抖动用 `random`，演示固定种子；生产里还要结合队列和全局并发上限，单个客户端的重试不能解决整体容量问题。
