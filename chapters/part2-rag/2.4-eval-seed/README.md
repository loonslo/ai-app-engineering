# L2.11 RAG 评测基线 · Gate（原 2.4）

[全书目录](../../README.md) · [上一章 2.3](../2.3-minimal-rag/README.md) · [下一章 2.5](../2.5-raw-sdk-rag-agent-loop/README.md)

- **能力**：把“答得对不对”拆成召回、引用、拒答、关键词四项；用固定样本证明评测器能抓住已知失败。
- **v2 路径**：L2.9 / 核心（Gate；RAG 评测基线）
- **前置**：[1.10 评测体系与嵌入式功能](../../part1-foundations/1.10-embedded-llm-feature/README.md)（掌握 Task/Trial/Grader/Transcript 架构）、[2.3 最小 RAG](../2.3-minimal-rag/README.md)。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页、`gate/starter.py`、`gate/cases.json`；**通过 gate 之前不要打开** `eval_seed.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.4-eval-seed/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 或 `cases.json` 来绕过检查。

## 为什么做这个 gate

关键词命中不代表答案正确，答案正确不代表引用可信，引用可信也不代表该拒答时拒答了。评测器的价值不是“给一个总分”，而是**在失败发生时指出是哪一层失败**。

本章评测器直接继承并特化了 [1.10 评测体系与嵌入式功能](../../part1-foundations/1.10-embedded-llm-feature/README.md) 的标准 Harness 概念：
- **Task（任务定义）**：对应评测集 `cases.json` 中的单条基准题，明确定义用户提问、`expected_chunks`、`should_refuse` 以及期望的关键词约束。
- **Trial（单次执行）**：受试 RAG 系统接收 Task 输入后的一次端到端运行轨迹，产出包含检索片段 ID 列表、回答文本、引用来源及拒绝标志的结果字典。
- **Grader（判分器）**：确定性的规则与判分函数 `evaluate_case`，对单次 Trial 进行多维度量化切片，严密区分召回、引用、拒答与关键词四层达标情况。
- **Transcript（运行明细与汇总）**：运行器 `run` 生成的逐行判定结果与总体统计指标（`pass_rate`、`retrieval_hit_rate`、`citation_accuracy`、`refusal_accuracy`）。

这个 gate 用 12 条固定样本和 12 份已产出的 RAG 结果，故意埋了 6 个失败：

- 召回少了片段；
- 引用了没召回过的片段；
- 作答但不给引用；
- 拒答却附了来源；
- 该答却拒答；
- 同一片段重复引用。

你的评测器必须逐条抓住它们，而不是“看起来都差不多”。

## 任务

实现 `gate/starter.py` 的四个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `load_cases` | 读取 JSON；校验字段、ID 唯一、类型；失败抛 `ValueError` |
| `evaluate_case` | 对一条结果给出 `retrieval_hit` / `citation_ok` / `refusal_ok` / `keyword_ok` / `passed` |
| `summarize` | 汇总 `pass_rate`、`retrieval_hit_rate`、`citation_accuracy`、`refusal_accuracy` |
| `run` | 逐条调用 `ask_fn`，异常不中断整批，返回 rows + summary |

关键口径：

- `sources` 是**片段 ID**（如 `refund-1`），不是文件名。
- `retrieval_hit`：`expected_chunks` 是否**全部**出现在 `retrieved_ids`；无期望片段时为 `None`。
- `citation_ok`：拒答时 `sources` 必须为空；作答时 `sources` 非空、覆盖全部期望片段、是召回集合的子集、无重复。
- `refusal_ok`：`refused` 是否等于 `should_refuse`。
- `keyword_ok`：`keywords` 是否全部出现在答案里。
- `passed`：以上全部成立（`retrieval_hit=None` 不参与）。
- 汇总时分母为 0 返回 `0.0`；`retrieval_hit_rate` 没有可计算样本时返回 `None`。

## 从 20 条到 50 条：评测集构建哲学

根据 Anthropic 发布的工程指导《Demystifying evals for AI agents》（读取日期：2026-10-28）：
> 在 AI 应用与 Agent 研发初期，团队常犯的错误是盲目追求数以千计的合成测试集，却缺乏对失败细节的洞察。最有效的高杠杆评测往往始于 20 到 50 条手工精细标注、来源于真实生产与实验失败的高信噪比 Golden Set。

构建高质量 Golden Set 的演进路径：
1. **20 条打底（核心边界覆盖）**：覆盖高频业务场景，显式注入并固化历史踩过的 Bug（如本章的 6 类典型失败：未召回漏引、跨界编造引用、拒答带证据、格式重复等）。这 20 条能够作为持续集成的快速烟雾测试门禁。
2. **扩充至 50 条（压力与对抗样本）**：引入需要跨文档对比的多跳推理（Multi-hop）、相似但过期的版本冲突、语料外无解提问（检验拒答鲁棒性）、以及在文档中蓄意伪造的 Prompt 注入文本。
3. **分层归因而非单一总分**：在评测中严禁仅记录一个笼统的 Accuracy，必须按照 Harness 范式将指标拆解为检索命中率（Retrieval Hit）、引用忠实度（Citation Accuracy）、拒答准确率（Refusal Accuracy）与语义关键词命中。

## 故障注入（必须亲手触发）

gate 已经内置这些场景，但你要能在自己的实现上复现并解释：

| # | 注入 | 期望 |
|---|---|---|
| 1 | 期望两个片段，只召回一个 | `retrieval_hit=False`，`passed=False` |
| 2 | 引用一个不在 `retrieved_ids` 里的 ID | `citation_ok=False` |
| 3 | 作答但 `sources=[]` | `citation_ok=False` |
| 4 | 拒答但 `sources` 非空 | `citation_ok=False` |
| 5 | 该答却 `refused=True` | `refusal_ok=False` |
| 6 | 同一片段引用两次 | `citation_ok=False` |
| 7 | `ask_fn` 抛 `TimeoutError` | 该行 `passed=False` 且有 `error`，整批继续 |
| 8 | 样本 ID 重复 / 缺字段 | `load_cases` 抛 `ValueError` |

## 验收标准

`gate_check.py` 的 14 项全部 PASS：

- 样本加载：12 条、ID 唯一、缺字段/重复 ID 被拒。
- 单条评测：正确样本通过；6 类失败分别被抓住；结果缺字段被拒。
- 汇总：`pass_rate=0.5`、`retrieval_hit_rate=8/9`、`citation_accuracy=7/12`、`refusal_accuracy=11/12`。
- 运行器：保持顺序、不修改输入、`ask_fn` 异常不中断整批。

通过后，在 [workbook.md](workbook.md) 写：

1. 哪一个失败项最容易漏判？为什么？
2. 如果只看 `pass_rate`，会漏掉什么？
3. 这套评测器接到你 2.3 的 RAG 上，最可能先暴露出哪类失败？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（14/14）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 2.4 eval_seed.py
```

对照时只回答：

1. 参考实现为什么把 `recall` 和 `citation_ok` 分开？
2. 参考实现怎么处理“召回了但上下文预算为 0”的情况？你的评测器能区分吗？
3. 参考实现没有 `run` 的异常兜底；如果 `ask_fn` 超时，整批会怎样？

## 概念地图

- **分项指标**：召回、引用、拒答、关键词各自回答不同问题，不能用一个总分替代。
- **已知失败注入**：评测器本身也要被测试；用固定失败样本验证它抓得住。
- **拒答与引用互斥**：拒答时附来源会制造“有证据”的假象。
- **引用子集约束**：只能引用召回到的片段，否则就是编造。
- **异常行**：一条失败不能让整批评测中断，否则你看不到其余样本。

## 边界

- 这 12 条是合成样本，只验证评测器的判定逻辑，不代表真实 RAG 质量。
- 关键词仍是粗粒度检查；语义正确性要靠 3.3 的 LLM Judge，最终要靠人工抽查。
- 通过 gate 不等于你的 RAG 达标；下一步是用真实模型跑 30 题并看指标。
