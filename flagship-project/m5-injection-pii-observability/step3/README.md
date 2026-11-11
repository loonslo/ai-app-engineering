# 里程碑 7.5 / step3 · 可观测性

[项目目录](../../README.md) · [上一步](../step2/README.md) · [下一步](../step4/README.md)

## 问题：一次失败如何从回复追到过程？

用户报告一个问题，我们需要通过同一请求标识关联模型调用、工具动作和存储记录。可观测性让排错从猜测回到证据。

## 概念

事件描述过程，指标描述聚合表现，追踪标识关联一次请求。记录失败与成功同样重要。

## 动手与观察

模拟一次失败并沿标识回查，检查结果、日志和事件是否相互一致，不记录秘密值。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/observability.py` | 新增 | trace 与延迟 |
| `tests/test_observability.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：API/CLI → ObservedApplication → 安全/缓存/业务链 → Trace。另有 52 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
2. `tests/test_application.py`：`Product`、`test_real_product_call_is_observed_without_recording_question`。
3. `src/customer_support/observability.py`：`Trace`、`Recorder`、`ObservedApplication`。
4. `tests/test_observability.py`：`test_success_and_failure_are_observed_without_question`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m5-injection-pii-observability/step3
cd .build/flagship/m5-injection-pii-observability/step3/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。内存记录器不是生产监控平台。运行结果写入本章 workbook.md。
