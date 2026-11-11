# L8 契约与不变量 · Gate（原 8.3）

[全书目录](../../README.md) · [上一章 8.2](../8.2-eval-data-engineering/README.md) · [下一章 8.4](../8.4-rag-layered-testing/README.md)

- **能力**：一次收集 API 契约错误；检查拒答不带来源、无来源工单必须转人工。
- **v3 路径**：选修 / 选修（AI 质量工程专项，评测岗加分）
- **前置**：5.1（API）。
- **时间盒**：4 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/contracts.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.3-mock-contract-invariant/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

只测字段类型，不测业务不变量，会出现“格式合法但行为错误”：拒答还带引用、工单没来源却不告诉用户转人工。

## 任务

实现 `validate_chat_response` 与 `assert_invariants`：

| 检查 | 规则 |
|---|---|
| answer | 非空字符串 |
| sources | 字符串列表 |
| ticket_id | 字符串或 null |
| 拒答 | 含“没有足够信息”时 sources 必须为空 |
| 工单 | 有 ticket_id 且无 sources，答案必须含“人工” |

关键口径：契约错误一次收集；不变量违反抛 `AssertionError`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | answer 空/sources 非 list | 契约错误 |
| 2 | ticket_id=1 | 契约错误 |
| 3 | 三个都错 | 一次 3 条 |
| 4 | 拒答带来源 | 不变量失败 |
| 5 | 工单无来源未说人工 | 不变量失败 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 离线 payload，不发 HTTP。
- 真实 API/模型输出未验证。
