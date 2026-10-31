"""capstone 的模型调用：原生 openai 客户端 + 超时 + 带抖动的退避重试 + 可选备用模型。

语义与原来的 get_reliable_llm 保持一致：
- 单次请求最多等 20 秒；
- 主模型最多尝试 4 次（只重试超时、连接错误、429、5xx），退避带抖动；
- 配置了 CAPSTONE_BACKUP_MODEL 时，主模型耗尽后换备用模型再试 2 次，并把 degraded 标为 True。
  备用模型是同一 provider 的另一个模型名，不能解决整个供应商故障。
"""

from __future__ import annotations

import logging
import os
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import openai

LOG = logging.getLogger(__name__)
PRIMARY_ATTEMPTS = 4
BACKUP_ATTEMPTS = 2
TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True)
class ChatReply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    degraded: bool = False


def is_transient(exc: BaseException) -> bool:
    """只有瞬时错误才值得重试；参数错、鉴权错重试没有意义。"""
    if isinstance(exc, (TimeoutError, ConnectionError, openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError)):
        return True
    return isinstance(exc, openai.APIStatusError) and exc.status_code >= 500


def _retry_after(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None)
    try:
        return float(response.headers.get("retry-after")) if response is not None else None
    except (TypeError, ValueError):
        return None


def call_with_retry(
    fn: Callable[[], Any],
    *,
    attempts: int,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
    base: float = 1.0,
    cap: float = 20.0,
) -> Any:
    """最多调用 attempts 次；全抖动退避；服务端给了 Retry-After 就按它等。"""
    rng = rng or random.Random()
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if attempt == attempts - 1 or not is_transient(exc):
                raise
            wait = _retry_after(exc)
            sleep(wait if wait is not None else rng.uniform(0, min(base * 2**attempt, cap)))
    raise AssertionError("不可达")


class ChatClient:
    """一个模型 ID 对应一个实例；client 由调用方注入，默认按 LLM_PROVIDER 创建。"""

    def __init__(
        self,
        model: str,
        *,
        backup_model: str = "",
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model
        self.backup_model = backup_model.strip()
        self._client = client
        self._sleep = sleep

    def _get_client(self) -> Any:
        if self._client is None:
            import common

            # max_retries=0：重试只在本类里做一层，避免与 SDK 自带重试相乘
            self._client = common.get_openai_client(timeout=TIMEOUT_SECONDS, max_retries=0)
        return self._client

    def _once(self, model: str, messages: list[dict], temperature: float) -> ChatReply:
        response = self._get_client().chat.completions.create(model=model, messages=messages, temperature=temperature)
        usage = getattr(response, "usage", None)
        content = response.choices[0].message.content
        return ChatReply(
            text=content if isinstance(content, str) else str(content or ""),
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            model=model,
        )

    def complete(self, messages: list[dict], *, temperature: float = 0.0) -> ChatReply:
        try:
            return call_with_retry(lambda: self._once(self.model, messages, temperature), attempts=PRIMARY_ATTEMPTS, sleep=self._sleep)
        except Exception as exc:  # noqa: BLE001
            if not self.backup_model or not is_transient(exc):
                raise
            LOG.warning("主模型 %s 重试耗尽（%s），切换备用模型 %s", self.model, type(exc).__name__, self.backup_model)
        reply = call_with_retry(
            lambda: self._once(self.backup_model, messages, temperature), attempts=BACKUP_ATTEMPTS, sleep=self._sleep
        )
        return ChatReply(reply.text, reply.input_tokens, reply.output_tokens, reply.model, degraded=True)


def get_chat(model: str | None = None) -> ChatClient:
    """创建聊天客户端；模型 ID 默认取当前 LLM_PROVIDER 配置的模型。"""
    import common

    return ChatClient(common.chat_model_name(model), backup_model=os.getenv("CAPSTONE_BACKUP_MODEL", ""))
