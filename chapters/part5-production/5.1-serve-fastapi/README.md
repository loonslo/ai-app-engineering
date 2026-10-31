# L5.1 FastAPI 服务与可靠性 · Gate（原 5.1 + 5.2 的服务边界）

[全书目录](../../README.md) · [上一章 4.15](../../part4-agents-langgraph/4.15-framework-landscape/README.md) · [下一章 5.2](../5.2-reliability-retry/README.md)

- **能力**：把模型能力包装成可测试的 HTTP 服务；有超时/重试/降级、trace_id、就绪探针和失败落库。
- **v2 路径**：L5.1 / 核心（Gate；服务与可靠性）
- **前置**：2.6（RAG 链）、4.10（检查点与会话）。本章 gate 只要求最小超时/重试；5.2 会在通过后展开 jitter、主备切换和真实成本。
- **环境**：离线 gate；需要 `fastapi`、`httpx`（TestClient 依赖）。参考实现另需真实模型和本地 embedding。
- **时间盒**：10 小时（1h 读 + 6h 实现 + 3h 故障注入与记录）。
- **闭卷规则**：只读本页、`gate/starter.py`；**通过 gate 之前不要打开** `serve_fastapi.py`、`run_server.py`。
- **验收命令**：

```bash
python chapters/part5-production/5.1-serve-fastapi/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 来绕过检查。

## 为什么做这个 gate

“能返回答案”只是及格线。一个能上生产的服务还要回答：

1. 出问题怎么查？`trace_id` 要贯穿响应头、日志和存储。
2. 上游挂了服务会不会死？超时、重试、降级要有边界，不能裸奔 500。
3. 这个月花了多少钱？token 与成本要落库。
4. 答得好不好？反馈入口要能接上评测集。

这个 gate 不考“会不会写 FastAPI 路由”，而是考：

> 把一次不可靠的模型调用，变成一个可观测、可降级、可测试的服务边界。

## 任务

实现 `gate/starter.py` 的三个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `estimate_cost` | 按环境变量单价估算成本；负 token 按 0 |
| `call_with_retry` | 超时 + 有限重试；只重试瞬时错误；耗尽抛 `UpstreamError` |
| `create_app` | 构造 FastAPI app；`/chat`、`/feedback`、`/stats`、`/history`、`/health`、`/ready` |

`answer_fn(question)` 返回：

```python
{
    "answer": str,
    "sources": list[str],
    "prompt_tokens": int,
    "completion_tokens": int,
}
```

`store` 协议（gate 会注入一个假 store）：

```python
save_qa(**kwargs) -> int
save_feedback(conversation_id, rating, comment=None) -> int
daily_stats(days) -> list[dict]
get_history(user_id, limit, before_id) -> list[dict]
```

`create_app` 的硬要求：

- `/health` 永远 200；`/ready` 在 `answer_fn is None` 时 503。
- `/chat` 的 `question` 长度 1–1000；返回 `answer/sources/conversation_id/trace_id/latency_ms`。
- 响应头 `X-Trace-Id` 与 body 的 `trace_id` 一致；调用方传了 `X-Trace-Id` 就沿用。
- `answer_fn` 为 `None` 时 `/chat` 503。
- 上游 `TimeoutError` / `ConnectionError` / `UpstreamError` -> 502；body 含 `trace_id`。
- 其他未处理异常 -> 500；body 含 `trace_id`，不泄露堆栈。
- 成功和失败**都要**调用 `store.save_qa`；失败时 `status="error"`。
- `/feedback` 的 `rating` 只允许 `1` 或 `-1`，否则 422。
- `/stats`、`/history` 直接读 store。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | `answer_fn` 第一次 `TimeoutError`，第二次成功 | 服务层重试后 200，`calls=2` |
| 2 | `answer_fn` 一直 `TimeoutError` | 502，body 有 `trace_id`，store 记 `status=error` |
| 3 | `answer_fn` 返回空 `answer` | 502，store 记失败 |
| 4 | `answer_fn` 抛 `RuntimeError` | 500，body 有 `trace_id`，不出现堆栈/内部信息 |
| 5 | 问题为空 / 超过 1000 字 | 422 |
| 6 | 无 `answer_fn` | `/health` 200、`/ready` 503、`/chat` 503 |
| 7 | 调用方传 `X-Trace-Id` | 响应头与 body 都沿用 |
| 8 | `rating=0` | 422 |
| 9 | `call_with_retry` 遇 `ValueError` | 立即抛出，不重试 |
| 10 | 慢调用超过 `timeout_s` | `UpstreamError`，不无限等待 |

## 验收标准

`gate_check.py` 的 17 项全部 PASS：

- 成本估算：0、输入、输出、负 token。
- 重试：首次成功、超时后成功、非瞬时错误不重试、耗尽、`attempts=0`、超时上限。
- 服务：无 answer_fn 的 `/health`/`/ready`/`/chat`；有 answer_fn 的 `/ready`。
- `/chat`：成功落库、trace 透传、长度校验、超时 502、空答案 502、未处理异常 500。
- `/feedback`/`/stats`/`/history`；服务层重试。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么失败请求也要落库？只记成功会怎样？
2. `/health` 和 `/ready` 为什么要分开？把数据库检查放进 `/health` 会怎样？
3. `call_with_retry` 为什么只重试瞬时错误？把 `ValueError` 也重试会怎样？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（17/17）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 5.1 run_server.py
```

对照时只回答：

1. 参考实现把 `build_answer_fn(retriever, client, model)` 做成工厂函数；这样做对测试有什么好处？
2. 参考实现的 `/chat` 用 `def` 而不是 `async def`；为什么？
3. 参考实现的 `lifespan` 在建库失败时仍让服务启动；你的 `create_app` 怎么处理“依赖没准备好”？
4. `/chat/stream` 为什么只能在"还没输出任何内容"之前重试？流中途失败时，状态码已经是 200，前端靠什么知道出错了？

## 流式（SSE）与限流

参考实现新增了 `/chat/stream`：用原生 `stream=True` 逐段转发，每帧是 `event:` + `data:` + 空行；第一帧 `meta` 带 `trace_id`（响应头 `X-Trace-Id` 同值），最后一帧 `done` 带来源与耗时，失败时发 `error` 帧。它不在 gate 内，用来对照"流式时失败处理为什么更难"。

限流（429）是生产里最常见的 LLM 调用错误来源之一：Datadog《State of AI Engineering 2026》（读取于 2026-10-31）统计，2026 年 2 月报错的 LLM 调用中 60% 由限流引起（3 月报错占比降到 2%，限流仍近三分之一；样本来自其客户遥测，只说明量级）。重试策略见 [5.2](../5.2-reliability-retry/README.md)。
## 概念地图

- **服务边界**：请求校验、超时、重试、降级、错误码、trace，都在这一层收口。
- **liveness vs readiness**：前者管“要不要重启”，后者管“要不要给流量”；混在一起会引发重启风暴。
- **失败也要落库**：只记成功，失败率永远是 0%，监控会给你假象。
- **有限重试**：只重试瞬时错误；参数错/鉴权错重试没有意义，还会放大故障。
- **可测试的工厂**：`create_app(answer_fn, store)` 让测试注入替身，不碰真实模型和数据库。

## 边界

- gate 用假 `answer_fn`/假 store，不调用真实模型，也不验证持久化实现；5.4 再讲 SQLite/Postgres。
- 认证、限流、多租户不在本章 gate 内；见 L5.4。
- 参考实现的超时在客户端上设、重试只在 `call_with_retry` 一层做（客户端 `max_retries=0`）；SSE 路径只在建立连接时重试。参考实现已用假检索器/假客户端和真实 DeepSeek 各跑过一次，没有做并发与断线测试。
- 通过 gate 不等于已经部署；真实上线、压测、恢复演练见 L5.7/L5.8。
