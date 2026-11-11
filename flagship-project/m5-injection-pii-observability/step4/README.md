# 里程碑 7.5 / step4 · 安全缓存

[项目目录](../../README.md) · [上一步](../step3/README.md) · [下一步](../../m6-quality-gate-container/step1/README.md)

## 问题：同一句问题什么时候可以复用旧答案？

缓存结果可能属于另一身份或过时知识。现在把租户、权限和知识版本放入复用范围，避免只有问题字符串的缓存键。

## 概念

缓存键是权限与版本边界；失效响应知识变化；命中是性能结果，答案正确还需独立检查。

## 动手与观察

保持问题不变，逐项改变身份与版本，核对是否命中；确认正常隔离没有因缓存绕开。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/cache.py` | 新增 | 租户版本缓存 |
| `tests/test_cache.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：API/CLI → ObservedApplication → CachedApplication → 业务链。另有 54 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
2. `tests/test_application.py`：`Product`、`test_cache_is_on_the_product_path_and_order_queries_bypass_it`。
3. `src/customer_support/cache.py`：`AnswerCache`、`CachedApplication`。
4. `tests/test_cache.py`：`test_cache_is_scoped_and_expires`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m5-injection-pii-observability/step4
cd .build/flagship/m5-injection-pii-observability/step4/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。尚未实现多实例和击穿保护。运行结果写入本章 workbook.md。
