# 里程碑 7.7 / step6 · 统一业务应用

[项目目录](../../README.md) · [上一步](../step5/README.md) · [下一步](../../m8-evidence-final-frontend/step1/README.md)

## 问题：功能分散以后，怎样回到一个正式入口？

安全、缓存、工具、反馈各自通过测试，仍可能在运行时彼此断开。统一应用把这些边界放回实际业务入口，累计测试确认能力可达。

## 概念

API 只接受请求，Application 决定流程，runtime 构建依赖。集成验收要覆盖主路径、失败与隔离。

## 动手与观察

从认证请求跟踪一次政策问答和一次订单工具，指出各边界在哪里执行，再运行累计回归。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/api.py` | 修改 | HTTP 契约 |
| `src/customer_support/application.py` | 修改 | 统一业务编排 |
| `src/customer_support/runtime.py` | 修改 | 真实依赖与最终 API 组合入口 |
| `tests/test_api.py` | 修改 | 保护行为及失败边界的测试 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：runtime → 认证 API → 同步/反馈/统一 application → 安全、缓存、工具、工单。另有 75 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/api.py`：`ChatRequest`、`ChatResponse`、`SyncRequest`、`create_app`。
2. `src/customer_support/application.py`：`ApplicationResult`、`SupportApplication`。
3. `src/customer_support/runtime.py`：`create_runtime_api`、`backup_threads`。
4. `tests/test_api.py`：`Product`、`test_final_api_rejects_missing_token_and_uses_signed_identity`。
5. `tests/test_application.py`：`Assistant`、`test_final_core_keeps_order_isolation_and_idempotent_escalation`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m7-capacity-feedback-recovery/step6
cd .build/flagship/m7-capacity-feedback-recovery/step6/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。仍是本地同步实现。运行结果写入本章 workbook.md。
