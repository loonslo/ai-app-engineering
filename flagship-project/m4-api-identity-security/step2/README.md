# 里程碑 7.4 / step2 · 写操作幂等

[项目目录](../../README.md) · [上一步](../step1/README.md) · [下一步](../step3/README.md)

## 问题：网络重试怎样避免创建两张工单？

客户端没有收到响应可能再次提交，第一次却已成功。幂等键把同一请求关联起来，让重复提交复用结果而不是再执行一次。

## 概念

同一键与同一内容可以重放；同一键配不同内容应冲突。幂等记录与真正写操作需要在正确边界协作。

## 动手与观察

重复请求后检查业务对象数量，再修改内容复用旧键，确认冲突处理；注明当前内存边界。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/idempotency.py` | 新增 | 写操作去重 |
| `tests/test_idempotency.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/api.py` | 修改 | HTTP 契约 |
| `src/customer_support/application.py` | 修改 | 统一业务编排 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：Idempotency-Key → API → application → IdempotencyStore → TicketStore。另有 40 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/api.py`：`Service`、`ChatRequest`、`ChatResponse`、`create_app`。
2. `src/customer_support/application.py`：`ApplicationResult`、`SupportApplication`。
3. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
4. `tests/test_application.py`：`Assistant`、`test_retried_product_request_reuses_the_same_ticket`。
5. `src/customer_support/idempotency.py`：`IdempotencyConflict`、`IdempotencyStore`。
6. `tests/test_idempotency.py`：`test_write_runs_once_and_key_cannot_change_meaning`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m4-api-identity-security/step2
cd .build/flagship/m4-api-identity-security/step2/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。内存实现尚未处理多实例并发。运行结果写入本章 workbook.md。
