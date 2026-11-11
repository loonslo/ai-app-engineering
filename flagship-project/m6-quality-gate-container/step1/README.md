# 里程碑 7.6 / step1 · CI 质量门

[项目目录](../../README.md) · [上一步](../../m5-injection-pii-observability/step4/README.md) · [下一步](../step2/README.md)

## 问题：质量报告怎样决定是否允许交付？

有报告却没有发布结论，退化仍然可能被合并。我们把指标和阈值变成可执行门禁，让缺失或失败证据产生明确退出状态。

## 概念

评测产出指标，质量门比较规则，CI 根据退出状态执行。阈值与评测集应一起审查。

## 动手与观察

分别降低质量、移除指标和提供合格指标，检查判定，再回看失败样本是否解释退化。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/quality_gate.py` | 新增 | CI 阈值 |
| `tests/test_quality_gate.py` | 新增 | 保护行为及失败边界的测试 |
| `tests/test_quality_gate_integration.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/evaluation.py` | 修改 | 离线用例与分层判断 |

调用过程：eval_cases → evaluate → metrics_from_results → quality_gate.check → 退出码。另有 57 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/evaluation.py`：`Assistant`、`EvalCase`、`load_cases`、`evaluate`、`metrics_from_results`、`run_evaluation`、`run_quality_gate`、`main`。
2. `src/customer_support/quality_gate.py`：`check`。
3. `tests/test_quality_gate.py`：`test_low_or_missing_metric_closes_gate`。
4. `tests/test_quality_gate_integration.py`：`Assistant`、`test_evaluation_result_reaches_the_release_gate`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m6-quality-gate-container/step1
cd .build/flagship/m6-quality-gate-container/step1/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。门禁只覆盖已有评测集。运行结果写入本章 workbook.md。
