# 里程碑 7.5 / step2 · PII 脱敏

[项目目录](../../README.md) · [上一步](../step1/README.md) · [下一步](../step3/README.md)

## 问题：发送给模型和日志的信息需要全部保留吗？

客户信息进入请求以后，应该尽量减少不必要暴露。我们用可控脱敏与映射理解边界，而不是随意删除导致业务无法关联。

## 概念

脱敏处理输入与记录，映射恢复需要明确业务用途；日志和共享报告的字段应分别决定。

## 动手与观察

用合成敏感字段检查前后内容，确认标识能关联且共享记录不带真实信息。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/privacy.py` | 新增 | PII 脱敏 |
| `tests/test_privacy.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：用户原文 → PrivacyApplication → 业务链；脱敏副本 → audit_log。另有 50 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
2. `tests/test_application.py`：`Product`、`test_product_audit_keeps_only_the_redacted_question`。
3. `src/customer_support/privacy.py`：`redact`、`PrivacyApplication`。
4. `tests/test_privacy.py`：`test_pii_is_removed_but_order_id_remains`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m5-injection-pii-observability/step2
cd .build/flagship/m5-injection-pii-observability/step2/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。正则无法覆盖所有个人信息。运行结果写入本章 workbook.md。
