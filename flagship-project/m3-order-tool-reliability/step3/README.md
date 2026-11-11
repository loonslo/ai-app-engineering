# 里程碑 7.3 / step3 · 人工升级闭环

[项目目录](../../README.md) · [上一步](../step2/README.md) · [下一步](../step4/README.md)

## 问题：说请转人工之后，工作真的转交了吗？

一句提示没有产生可追踪工单，也没有保存需要人工处理的原因。我们把升级变成实际的业务对象，让后续能检查状态。

## 概念

升级规则决定何时需要人工，工单保存身份与上下文，应用返回工单状态。通知文本与工单创建必须区分。

## 动手与观察

触发证据不足场景，核对工单与回复的关联；记录当前内存实现仍不能保证重启后保留。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/tickets.py` | 新增 | 人工工单 |
| `tests/test_tickets.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/application.py` | 修改 | 统一业务编排 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |
| `tests/test_application.py` | 修改 | 保护行为及失败边界的测试 |

调用过程：application.handle → assistant → escalate → TicketStore。另有 34 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/application.py`：`Assistant`、`ApplicationResult`、`SupportApplication`。
2. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
3. `tests/test_application.py`：`Assistant`、`test_refusal_creates_a_ticket_on_the_real_product_path`。
4. `src/customer_support/tickets.py`：`Ticket`、`TicketStore`、`escalate`。
5. `tests/test_tickets.py`：`test_missing_evidence_creates_open_ticket_but_answerable_question_does_not`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m3-order-tool-reliability/step3
cd .build/flagship/m3-order-tool-reliability/step3/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。内存工单尚未幂等持久化。运行结果写入本章 workbook.md。
