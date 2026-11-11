# 3.7 回归对比：Baseline、Candidate 与质量门禁

[全书目录](../../README.md) · [上一章 L3.5](../3.5-eval-dataset-ragas/README.md) · [下一章 L3.6（3.8）](../3.8-prompt-ab-judge/README.md)

- **目标**：在同一批问题上对比基线（Baseline）与候选（Candidate）系统，计算质量指标、P50/P99 延迟与异常率，识别质量退化告警，掌握 pass@k 与 pass^k 的场景选型，构建可用于 CI 的回归门禁。
- **v3 路径**：L3.6 / 核心（Gate；回归曲线）
- **前置**：2.6（被测检索与来源追踪）、3.2。
- **环境**：默认完全离线运行；带 `--live` 可发起真实模型调用。
- **命令**：`python chapters/part3-evals/3.7-eval-regression-curve/gate/gate_check.py`

## 问题

每次修改 Prompt、知识库切分策略或检索召回算法后，你可能会发现评测集上的“平均分”上升了 2 分。
然而，平均分上升往往会掩盖局部严重的质量退化：
1. 原本必对的合规/事实问题突然全部答错；
2. 尾部 P99 延迟由于多次检索重试出现恶化；
3. 偶发超时导致运行时错误率（Error Rate）升高。

我们需要一种能够在同一基准集上并排对比版本指标、输出退化告警，并在退化发生时阻断发布的回归对比与门禁机制。

## 概念

- **Baseline vs Candidate**：基线是当前稳定运行的生产版本；候选是经过改动待发布的被测版本。两者必须在完全相同的评测集上运行才有统计可比性。
- **P50 / P99 延迟**：均值容易被少量极端快/慢的值拉偏。P50 反映典型用户体验，P99 反映系统最慢的尾部延迟瓶颈。
- **Error Rate**：仅统计请求抛出异常（网络超时、限流 429、代码崩溃）的运行时错误比例，与回答内容质量指标区分统计。
- **回归告警（Regression Alerts）**：设定容忍阈值（如错误率上升、P99 增加超 2000ms、通过率下降超 2%），自动抓出性能退化。
- **pass@k 与 pass^k（pass-all-k）**：
  - **pass@k**：在 $k$ 次独立试验中至少成功 1 次的概率；
  - **pass^k**：单次成功率为 $p$ 时，连续 $k$ 次全部成功的概率（$p^k$）。

## 任务

### 规则

- 闭卷实现：只读本任务书，不打开 `regression_curve.py`。
- 实现 `gate/starter.py` 中的 8 个核心函数并通过 13 项离线 Gate 检查：
  - 原有 4 个函数：`percentile`、`score_case`、`summarize`、`regression_alerts`；
  - 进阶追加 4 个函数：`pass_at_k`、`pass_all_k`、`empirical_pass_all`、`split_suites`。

### 关键口径

| 函数 | 输入 | 输出 | 关键约束与边界 |
|---|---|---|---|
| `percentile` | `values: list[float], pct: int` | `float` | 线性插值分位数；空列表返回 0.0；pct 不在 0–100 抛 ValueError |
| `score_case` | `case: dict, outputs: dict` | `dict` | 计算 `keyword_score`、`citation_score`、`refusal_ok`；当 keyword>=0.67 且 citation>=0.67 且 refusal_ok==1.0 时 `passed=True` |
| `summarize` | `rows: list[dict]` | `dict` | 汇总 cases、error_rate、p50_latency_ms、p99_latency_ms、pass_rate、keyword_score、citation_score、refusal_ok、failures 列表；空 rows 全 0 |
| `regression_alerts` | `baseline: dict, candidate: dict` | `list[str]` | 检测 5 类退化：error_rate 上升 > 0、p99 上升 > 2000ms、pass_rate 下降 > 0.02、citation_score 下降 > 0.02、refusal_ok 下降 > 0 |
| `pass_at_k` | `n: int, c: int, k: int` | `float` | 无偏估计 $1 - \frac{C(n-c, k)}{C(n, k)}$；当 $n-c < k$ 时返回 1.0；$k < 1$、$k > n$、$c > n$ 或任一参数为负抛 ValueError |
| `pass_all_k` | `success_rate: float, k: int` | `float` | 计算 $p^k$；success_rate 不在 [0.0, 1.0] 或 $k < 1$ 抛 ValueError |
| `empirical_pass_all` | `results: dict[str, list[bool]], k: int` | `float` | 统计前 $k$ 次记录全为 True 的任务比例；空字典 `{}` 返回 0.0；某任务记录不足 $k$ 次或 $k < 1$ 抛 ValueError |
| `split_suites` | `results: dict, floor: float = 0.95` | `tuple[list, list]` | 按通过率划分 `(regression_suite, capability_suite)` 并按任务名排序；floor 不在 [0.0, 1.0] 抛 ValueError |

### 故障注入预测

在实现前，先在 [workbook.md](workbook.md) 中预测以下场景的行为：
1. 平均分上升但某一类样本全部失败时，回归告警是否能够捕获；
2. 包含网络超时的异常行如何影响 error_rate；
3. 5 类指标退化的边界触发逻辑；
4. pass@k 参数非法（$k < 1$、$k > n$）与边界场景；
5. empirical_pass_all 在空输入与记录不足时的处理；
6. split_suites 的 floor 越界校验。

## 验收

```bash
python chapters/part3-evals/3.7-eval-regression-curve/gate/gate_check.py
```

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么平均分上涨仍可能藏着回归？
2. p99 和均值各适合回答什么问题？
3. 告警阈值应该由谁定？定得太松/太紧的代价？
4. 为什么面向客户的生产系统不能仅看 pass@k，而必须关注 pass^k？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（13/13）。
- workbook 里的失败分析与四个问题的回答。

## 能力评测与回归评测的工程边界

在构建自动化评测套件时，工程实践中常区分两类不同用途的评测：

1. **能力评测（Capability Evals）**：
   - **目标**：摸索模型或系统在复杂、长尾、新引入任务场景下的表现边界。
   - **特性**：初期通过率可能较低，重点在于观察迭代改进趋势。
   - **度量**：本章的判断是能力评测常关注 **pass@k**——在 $k$ 次独立尝试中只要有 1 次成功即可（适合提供多样化备选答案、允许重试的场景；在编程基准测试中，开发实践通常重点关注首次通过率 pass@1）。这是本章的工程判断，不是 Anthropic 原文的固定对应。

2. **回归评测（Regression Evals）**：
   - **目标**：守住系统在已上线业务、核心查询和关键合规用例中的基线。
   - **特性**：预期通过率应维持在高位（如 $\ge 95\%$ 或 $100\%$）。在发布门禁中，核心指标下降即为明显的退化信号。
   - **度量**：本章的判断是回归与面向客户的场景更关注 **pass^k（pass-all-k）**——单次成功率为 $p$ 时连续 $k$ 次独立试验全部成功的概率（$p^k$）。对于面向客户的企业客服、交易下单等需要高稳定性的场景，单次 95% 通过率在连续独立执行 5 次时复合全通率约为 $77.4\%$（$0.95^5$），稳定交付需关注连续通过率。

> **行业参考**：Anthropic 评测指南《Demystifying evals for AI agents》（[Anthropic 官网](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)，2026-01-09；读取日期：2026-10-31）的选择依据是按产品需求：只要一次成功就够用时用 pass@k（编码最看重 pass@1），要求每次都可靠时用 pass^k；原文并没有把“能力评测”与“回归评测”固定对应到两个指标。上面的对应关系是本章的工程判断；将评测套件划分为能力集与回归集也属于工程落地的测试策略。

## 通过后对照参考实现

通过 gate 后，再运行并对照参考实现：

```bash
python tools/run_chapter.py 3.7
```

### CI 回归门禁用法

参考实现支持作为 CI/CD 质量卡点：

```bash
# 当检测到回归退化告警时以非 0 退出（exit 1），阻止 CI 合并
python tools/run_chapter.py 3.7 --fail-on-regression

# 将候选版本的失败样本写入 shared-data/failures.json 供 3.10 诊断
python tools/run_chapter.py 3.7 --write-failures

# 指定自定义评测用例集
python tools/run_chapter.py 3.7 --cases path/to/eval_set.json
```

失败记录含 `mode` 字段（`offline` / `live`）。3.10 仍按有没有 `retrieval_context` 推断来源；用 3.7 离线写出的失败库时，请给 3.10 显式加 `--mode offline`，否则真实检索上下文会被误判为 live 产物。

对照时思考：
1. 原生参考实现如何脱离 LCEL 完成 Baseline 与 Candidate 的对照并统计 P50/P99 耗时？
2. 在面向终端用户的业务场景中，为什么衡量指标应当关注 pass^k 而非单一 pass@k？
3. `split_suites` 将高通过率任务与低通过率任务分流，对 CI/CD 流水线的门禁策略有何指导意义？

## 概念地图

- **基线与候选**：同一题集、同一配置才有可比性。
- **平均分陷阱**：总分掩盖某类样本的局部退化。
- **分位数**：p50/p99 看尾部延迟，均值看总体。
- **错误率**：只统计运行时异常，不混同质量差。
- **门禁：阈值是业务风险选择**：技术只能给出退化幅度，阻断与否取决于业务能承受多少风险。
- **pass@k 与 pass^k**：试错探索看 pass@k，稳定上线看 pass^k。
- **套件分流（split_suites）**：回归集进 CI 强卡点，能力集进看板持续迭代。

## 边界

- gate 用固定数据离线测试，不调用真实模型。
- 通过 gate 只证明指标/告警与概率计算逻辑正确，不证明候选版在真实场景下的表现。
- 完整的端到端上线验证还需结合 3.10 失败诊断与线上持续监控。
