# 里程碑 7.4 / step4 · 增量知识同步

[项目目录](../../README.md) · [上一步](../step3/README.md) · [下一步](../../m5-injection-pii-observability/step1/README.md)

## 问题：知识更新和删除怎样避免残留？

全量重建耗时，单纯新增又可能留下过时片段。我们依据来源与内容变化生成同步计划，明确新增、修改、删除与跳过。

## 概念

内容哈希描述变化；计划描述将执行的动作；应用执行与失败恢复是后续职责。生成计划不等于向量库已经更新。

## 动手与观察

给合成目录增加、修改和删除文件，核对计划，再确认检索主链如何消费新版本。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/sync.py` | 新增 | 增量同步计划 |
| `tests/test_sync.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/api.py` | 修改 | HTTP 契约 |
| `src/customer_support/runtime.py` | 修改 | 真实依赖与最终 API 组合入口 |
| `tests/test_api.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：HTTP /knowledge/sync-plan → SyncingApplication → scan/plan → knowledge_path。另有 45 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/api.py`：`ChatRequest`、`ChatResponse`、`SyncRequest`、`create_app`。
2. `src/customer_support/runtime.py`：`create_runtime_api`。
3. `tests/test_api.py`：`Product`、`test_incremental_sync_plan_is_reachable_from_the_product_api`。
4. `src/customer_support/sync.py`：`SyncPlan`、`scan`、`plan`、`SyncingApplication`。
5. `tests/test_sync.py`：`test_sync_distinguishes_change_and_delete`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m4-api-identity-security/step4
cd .build/flagship/m4-api-identity-security/step4/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。执行向量事务和失败恢复仍待实现。运行结果写入本章 workbook.md。
