# L5.7 扩展：CI 分层门禁 · Gate（原 8.9）

[全书目录](../../README.md) · [上一章 8.8](../8.8-security-resilience-perf/README.md) · [下一章 8.10](../8.10-production-feedback-loop/README.md)

- **能力**：把多层结果合并成发布判定；缺层、必需层失败、flaky 都阻断；可选层失败只记录。
- **v2 路径**：L5.7 / 核心阅读（Gate；CI 分层门禁）
- **v3 路径**：L5.8 / 核心阅读（归入 L5.8）
- **前置**：8.8（证据层）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/ci_gate.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.9-ci-layered-gate/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

CI 门禁最容易“默认放行”：

- 必需层失败仍放行；
- 报告没生成，被当成通过；
- 可选层失败误阻断；
- flaky 重跑到绿，不查原因；
- 只看总数，不区分缺层/失败/不稳定。

这个 gate 用层结果和历史，验证失败关闭规则。

## 任务

实现 `gate/starter.py` 的 `flaky_tests` 和 `evaluate_gate`：

| 函数 | 你要交付的行为 |
|---|---|
| `flaky_tests` | 历史中既有 True 又有 False 的测试名，排序 |
| `evaluate_gate` | 必需层失败/缺层/flaky 阻断；可选层失败不阻断 |

关键口径：

- `failed_layers` 只放必需层失败。
- `missing_layers` 是 required_layers 中没有报告的层。
- 三者都空才 `passed=True`。
- 空输入 + 无 required -> 放行；有 required -> 缺层阻断。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 全部通过 | 放行 |
| 2 | 必需层失败 | 阻断 |
| 3 | 可选层失败 | 放行 |
| 4 | required 缺报告 | 阻断，missing 列出 |
| 5 | 历史 True/False 混合 | flaky 阻断 |
| 6 | 空输入/有 required | 放行/阻断 |

## 验收标准

`gate_check.py` 的 6 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- gate 只验证判定逻辑，不执行 CI。
- 门禁可信度取决于输入证据真实、指标口径稳定。
