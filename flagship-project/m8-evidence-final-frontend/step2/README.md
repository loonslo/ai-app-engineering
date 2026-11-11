# 里程碑 7.8 / step2 · 最终验收

[项目目录](../../README.md) · [上一步](../step1/README.md) · [下一步](../step3/README.md)

## 问题：最后验收如何避免只检查新功能？

整合结束后需要回顾整个业务链，而不是只运行最后新增测试。可执行验收让关键功能和失败路径一起产生结果。

## 概念

验收清单描述能力，checks 执行证据，最终结果汇总失败。学习完成状态还需个人实际练习记录。

## 动手与观察

运行离线累计验收，逐项记录测试范围；列出真实模型、远端 CI、部署与恢复仍待完成的部分。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/acceptance.py` | 新增 | 最终验收 |
| `tests/test_final_acceptance.py` | 新增 | 保护行为及失败边界的测试 |

调用过程：可执行 checks → run_acceptance → 任一能力失败则最终验收失败。另有 84 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/acceptance.py`：`accept`、`run_acceptance`、`_Retriever`、`_Model`、`build_offline_checks`。
2. `tests/test_final_acceptance.py`：`test_every_required_capability_must_pass`、`test_final_acceptance_executes_checks_and_fails_closed`、`test_repository_offline_acceptance_reaches_real_components`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m8-evidence-final-frontend/step2
cd .build/flagship/m8-evidence-final-frontend/step2/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。本地毕业项目不等于已生产上线。运行结果写入本章 workbook.md。
