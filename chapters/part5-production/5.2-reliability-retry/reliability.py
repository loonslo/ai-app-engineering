"""
章节 5.2 · 可靠性：超时、带抖动的退避重试、成本统计（原生 openai SDK）
==========================================================
LLM 调用会超时、会被限流（429）、会偶发 5xx。上线前必须加防护，还要能算清
"每次调用花了多少 token / 多少钱"。

知识点：
1. 请求超时：在客户端上设置，别让一次卡住的调用拖垮整个服务
2. 指数退避 + 抖动（jitter）：只重试瞬时错误；等待有上限；多个客户端不要同一时刻一起重试
3. 429 / Retry-After：服务端说了该等多久就按它说的等
4. 降级：主模型重试耗尽后换备用模型（思路同 1.7）
5. token / 成本统计：用响应里的 usage

和 gate 的关系：下面的 backoff_delays / is_retryable / estimate_cost 与 gate 任务书
的三个函数同名同口径；先自己通过 gate，再来对照。

前置：1.1、1.7；DEEPSEEK_API_KEY（仅 --live 需要）
运行：python tools/run_chapter.py 5.2            （离线演示：脚本化的假客户端，不联网）
      python tools/run_chapter.py 5.2 --live     （调用真实模型，会产生少量费用）
==========================================================
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import openai


# ---------- 与 gate 同口径的三个纯函数 ----------
def backoff_delays(max_retries: int, base: float = 1.0, max_delay: float = 20.0) -> list[float]:
    """base, 2*base, 4*base...，每项不超过 max_delay。"""
    if max_retries < 0 or base <= 0 or max_delay <= 0:
        raise ValueError("max_retries 不能为负，base 与 max_delay 必须为正")
    return [min(base * 2**i, max_delay) for i in range(max_retries)]


def is_retryable(exc: BaseException) -> bool:
    """瞬时错误才重试：超时、连接错误、429、5xx。参数错、权限错重试也没用。"""
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    if isinstance(exc, (openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError)):
        return True
    return isinstance(exc, openai.APIStatusError) and exc.status_code >= 500


def estimate_cost(usage: dict | None, price_per_1k: float) -> float:
    """total_tokens / 1000 * 单价；usage 缺失按 0 处理。"""
    if price_per_1k < 0:
        raise ValueError("单价不能为负")
    if not usage or "total_tokens" not in usage:
        return 0.0
    return usage["total_tokens"] / 1000 * price_per_1k


# ---------- 带抖动的重试 ----------
def retry_after_seconds(exc: BaseException) -> float | None:
    """429 / 503 常带 Retry-After 头（秒数）；有就按服务端说的等。"""
    response = getattr(exc, "response", None)
    value = response.headers.get("retry-after") if response is not None else None
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def call_with_retry(
    fn: Callable[[], Any],
    *,
    max_retries: int = 3,
    base: float = 1.0,
    max_delay: float = 20.0,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
    log: Callable[[str], None] = print,
) -> Any:
    """调用 fn；瞬时错误按"指数退避 + 全抖动"重试，最多 max_retries 次重试。

    全抖动 = 在 [0, 退避上限] 里随机取一个等待值，让一批客户端的重试错开，
    不会在同一时刻再次打满服务。不可重试的错误立刻抛出，不吞异常。
    """
    rng = rng or random.Random()
    delays = backoff_delays(max_retries, base, max_delay)
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == max_retries or not is_retryable(exc):
                raise
            wait = retry_after_seconds(exc)
            if wait is None:
                wait = rng.uniform(0, delays[attempt])
            log(f"  第 {attempt + 1} 次失败（{type(exc).__name__}），{wait:.2f}s 后重试")
            sleep(wait)
    raise AssertionError("不可达")


def chat_with_fallback(
    clients_and_models: list[tuple[Any, str]], messages: list[dict], **retry_kwargs: Any
) -> tuple[Any, str]:
    """按顺序尝试 (client, model)；某个模型重试耗尽仍失败就换下一个。返回 (响应, 实际用的模型)。"""
    last: Exception | None = None
    for client, model in clients_and_models:
        try:
            resp = call_with_retry(
                lambda c=client, m=model: c.chat.completions.create(model=m, messages=messages),
                **retry_kwargs,
            )
            return resp, model
        except Exception as exc:
            last = exc
            if not is_retryable(exc):
                raise
    raise RuntimeError("所有模型都失败") from last


# ---------- 缓存：只给评测/开发用 ----------
# 精确匹配缓存：key = (模型, 消息) 的哈希。没有过期、没有淘汰，只增不减；
# 用户问题几乎不重复，知识库更新后旧答案也不会失效，所以不要接到对外问答链路。
# 适合反复跑同一批固定评测题。
class EvalCache:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.data: dict[str, str] = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    @staticmethod
    def key(model: str, messages: list[dict]) -> str:
        return hashlib.sha256(json.dumps([model, messages], ensure_ascii=False).encode()).hexdigest()

    def get_or_call(self, model: str, messages: list[dict], call: Callable[[], str]) -> str:
        k = self.key(model, messages)
        if k not in self.data:
            self.data[k] = call()
            self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        return self.data[k]


# ---------- 离线演示用的脚本化客户端 ----------
def _error(cls: type[openai.APIStatusError], status: int, headers: dict | None = None) -> openai.APIStatusError:
    request = httpx.Request("POST", "http://fake.local/v1/chat/completions")
    return cls("scripted", response=httpx.Response(status, request=request, headers=headers or {}), body=None)


class ScriptedClient:
    """按脚本依次返回错误或成功文本；不联网。"""

    def __init__(self, script: list[Exception | str]) -> None:
        self.script = list(script)
        self.chat = self
        self.completions = self

    def create(self, *, model: str, messages: list[dict]) -> Any:
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        usage = type("U", (), {"total_tokens": 120})()
        message = type("M", (), {"content": step})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


def run_offline() -> int:
    print("[离线演示] 脚本化客户端，等待时间用假 sleep，不会真的等\n")
    waits: list[float] = []
    rng = random.Random(7)  # 固定种子，演示输出可复现

    print("1) 先 429（带 Retry-After: 3）再 500，最后成功：")
    client = ScriptedClient([_error(openai.RateLimitError, 429, {"retry-after": "3"}),
                             _error(openai.InternalServerError, 500), "RAG 是检索增强生成。"])
    resp = call_with_retry(lambda: client.chat.completions.create(model="m", messages=[]),
                           sleep=waits.append, rng=rng)
    print("  回答：", resp.choices[0].message.content, "| 等待序列：", [round(w, 2) for w in waits])

    print("\n2) 400 参数错：不重试，直接抛出：")
    client = ScriptedClient([_error(openai.BadRequestError, 400), "不会走到这里"])
    try:
        call_with_retry(lambda: client.chat.completions.create(model="m", messages=[]), sleep=waits.append)
    except openai.BadRequestError:
        print("  已抛出 BadRequestError，脚本里还剩", len(client.script), "步没有被消费")

    print("\n3) 主模型一直 503，重试耗尽后降级到备用模型：")
    primary = ScriptedClient([_error(openai.InternalServerError, 503)] * 3)
    backup = ScriptedClient(["（备用模型的回答）"])
    resp, used = chat_with_fallback([(primary, "main"), (backup, "backup")], [],
                                    max_retries=2, sleep=waits.append, rng=rng)
    print("  实际使用：", used, "→", resp.choices[0].message.content)

    print("\n4) 成本估算（单价 0.001 元/1K token 仅为占位，请换成真实价格）：",
          estimate_cost({"total_tokens": 120}, 0.001), "元")
    return 0


def run_live() -> int:
    import common

    try:
        # max_retries=0：关掉 SDK 自带重试，重试只由上面这一层负责，避免两层重试叠加成重试风暴
        client = common.get_openai_client(timeout=20.0, max_retries=0)
        model = common.chat_model_name()
        messages = [{"role": "user", "content": "用一句话解释 RAG"}]
        resp = call_with_retry(lambda: client.chat.completions.create(model=model, messages=messages))
    except Exception as exc:  # 只给类型和提示，SDK 异常正文可能含 URL
        print(f"运行失败（{type(exc).__name__}）：检查模型配置、密钥与网络；未生成成功结果。", file=sys.stderr)
        return 1
    print(f"[live 真实模型 {model}]", resp.choices[0].message.content)
    usage = resp.usage.model_dump() if resp.usage else None
    print("token 用量：", usage)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="5.2 可靠性：超时、退避、成本")
    parser.add_argument("--live", action="store_true", help="调用真实模型")
    args = parser.parse_args()
    return run_live() if args.live else run_offline()


if __name__ == "__main__":
    raise SystemExit(main())

# ----------------------------------------------------------
# 小结：
# - 超时 + 重试是 LLM 调用的标配；限流（429）是生产里最常见的错误来源之一
# - 只重试瞬时错误；退避要有上限；要加抖动；服务端给了 Retry-After 就听它的
# - SDK 自带重试和你自己的重试只留一层，否则次数相乘
# - 降级要有序：先重试主模型，耗尽再换备用，并记录实际用了谁
# - 缓存只给评测/开发用，别接面向用户的问答链路
