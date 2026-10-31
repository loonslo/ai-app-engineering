# L5.6 可观测性：OpenTelemetry · Gate

[全书目录](../../README.md) · [上一章 L5.5](../5.7-security-guardrails/README.md) · [下一章 L5.7](../5.10-control-execution-plane/README.md)

- **能力**：按 GenAI 语义约定给模型调用和工具调用打 span；记录 usage 与错误；默认不采集正文；跨服务传递 trace context；从一棵 trace 里快速定位一次失败。
- **v3 路径**：L5.6 / 核心（Gate；OpenTelemetry）
- **岗位任务 / 面试题型**：T5 / F3
- **前置**：L3.6（追踪与评测平台）、L5.1（trace_id 贯穿请求）。
- **时间盒**：6 小时（2h 读 + 3h 实现 + 1h 记录）。
- **闭卷规则**：只读本页、`gate/starter.py` 和 OpenTelemetry 官方文档；通过 gate 之前不要打开 `otel_observability.py`。
- **验收命令**：

```bash
python chapters/part5-production/5.9-otel-observability/gate/gate_check.py
```

13 项全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。gate 用 `opentelemetry-sdk` 的 `InMemorySpanExporter` 收集 span，不联网、不需要密钥。

## 为什么做这个 gate

线上出问题时，用户只会说“刚才那个回答不对”。没有 trace，你只能猜；有 trace，你能看到这次请求经过了哪些模型调用和工具、各花多久、哪一步报错、用了多少 token。可观测性最常见的错误是：

- span 名字和属性各写各的，换个后端就看不懂；
- 记了 usage 却把缓存命中的 token 当成额外 token，或者重复计数；
- 失败时把整段异常（含 prompt、本机路径）都塞进 trace，trace 成了泄露源；
- 默认就采集 prompt 和回答，没有脱敏、也没有开关；
- 跨服务时丢了 trace context，一次请求在后端变成互不相干的几棵树。

## 概念

1. **trace / span / attribute / event**：trace 是一次请求经过的全部工作；span 是其中一段有起止时间的工作，有父子关系；attribute 是 span 上的键值（`gen_ai.request.model`）；event 是 span 内某个时刻发生的事（异常）。
2. **GenAI 语义约定**：OpenTelemetry 在独立仓库 [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai) 维护模型调用的属性与 span 命名。本章依据提交 `3fe84604a5`（读取于 2026-10-31）：
   - 模型调用 span：名字 `{gen_ai.operation.name} {gen_ai.request.model}`，kind 为 `CLIENT`；属性 `gen_ai.operation.name`、`gen_ai.request.model`、`gen_ai.provider.name`；
   - 用量：`gen_ai.usage.input_tokens`、`gen_ai.usage.output_tokens`；命中缓存的输入有标准属性 `gen_ai.usage.cache_read.input_tokens`，约定里它已被包含在 `input_tokens` 内，所以不要从 `input_tokens` 里扣；
   - 工具调用 span：操作名 `execute_tool`，名字 `execute_tool {gen_ai.tool.name}`，属性 `gen_ai.tool.name`、`gen_ai.tool.call.id`；
   - 正文：`gen_ai.input.messages` / `gen_ai.output.messages`，按 role + parts 的结构写成 JSON；属于 Opt-In 内容，默认不采集；
   - 这些约定截至本章写作时仍处于 **Development** 状态，会变化。升级 SDK 或后端前，先对照官方文档重新核对，不要凭记忆写属性名。
3. **W3C `traceparent` 头**：[W3C Trace Context](https://www.w3.org/TR/trace-context/)（REC，2021-11-23，读取于 2026-10-31）。格式 `00-<32 位小写十六进制 trace_id>-<16 位小写十六进制 parent span_id>-<2 位 flags>`；flags 最低位表示“上游已采样”；trace_id 或 span_id 全为 0 无效。下游服务据此把自己的 span 挂到同一棵 trace 下。
4. **正文采集默认关闭**：prompt 里可能有个人信息、密钥、业务数据。需要正文时，先脱敏（见 [5.7](../5.7-security-guardrails/README.md)）再写入，并限定在能关掉开关的环境里排查。
5. **采样与指标**：每个请求都完整记录成本高。常见做法是按比例采样，同时对错误和慢请求提高采样率；延迟直方图、token 计数、成本这类汇总数据用指标（metrics）而不是从 span 里临时算，指标不受采样影响。本章 gate 不覆盖采样与指标，只在参考实现里留有注释。
6. **后端**：Langfuse、Phoenix 的 OTLP 接入见 [3.6](../../part3-evals/3.6-langsmith-eval/README.md)（该章已核对）；LangSmith 见其 [OpenTelemetry 文档](https://docs.langchain.com/langsmith/trace-with-opentelemetry)，Datadog 见其 [OpenTelemetry Instrumentation 文档](https://docs.datadoghq.com/llm_observability/instrumentation/otel_instrumentation)（均为 2026-10-31 的搜索结果页，端点与协议请以各自当前文档为准，本章没有逐个实测）。
7. **“10 分钟定位一次故障”的排查顺序**：① 用户给 trace_id，在后端搜到整棵 trace；② 看总耗时和最长的 span，判断慢在模型、检索还是工具；③ 找状态为 ERROR 的 span 和 `error.type`；④ 看 usage 是否异常膨胀、缓存是否命中；⑤ 需要正文时，只在能打开采集开关的环境里复现。

## 任务

实现 `gate/starter.py`：

| 接口 | 你要交付的行为 |
|---|---|
| `Usage` | 已给出：`input_tokens`（含缓存部分）、`output_tokens`、`cached_input_tokens` |
| `llm_span` | 上下文管理器；名字 `"{operation} {model}"`，CLIENT；写三个属性；让里面的 span 成为子 span |
| `tool_span` | 上下文管理器；名字 `execute_tool {tool_name}`，INTERNAL；写操作名、工具名、调用 ID |
| `record_usage` | 写输入、输出 token；有命中缓存时再写标准的 `cache_read` 属性 |
| `record_error` | 状态 ERROR，`error.type`，`exception` 事件只带 `exception.type`；不写消息和堆栈 |
| `maybe_capture_content` | `capture` 为假什么都不写；为真先脱敏，再按 role + parts 写成 JSON |
| `inject_traceparent` / `extract_traceparent` | 写入与解析 `traceparent`；非法输入写入时报错、解析时返回 `None` |
| `summarize_trace` | 总耗时（毫秒）、模型调用数、工具调用数、token 合计、出错 span 的名字 |

关键口径：

- `record_error` 为什么只记类型：异常消息里可能含 prompt，堆栈里可能含本机路径；SDK 的 `record_exception` 默认都会写，所以创建 span 时要把它关掉。
- `inject_traceparent` 不修改传入的字典；ID 必须是小写十六进制，大写视为非法。
- `summarize_trace` 的耗时用“最晚结束 − 最早开始”，不是各 span 耗时相加（它们有重叠）。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 模型调用 span | 名字 `chat demo-model`，CLIENT，三个属性齐全 |
| 2 | 工具调用 span | 名字 `execute_tool lookup_order`，INTERNAL，三个属性齐全 |
| 3 | `Usage(100, 20, cached_input_tokens=60)` | `input_tokens=100`、`output_tokens=20`、`cache_read.input_tokens=60` |
| 4 | `Usage(10, 2)` | 不出现 `cache_read` 属性 |
| 5 | `ValueError("SECRET-PROMPT-…")` | 状态 ERROR、有 `error.type`；整个 span 里搜不到 SECRET |
| 6 | `capture=False` | 没有任何正文属性 |
| 7 | `capture=True` 且 prompt 带手机号 | 属性里是脱敏后的内容，结构是 role + parts |
| 8 | `inject_traceparent(..., sampled=True/False)` | 末段 `01` / `00`；入参字典不变 |
| 9 | 全零、过短、大写的 ID | 写入时 `ValueError` |
| 10 | 合法头（头名大小写不同） | 返回 `(trace_id, span_id, sampled)` |
| 11 | 版本不是 00、全零 ID、flags 一位、ID 少一位 | 返回 `None` |
| 12 | 两次模型调用 + 一次工具 + 一次失败 | `total_ms=1000, llm_spans=2, tool_spans=1, tokens=170, error_spans=[…]` |
| 13 | 工具 span 在模型调用的 `with` 里创建 | 父 span 是模型调用，同一 `trace_id` |

## 验收标准

`gate_check.py` 的 13 项全部 PASS：span 名称与属性（模型、工具）、usage、缓存属性、错误、正文默认关闭、脱敏采集、traceparent 写入与非法输入、traceparent 解析与非法输入、汇总、父子关系。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么 `input_tokens` 要包含命中缓存的部分，而不是只记未命中的部分？
2. `record_error` 不记异常消息，排查时会少什么信息？你打算怎样补回来而不泄露内容？
3. 如果每个请求都采集正文，除了隐私，还会带来什么运营问题？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（13/13）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 5.9
python tools/run_chapter.py 5.9 --capture-content
```

默认把 span 以 JSON 行打到控制台（中文会被转义成 `\uXXXX`，这是 JSON 的正常写法，不是乱码），并在结尾输出 `summarize_trace` 的汇总；不需要网络和密钥。设置 `OTEL_EXPORTER_OTLP_ENDPOINT` 会改为发送到 OTLP 后端，这需要另外安装 `opentelemetry-exporter-otlp-proto-http`（课程没有锁定它）；没装时脚本会给出提示并以退出码 1 结束。

对照时只回答：

1. 参考实现创建 span 时为什么传 `record_exception=False` 和 `set_status_on_exception=False`？
2. `--capture-content` 时，输出里的手机号变成了什么？没有这个开关时，输出里有没有 `gen_ai.input.messages`？
3. 汇总里的 `error_spans` 是从哪个字段判断出来的？

## 概念地图

- **span 与 attribute**：名字和属性名统一遵循语义约定，才能换后端不换埋点。
- **usage**：输入含缓存；缓存命中用标准属性单独标出。
- **错误**：只记类型和状态；内容不外泄。
- **正文**：默认关；开就先脱敏。
- **trace context**：`traceparent` 把跨服务的 span 串成一棵树。
- **排查**：从 trace_id 到慢点、到错误、到 usage，再到正文。

## 边界

- gate 只检查内存里的 span 属性与计算结果，不验证真实后端、采样、指标、导出重试，也没有验证与具体 Web 框架的自动埋点。
- GenAI 语义约定仍是 Development 状态；属性名以实施时的官方文档为准，本章依据的提交与读取日期见上文。
- 参考实现的 trace 来自脚本化的请求，不是真实模型；OTLP 发送路径未在本章实测。
- 不覆盖日志与指标的关联，也不覆盖跨进程的真实 `traceparent` 传播（只验证头的写入与解析）。
