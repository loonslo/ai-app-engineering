# 里程碑 7.8 / step1 · 面试证据与项目讲解

[项目目录](../../README.md) · [上一步](../../m7-capacity-feedback-recovery/step6/README.md) · [下一步](../step2/README.md)

## 问题：面试里哪些结论有证据支持？

项目故事需要对应真实文件和结果，不能用目录存在代替上线能力。我们整理问题、取舍、实现和证据，让每个结论都能回查。

## 概念

陈述描述解决的问题，证据指向代码与运行记录，边界说明尚未验证。文件审计只检查可定位性。

## 动手与观察

挑三项能力各做一分钟说明，并逐项指出测试或报告；去掉没有真实证据的性能和上线说法。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `docs/PROJECT_STORY.md` | 新增 | 配置、运行入口或交付证据 |
| `src/customer_support/evidence.py` | 新增 | 证据核验 |
| `tests/test_evidence.py` | 新增 | 保护行为及失败边界的测试 |
| `tests/test_runtime_evidence.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/runtime.py` | 修改 | 真实依赖与最终 API 组合入口 |

调用过程：项目陈述 → runtime.verify_project_evidence → 仓库真实文件。另有 79 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/runtime.py`：`create_runtime_api`、`backup_threads`、`verify_project_evidence`。
2. `src/customer_support/evidence.py`：`missing_evidence`。
3. `tests/test_evidence.py`：`test_missing_claim_evidence_is_reported`。
4. `tests/test_runtime_evidence.py`：`test_runtime_evidence_gate_rejects_an_unverifiable_claim`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m8-evidence-final-frontend/step1
cd .build/flagship/m8-evidence-final-frontend/step1/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。不夸大未做的生产验证。运行结果写入本章 workbook.md。
