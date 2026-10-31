# L5.8 扩展：推理基准 · Gate（原 9.12）

[全书目录](../../README.md) · [上一章 9.11](../9.11-vllm-gpu/README.md) · [下一章 10.1](../../part10-mcp-a2a-optional/10.1-mcp-auth-approval/README.md)

- **能力**：nearest-rank 分位数；只统计成功请求的延迟/吞吐；错误率按全样本；SLO 门禁。
- **v2 路径**：L5.8 / 选读（Gate；推理基准）
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：7.5（容量/性能）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/benchmark.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.12-inference-benchmark/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

基准最容易“把尾延迟平均掉”：

- p95 用均值/线性插值，掩盖慢请求；
- 失败请求混进延迟统计；
- 错误率分母用成功数；
- 没有成功样本仍发布；
- SLO 比较方向写反。

这个 gate 用固定样本验证分位数、汇总和门禁。

## 任务

实现 `percentile`、`summarize`、`release_errors`：

| 函数 | 你要交付的行为 |
|---|---|
| `percentile` | nearest-rank；空/p 越界报错 |
| `summarize` | 成功样本分位数/吞吐；全样本错误率；空/无成功报错 |
| `release_errors` | p95 延迟/TTFT/错误率超限项 |

关键口径：

- p95 两个样本取较慢那个。
- 吞吐 = 成功输出 tokens / 成功延迟总和（秒）。
- 错误率 = (总数-成功数)/总数。
- 严格大于 SLO 才算超限。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | [100,200] p95 | 200 |
| 2 | 3 成功 + 1 失败 | p95 只看成功、错误率 .25 |
| 3 | 空/无成功 | `ValueError` |
| 4 | SLO 未超 | () |
| 5 | 三项超限 | 3 条错误 |

## 验收标准

`gate_check.py` 的 4 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 合成样本，不跑真实推理服务。
- 并发吞吐、GPU 指标见 9.11/9.12 参考实现。
