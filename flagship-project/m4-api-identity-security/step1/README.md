# 里程碑 7.4 / step1 · FastAPI 服务边界

[项目目录](../../README.md) · [上一步](../../m3-order-tool-reliability/step4/README.md) · [下一步](../step2/README.md)

## 问题：命令行能力怎样被网页调用？

我们把统一业务入口包装成 HTTP 接口。请求响应有固定契约，业务逻辑继续留在应用层，避免每个端点另写一套问答。

## 概念

接口校验形状，Application 决定路线，模型与仓库作为依赖。此时接口尚未完成可信身份认证。

## 动手与观察

用测试客户端提交正常和缺字段请求，比较契约与业务失败；解释 HTTP 成功码与答案可信度的区别。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/api.py` | 新增 | HTTP 契约 |
| `src/customer_support/runtime.py` | 新增 | 真实依赖与最终 API 组合入口 |
| `tests/test_api.py` | 新增 | 保护行为及失败边界的测试 |
| `pyproject.toml` | 修改 | 配置、运行入口或交付证据 |

调用过程：HTTP /chat → create_app → application.handle → 7.2–7.3 的累积主链。另有 40 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/api.py`：`Service`、`ChatRequest`、`ChatResponse`、`create_app`。
2. `src/customer_support/runtime.py`：`create_runtime_api`。
3. `tests/test_api.py`：`Fake`、`test_api_schema_and_validation`、`Product`、`test_api_calls_the_cumulative_product_not_a_new_chat_implementation`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m4-api-identity-security/step1
cd .build/flagship/m4-api-identity-security/step1/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。API 尚未认证。运行结果写入本章 workbook.md。
