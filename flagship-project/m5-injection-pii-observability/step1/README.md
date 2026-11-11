# 里程碑 7.5 / step1 · 提示词注入防护

[项目目录](../../README.md) · [上一步](../../m4-api-identity-security/step4/README.md) · [下一步](../step2/README.md)

## 问题：资料里的伪指令能不能改变系统行为？

外部文档可能要求系统忽略规则或执行工具。我们把它继续视为证据，加入可观察的防护，并保留正常内容通过的测试。

## 概念

输入检测辅助识别风险，可信任务与工具权限由程序控制。字符串规则会误报，也不覆盖所有攻击。

## 动手与观察

准备伪指令与容易误伤的正常文本，比较判定，解释真实授权仍在哪个边界执行。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/security.py` | 新增 | 注入检查 |
| `tests/test_security.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |
| `src/customer_support/workflow.py` | 修改 | LangGraph 状态和分支 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：API/CLI → SecuredApplication + 文档过滤 → workflow → assistant。另有 47 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
2. `src/customer_support/workflow.py`：`SupportState`、`build_graph`、`WorkflowAssistant`。
3. `tests/test_application.py`：`Product`、`test_injection_is_blocked_before_the_product_chain_runs`。
4. `src/customer_support/security.py`：`suspicious`、`filter_documents`、`SecuredApplication`。
5. `tests/test_security.py`：`test_injection_in_question_or_document_is_detected`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m5-injection-pii-observability/step1
cd .build/flagship/m5-injection-pii-observability/step1/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。关键词规则会漏报和误报。运行结果写入本章 workbook.md。
