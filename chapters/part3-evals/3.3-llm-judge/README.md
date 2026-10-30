# L3.4 LLM Judge 与校准 · Gate（原 3.3）

[全书目录](../../README.md) · [上一章 3.2](../3.2-eval-basics/README.md) · [下一章 3.4](../3.4-eval-dataset-build/README.md)

- **能力**：用 LLM 评语义正确性/忠实度，解析结构化裁决，并用人工标签校准裁判。
- **v2 路径**：L3.4 / 核心（Gate；Judge 校准）
- **前置**：1.3（结构化输出）、3.2（基础评测）；真实跑裁判时还需要 `DEEPSEEK_API_KEY`。
- **时间盒**：6 小时（1h 读 + 3h 实现 + 2h 校准与失败分析）。
- **闭卷规则**：只读本页、`gate/starter.py`；**通过 gate 之前不要打开** `llm_judge.py`。
- **验收命令**：

```bash
python chapters/part3-evals/3.3-llm-judge/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 来绕过检查。

## 为什么做这个 gate

关键词评测太死板：答案写“检索增强生成”，标准答案写“检索+生成”，意思一样却判没命中。LLM Judge 能处理同义表达，但它自己也可能是错的、偏的、格式不稳定的。

所以这个 gate 不考“会不会调用裁判”，而考三件事：

1. **裁判输出可解析**：分数、理由、围栏 JSON、夹在说明文字里的 JSON、非法输出。
2. **失败可重试、可终止**：格式错/模型异常时重试，重试耗尽给可读错误，不静默吞掉。
3. **裁判可校准**：用人工标签算一致率和混淆矩阵，能发现“全判通过”的裁判。

## 任务

实现 `gate/starter.py` 的四个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `build_prompt` | 包含问题、答案、标准答案、上下文；说明 1–5 分、只看意思、依据上下文 |
| `parse_verdict` | 解析纯 JSON / 围栏 JSON / 带说明文字的 JSON；非法输出抛 `JudgeFormatError` |
| `judge` | 调裁判、解析、失败重试；返回 `score`/`reason`/`attempts` |
| `calibrate` | 用 `human_pass` 和 `judge_score` 算一致率、混淆矩阵、不一致列表、平均分 |

关键口径：

- `score` 必须是 **1–5 的整数**；`True` 不算整数。
- `reason` 必须非空。
- `attempts < 1` 抛 `ValueError`。
- 校准阈值默认 4：`score >= 4` 视为“判通过”。
- `agreement = (tp + tn) / total`；`mean_score` 是平均分；样本为空时两者都返回 `0.0`。
- `calibrate` 不修改传入的样本。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 裁判输出 `not json` | `JudgeFormatError` |
| 2 | `{"score": 0}` / `{"score": 6}` | `JudgeFormatError` |
| 3 | `{"score": true}` | `JudgeFormatError`（bool 不是整数分） |
| 4 | `{"score": 4, "reason": "  "}` | `JudgeFormatError` |
| 5 | 第一次非法、第二次合法 | `attempts=2`，返回合法分数 |
| 6 | `llm_fn` 抛 `TimeoutError`，第二次合法 | `attempts=2`，返回合法分数 |
| 7 | 两次都非法 | 抛 `JudgeFormatError` |
| 8 | 裁判永远给 5 分 | 一致率只有 0.5，并列出 6 条不一致 |

## 验收标准

`gate_check.py` 的 14 项全部 PASS：

- Prompt：四项齐全，1–5 分、只看意思、依据上下文。
- 解析：纯 JSON、围栏 JSON、带说明文字、6 类非法输出。
- 重试：合法不重试、非法后重试、异常后重试、耗尽抛错、`attempts=0`。
- 校准：12 条样本的 `agreement=8/12`、混淆矩阵 `tp=4,tn=4,fp=2,fn=2`、不一致列表、`mean_score=39/12`。
- 校准边界：全判通过的低质量裁判能被抓住；空样本；非法样本。

通过后，在 [workbook.md](workbook.md) 写：

1. 你的 `parse_verdict` 最容易漏掉哪种非法输出？
2. 为什么“裁判全给 5 分”在 `agreement` 上会暴露？
3. 如果人工标签本身有错，校准结果会怎样？你怎么发现？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（14/14）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 3.3
```

对照时只回答：

1. 原生参考实现如何通过 Tool-as-Output（`tools=[JUDGE_TOOL]`）与 `parse_verdict` 实现双重格式防御？
2. 为什么在两两对比中需要通过“候选位置互换（Position Swap）”来减轻裁判的位置偏见？
3. 当人工标签与裁判判定存在系统性偶然重合时，Cohen's Kappa（κ）相比粗略一致率（Agreement）提供了什么额外价值？

## 判分器分级与工程选型阶梯

在 AI 系统的质量评测中，判分机制应遵循严格的工程优先级阶梯，避免盲目引入高成本的大模型裁判：

1. **代码判分（Code-based / Rule-based Evaluator）**：
   - **手段**：精确字符串包含、正则匹配、JSON Schema 校验、SQL/AST 语法树断言、确定性算法（如 BM25 关键词匹配、编辑距离）。
   - **优势**：执行速度极快（微秒/毫秒级）、零 API 费用、结果 100% 确定可复现。
   - **原则**：**优先用代码判分**；凡是能用规则量化、格式约束或代码判决的指标，绝不上模型。

2. **模型判分（Model-based / LLM-as-Judge）**：
   - **手段**：利用通用或微调的大模型依据预设 Rubric（打分量表）评估语义正确性、忠实度、总结完整性等主观维度。
   - **局限**：存在自相矛盾、格式脆弱、长度偏见（偏好冗长文本）与位置偏见（Position Bias）。
   - **原则**：代码判不了的才用 LLM Judge，且必须结合结构化输出工具与重试终止边界。

3. **人工校准（Human-in-the-loop Calibration）**：
   - **手段**：资深业务专家或标注员对评测样本进行双盲标注，作为“金标准（Ground Truth）”。
   - **原则**：**用人工标注校准 Judge**；通过混淆矩阵、一致率（Agreement Rate）与 Cohen's Kappa（κ）系数定期监控裁判退化，确认模型裁判能否可信替代人工抽检。

> **行业参考**：上述判分阶梯与工程原则详见 Anthropic 发布的评测实践指南《Demystifying evals for AI agents》（[Anthropic 官网](https://www.anthropic.com/news/evals-for-ai-agents)，2026-01-09；读取日期：2026-10-30）。

## 核心深入阅读

- 进阶校准方法论、评分量表制定与群体裁判（Judge Committees）深度演练，请阅读 [8.5 LLM Judge 校准](../../part8-ai-quality-optional/8.5-judge-calibration/README.md)。

## 概念地图

- **裁判也是被测系统**：裁判会偏、会错、会格式不稳定；必须校准，不能把分数当真理。
- **结构化裁决**：分数 + 理由，才能统计、追溯和做混淆矩阵。
- **重试边界**：只重试格式/瞬时错误；重试耗尽要抛可读错误，不能无限循环。
- **一致率与混淆矩阵**：一致率给总体，混淆矩阵告诉你错在“放过坏答案”还是“错杀好答案”。
- **人工标签**：校准的基准；标签本身也要抽检，否则校准的是错的。

## 边界

- gate 用脚本化裁判输出，不调用真实模型；通过它只证明解析、重试、校准逻辑正确。
- 真实裁判的效果还取决于 prompt、模型能力和人工标签质量。
- 裁判分数不能替代来源、权限、引用边界和业务规则的检查。
