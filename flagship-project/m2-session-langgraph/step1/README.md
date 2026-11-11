# 里程碑 7.2 / step1 · 连续追问与会话隔离

[项目目录](../../README.md) · [上一步](../../m1-rag-mvp/step4/README.md) · [下一步](../step2/README.md)

## 问题：那发票呢，如何知道用户在问什么？

连续追问省略了背景。应用需要在正确会话里补足检索问题，同时防止另一用户的历史进入当前请求。

## 概念

会话键确定边界，历史补充背景，长度预算限制输入。存了历史和发送全部历史不是同一件事。

## 动手与观察

同一用户跨两轮追问后，再换身份执行相同短问题，检查历史隔离及长度限制。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/application.py` | 新增 | 统一业务编排 |
| `src/customer_support/conversation.py` | 新增 | 会话历史与追问改写 |
| `tests/test_application.py` | 新增 | 保护行为及失败边界的测试 |
| `tests/test_conversation.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/app.py` | 修改 | 交互式用户入口 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |

调用过程：app → bootstrap.build_application → SupportApplication → History → assistant。另有 25 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/app.py`：`Application`、`build_product_assistant`、`print_answer`、`run_interactive`、`main`。
2. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
3. `src/customer_support/application.py`：`Assistant`、`SupportApplication`。
4. `src/customer_support/conversation.py`：`Turn`、`History`。
5. `tests/test_application.py`：`RecordingAssistant`、`test_conversation_is_on_the_product_path`。
6. `tests/test_conversation.py`：`test_follow_up_uses_only_same_session_and_history_is_bounded`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m2-session-langgraph/step1
cd .build/flagship/m2-session-langgraph/step1/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。短问题规则只是第一版追问识别。运行结果写入本章 workbook.md。
