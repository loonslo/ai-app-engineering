"""0.4 AI 应用的 Python 工程底座 · 接口定义与练习骨架。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Literal, TypeVar

import httpx
from pydantic import BaseModel, Field

T = TypeVar("T")


class SettingsError(ValueError):
    """配置读取与校验失败异常。"""


class HttpError(Exception):
    """HTTP 请求封装异常。"""

    def __init__(self, kind: str) -> None:
        # kind: "status:<code>" | "invalid_json" | "timeout"
        super().__init__(kind)
        self.kind = kind


class Settings(BaseModel):
    """LLM 调用与工程配置模型。"""

    provider: Literal["deepseek", "openai", "openai_compatible", "ollama"]
    model: str = Field(min_length=1)  # 去掉首尾空白后不能为空
    timeout_s: float = Field(gt=0, le=120)  # 0 < timeout_s <= 120
    max_retries: int = Field(ge=0, le=5)  # 0 <= max_retries <= 5


def load_settings(env: Mapping[str, str]) -> Settings:
    """读取 LLM_PROVIDER、MODEL、TIMEOUT_S、MAX_RETRIES。

    校验失败抛 SettingsError，消息列出出错的字段名，不包含任何敏感变量的值。
    """
    raise NotImplementedError


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
    raise NotImplementedError


async def gather_limited(
    factories: list[Callable[[], Awaitable[T]]],
    limit: int,
) -> list[T]:
    """factories 是返回协程的无参函数列表；同时运行的协程不超过 limit；结果顺序与输入一致；limit < 1 抛 ValueError。"""
    raise NotImplementedError


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
    raise NotImplementedError
