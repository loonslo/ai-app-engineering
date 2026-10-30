"""L2.10 记忆与上下文压缩 · 原生实现

演示长会话历史预算压缩（保留系统提示、尾部对话、固定重要消息、其余提取摘要）
以及多租户隔离、策略管控的长期事实与偏好记忆库。
支持 --live 开启真实大模型摘要生成，并演示 20 轮对话关键事实保留评测。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common import chat_model_name, get_openai_client  # noqa: E402


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
    4. 若除去摘要外的必须保留消息（system + pinned + tail）本身已超出 budget，
       抛出带原因的 ValueError；
    5. 其余中间未固定消息交给 summarize_fn 压缩为一条 role="system"、以 "[摘要] " 开头的消息；
    6. 若加入摘要后总 token 超出 budget，基于 count_tokens 对摘要内容进行截断，严格保证不超预算；
       若剩余预算连最低摘要前缀与截断符都放不下，则省略摘要消息以严格保证不超预算；
    7. prefix_changed 指示首条 system 消息之后的内容是否改变。
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

    fixed_msgs = head + pinned + tail
    fixed_tokens = count_tokens(fixed_msgs)
    if fixed_tokens > budget:
        raise ValueError(
            f"必须保留的消息已超出预算限制：必须保留 {fixed_tokens} tokens，预算限制为 {budget} tokens"
        )

    if to_summarize:
        try:
            summary_content = summarize_fn(to_summarize)
            prefix = "[摘要] "
            base_text = summary_content.strip()
        except Exception:
            prefix = "[摘要不可用，已截断 "
            base_text = f"{len(to_summarize)} 条]"

        suffix = "...[截断]"
        full_msg = {"role": "system", "content": f"{prefix}{base_text}"}
        if count_tokens(head + [full_msg] + pinned + tail) <= budget:
            summary_msg = full_msg
        else:
            # 采用二分法根据 count_tokens 寻找不超预算的最大截断长度
            low = 0
            high = len(base_text)
            best_msg = None
            while low <= high:
                mid = (low + high) // 2
                cand_text = f"{prefix}{base_text[:mid]}{suffix}" if mid > 0 else f"{prefix}{suffix}"
                cand_msg = {"role": "system", "content": cand_text}
                if count_tokens(head + [cand_msg] + pinned + tail) <= budget:
                    best_msg = cand_msg
                    low = mid + 1
                else:
                    high = mid - 1
            summary_msg = best_msg

        if summary_msg is not None:
            new_msgs = head + [summary_msg] + pinned + tail
        else:
            new_msgs = head + pinned + tail
    else:
        new_msgs = head + pinned + tail

    if len(messages) > 1 and len(new_msgs) > 1:
        prefix_changed = new_msgs[1:] != messages[1:]
    else:
        prefix_changed = new_msgs != messages

    return CompactResult(
        messages=new_msgs,
        summarized_count=len(to_summarize),
        prefix_changed=prefix_changed,
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
        confirmed: bool = True,
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


def _offline_summarize(msgs: list[dict]) -> str:
    """本地确定性离线摘要生成器。"""
    text = " ".join(m.get("content", "") for m in msgs)
    details = []
    if "ORD-" in text:
        details.append("已确认订单物流状态")
    emails = re.findall(r"[\w\.-]+@[\w\.-]+", text)
    if emails:
        details.append(f"登记联系邮箱为 {emails[0]}")
    details.append("已讨论退换货运费、保修与开票政策")
    return "；".join(details) + "。"


def make_summarizer(live: bool) -> Callable[[list[dict]], str]:
    if live:
        try:
            client = get_openai_client()
        except Exception as exc:
            print(f"[可读提示] 未能初始化客户端（未配置有效 API 密钥）：{exc}", file=sys.stderr)
            sys.exit(1)
        model = chat_model_name()

        def live_summarize(msgs: list[dict]) -> str:
            conversation_text = "\n".join(f"{m['role']}: {m['content']}" for m in msgs)
            try:
                resp = client.chat.completions.create(
                    model=model,
                    temperature=0.0,
                    messages=[
                        {
                            "role": "system",
                            "content": "请用一两句话高度概括以下对话的核心业务事实，重点保留用户提及的联系方式与关键要求：",
                        },
                        {"role": "user", "content": conversation_text},
                    ],
                )
                content = resp.choices[0].message.content
                if not content or not content.strip():
                    print("[错误] 在线模型返回内容为空，未能生成有效摘要。", file=sys.stderr)
                    sys.exit(1)
                return content.strip()
            except Exception as exc:
                print(f"[错误] 在线模型摘要调用失败（{type(exc).__name__}: {exc}），终止运行。", file=sys.stderr)
                sys.exit(1)

        return live_summarize

    return _offline_summarize


def main() -> None:
    parser = argparse.ArgumentParser(description="2.14 记忆与上下文压缩演示")
    parser.add_argument("--live", action="store_true", help="启用真实在线模型生成摘要")
    args = parser.parse_args()

    print("=== L2.10 记忆与上下文压缩演示 ===")
    if args.live:
        print("[模式] 正在使用 --live 在线调用模型生成摘要。")
    else:
        print("[模式] 默认离线模式（未发起在线模型调用，可通过 --live 开启）。")

    summarizer = make_summarizer(live=args.live)

    # 1. 基础压缩演示
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

    print(f"\n[测试 1] 基础压缩：原始消息 {len(history)} 条")
    compacted = compact_history(
        history,
        budget=120,
        summarize_fn=summarizer,
        keep_last=2,
    )
    print(f"压缩后条数：{len(compacted.messages)}")
    print(f"压缩涉及历史消息数：{compacted.summarized_count}")
    print(f"前缀变化标志：{compacted.prefix_changed}")
    print(f"压缩后总 Token: {default_count_tokens(compacted.messages)} (预算 120)")
    for idx, msg in enumerate(compacted.messages):
        pinned_mark = " [PINNED]" if msg.get("pinned") else ""
        print(f"  [{idx}] {msg['role']}: {msg['content']}{pinned_mark}")

    # 2. 细则要求：20 轮对话记忆评测（关键事实保留验证）
    print("\n[测试 2] 20 轮长对话关键事实保留评测")
    long_20_rounds = [{"role": "system", "content": "You are an AI customer support assistant."}]
    # 第 1 轮明确固定关键事实（靠 pinned 机制）：用户的收货地址
    long_20_rounds.append({"role": "user", "content": "请牢记：我的收货地址是上海市徐汇区淮海中路 100 号", "pinned": True})
    long_20_rounds.append({"role": "assistant", "content": "好的，已永久记录您的收货地址为上海市徐汇区淮海中路 100 号。"})
    # 第 2 轮常规对话
    long_20_rounds.append({"role": "user", "content": "咨询业务问题第 2 轮：关于退换货运费"})
    long_20_rounds.append({"role": "assistant", "content": "答复第 2 轮：支持 7 天无理由退换货"})
    # 第 3 轮提供未固定普通事实（只能靠摘要机制保留）：发票邮箱
    long_20_rounds.append({"role": "user", "content": "我的电子发票联系邮箱是 alice@example.com，开票时发给我"})
    long_20_rounds.append({"role": "assistant", "content": "已记录您的电子发票联系邮箱为 alice@example.com。"})
    # 模拟后续 17 轮常规对话 (4-20 轮)
    for i in range(4, 21):
        long_20_rounds.append({"role": "user", "content": f"咨询业务问题第 {i} 轮：关于商品保修条款"})
        long_20_rounds.append({"role": "assistant", "content": f"答复第 {i} 轮：全国联保一年"})

    print(f"构建 20 轮长对话：原始消息共 {len(long_20_rounds)} 条，Token 数：{default_count_tokens(long_20_rounds)}")
    res_20 = compact_history(long_20_rounds, budget=280, summarize_fn=summarizer, keep_last=4)
    print(f"在预算 280 下压缩完成：保留消息条数 {len(res_20.messages)}，压缩后 Token 数：{default_count_tokens(res_20.messages)}")

    # 校验两类事实的保留情况
    all_content = " ".join(m["content"] for m in res_20.messages)
    address_retained = "上海市徐汇区淮海中路" in all_content
    email_retained = "alice@example.com" in all_content

    mode_label = "--live 真实模型生成" if args.live else "离线规则替身生成"
    print(f"\n20 轮评测检验报告（{mode_label}）：")
    if not args.live:
        print("  [说明] 离线模式下 PASS 来自本地正则表达式抽取替身；大模型的实际压缩抽象与语义保留能力须通过 --live 验证。")
    print(f"  1. [Pinned 事实] 收货地址（pinned 机制保留）：{'PASS (保留成功)' if address_retained else 'FAIL (丢失)'}")
    print(f"  2. [未固定事实] 发票邮箱（摘要机制保留）：{'PASS (保留成功)' if email_retained else 'FAIL (丢失)'}")

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
