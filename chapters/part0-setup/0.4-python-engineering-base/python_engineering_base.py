"""0.4 AI 应用的 Python 工程底座 · 参考实现与离线演示。

涵盖：
- Pydantic v2 配置契约校验与错误信息脱敏
- 带指数退避与可注入 fake sleep 的异步重试机制
- 基于 asyncio.Semaphore 的受限并发调度并保证结果保序
- 使用 httpx.MockTransport 进行离线网络测试替身
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Literal, TypeVar

import httpx
from pydantic import BaseModel, Field, ValidationError

T = TypeVar("T")


class SettingsError(ValueError):
    """配置读取与校验失败异常。"""


class HttpError(Exception):
    """HTTP 请求封装异常。"""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class Settings(BaseModel):
    """LLM 调用与工程配置模型。"""

    provider: Literal["deepseek", "openai", "openai_compatible", "ollama"]
    model: str = Field(min_length=1)  # 去掉首尾空白后不能为空
    timeout_s: float = Field(gt=0, le=120)  # 0 < timeout_s <= 120
    max_retries: int = Field(ge=0, le=5)  # 0 <= max_retries <= 5


def load_settings(env: Mapping[str, str]) -> Settings:
    """从环境变量字典加载并校验配置。

    校验失败抛 SettingsError，消息仅列出出错的字段名，不泄露任何输入内容或敏感密钥值。
    """
    raw_provider = env.get("LLM_PROVIDER")
    raw_model = env.get("MODEL")
    raw_timeout = env.get("TIMEOUT_S")
    raw_retries = env.get("MAX_RETRIES")

    data: dict[str, Any] = {}
    if raw_provider is not None:
        data["provider"] = raw_provider.strip().lower()

    if raw_model is not None:
        data["model"] = raw_model.strip()

    if raw_timeout is not None:
        try:
            data["timeout_s"] = float(raw_timeout)
        except ValueError:
            raise SettingsError("配置校验失败，无效字段: timeout_s") from None

    if raw_retries is not None:
        try:
            data["max_retries"] = int(raw_retries)
        except ValueError:
            raise SettingsError("配置校验失败，无效字段: max_retries") from None

    try:
        return Settings(**data)
    except ValidationError as exc:
        # 提取出错字段名称，避免打印包含敏感信息的 input value
        invalid_fields = sorted({str(err["loc"][0]) for err in exc.errors() if err["loc"]})
        fields_str = ", ".join(invalid_fields) if invalid_fields else "unknown"
        raise SettingsError(f"配置校验失败，无效字段: {fields_str}") from None


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    base_delay: float,
    sleep: Callable[[float], Awaitable[None]],
    retry_on: tuple[type[BaseException], ...],
) -> T:
    """最多调用 attempts 次。

    第 i 次失败后等待 base_delay * 2**i（i 从 0 开始），等待通过注入的 sleep 完成；
    只对 retry_on 中的异常重试，其他异常立即抛出；
    次数用尽时抛出最后一次的异常。attempts < 1 抛 ValueError。
    """
    if attempts < 1:
        raise ValueError("attempts 必须大于等于 1")

    for attempt in range(attempts):
        try:
            return await fn()
        except retry_on:
            if attempt == attempts - 1:
                raise
            delay = base_delay * (2**attempt)
            await sleep(delay)


async def gather_limited(
    factories: list[Callable[[], Awaitable[T]]],
    limit: int,
) -> list[T]:
    """factories 是返回协程的无参函数列表；同时运行的协程不超过 limit；结果顺序与输入一致；limit < 1 抛 ValueError。"""
    if limit < 1:
        raise ValueError("limit 必须大于等于 1")

    sem = asyncio.Semaphore(limit)

    async def run_worker(factory: Callable[[], Awaitable[T]]) -> T:
        async with sem:
            return await factory()

    tasks = [run_worker(f) for f in factories]
    return list(await asyncio.gather(*tasks))


async def fetch_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout_s: float,
) -> dict[str, Any]:
    """GET url。

    非 2xx 抛 HttpError("status:<code>")；
    响应体不是 JSON 对象抛 HttpError("invalid_json")；
    超时（httpx.TimeoutException）抛 HttpError("timeout")。
    """
    try:
        response = await client.get(url, timeout=timeout_s)
    except httpx.TimeoutException as exc:
        raise HttpError("timeout") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise HttpError(f"status:{response.status_code}")

    try:
        data = response.json()
    except Exception as exc:
        raise HttpError("invalid_json") from exc

    if not isinstance(data, dict):
        raise HttpError("invalid_json")

    return data


async def demo_offline() -> None:
    print("--- 1. 配置加载与脱敏演示 ---")
    settings = load_settings(
        {
            "LLM_PROVIDER": "deepseek",
            "MODEL": "deepseek-flash",
            "TIMEOUT_S": "30",
            "MAX_RETRIES": "3",
        }
    )
    print(f"配置解析成功: provider={settings.provider}, model={settings.model}")

    print("\n--- 2. 带退避与 fake_sleep 的重试演示 ---")
    attempts_done = 0

    async def flaky_task() -> str:
        nonlocal attempts_done
        attempts_done += 1
        if attempts_done < 3:
            print(f"  [Task] 第 {attempts_done} 次尝试失败...")
            raise ConnectionError("网络抖动")
        print(f"  [Task] 第 {attempts_done} 次尝试成功！")
        return "result_ok"

    async def fake_sleep(duration: float) -> None:
        print(f"  [Sleep] 模拟休眠 {duration} 秒（测试中不产生实际阻塞）")

    result = await retry_async(
        flaky_task,
        attempts=4,
        base_delay=1.0,
        sleep=fake_sleep,
        retry_on=(ConnectionError,),
    )
    print(f"重试执行结果: {result}")

    print("\n--- 3. 信号量受限并发调度演示 ---")
    running = 0

    def make_task(i: int) -> Callable[[], Awaitable[str]]:
        async def work() -> str:
            nonlocal running
            running += 1
            print(f"  [Worker {i}] 开始运行 (当前并发={running})")
            await asyncio.sleep(0.01)
            running -= 1
            return f"item_{i}"

        return work

    items = await gather_limited([make_task(i) for i in range(5)], limit=2)
    print(f"并发结果顺序: {items}")

    print("\n--- 4. MockTransport 离线请求演示 ---")

    async def mock_router(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "healthy", "service": "llm-gateway"})

    transport = httpx.MockTransport(mock_router)
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await fetch_json(client, "http://offline.local/health", timeout_s=5.0)
        print(f"离线 MockTransport 响应: {resp}")


if __name__ == "__main__":
    asyncio.run(demo_offline())
