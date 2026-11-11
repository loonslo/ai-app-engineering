# 里程碑 7.7 / step3 · 用户反馈闭环

[项目目录](../../README.md) · [上一步](../step2/README.md) · [下一步](../step4/README.md)

## 问题：用户反馈怎样形成可靠改进？

点踩需要保存到业务记录，并关联原问题，才能回查原因。直接把所有负反馈当成标准答案会污染评测，所以后续仍要审查。

## 概念

反馈存储保存关联，接口统一收集，人工核对产生可用回归案例。记录反馈与修复问题之间需要证据。

## 动手与观察

提交反馈后读取关联记录，检查重复、缺目标和跨身份情形，再写出审查后可转成哪条测试。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `src/customer_support/feedback.py` | 新增 | 反馈队列 |
| `tests/test_feedback.py` | 新增 | 保护行为及失败边界的测试 |
| `tests/test_feedback_api.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/runtime.py` | 修改 | 真实依赖与最终 API 组合入口 |

调用过程：同一 FastAPI → /chat、/knowledge/sync-plan、/feedback → FeedbackStore。另有 71 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/runtime.py`：`create_runtime_api`。
2. `src/customer_support/feedback.py`：`Feedback`、`FeedbackStore`、`FeedbackRequest`、`attach_feedback_routes`。
3. `tests/test_feedback.py`：`test_only_negative_unreviewed_feedback_enters_queue`。
4. `tests/test_feedback_api.py`：`test_feedback_enters_the_review_store_through_the_product_api`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m7-capacity-feedback-recovery/step3
cd .build/flagship/m7-capacity-feedback-recovery/step3/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。反馈可能有偏差且需人工复核。运行结果写入本章 workbook.md。
