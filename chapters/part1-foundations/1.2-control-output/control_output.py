"""章节 1.2 · 输出控制与流式生成

知识点：
1. 原生 API 控制生成行为：temperature、max_tokens、stop
2. stream=True 流式响应与 TTFT（首 Token 延迟）实时测量
3. 优雅处理流式 Usage 元数据（厂商支持 stream_options 时获取，缺失时降级提示）
4. 流式中断与异常契约的防御性处理

运行方式：
    python chapters/part1-foundations/1.2-control-output/control_output.py
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

# 导入共享配置与客户端工厂
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from common import chat_model_name, get_openai_client
except ImportError:
    chat_model_name = None  # type: ignore
    get_openai_client = None  # type: ignore


class RequestError(ValueError):
    """请求参数不合法。"""


def build_request(
    temperature: float = 0.0,
    max_tokens: int = 512,
    stop: list[str] | None = None,
) -> dict[str, Any]:
    """构造标准输出控制请求参数。

    要求：
    - temperature 必须在 0–2（含端点）的浮点数/整数；
    - max_tokens 必须是 1–8192 的整数（排除布尔值）；
    - stop 缺省为 []；必须是 list，元素为非空字符串，最多 4 个；
    - 任何不合法抛 RequestError。
    """
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise RequestError("temperature 必须为数值")
    if temperature < 0.0 or temperature > 2.0:
        raise RequestError(f"temperature={temperature} 超出 [0, 2] 合法范围")

    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int):
        raise RequestError("max_tokens 必须为整数")
    if max_tokens < 1 or max_tokens > 8192:
        raise RequestError(f"max_tokens={max_tokens} 超出 [1, 8192] 合法范围")

    if stop is None:
        stop = []
    if not isinstance(stop, list):
        raise RequestError("stop 必须为列表")
    if len(stop) > 4:
        raise RequestError(f"stop 列表长度不能超过 4，实际: {len(stop)}")
    for item in stop:
        if not isinstance(item, str) or not item:
            raise RequestError("stop 元素必须为非空字符串")

    return {
        "temperature": float(temperature),
        "max_tokens": max_tokens,
        "stop": list(stop),
    }


def collect_stream(
    chunks: Iterable[str],
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """收集流式片段并记录首 Token 延迟与状态。

    返回：
    - text: str（按顺序拼接）
    - chunks: int（收到的片段数）
    - first_chunk_ms: int（从开始到第一个片段的毫秒数；没有片段为 -1）
    - error: str | None（empty_stream / bad_chunk / model_error）
    """
    text_parts: list[str] = []
    chunk_count = 0
    first_chunk_ms = -1
    t0 = clock()

    try:
        for chunk in chunks:
            if chunk_count == 0:
                first_chunk_ms = int(round((clock() - t0) * 1000))
            if not isinstance(chunk, str):
                return {
                    "text": "".join(text_parts),
                    "chunks": chunk_count,
                    "first_chunk_ms": first_chunk_ms,
                    "error": "bad_chunk",
                }
            text_parts.append(chunk)
            chunk_count += 1
    except Exception:
        return {
            "text": "".join(text_parts),
            "chunks": chunk_count,
            "first_chunk_ms": first_chunk_ms,
            "error": "model_error",
        }

    if chunk_count == 0:
        return {
            "text": "",
            "chunks": 0,
            "first_chunk_ms": -1,
            "error": "empty_stream",
        }

    return {
        "text": "".join(text_parts),
        "chunks": chunk_count,
        "first_chunk_ms": first_chunk_ms,
        "error": None,
    }


def stream_text(
    chat_fn: Callable[[dict[str, Any]], Iterable[str]],
    request: dict[str, Any],
) -> dict[str, Any]:
    """把请求交给 chat_fn，收集它返回的流。"""
    try:
        chunks = chat_fn(request)
    except TimeoutError:
        return {
            "text": "",
            "chunks": 0,
            "first_chunk_ms": -1,
            "error": "timeout",
        }
    except Exception:
        return {
            "text": "",
            "chunks": 0,
            "first_chunk_ms": -1,
            "error": "model_error",
        }

    return collect_stream(chunks)


def demonstrate_live_stream() -> None:
    if get_openai_client is None or chat_model_name is None:
        print("[提示] 无法导入 common 模块，跳过真实请求演示。")
        return

    try:
        client = get_openai_client()
    except Exception as exc:
        print(f"[提示] 未能初始化客户端（{exc}）。演示跳过真实网络请求。")
        return

    model = chat_model_name()
    req_params = build_request(temperature=0.7, max_tokens=100, stop=["4.", "四、"])

    print(f"=== 演示原生流式调用与参数控制（模型: {model}）===")
    print(f"控制参数: {req_params}")
    print("提问: 请按 1. 2. 3. 4. 列出软件测试的核心价值，简短作答。")
    print("【实时流式输出】: ", end="", flush=True)

    t0 = time.perf_counter()
    first_token_time: float | None = None
    stream_chunks = 0
    full_text = []
    final_usage = None

    try:
        # 支持 include_usage 的流式调用
        response_stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "请按 1. 2. 3. 4. 列出软件测试的核心价值，简短作答。"}
            ],
            temperature=req_params["temperature"],
            max_tokens=req_params["max_tokens"],
            stop=req_params["stop"] if req_params["stop"] else None,
            stream=True,
            stream_options={"include_usage": True},
        )

        for chunk in response_stream:
            # 捕获 usage（通常在流的最后一个空 choices chunk 返回）
            if getattr(chunk, "usage", None) is not None:
                final_usage = chunk.usage

            if chunk.choices and chunk.choices[0].delta.content:
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                delta_content = chunk.choices[0].delta.content
                full_text.append(delta_content)
                print(delta_content, end="", flush=True)
                stream_chunks += 1

        print("\n")
        ttft_ms = (
            int(round((first_token_time - t0) * 1000)) if first_token_time else -1
        )
        total_time_ms = int(round((time.perf_counter() - t0) * 1000))

        print("【流式性能与统计】")
        print(f"  - 首 Token 延迟 (TTFT): {ttft_ms} ms")
        print(f"  - 总耗时: {total_time_ms} ms")
        print(f"  - 收到数据块数 (Chunks): {stream_chunks}")
        if final_usage:
            print(f"  - Token 用量: prompt={final_usage.prompt_tokens}, completion={final_usage.completion_tokens}, total={final_usage.total_tokens}")
        else:
            print("  - Token 用量: 【流式 usage 缺失】当前上游服务商未在流式末尾返回 usage 信息")
    except Exception as exc:
        print(f"\n[调用异常]: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    demonstrate_live_stream()
