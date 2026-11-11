# 里程碑 7.4 / step3 · 可信身份

[项目目录](../../README.md) · [上一步](../step2/README.md) · [下一步](../step4/README.md)

## 问题：请求自称是谁，为什么不能直接相信？

如果正文里的 user_id 就决定读谁的订单，任何人都可以冒充。我们把可信身份从认证结果传入业务，正文只承担业务参数。

## 概念

认证确认身份，授权确认资源范围，Identity 是业务层消费的可信结果。两类判断都要在访问前完成。

## 动手与观察

对照有效、无效与身份不一致请求，验证不能用自报字段绕过边界；真实身份系统尚需独立接入。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/auth.py` | 新增 | JWT 身份 |
| `tests/test_auth.py` | 新增 | 保护行为及失败边界的测试 |
| `pyproject.toml` | 修改 | 配置、运行入口或交付证据 |
| `src/customer_support/api.py` | 修改 | HTTP 契约 |
| `src/customer_support/runtime.py` | 修改 | 真实依赖与最终 API 组合入口 |
| `tests/test_api.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：Bearer token → TokenVerifier → Identity → API → application。另有 42 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/api.py`：`ChatRequest`、`ChatResponse`、`create_app`。
2. `src/customer_support/runtime.py`：`create_runtime_api`。
3. `tests/test_api.py`：`Product`、`test_api_uses_signed_identity_and_rejects_missing_token`。
4. `src/customer_support/auth.py`：`AuthenticationError`、`Identity`、`TokenVerifier`。
5. `tests/test_auth.py`：`test_signed_identity_works_and_tampering_fails`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m4-api-identity-security/step3
cd .build/flagship/m4-api-identity-security/step3/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。本地共享 secret 不等于企业 SSO。运行结果写入本章 workbook.md。
