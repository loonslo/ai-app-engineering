# 里程碑 7.3 / step2 · 工具超时与有限重试

[项目目录](../../README.md) · [上一步](../step1/README.md) · [下一步](../step3/README.md)

## 问题：订单服务偶尔失败时，何时重试？

临时上游错误可以重试，永久错误继续重试只会浪费预算。我们把异常类别和次数明确化，让用户能得到可解释的失败。

## 概念

重试策略只处理允许的临时只读失败；超时限制等待；工具层返回可观察结果，业务层决定下一步。

## 动手与观察

使用替身模拟先失败后成功和永久错误，比较调用次数，解释为什么写操作不能照搬策略。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/tool_runner.py` | 新增 | 工具错误分类与重试 |
| `tests/test_tool_runner.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/application.py` | 修改 | 统一业务编排 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：application.handle → call_read_only → OrderRepository → 有限重试结果。另有 33 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/application.py`：`Assistant`、`ApplicationResult`、`SupportApplication`。
2. `tests/test_application.py`：`Assistant`、`FlakyOrders`、`test_product_order_path_uses_the_read_only_retry_policy`。
3. `src/customer_support/tool_runner.py`：`TransientToolError`、`PermanentToolError`、`ToolResult`、`call_read_only`。
4. `tests/test_tool_runner.py`：`test_transient_error_retries_with_hard_limit`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m3-order-tool-reliability/step2
cd .build/flagship/m3-order-tool-reliability/step2/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。写操作不能直接套用读重试。运行结果写入本章 workbook.md。
