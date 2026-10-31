# L8 安全/韧性/性能 · Gate（原 8.8）

[全书目录](../../README.md) · [上一章 8.7](../8.7-api-sse-e2e/README.md) · [下一章 8.9](../8.9-ci-layered-gate/README.md)

- **能力**：有限重试/线性退避；输入校验；nearest-rank 分位数；SLO 判断。
- **v2 路径**：L8 / 选做（Gate；安全/韧性/性能）
- **v3 路径**：L5.5 / 核心阅读（归入 L5.5）
- **前置**：5.2（重试）、7.5（性能）。
- **时间盒**：5 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/resilience.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.8-security-resilience-perf/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

重试/输入/SLO 最容易“默认通过”：无限重试、控制字符进日志、p95 插值把尾延迟平均掉、空样本算通过。

## 任务

实现 `call_with_retry`、`validate_input`、`percentile`、`meets_slo`：

| 函数 | 要求 |
|---|---|
| retry | 最多 max_attempts；线性退避；sleep 可注入；返回 result/attempts/error |
| input | 空白/超长/控制字符（换行/制表符除外） |
| percentile | nearest-rank；空/ratio 越界报错 |
| SLO | p95≤预算且错误率≤上限；空样本报错 |

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 首次成功 | attempts=1 |
| 2 | 前两次失败 | attempts=3 |
| 3 | 全失败 | attempts=max、error 保留、退避 [1,2] |
| 4 | max=0/负退避 | `ValueError` |
| 5 | 空白/超长/控制字符 | 报错 |
| 6 | p95 尾样本/SLO 超限/空样本 | 200/False/报错 |

## 验收标准

`gate_check.py` 的 6 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 注入 sleep，不真实等待；不压测服务。
- 生产 SLO/容量仍需真实负载。
