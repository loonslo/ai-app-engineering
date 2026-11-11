# 里程碑 7.7 / step2 · 容量与压测判定

[项目目录](../../README.md) · [上一步](../step1/README.md) · [下一步](../step3/README.md)

## 问题：多少请求才算服务有足够容量？

一次问答速度快无法说明并发容量。我们把压测样本和服务目标作为发布输入，检查慢请求、失败与预算。

## 概念

负载描述请求分布；延迟分位数描述尾部：p95 取升序后第 ceil(0.95 × n) 个样本，小样本也保留最慢的请求；样本为空时报错，不默认通过。readiness 判定需要真实样本，合成样本只验证计算。

## 动手与观察

使用确定性数据先验证判定，再写出真实并发、上游限流和硬件的实验计划。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/capacity.py` | 新增 | 容量报告 |
| `tests/test_capacity.py` | 新增 | 保护行为及失败边界的测试 |
| `tests/test_release_readiness.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/readiness.py` | 修改 | 启动检查 |

调用过程：配置检查 + 压测样本 → release_readiness → 发布判定。另有 68 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/readiness.py`：`readiness`、`ensure_ready`、`release_readiness`。
2. `src/customer_support/capacity.py`：`CapacityReport`、`report`。
3. `tests/test_capacity.py`：`test_capacity_fails_on_latency_or_errors`、`test_small_sample_p95_keeps_the_slowest_request`、`test_empty_samples_are_rejected_instead_of_passing`。
4. `tests/test_release_readiness.py`：`test_capacity_result_enters_the_release_readiness_gate`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m7-capacity-feedback-recovery/step2
cd .build/flagship/m7-capacity-feedback-recovery/step2/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。假样本不代表真实容量。运行结果写入本章 workbook.md。
