# L3.6 回归对比 · Gate（原 3.7）

[全书目录](../../README.md) · [上一章 3.6](../3.6-langsmith-eval/README.md) · [下一章 3.8](../3.8-prompt-ab-judge/README.md)

- **能力**：用同一批样本比较 baseline/candidate 的通过率、引用、拒答、延迟和错误率，计算 pass@k 与 pass^k 稳定性，并触发回归告警。
- **v2 路径**：L3.6 / 核心（Gate；回归对比）
- **前置**：3.2（指标）、3.5（评测集）。
- **时间盒**：6 小时（1h 读 + 4h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `regression_curve.py`。
- **验收命令**：

```bash
python chapters/part3-evals/3.7-eval-regression-curve/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

“平均分涨了”可能掩盖某类问题全错。回归对比最容易出这些错：

- 基线和候选用了不同题集/配置，比较无意义；
- 只报平均分，不保留失败样本；
- 延迟分位数算错，p99 被最大值或均值替代；
- 告警阈值写反（涨了当降了）；
- 错误率和质量差混为一谈；
- 混淆探索型场景的 pass@k 与生产稳定性场景的 pass^k。

这个 gate 验证分位数、单条评分、汇总统计、告警阈值以及 pass@k / pass^k / 套件划分。

## 任务

实现 `gate/starter.py` 的函数：

| 函数 | 你要交付的行为 |
|---|---|
| `percentile` | 线性插值分位数；空列表 0；pct 越界报错 |
| `score_case` | keyword/citation/refusal 三项分 + `passed` |
| `summarize` | cases/error_rate/p50/p99/pass_rate/三项均分/failures |
| `regression_alerts` | 5 类退化告警；无退化返回 [] |
| `pass_at_k` | n 次独立尝试中 c 次成功时“k 次里至少成功 1 次”的无偏估计：$1 - C(n-c, k) / C(n, k)$；参数非法报错；$n-c < k$ 返回 1.0 |
| `pass_all_k` | 单次成功率为 p 时连续 k 次全部成功的理论概率 $p^k$；p 越界或 $k < 1$ 报错 |
| `empirical_pass_all` | 每个任务取前 k 次记录统计“k 次全部通过”的任务占比；记录不足 k 次报错 |
| `split_suites` | 通过率 $\ge$ `regression_floor` 归入回归集，其余归入能力集；两个列表均按任务名排序 |

关键口径：

- `keyword_score`/`citation_score` 没有对应标注时记 1.0。
- `refusal_ok`：拒答词是否与 `should_refuse` 一致。
- `passed`：keyword $\ge 0.67$、citation $\ge 0.67$、refusal_ok=1。
- 告警：error 上升 >0；p99 上升 >2000ms；pass 下降 >0.02；citation 下降 >0.02；refusal 下降 >0。
- 空 rows -> 全 0，`failures=[]`。
- `pass_at_k` 中 $k > n$、$c > n$ 或任一参数为负抛 `ValueError`；$n - c < k$ 时返回 1.0。
- `split_suites` 默认 floor 为 0.95，返回 `(regression_suite, capability_suite)`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 空/单值/插值 | 0 / 自身 / 5 |
| 2 | 正确样本 | 三项满分，passed |
| 3 | 关键词未命中 | score<0.67，failed |
| 4 | 应拒未拒 / 正确拒答 | 0 / 1 |
| 5 | 缺来源 | citation=0，failed |
| 6 | 汇总含异常行 | error_rate=0.5、p50=20、p99=29.8 |
| 7 | 5 类退化 | 5 条告警 |
| 8 | 阈值边界 | 不误报 |
| 9 | `pass_at_k` 传入负数或 $k > n$ | 抛出 `ValueError` |
| 10 | `pass_at_k` 剩余失败数 $n - c < k$ | 返回 1.0 |
| 11 | `pass_all_k` 传入 $p = -0.1$ 或 $k = 0$ | 抛出 `ValueError` |
| 12 | `empirical_pass_all` 某任务记录不足 $k$ 次 | 抛出 `ValueError` |
| 13 | `split_suites` 传入非法 `regression_floor`（如 1.2） | 抛出 `ValueError` |

## 验收标准

`gate_check.py` 的 13 项全部 PASS（原 8 项 + 追加 5 项）：

- 原 8 项：分位数、正确样本、关键词、拒答、来源、汇总、告警、边界。
- 追加 5 项：pass@k 估计与边界、pass@k 参数校验、pass^k 概率计算与边界、经验连续通过率统计、评测集划分与排序。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么平均分上涨仍可能藏着回归？
2. p99 和均值各适合回答什么问题？
3. 为什么面向客户的生产系统不能仅看 pass@k，而必须关注 pass^k？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（13/13）。
- workbook 里的失败分析与三个问题的回答。

## 能力评测与回归评测的工程边界

在构建持续评测（Continuous Evals）流水线时，必须明确区分两类性质完全不同的评测套件：

1. **能力评测（Capability Evals）**：
   - **目标**：摸高，探索模型在极端、复杂或新引入任务场景下的表现边界。
   - **特性**：起点通过率通常较低（可能仅 30%~60%），刻意留出充足的提升与探索空间。
   - **度量**：常关注 **pass@k**——在 $k$ 次独立尝试中只要有 1 次成功即可（适合代码生成、Agent 自主修复等“允许试错、最终对一次就算成功”的场景）。

2. **回归评测（Regression Evals）**：
   - **目标**：守底，守住系统在已上线业务、关键用例与高频查询中的确定性基线。
   - **特性**：预期通过率应无限接近 100%（例如 $\ge 95\%$ 或 $100\%$）。在发布门禁中，**任何通过率的微小下降或关键用例报错都是致命的退化信号**。
   - **度量**：必须关注 **pass^k（pass-all-k）**——单次成功率为 $p$ 时连续 $k$ 次全部成功的概率（$p^k$）。对于面向客户的企业客服、金融问答、权限隔离等零容错场景，单次 95% 通过率在 5 轮交互后复合成功率仅剩约 $77.4\%$（$0.95^5$），必须以连续稳定全通为发布标准。

> **行业参考**：关于能力评测与回归评测的分流规范，以及 pass@k 与 pass^k 的场景选型，详见 Anthropic 发布的权威指南《Demystifying evals for AI agents》（[Anthropic 官网](https://www.anthropic.com/news/evals-for-ai-agents)，2026-01-09；读取日期：2026-10-30）。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 3.7
```

对照时只回答：

1. 原生参考实现如何脱离 LCEL 管道完成 Baseline 与 Candidate 的对照并统计 P50/P99 物理耗时？
2. 在企业客服或合规 RAG 场景中，为什么衡量指标应当关注 pass^k（pass-all-k）而非 pass@k？
3. `split_suites` 将高通过率任务与低通过率任务分流，对 CI/CD 流水线的门禁策略有何指导意义？

## 概念地图

- **基线与候选**：同一题集、同一配置才有可比性。
- **平均分陷阱**：总分掩盖某类样本的集体退化。
- **分位数**：p50/p99 看尾部延迟，均值看总体。
- **错误率**：只统计运行时异常，不混同质量差。
- **pass@k 与 pass^k**：试错探索看 pass@k，稳定上线看 pass^k。
- **套件分流（split_suites）**：回归集进 CI 强卡点，能力集进看板持续迭代。

## 边界

- gate 用固定数据离线测试，不调用真实模型。
- 通过 gate 只证明指标/告警与概率计算逻辑正确，不证明候选版在真实场景下的表现。
- 完整的端到端上线验证还需结合 3.10 失败诊断与线上持续监控。
