# 里程碑 7.3 / step1 · 受控订单查询工具

[项目目录](../../README.md) · [上一步](../../m2-session-langgraph/step2/README.md) · [下一步](../step2/README.md)

## 问题：我的订单，为什么不能靠知识库回答？

订单状态是个人业务数据，不是公共政策。现在加入只读工具分支，先检查用户与资源归属，再返回受控数据。

## 概念

检索处理公共资料，订单仓库读取结构化记录，工具边界检查身份与订单归属。模型提出请求不能代替权限判断。

## 动手与观察

为自己的订单、别人的订单和不存在订单各运行一例，确保失败不泄露原始记录。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/orders.py` | 新增 | 订单归属查询 |
| `tests/test_orders.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/application.py` | 修改 | 统一业务编排 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：app → application.handle → 订单归属查询或 RAG 问答。另有 30 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/application.py`：`Assistant`、`ApplicationResult`、`SupportApplication`。
2. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
3. `tests/test_application.py`：`Assistant`、`test_order_query_is_reachable_from_the_product_application`。
4. `src/customer_support/orders.py`：`OrderNotFound`、`ForbiddenOrder`、`Order`、`OrderRepository`。
5. `tests/test_orders.py`：`test_order_query_enforces_ownership`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m3-order-tool-reliability/step1
cd .build/flagship/m3-order-tool-reliability/step1/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。当前只有只读内存订单仓库。运行结果写入本章 workbook.md。
