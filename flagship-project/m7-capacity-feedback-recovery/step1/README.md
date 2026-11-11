# 里程碑 7.7 / step1 · 向量库迁移契约

[项目目录](../../README.md) · [上一步](../../m6-quality-gate-container/step2/README.md) · [下一步](../step2/README.md)

## 问题：替换向量后端怎样保持同步语义？

向量库接口不同，知识同步仍应维持来源级新增更新与删除行为。我们先固定适配契约，再让计划执行调用这些接口。

## 概念

适配器统一 upsert 与删除行为，来源标识稳定关联知识，失败不能被静默当成功。

## 动手与观察

使用内存后端验证同步计划执行及删除，再指出真实外部向量服务仍缺哪些验证。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `deployment/pgvector_schema.sql` | 新增 | 配置、运行入口或交付证据 |
| `src/customer_support/vector_store.py` | 新增 | 存储协议 |
| `tests/test_sync_vector_store.py` | 新增 | 保护行为及失败边界的测试 |
| `tests/test_vector_store_contract.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/sync.py` | 修改 | 增量同步计划 |

调用过程：scan/plan → apply_plan → VectorStore.upsert/delete_source。另有 64 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/sync.py`：`SyncPlan`、`scan`、`plan`、`apply_plan`、`SyncingApplication`。
2. `src/customer_support/vector_store.py`：`VectorStore`。
3. `tests/test_sync_vector_store.py`：`Store`、`test_sync_plan_reaches_the_vector_store_contract`。
4. `tests/test_vector_store_contract.py`：`MemoryStore`、`test_contract_requires_tenant_scoped_search_and_delete`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m7-capacity-feedback-recovery/step1
cd .build/flagship/m7-capacity-feedback-recovery/step1/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。schema 存在不等于已完成远端迁移。运行结果写入本章 workbook.md。
