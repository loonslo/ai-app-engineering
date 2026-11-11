# L4.11 Agent 轨迹评测 · Gate（原 3.9）

[全书目录](../../README.md) · [上一章 L4.6](../../part4-agents-langgraph/4.14-supervisor-fanout/README.md) · [下一章 L4.8](../../part4-agents-langgraph/4.17-native-vs-sdk-gate/README.md)

- **能力**：从轨迹提取工具调用；判定期望/禁用工具、完成、步数、最少调用；汇总通过率。
- **v3 路径**：L4.7 / 核心（Gate；Agent 评测）
- **岗位任务 / 面试题型**：T3、T4 / F4、F5
- **前置**：3.2–3.5（RAG 评测）；建议 4.10/4.11 后学。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `trajectory_eval.py`。
- **验收命令**：

```bash
python chapters/part3-evals/3.9-agent-trajectory-eval/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

回答体面不等于行为安全。Agent 评测最容易漏：

- 只看最终答案，不看调了哪些工具；
- 禁用工具在轨迹里出现，仍判通过；
- 没有 final 也算完成；
- 绕远路/死循环不告警；
- 工具调用次数不足，答案其实是编的。

这个 gate 用合成轨迹，验证工具选择、安全屏障、完成度和步数。

## 按结果判分，而不是背诵步骤

[Anthropic《Demystifying evals for AI agents》](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)（读取于 2026-10-31）区分
transcript（运行全过程）与 outcome（环境中的最终状态）。例如“已退款”的回答不是退款到账的证据，应检查退款记录；
不同的合法工具路径可以得到相同结果，不要把某一条参考轨迹的步骤顺序硬编码成唯一正确答案。
原 gate 的工具提取与安全断言保留，新增 `grade_run` 让结果、权限、部分完成与效率分开判。

先亲自读 transcript，再写判分器：确认失败是模型没完成任务、工具故障，还是判分规则误伤。
每次独立试验从干净的订单、审批、缓存和消息历史开始，否则上次写入可能让本次“凭空通过”。
面向客户、要求反复可靠完成的任务，要看 **pass^k**（同一任务前 k 次独立试验全部成功），不是一次对话中 k 轮成功。
本章的 pass@1 是每题首次试验是否满分，再对任务等权平均；不是从多次重试里挑一次成功。
请把 [8.6 Agent 轨迹测试](../../part8-ai-quality-optional/8.6-agent-trajectory-testing/README.md) 作为本章核心阅读，补看参数、顺序与副作用验证。

## 任务

实现 `gate/starter.py` 的五个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `extract_tool_names` | 提取 ai 步的 tool_calls[].name，保持顺序 |
| `evaluate_trajectory` | 计算 expected/forbidden/completed/steps/min_calls/keyword/passed |
| `summarize_trajectories` | 汇总通过率/期望/禁用/完成率；空集全 0 |
| `grade_run` | 结果不对/调用禁止工具时清零；子项按比例、超步扣0.2 |
| `consistency_report` | 每题 pass@1、pass^k 与任务等权总体均值 |

关键口径：

- `expected_ok`：期望工具全部出现；`forbidden_ok`：禁用工具一个都不出现。
- `completed`：存在 `role="final"`。
- `step_count` 只数 ai 步；`tool_call_count` 只数有 tool_calls 的 ai 步。
- `step_count > max_steps` 超限；`tool_call_count >= min_tool_calls` 才达标。
- `passed` 要求五项全满足；关键词只是参考分，不参与 passed。
- `grade_run` 沿用 ai/tool/final 轨迹，步数只数 ai；空子项列表记满分；扣分最低为0，最高为1，最后保留两位小数。
- 违规列表先 `forbidden_tool` 后 `max_steps`；结果失败仍可报告违规。
- `consistency_report` 返回 `tasks` 与 `overall` 两层，指标键为 `pass@1` 和 `pass^k`；空输入总体为0，不足 k 次的任务 pass^k 为0，k<1 抛 ValueError。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 正常轨迹 | passed，工具提取正确 |
| 2 | 调禁用工具 | forbidden_ok=False，failed |
| 3 | 缺期望工具 | expected_ok=False，failed |
| 4 | 无 final | completed=False，failed |
| 5 | ai 步超过 max_steps | 超限，failed |
| 6 | 工具调用不足 + 关键词部分命中 | min_calls=False、keyword=2/3 |
| 7 | 汇总 good+bad | pass_rate=0.5 |
| 8 | 结果失败 / 调禁止工具 | score=0；禁止工具标记 forbidden_tool |
| 9 | ai 步超上限 | 扣0.2并记录 max_steps |
| 10 | 三个子项通过两个 | score=0.67 |
| 11 | 首次成功、第二次失败 | pass@1=1，pass^2=0；不足k次不算稳定 |

## 验收标准

`gate_check.py` 的 11 项全部 PASS（原 7 项 + 新 4 项）：

- 工具提取、正常、禁用、缺期望、未完成/超步数、最少调用/关键词、汇总。
- 新增：结果失败/禁止工具清零、超步扣分、部分分、pass^k 统计。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么禁用工具检查比关键词检查更重要？
2. `passed` 为什么不把 keyword_score 算进去？
3. 真实轨迹从哪里采集？哪些字段必须记录？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（11/11）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 3.9
```

对照时只回答：

1. 参考实现的 `evaluate_trajectory` 和你的判定项一致吗？
2. 参考实现的 `agent_041` 为什么 RAG 判通过、Agent 判违规？
3. 参考实现的 `step_count` 和 `tool_call_count` 有什么区别？

## 概念地图

- **轨迹**：思考-行动过程，不只是最终答案。
- **期望/禁用工具**：该调的调了、不该调的没调。
- **完成度**：有 final 才算完成。
- **步数**：绕远路/死循环告警。
- **最少调用**：确保真的用了工具，不是编答案。
- **安全屏障**：禁用工具是 Agent 评测独有维度。
- **结果优先**：最终状态正确不等于路径唯一；安全违规仍必须否决。
- **重复稳定性**：每次干净环境，统计首次成功与前 k 次全部成功。

## 边界

- gate 用合成轨迹，不采集真实 Agent。
- 通过 gate 只证明评测规则正确，不代表真实 Agent 表现。
- 工具顺序/参数/副作用见 8.6。
