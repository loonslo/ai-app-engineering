"""章节 1.4 · 多轮对话与上下文预算控制

知识点：
1. 原生 messages 列表维护多轮会话状态与时间顺序
2. 跨请求会话内存隔离（SessionMemory）
3. 滑动窗口与字符/Token 预算裁剪（强制保留 system prompt 并丢弃过旧上下文）
4. 对话摘要压缩（使用小模型对历史进行阶段性 Summary 压缩）

运行方式：
    python chapters/part1-foundations/1.4-context-memory/context_memory.py
"""

from __future__ import annotations

import sys
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


class MemoryError(ValueError):
    """会话或消息不合法。"""


class SessionMemory:
    """按 session_id 隔离的内存会话管理器。"""

    def __init__(self) -> None:
        self._data: dict[str, list[dict[str, str]]] = {}

    def add(self, session_id: str, role: str, content: str) -> None:
        """追加一条消息。

        要求：
        - session_id 非空字符串；
        - role 只能是 "system"、"user" 或 "assistant"；
        - content 是字符串。
        """
        if not isinstance(session_id, str) or not session_id:
            raise MemoryError("session_id 不能为空")
        if role not in {"system", "user", "assistant"}:
            raise MemoryError(f"不支持的 role: {role}")
        if not isinstance(content, str):
            raise MemoryError("content 必须为字符串")

        if session_id not in self._data:
            self._data[session_id] = []
        self._data[session_id].append({"role": role, "content": content})

    def get(self, session_id: str) -> list[dict[str, str]]:
        """返回该会话的消息副本；不存在返回 []。"""
        items = self._data.get(session_id, [])
        return [dict(msg) for msg in items]

    def clear(self, session_id: str) -> None:
        """清空该会话；不存在时静默返回。"""
        self._data.pop(session_id, None)


def trim_history(messages: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
    """按字符预算裁剪历史。

    要求：
    - max_chars < 0 抛 ValueError；
    - 空列表返回 []；
    - system 消息永远保留，按原顺序放在最前（即使超预算也不截断）；
    - 非 system 消息从最新往前选，遇到第一条放不下的就停止；
    - 不截断单条消息，不修改输入，输出保持时间先后顺序；
    - 消息缺少 role/content 或 content 不是字符串，抛 ValueError。
    """
    if max_chars < 0:
        raise ValueError("max_chars 不能为负数")
    if not messages:
        return []

    # 校验输入有效性
    for msg in messages:
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            raise ValueError("消息格式不合法: 必须包含 role 与 content 字段")
        if not isinstance(msg["content"], str):
            raise ValueError("content 必须为字符串类型")

    system_msgs: list[dict[str, Any]] = []
    non_system_msgs: list[dict[str, Any]] = []

    for msg in messages:
        copied_msg = dict(msg)
        if msg["role"] == "system":
            system_msgs.append(copied_msg)
        else:
            non_system_msgs.append(copied_msg)

    # 非 system 消息从最新往前挑选
    chosen_non_system: list[dict[str, Any]] = []
    used_chars = 0

    for msg in reversed(non_system_msgs):
        msg_len = len(msg["content"])
        if used_chars + msg_len <= max_chars:
            chosen_non_system.append(msg)
            used_chars += msg_len
        else:
            # 遇到第一条放不下的就停止
            break

    # 恢复正向时间顺序
    chosen_non_system.reverse()

    return system_msgs + chosen_non_system


def estimate_tokens_approx(text: str) -> int:
    """粗略估算 Token 数量（中英混合按约 1.5 字符/Token 估算，非精确分词）。"""
    return max(1, int(len(text) * 0.75))


def summarize_history(history: list[dict[str, str]]) -> str:
    """使用大模型对较长的历史进行要点提炼摘要（离线兜底返回模拟字符串）。"""
    if get_openai_client is None or chat_model_name is None:
        return "[摘要] 用户询问了 Python 异步编程基础与并发控制。"

    try:
        client = get_openai_client()
        model = chat_model_name()
        summary_prompt = [
            {"role": "system", "content": "请用一句话简要总结以下对话的历史核心上下文与用户偏好："},
            {"role": "user", "content": "\n".join(f"{m['role']}: {m['content']}" for m in history)},
        ]
        resp = client.chat.completions.create(
            model=model,
            messages=summary_prompt,
            temperature=0.0,
            max_tokens=60,
        )
        return resp.choices[0].message.content or ""
    except Exception:
        return "[摘要] 历史对话涉及系统工程与模型参数调优。"


def demonstrate_conversation() -> None:
    print("=== 多轮对话与上下文预算演示 ===")
    memory = SessionMemory()
    session_id = "user_session_101"

    # 添加系统指令与多轮历史
    memory.add(session_id, "system", "你是一个专业的 Python 后端技术教练。")
    memory.add(session_id, "user", "你好，我想了解 asyncio 的底层事件循环机制。")
    memory.add(session_id, "assistant", "你好！事件循环是 asyncio 的核心调度器，基于 epoll/kqueue/select 等多路复用机制运行。")
    memory.add(session_id, "user", "那么如何避免慢协程阻塞整个线程？")
    memory.add(session_id, "assistant", "对 CPU 密集型任务可以使用 loop.run_in_executor 或 ProcessPoolExecutor 卸载计算。")
    memory.add(session_id, "user", "请给我一个最小代码示例。")

    raw_history = memory.get(session_id)
    print(f"当前完整会话轮数: {len(raw_history)} 消息")

    print("\n--- 1. 上下文预算裁剪 (max_chars=80) ---")
    trimmed = trim_history(raw_history, max_chars=80)
    for idx, msg in enumerate(trimmed):
        print(f"  [{idx}] {msg['role']}: {msg['content']}")

    print("\n--- 2. 对话历史压缩摘要演示 ---")
    summary = summarize_history(raw_history)
    print(f"提炼摘要: {summary}")

    if get_openai_client is None or chat_model_name is None:
        print("\n[提示] 缺少 common 模块，跳过真实多轮调用。")
        return

    try:
        client = get_openai_client()
    except Exception as exc:
        print(f"\n[提示] 未能初始化客户端（{exc}）。演示跳过真实网络请求。")
        return

    model = chat_model_name()
    print(f"\n--- 3. 携带裁剪后上下文执行真实模型生成（模型: {model}）---")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=trimmed,  # type: ignore
            temperature=0.0,
            max_tokens=150,
        )
        reply = resp.choices[0].message.content
        print(f"【助手回答】:\n{reply}")
    except Exception as exc:
        print(f"调用异常: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    demonstrate_conversation()
