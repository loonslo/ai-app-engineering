# 里程碑 7.7 / step4 · 模型供应商降级

[项目目录](../../README.md) · [上一步](../step3/README.md) · [下一步](../step5/README.md)

## 问题：主模型不可用时，备用路线怎样表达？

临时故障时可以切到备用模型，但备用也可能失败，返回结果还应说明实际路线。降级逻辑必须进入统一调用链才能生效。

## 概念

Provider 接口分离模型连接；临时错误触发 fallback；结果与事件保留路线。内容错误不一定适合自动重试切换。

## 动手与观察

模拟主模型临时失败、永久错误和双失败，核对切换次数及最终状态。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/providers.py` | 新增 | 模型 fallback |
| `tests/test_providers.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |

调用过程：bootstrap → primary.invoke → 临时错误时 fallback.invoke → workflow。另有 74 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/bootstrap.py`：`build_embeddings`、`_build_chat`、`build_chat_model`、`build_assistant`、`build_application`。
2. `src/customer_support/providers.py`：`Provider`、`TemporaryProviderError`、`answer_with_fallback`、`TransientChatModel`、`FallbackChatModel`。
3. `tests/test_providers.py`：`P`、`test_temporary_failure_uses_fallback`、`test_langchain_invoke_contract_also_uses_fallback`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m7-capacity-feedback-recovery/step4
cd .build/flagship/m7-capacity-feedback-recovery/step4/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。备用模型质量仍需独立评测。运行结果写入本章 workbook.md。
