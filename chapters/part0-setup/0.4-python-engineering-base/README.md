# 0.4 AI 应用的 Python 工程底座 · Gate

[全书目录](../../README.md) · [上一章 L0.3](../0.3-coding-agent-workflow/README.md) · [下一章 L0.5](../0.5-job-map-gap/README.md)

- **能力**：用 Pydantic v2 定义配置与数据契约并进行敏感信息脱敏；编写带指数退避与假时钟注入的异步重试；实现基于信号量的保序并发限流；用 httpx.MockTransport 构建离线确定性 HTTP 异常测试。
- **v3 路径**：L0.4 / 核心（Gate；Python 工程底座）
- **岗位任务 / 面试题型**：T5、T7 / F1、F4
- **前置**：已完成 [L0.3 用编码 Agent 开发与审查](../0.3-coding-agent-workflow/README.md)
- **时间盒**：3 小时（1h 读 + 1.5h 实现 + 0.5h 记录）
- **闭卷规则**：只读本页、`gate/starter.py` 和 Python 标准库、Pydantic、httpx 官方文档；通过 gate 之前不要打开参考实现。
- **验收命令**：

```bash
python chapters/part0-setup/0.4-python-engineering-base/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 来绕过检查。

---

## 为什么做这个 gate

很多初学者试图跳过 Python 工程底座直接去调用大模型框架，结果在面对网络偶发抖动、速率限制（429）、配置格式错误、并发打满连接池时手足无措。在现代 AI 后端系统中，模型只是一个可能随时超时或报错的外部 HTTP 依赖。如何防御外部依赖的不确定性，是区分“Demo 玩具”与“生产级工程”的分水岭。

这个 gate 检验四大核心工程能力：
1. **边界校验与错误脱敏**：系统边界用 Pydantic，内部流转用 dataclass；校验失败时绝不把带有密钥的输入泄露到错误信息中；
2. **带退避的确定性重试**：只对暂时性错误重试，支持假时钟注入，让重试单元测试毫秒级完成；
3. **受控的异步并发**：用信号量严格控制并发上限，且保证返回结果列表顺序与输入严格一致；
4. **离线测试替身**：用 `httpx.MockTransport` 在断网环境下 100% 模拟 500、畸形响应与超时。

---

## 概念

### 1. 类型体系分工：`dataclass` 与 Pydantic `BaseModel`
- **Python 标准库 `dataclass`**：内部确定性对象、管道内部传递的中间状态、纯数据载荷。轻量、零运行时校验开销；
- **Pydantic v2 `BaseModel`**：系统外部边界输入、环境变量、LLM 结构化提取。具备严格的运行时类型强制转换与验证规则。
- **核心工程原则**：跨越信任边界的数据必须经过 Pydantic 严格校验；应用内部流转数据优先使用 `dataclass`。

### 2. 校验错误脱敏与防泄密
Pydantic 默认的 `ValidationError.errors()` 中包含 `input` 字段（即用户输入的原始内容）。若直接打印或抛出该异常，当输入恰好是 `api_key` 时密钥将直接泄露到外部响应或监控平台。必须解析错误字段定位（`loc`），仅提取出错字段名，绝不输出敏感值。

### 3. 指数退避与时钟注入（Fake Sleep）
在遇到偶发性网络抖动时，按 $\text{base\_delay} \times 2^i$ 进行指数退避。通过将 `sleep` 协程作为参数注入，单元测试中可传入仅记录时长而不实际休眠的假时钟，避免测试等待。

### 4. 离线测试替身：`httpx.MockTransport`
在内存中接管 HTTP 请求处理逻辑，脱离真实外部服务返回模拟状态码或异常。

---

## 任务

在 `gate/starter.py` 中实现以下 4 个核心函数：

| 函数 | 你要交付的行为 |
|---|---|
| `load_settings(env)` | 读取 `LLM_PROVIDER`、`MODEL`、`TIMEOUT_S`、`MAX_RETRIES`；非法或超出范围抛 `SettingsError`，指出错误字段名且绝不包含敏感变量值 |
| `retry_async(fn, attempts, base_delay, sleep, retry_on)` | 最多重试 `attempts` 次，退避间隔 $\text{base\_delay} \times 2^i$；只重试 `retry_on` 异常，其他立即抛出；次数用尽抛最后异常；`attempts < 1` 抛 `ValueError` |
| `gather_limited(factories, limit)` | 运行协程工厂列表；并发度不超过 `limit`；返回结果顺序与输入完全对齐；`limit < 1` 抛 `ValueError` |
| `fetch_json(client, url, timeout_s)` | GET 请求；非 2xx 抛 `HttpError("status:<code>")`；非字典 JSON 响应抛 `HttpError("invalid_json")`；超时抛 `HttpError("timeout")` |

---

## 关键约定

- `SettingsError` 继承自 `ValueError`；错误信息必须包含出错的字段名，严禁包含该字段的实际取值；
- `HttpError` 消息格式固定为 `"status:<code>"`、`"invalid_json"`、`"timeout"`；
- `gather_limited` 必须保证 `result[i]` 对应 `factories[i]` 的执行结果；
- `retry_async` 必须调用注入的 `sleep`，严禁在函数内调用全局 `asyncio.sleep`。

---

## 故障注入（必须亲手触发）

| # | 注入场景 | 期望行为 |
|---|---|---|
| 1 | 传入非法的 `LLM_PROVIDER="foo"` | 抛出 `SettingsError`，消息中包含 `"provider"` |
| 2 | 传入空白 `MODEL="   "` | 抛出 `SettingsError`，消息中包含 `"model"` |
| 3 | 传入超出范围的 `TIMEOUT_S="200"` | 抛出 `SettingsError`，消息中包含 `"timeout_s"` |
| 4 | 配置中包含非法密钥数据 | 抛出 `SettingsError`，错误信息中绝不出现密钥明文 |
| 5 | 重试时遇到非 `retry_on` 列出的异常 | 立即抛出，不进入重试，假时钟调用次数为 0 |
| 6 | 并发限流传入 `limit=0` 或负数 | 抛出 `ValueError` |
| 7 | HTTP 请求返回 500 状态码 | 抛出 `HttpError("status:500")` |
| 8 | HTTP 请求返回数组型 JSON `[1, 2, 3]` | 抛出 `HttpError("invalid_json")` |
| 9 | HTTP 请求发生超时（TimeoutException） | 抛出 `HttpError("timeout")` |

---

## 验收标准

`gate_check.py` 的 12 项检查全部 PASS：
- **配置与脱敏 (1-4)**：非法 provider、空白 model、超时区间校验、错误信息脱敏无密钥明文；
- **异步重试 (5-7)**：指数退避与假时钟注入、非可重试异常立即抛出、次数用尽抛最后异常；
- **并发限流 (8-9)**：信号量并发受控与保序对齐、非法 limit 抛 ValueError；
- **HTTP 异常封装 (10-12)**：非 2xx 状态码封装、非字典 JSON 封装、超时封装。

---

## 提交物

- `gate/starter.py`（完成实现的闭卷代码）
- `gate/gate_report.json`（12/12 全部通过报告）
- [workbook.md](workbook.md) 中记录实验过程与反思

---

## 通过后对照参考实现

通过 gate 之前不要阅读参考解。通过后运行参考实现进行对照：

```bash
python chapters/part0-setup/0.4-python-engineering-base/python_engineering_base.py
```

对照思考以下问题：
1. 参考实现如何通过集合推导式提取 `ValidationError` 中的字段名并脱敏？与你的写法有何区别？
2. 在 `retry_async` 中，为什么假时钟参数注入能让原本需要数秒的重试在毫秒内完成？
3. `gather_limited` 如何在保证 `asyncio.Semaphore` 限制并发的同时，保证返回列表下标与输入严格一致？

---

## 概念地图

- **契约先行**：凡是来自外界的数据（配置、网络、LLM）必须经 Pydantic 校验；
- **错误脱敏**：安全边界永远不向外泄露系统内部凭据；
- **测试替身**：网络、时间、模型都应具备确定性的测试替身（MockTransport / Fake Sleep）；
- **有界资源**：异步并发必须设定上限，网络调用必须设定硬超时。

---

## 边界

- **非真实分布式限流**：`gather_limited` 仅针对单进程内部协程并发，多实例分布式限流需结合 Redis 或网关限流；
- **重试不包含抖动因子**：本章实现为纯指数退避，生产高并发下建议引入 Full Jitter 避免羊群效应；
- **离线替身不代表真实网络延迟**：通过 MockTransport 验证了状态处理逻辑，不代表公网下的网络抖动已实测。
