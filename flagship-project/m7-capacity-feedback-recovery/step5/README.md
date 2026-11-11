# 里程碑 7.7 / step5 · 备份与恢复验证

[项目目录](../../README.md) · [上一步](../step4/README.md) · [下一步](../step6/README.md)

## 问题：备份文件存在，能证明数据可恢复吗？

真正恢复要重新读取并核对数据完整性。我们把正式会话库的备份、完整性检查和恢复观察联系起来，避免只复制一个看似正常的文件。

## 概念

备份取得一致副本，完整性检查发现结构异常，恢复验证确认业务数据可用。目标路径必须明确。

## 动手与观察

用合成会话库备份到独立路径，检查 integrity_check 和读取结果；真实灾难恢复另行演练。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/backup.py` | 新增 | 备份恢复 |
| `tests/test_backup.py` | 新增 | 保护行为及失败边界的测试 |
| `tests/test_thread_backup.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/runtime.py` | 修改 | 真实依赖与最终 API 组合入口 |
| `src/customer_support/thread_store.py` | 修改 | SQLite 会话 |

调用过程：正式 thread_db_path → SQLiteThreadStore.backup_to → integrity_check。另有 75 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/runtime.py`：`create_runtime_api`、`backup_threads`。
2. `src/customer_support/thread_store.py`：`Message`、`SQLiteThreadStore`。
3. `src/customer_support/backup.py`：`backup`、`integrity`。
4. `tests/test_backup.py`：`test_backup_is_actually_readable`。
5. `tests/test_thread_backup.py`：`test_the_product_thread_store_creates_a_verified_backup`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m7-capacity-feedback-recovery/step5
cd .build/flagship/m7-capacity-feedback-recovery/step5/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。本地 SQLite 演练不等于云数据库灾备。运行结果写入本章 workbook.md。
