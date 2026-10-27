# 0.4 AI 应用的 Python 工程底座

- **课时**：3h（1h 读 + 1.5h 实现 + 0.5h 记录）
- **v3 路径**：L0.4 / 核心（Gate；Python 工程底座）
- **岗位任务 / 面试题型**：T5、T7 / F1、F4
- **前置依赖**：已完成 [0.3 用编码 Agent 开发与审查](../0.3-coding-agent-workflow/README.md)
- **学完能做**：用 Pydantic v2 定义配置与数据契约；写带超时、重试、并发上限的 async 代码；用 httpx 的 `MockTransport` 离线测试 HTTP 客户端。

---

## 1. 类型体系分工：`dataclass` 与 Pydantic `BaseModel`

在现代 Python AI 应用与基础设施开发中，数据模型的类型分工非常明确：

| 模型类型 | 适用场景 | 优势与开销 | 典型示例 |
|---|---|---|---|
| **Python 标准库 `dataclass`** | 内部确定性对象、管道内部传递的中间状态、纯数据载荷 | 轻量、无运行时校验开销、标准库零依赖 | 知识库检索片段 `Document`、Agent 内部状态快照 |
| **Pydantic v2 `BaseModel`** | 外部边界输入、环境变量、LLM Structured Output（结构化提取）、HTTP 请求入参 | 严格的运行时类型强制转换、强校验规则（如范围、正则、枚举） | 环境变量配置 `Settings`、提取的用户工单 JSON |

**核心工程原则**：
> 凡是跨越系统信任边界的数据（来自网络、用户请求、外部环境变量或 LLM 生成的 JSON），必须经过 Pydantic 严格校验；凡是应用内部流转的受信数据结构，优先使用 `dataclass` 保持轻量与高效。

---

## 2. Pydantic 校验错误剖析与错误脱敏

当外界传入非法数据时，Pydantic 会抛出 `ValidationError`。例如：

```python
from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    api_key: str
    temperature: float = Field(ge=0.0, le=2.0)
```

若传入 `{"api_key": "sk-1234567890", "temperature": 3.5}`，Pydantic 默认的 `exc.errors()` 结构中会包含：
- `loc`: 出错字段路径，如 `('temperature',)`
- `msg`: 错误描述
- `type`: 错误类型
- `input`: 用户输入的原始数据！

### 安全陷阱：密钥泄露
如果系统在捕获 `ValidationError` 后直接将 `str(exc)` 记录到日志或返回给客户端，而用户的输入恰好包含敏感的 `api_key` 或密码，**密钥就会直接泄露到外部响应或监控平台中**。

### 正确的脱敏实践
在配置加载（如 `load_settings`）层，应解析 `ValidationError.errors()`，只提取出错的字段名称（`loc`），向调用方返回结构清晰、不包含任何输入值的自定义异常：

```python
try:
    return Settings(**data)
except ValidationError as exc:
    invalid_fields = sorted({str(err["loc"][0]) for err in exc.errors() if err["loc"]})
    # 仅指出哪些字段出错，绝对不输出用户传入的敏感值
    raise SettingsError(f"配置校验失败，无效字段: {', '.join(invalid_fields)}") from None
```

---

## 3. 异步并发基础：超时与信号量限流

在 AI 应用中，LLM API 调用通常耗时在数百毫秒到数十秒之间，全链路异步化（`async`/`await`）是高吞吐服务的必备基础。

### 3.1 超时控制：`asyncio.wait_for` 与客户端超时
网络挂起是导致服务雪崩的头号原因。每个异步调用都必须具备确定性的超时上限：
```python
# 客户端级别或单次请求级别必须指定 timeout
async with httpx.AsyncClient(timeout=30.0) as client:
    resp = await client.get(url)
```

### 3.2 并发限流：`asyncio.Semaphore`
盲目使用 `asyncio.gather(*[call_llm(p) for p in prompts])` 在面对成千上万个任务时，会瞬间打满系统文件描述符或触发服务商的 Rate Limit（429 Too Many Requests）。

使用 `asyncio.Semaphore` 可以精确控制正在执行的协程数量，同时保证返回结果的列表顺序与输入顺序严格对齐：

```python
async def gather_limited(factories, limit: int):
    sem = asyncio.Semaphore(limit)
    async def worker(f):
        async with sem:
            return await f()
    return await asyncio.gather(*(worker(f) for f in factories))
```

---

## 4. 带指数退避的重试：依赖注入与可测试性

在遇到偶发性网络超时或 503 服务抖动时，重试是提升系统稳定性的核心手段。但重试设计有两项核心原则：
1. **只重试可重试的异常**：网络超时、连接断开或特定的临时服务端错误可以重试；但参数校验失败、401 认证错误或语法错误绝不能重试。
2. **避免羊群效应（Thundering Herd）**：采用指数退避机制（Exponential Backoff），第 $i$ 次重试等待时间为 $\text{base\_delay} \times 2^i$。
3. **依赖注入时钟（Fake Sleep）**：
   在编写单元测试时，如果真实调用 `time.sleep` 或 `asyncio.sleep`，几轮重试就会让测试运行变慢几秒甚至十几秒。
   **将 sleep 协程作为参数注入**，在单元测试中传入不实际休眠的假时钟（仅记录调用时长），测试可以毫秒级瞬时完成！

---

## 5. 离线测试替身：`httpx.MockTransport`

作为测试工程师转向 AI 开发的核心优势之一，就是严谨的测试替身意识。
在测试调用 OpenAI、DeepSeek 等第三方 API 的业务逻辑时，绝不能依赖真实网络环境。

`httpx` 提供了极具威力的 `MockTransport`，允许我们拦截所有 HTTP 请求并在内存中返回模拟响应或触发特定网络异常：

```python
import httpx

# 离线模拟服务返回 500 状态码
async def mock_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, json={"error": "gateway overloaded"})

transport = httpx.MockTransport(mock_handler)
async with httpx.AsyncClient(transport=transport) as client:
    # 请求完全在内存中执行，零网络 I/O，100% 确定性
    ...
```

本课程所有章节的离线 Gate 均基于这一设计，确保在断网、无 API 密钥的环境下依然可以 100% 确定性地自动化验证。

---

## 6. 动手练习与 Gate 验证

1. **阅读接口定义**：
   打开 [gate/starter.py](gate/starter.py)，阅读待实现的 4 个核心工程组件：
   - `load_settings`（配置加载与敏感信息脱敏）
   - `retry_async`（指数退避与 fake_sleep 注入）
   - `gather_limited`（信号量并发限流与顺序保持）
   - `fetch_json`（httpx 请求与离线异常封装）
2. **在 `starter.py` 中完成实现**。
3. **执行离线 Gate 验证**：
   ```powershell
   python chapters/part0-setup/0.4-python-engineering-base/gate/gate_check.py
   ```
   检查全部 12 项注入与断言是否全部通过。
4. **运行参考演示**：
   可参考 [python_engineering_base.py](python_engineering_base.py) 的实现与本地运行输出：
   ```powershell
   python chapters/part0-setup/0.4-python-engineering-base/python_engineering_base.py
   ```
5. **记录证据**：
   在 [workbook.md](workbook.md) 中记录实验观察与验证输出，并勾选 [gate/CHECKLIST.md](gate/CHECKLIST.md)。
