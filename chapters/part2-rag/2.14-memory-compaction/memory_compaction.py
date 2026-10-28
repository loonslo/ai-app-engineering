"""L2.10 记忆与上下文压缩 · 原生实现

演示长会话历史预算压缩（保留系统提示、尾部对话、固定重要消息、其余提取摘要）
以及多租户隔离、策略管控的长期事实与偏好记忆库。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CompactResult:
    messages: list[dict]
    summarized_count: int
    prefix_changed: bool


def default_count_tokens(messages: list[dict]) -> int:
    """简易字符数统计（实际项目中可替换为 tiktoken / tokenizers）。"""
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

    保留规则：
    1. 首条 system 消息必须原样保留；
    2. 尾部 keep_last 条消息原样保留；
    3. 中间被标记 pinned=True 的消息原样保留；
    4. 其余中间消息交给 summarize_fn 压缩为一条 role="system"、以 [摘要] 开头的消息；
    5. 若 summarize_fn 异常，降级为截断提示；
    6. prefix_changed 指示首条 system 消息之后的内容是否改变（便于前缀缓存命中分析）。
    """
    if count_tokens(messages) <= budget:
        return CompactResult(messages=list(messages), summarized_count=0, prefix_changed=False)

    if not messages:
        return CompactResult(messages=[], summarized_count=0, prefix_changed=False)

    if messages[0].get("role") == "system":
        head = [messages[0]]
        rest = messages[1:]
    else:
        head = []
        rest = messages[:]

    if keep_last > 0:
        tail = rest[-keep_last:] if len(rest) >= keep_last else rest[:]
        middle = rest[:-keep_last] if len(rest) >= keep_last else []
    else:
        tail = []
        middle = rest[:]

    pinned = [m for m in middle if m.get("pinned")]
    to_summarize = [m for m in middle if not m.get("pinned")]

    if to_summarize:
        try:
            summary_content = summarize_fn(to_summarize)
            summary_msg = {"role": "system", "content": f"[摘要] {summary_content}"}
        except Exception:
            summary_msg = {"role": "system", "content": f"[摘要不可用，已截断 {len(to_summarize)} 条]"}
        new_msgs = head + [summary_msg] + pinned + tail
    else:
        new_msgs = head + pinned + tail

    return CompactResult(
        messages=new_msgs,
        summarized_count=len(to_summarize),
        prefix_changed=True,
    )


class MemoryStore:
    """按 (tenant_id, user_id) 严格隔离、支持策略管控的记忆存储。"""

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
        """写入记忆。source 必须在 {'user', 'model'} 中；未确认的模型自主写入被拒绝。"""
        if source not in {"user", "model"}:
            return False
        if source == "model" and not confirmed:
            return False
        t_key = (tenant_id, user_id)
        if t_key not in self._store:
            self._store[t_key] = {}
        self._store[t_key][key] = value
        return True

    def recall(self, tenant_id: str, user_id: str, key: str) -> str | None:
        """读取指定租户与用户的记忆键。"""
        t_key = (tenant_id, user_id)
        return self._store.get(t_key, {}).get(key, None)

    def forget(self, tenant_id: str, user_id: str, key: str) -> bool:
        """删除指定记忆键。"""
        t_key = (tenant_id, user_id)
        if t_key in self._store and key in self._store[t_key]:
            del self._store[t_key][key]
            return True
        return False

    def export(self, tenant_id: str, user_id: str) -> dict[str, str]:
        """安全导出记忆副本。"""
        t_key = (tenant_id, user_id)
        return dict(self._store.get(t_key, {}))


def main() -> None:
    print("=== L2.10 记忆与上下文压缩演示 ===")
    history = [
        {"role": "system", "content": "You are a customer service assistant."},
        {"role": "user", "content": "我上一单 ORD-8888 什么时候发货？"},
        {"role": "assistant", "content": "正在为您查询 ORD-8888 的物流状态..."},
        {"role": "user", "content": "我的收货地址是上海市徐汇区", "pinned": True},
        {"role": "assistant", "content": "已为您更新地址为上海市徐汇区。"},
        {"role": "user", "content": "满多少包邮？"},
        {"role": "assistant", "content": "全场满 99 元包邮。"},
        {"role": "user", "content": "用什么快递？"},
        {"role": "assistant", "content": "默认顺丰速运。"},
    ]

    print(f"原始消息条数：{len(history)}")
    compacted = compact_history(
        history,
        budget=100,
        summarize_fn=lambda msgs: "用户询问订单发货与运费政策，已获解答。",
        keep_last=2,
    )
    print(f"压缩后条数：{len(compacted.messages)}")
    print(f"压缩涉及历史消息数：{compacted.summarized_count}")
    print(f"前缀变化标志：{compacted.prefix_changed}")
    print("压缩后消息：")
    for idx, msg in enumerate(compacted.messages):
        pinned_mark = " [PINNED]" if msg.get("pinned") else ""
        print(f"  [{idx}] {msg['role']}: {msg['content']}{pinned_mark}")

    print("\n--- 长期记忆与多租户隔离演示 ---")
    store = MemoryStore()
    store.remember("tenant_a", "alice", "preferred_language", "zh-CN", source="user", confirmed=True)
    rejected = store.remember(
        "tenant_a", "alice", "credit_card", "1234-5678", source="model", confirmed=False
    )
    print(f"模型未确认写入被拦截：{not rejected}")
    print(f"租户 A Alice 语言偏好：{store.recall('tenant_a', 'alice', 'preferred_language')}")
    print(f"跨租户 B Alice 隔离测试：{store.recall('tenant_b', 'alice', 'preferred_language')}")
    print(f"租户 A 导出记忆副本：{json.dumps(store.export('tenant_a', 'alice'), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
