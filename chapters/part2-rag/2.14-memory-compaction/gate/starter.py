"""L2.10 记忆与上下文压缩 · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
memory_compaction.py。实现下面两个核心组件，然后运行：

    python chapters/part2-rag/2.14-memory-compaction/gate/gate_check.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CompactResult:
    messages: list[dict]
    summarized_count: int
    prefix_changed: bool


def default_count_tokens(messages: list[dict]) -> int:
    """默认简易字符数统计。"""
    return sum(len(m.get("content", "")) for m in messages)


def compact_history(
    messages: list[dict],
    budget: int,
    summarize_fn: Callable[[list[dict]], str],
    *,
    keep_last: int = 4,
    count_tokens: Callable[[list[dict]], int] = default_count_tokens,
) -> CompactResult:
    """在预算内压缩长会话历史。

    要求：
    - 不超预算时原样返回，summarized_count=0，prefix_changed=False；
    - 超预算时：
      1. 保留第一条 system 消息（若首条为 system）与最后 keep_last 条消息；
      2. 标记了 "pinned": True 的消息永远原样保留，并维持原有相对顺序；
      3. 其余中间未固定消息若存在，交给 summarize_fn(list) -> str 压缩为一条 role="system"、
         以 "[摘要]" 开头的消息，紧随第一条 system 消息之后；若无中间可压缩消息，则不插入摘要消息；
      4. 若 summarize_fn 抛出异常，降级为直接截断，摘要内容记 "[摘要不可用，已截断 N 条]"；
      5. 压缩后必须确保不超预算：若生成摘要后总 token 仍超 budget，则对摘要消息内容进行截断（保留前缀并在末尾追加 '...[截断]'），使压缩后的总 token 数严格不超过 budget；若除去摘要外的必须保留消息（system + pinned + tail）本身已占满或超出 budget，则不再插入摘要消息，直接返回固定保留消息；
      6. prefix_changed 指示首条 system 消息之后的内容（messages[1:]）是否发生了变更。
    """
    raise NotImplementedError("实现会话压缩 compact_history")


class MemoryStore:
    """按租户与用户严格隔离、支持策略管控的长期事实与偏好记忆库。"""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], dict[str, str]] = {}

    def remember(
        self,
        tenant_id: str,
        user_id: str,
        key: str,
        value: str,
        *,
        source: str,
        confirmed: bool,
    ) -> bool:
        """写入记忆。

        要求：
        - source 必须在 {"user", "model"} 中；
        - 当 source == "model" 且 confirmed == False 时，拒绝未确认的模型自主写入，返回 False；
        - 其余合法写入更新存储并返回 True。
        """
        raise NotImplementedError("实现记忆写入")

    def recall(self, tenant_id: str, user_id: str, key: str) -> str | None:
        """读取指定租户与用户的特定记忆键；不存在或跨用户/跨租户返回 None。"""
        raise NotImplementedError("实现记忆读取")

    def forget(self, tenant_id: str, user_id: str, key: str) -> bool:
        """删除指定键；存在并删除返回 True，不存在返回 False。"""
        raise NotImplementedError("实现记忆删除")

    def export(self, tenant_id: str, user_id: str) -> dict[str, str]:
        """导出指定租户与用户的全部记忆字典副本。"""
        raise NotImplementedError("实现记忆导出")
