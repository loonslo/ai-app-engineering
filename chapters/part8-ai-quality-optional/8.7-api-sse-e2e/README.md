# L8 API/SSE E2E · Gate（原 8.7）

[全书目录](../../README.md) · [上一章 8.6](../8.6-agent-trajectory-testing/README.md) · [下一章 8.8](../8.8-security-resilience-perf/README.md)

- **能力**：解析 SSE 事件；拼接 token/message 文本；校验 E2E 响应契约。
- **v2 路径**：L8 / 选做（Gate；API/SSE E2E）
- **v3 路径**：选修 / 选修（AI 质量工程专项，评测岗加分）
- **前置**：5.1（API）、8.3（契约）。
- **时间盒**：4 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/api_e2e.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.7-api-sse-e2e/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

流式输出最容易“最后看起来对、过程已经坏了”：事件名/ID 丢、多行 data 被截断、done/error 被拼进正文、request_id 类型错。

## 任务

实现 `parse_sse`、`combine_text`、`validate_e2e_response`：

| 函数 | 要求 |
|---|---|
| parse_sse | 空行分块；event/id/多行 data；无 data 丢弃；默认 message |
| combine_text | 只拼 token/message；JSON 取 text 或转字符串；非 JSON 原样 |
| validate_e2e | answer/sources/ticket_id + request_id 字符串 |

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | event/id/two data | 字段正确 |
| 2 | 多行 data | 换行连接 |
| 3 | 无 data 块 | 丢弃 |
| 4 | done/plain/JSON 数组 | 只拼 token/message |
| 5 | request_id=1 | 契约错误 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 不启 HTTP/SSE 服务，只解析文本。
- 真实网络/超时/断流未验证。
