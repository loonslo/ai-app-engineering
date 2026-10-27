"""章节 1.1 · 一次调用与 LLM 边界

知识点：
1. 原生 OpenAI 客户端调用大模型（单次问答与基础返回结构）
2. 响应对象的关键字段提取：content、usage、finish_reason
3. 三类典型 API 错误的识别与防御：认证失败、超时、限流（429）
4. 不依赖 LangChain 框架，理解框架底层的 HTTP 封装本质

运行方式：
    python chapters/part1-foundations/1.1-first-call/first_call.py
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import openai

# 导入共享配置与客户端工厂
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common import chat_model_name, get_openai_client  # noqa: E402


class CallError(RuntimeError):
    """可预期的调用或解析失败。"""


def build_messages(system: str, question: str) -> list[dict[str, str]]:
    """构造标准角色消息列表。

    要求：
    - 返回 [{"role": "system", "content": system}, {"role": "user", "content": question}]
    - system 或 question 为空字符串或纯空白时抛 ValueError
    """
    if not system or not system.strip():
        raise ValueError("system 角色提示词不能为空")
    if not question or not question.strip():
        raise ValueError("question 用户问题不能为空")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]


def parse_response(response: object) -> dict[str, Any]:
    """把模型返回对象或原始响应字典压成标准字段结构。

    返回：
    - content: str
    - input_tokens: int
    - output_tokens: int
    - finish_reason: str（缺省 "stop"）
    """
    if not isinstance(response, dict):
        raise CallError("bad_response")

    content = response.get("content")
    if not isinstance(content, str) or not content.strip():
        raise CallError("empty_response")

    usage = response.get("usage")
    input_tokens = 0
    output_tokens = 0
    if isinstance(usage, dict):
        # 兼顾 input_tokens 与 prompt_tokens
        raw_in = usage.get("input_tokens")
        if raw_in is None:
            raw_in = usage.get("prompt_tokens")
        raw_out = usage.get("output_tokens")
        if raw_out is None:
            raw_out = usage.get("completion_tokens")

        if isinstance(raw_in, int):
            input_tokens = raw_in
        if isinstance(raw_out, int):
            output_tokens = raw_out

    finish_reason = response.get("finish_reason")
    if not isinstance(finish_reason, str) or not finish_reason:
        finish_reason = "stop"

    return {
        "content": content,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "finish_reason": finish_reason,
    }


def call_once(
    system: str,
    question: str,
    chat_fn: Callable[[list[dict[str, str]]], object],
) -> dict[str, Any]:
    """执行一次调用，并在遇到异常时代为捕获并转为错误字段返回。"""
    if not question or not question.strip():
        raise ValueError("问题不能为空")

    try:
        messages = build_messages(system, question)
    except ValueError:
        raise

    try:
        raw_resp = chat_fn(messages)
    except TimeoutError:
        return {
            "content": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "finish_reason": "stop",
            "error": "timeout",
        }
    except Exception:
        return {
            "content": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "finish_reason": "stop",
            "error": "model_error",
        }

    try:
        parsed = parse_response(raw_resp)
        parsed["error"] = None
        return parsed
    except CallError as err:
        return {
            "content": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "finish_reason": "stop",
            "error": str(err),
        }


def demonstrate_live_call() -> None:
    """演示使用原生 SDK 进行一次真实调用与字段打印。"""
    try:
        client = get_openai_client()
    except Exception as exc:
        print(f"【提示】未配置模型 API 密钥或服务不可用（{exc}）。演示跳过真实网络请求。")
        return

    model = chat_model_name()
    messages = [
        {"role": "system", "content": "你是一个严谨的 AI 工程师，请用简练的一两句话回答。"},
        {"role": "user", "content": "用一句话解释什么是检索增强生成（RAG）？"},
    ]

    print(f"=== 1. 执行原生一次调用（模型: {model}）===")
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
        )
        choice = completion.choices[0]
        usage = completion.usage

        print("\n【模型输出内容】")
        print(choice.message.content)

        print("\n【关键元数据】")
        print(f"  - finish_reason: {choice.finish_reason}")
        if usage:
            print(f"  - prompt_tokens: {usage.prompt_tokens}")
            print(f"  - completion_tokens: {usage.completion_tokens}")
            print(f"  - total_tokens: {usage.total_tokens}")
    except openai.AuthenticationError:
        print("【错误分类·认证失败】API Key 无效或未授权（HTTP 401）。请检查密钥是否正确配置。")
    except openai.APITimeoutError:
        print("【错误分类·超时错误】请求上游服务超时，建议结合指数退避重试或检查网络联通性。")
    except openai.RateLimitError:
        print("【错误分类·限流错误】触发服务商并发或速率上限（HTTP 429），需排队重试或申请提额。")
    except Exception as exc:
        print(f"【调用异常】其他错误: {type(exc).__name__}: {exc}")


def demonstrate_error_handling() -> None:
    """演示三类典型 API 错误的识别与分类逻辑。"""
    print("\n=== 2. 三类关键 API 异常的识别与处理策略 ===")
    error_cases = [
        (
            openai.AuthenticationError(
                message="Incorrect API key provided",
                response=openai._models.FinalRequestOptions(method="post", url="/chat/completions"),  # type: ignore
                body={"error": {"message": "Invalid API key"}},
            ),
            "认证失败（401）：不可重试，应立即告警并检查配置密钥。",
        ),
        (
            openai.APITimeoutError(request=None),  # type: ignore
            "网络或读取超时：属于可重试错误，应采用指数退避（Exponential Backoff）重试。",
        ),
        (
            openai.RateLimitError(
                message="Rate limit reached",
                response=openai._models.FinalRequestOptions(method="post", url="/chat/completions"),  # type: ignore
                body={"error": {"message": "Rate limit exceeded"}},
            ),
            "速率限制（429）：可重试错误，应读取 Retry-After 头部或增加重试等待间隔。",
        ),
    ]

    for err, strategy in error_cases:
        err_name = type(err).__name__
        print(f"  - 识别捕获 [{err_name}]: {strategy}")


if __name__ == "__main__":
    demonstrate_live_call()
    demonstrate_error_handling()
