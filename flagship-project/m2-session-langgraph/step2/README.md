# 里程碑 7.2 / step2 · LangGraph 显式控制流

[项目目录](../../README.md) · [上一步](../step1/README.md) · [下一步](../../m3-order-tool-reliability/step1/README.md)

## 问题：分支增多，怎样让业务路线看得见？

校验、检索、拒答和回答已经形成多个路线。我们把这些分支写进显式状态图，目的在于看清每个出口，而不是增加框架层次。

## 概念

状态保存问题与处理结果；节点分别负责校验、检索和回答；条件边根据实际结果选择路线；正常与失败都需要终止。

## 动手与观察

画出有证据、无证据和不合法输入三条路线，对照节点输出，验证新图仍从原应用入口可达。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/workflow.py` | 新增 | LangGraph 状态和分支 |
| `tests/test_workflow.py` | 新增 | 保护行为及失败边界的测试 |
| `pyproject.toml` | 修改 | 配置、运行入口或交付证据 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |

调用过程：app → bootstrap → SupportApplication → WorkflowAssistant/LangGraph → assistant。另有 29 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
2. `src/customer_support/workflow.py`：`SupportState`、`build_graph`、`WorkflowAssistant`。
3. `tests/test_workflow.py`：`test_graph_stops_invalid_and_refuses_without_evidence`、`test_workflow_adapter_keeps_the_product_ask_contract`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m2-session-langgraph/step2
cd .build/flagship/m2-session-langgraph/step2/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。用了 LangGraph 不等于自主 Agent。运行结果写入本章 workbook.md。
