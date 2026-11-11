# 里程碑 7.3 / step4 · SQLite 会话持久化

[项目目录](../../README.md) · [上一步](../step3/README.md) · [下一步](../../m4-api-identity-security/step1/README.md)

## 问题：重启之后，会话为什么还应该存在？

内存历史无法支撑连续使用。现在把会话存入 SQLite，并让可信租户、用户和线程共同构成读写范围。

## 概念

线程仓储负责持久化，应用层仍处理问答。数据库文件存在、结构正确和会话隔离各有独立证据。

## 动手与观察

保存后重新建立仓储读取，再用另一个身份尝试相同线程标识。使用合成数据库，检查异常与事务路径。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/thread_store.py` | 新增 | SQLite 会话 |
| `tests/test_thread_store.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |
| `src/customer_support/conversation.py` | 修改 | 会话历史与追问改写 |
| `src/customer_support/settings.py` | 修改 | 截至本节的运行路径与环境配置 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：app/API → application → PersistentHistory → SQLiteThreadStore。另有 35 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
2. `src/customer_support/conversation.py`：`Turn`、`History`、`PersistentHistory`。
3. `src/customer_support/settings.py`：`Settings`。
4. `tests/test_application.py`：`Assistant`、`test_product_follow_up_survives_history_object_restart`。
5. `src/customer_support/thread_store.py`：`Message`、`SQLiteThreadStore`。
6. `tests/test_thread_store.py`：`test_messages_persist_and_are_isolated`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m3-order-tool-reliability/step4
cd .build/flagship/m3-order-tool-reliability/step4/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。SQLite 只代表本地单实例验证。运行结果写入本章 workbook.md。
