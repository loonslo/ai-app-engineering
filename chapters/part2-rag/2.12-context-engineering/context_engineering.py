"""L2.1 上下文工程总论 · 参考实现

核心能力：
1. 确定性 Token 近似计量 (count_tokens)；
2. 静态前缀前置与动态段落装配 (assemble_context)，最大化 Prompt Caching 命中；
3. 基于 Priority 与 Required 的确定性预算裁剪；
4. 缓存破坏（时间戳污染）与单段过大静态审查 (lint_context)。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import re
import sys
from pathlib import Path
from typing import Literal

# 导入共享 common
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from common import chat_model_name, get_openai_client
except ImportError:
    chat_model_name = None  # type: ignore
    get_openai_client = None  # type: ignore


class ContextBudgetError(ValueError):
    """当必需段落（required=True）超出预算时抛出。"""


@dataclass(frozen=True)
class Section:
    name: str
    text: str
    kind: Literal["static", "dynamic"]
    priority: int  # 越大越优先
    required: bool = False


@dataclass(frozen=True)
class AssembledContext:
    text: str
    included: tuple[str, ...]
    dropped: tuple[str, ...]
    tokens: int
    static_prefix_hash: str
    warnings: tuple[str, ...]


_CJK_PATTERN = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]"
)
_DATE_TIME_PATTERN = re.compile(
    r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}:\d{2}(?::\d{2})?\b"
)


def count_tokens(text: str) -> int:
    """确定性近似计数：每个 CJK 字符记 1；其余非 CJK 部分按空白切分，每个非空片段记 1。"""
    if not text:
        return 0

    cjk_count = len(_CJK_PATTERN.findall(text))
    # 将 CJK 字符替换为空格后按空白切分剩余西文字符与标点片段
    non_cjk_text = _CJK_PATTERN.sub(" ", text)
    non_cjk_tokens = len(non_cjk_text.split())
    return cjk_count + non_cjk_tokens


def assemble_context(sections: list[Section], budget: int) -> AssembledContext:
    """按预算组装上下文。"""
    # 1. 过滤同名或完全相同文本的 section（保留首次出现）
    seen_names: set[str] = set()
    seen_texts: set[str] = set()
    unique_sections: list[Section] = []
    warnings: list[str] = []

    for s in sections:
        if s.name in seen_names or s.text in seen_texts:
            warnings.append(f"duplicate:{s.name}")
            continue
        seen_names.add(s.name)
        seen_texts.add(s.text)
        unique_sections.append(s)

    # 2. 检查 required 段落
    required_sections = [s for s in unique_sections if s.required]
    non_required = [s for s in unique_sections if not s.required]

    req_tokens_map = {s.name: count_tokens(s.text) for s in unique_sections}
    req_tokens_total = sum(req_tokens_map[s.name] for s in required_sections)
    if req_tokens_total > budget:
        raise ContextBudgetError(
            f"Required sections exceed budget: required tokens={req_tokens_total}, budget={budget}"
        )

    # 3. 对非 required 按 priority 降序尝试纳入（同 priority 保持输入稳定顺序）
    # 使用 Python 的稳定排序：对非 required 段落按 priority 降序
    non_required_sorted = sorted(non_required, key=lambda s: s.priority, reverse=True)

    included_set: set[str] = {s.name for s in required_sections}
    current_tokens = req_tokens_total

    for s in non_required_sorted:
        tok = req_tokens_map[s.name]
        if current_tokens + tok <= budget:
            included_set.add(s.name)
            current_tokens += tok

    # 确定哪些被 dropped
    dropped_list: list[str] = [
        s.name for s in unique_sections if s.name not in included_set
    ]

    # 4. 组装输出文本：先输出全部纳入的 static 段落（按原始传入顺序），再输出 dynamic（按原始顺序）
    included_static: list[Section] = [
        s for s in unique_sections if s.name in included_set and s.kind == "static"
    ]
    included_dynamic: list[Section] = [
        s for s in unique_sections if s.name in included_set and s.kind == "dynamic"
    ]

    ordered_included = included_static + included_dynamic
    assembled_text = "\n\n".join(s.text for s in ordered_included)
    final_tokens = count_tokens(assembled_text)

    # 5. static 前缀哈希
    static_text = "\n\n".join(s.text for s in included_static)
    static_hash = hashlib.sha256(static_text.encode("utf-8")).hexdigest()

    included_names = tuple(s.name for s in ordered_included)
    return AssembledContext(
        text=assembled_text,
        included=included_names,
        dropped=tuple(dropped_list),
        tokens=final_tokens,
        static_prefix_hash=static_hash,
        warnings=tuple(warnings),
    )


def lint_context(sections: list[Section], budget: int) -> list[str]:
    """静态审查上下文质量：时间戳污染与单段超限。"""
    warnings: list[str] = []
    half_budget = budget * 0.5

    for s in sections:
        if s.kind == "static" and _DATE_TIME_PATTERN.search(s.text):
            warnings.append(f"volatile_in_static:{s.name}")
        tok = count_tokens(s.text)
        if tok > half_budget:
            warnings.append(f"oversized:{s.name}")

    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="L2.1 上下文工程演示")
    parser.add_argument("--live", action="store_true", help="调用真实模型测试 Prompt Caching 命中")
    args = parser.parse_args()

    # 构造示例上下文段落
    system_static = Section(
        name="system_prompt",
        text=(
            "你是一个专业的电商售后客服智能体。请遵循以下不可违反的原则：\n"
            "1. 仅依据提供的官方售后政策解答用户咨询；\n"
            "2. 涉及未拆封商品退换货，时效为签收后 7 天以内；\n"
            "3. 遇到投诉或争议工单，保持礼貌克制，主动引导转接人工复核。"
        ),
        kind="static",
        priority=100,
        required=True,
    )
    user_info = Section(
        name="user_profile",
        text="用户等级：VIP2；注册时间：2023年；历史退货率：1.2%。",
        kind="dynamic",
        priority=30,
        required=False,
    )
    knowledge = Section(
        name="kb_policy",
        text="【官方物流细则】顺丰特快支持同城半日达与跨省次日达；退货运费险最高赔付 12 元/单。",
        kind="static",
        priority=60,
        required=False,
    )
    user_query = Section(
        name="user_query",
        text="我昨天买的衣服码数选小了，吊牌没拆，现在退货运费谁出？",
        kind="dynamic",
        priority=90,
        required=True,
    )

    sections = [system_static, knowledge, user_info, user_query]
    budget = 200

    print("=== 1. 静态上下文 Lint 检查 ===")
    lint_res = lint_context(sections, budget)
    print(f"Lint 结果（无告警即为干净）：{lint_res or '全部通过 (干净上下文)'}")

    print("\n=== 2. 上下文装配（预算控制与前缀哈希）===")
    assembled = assemble_context(sections, budget)
    print(f"装配段落列表: {assembled.included}")
    print(f"丢弃段落列表: {assembled.dropped}")
    print(f"总 Token 消耗: {assembled.tokens} / 预算 {budget}")
    print(f"静态前缀哈希 (用于命中 Prompt Caching): {assembled.static_prefix_hash}")
    print("\n装配正文预览:\n" + "-" * 40)
    print(assembled.text)
    print("-" * 40)

    if args.live:
        print("\n=== 3. 真实模型 Prompt Caching 测试 ===")
        if get_openai_client is None or chat_model_name is None:
            print("[可读提示] 缺少 common 依赖或未安装 openai SDK，无法执行 --live。")
            return
        try:
            client = get_openai_client()
        except Exception as exc:
            print(f"[可读提示] 当前未配置模型 API 密钥（{exc}），请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY。")
            return
        if client is None:
            print("[可读提示] 当前未配置模型 API 密钥，请在 .env 中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY。")
            return

        model = chat_model_name()
        print(f"使用模型: {model}")
        messages = [
            {"role": "system", "content": system_static.text + "\n\n" + knowledge.text},
            {"role": "user", "content": user_query.text},
        ]

        print("发起第 1 次调用（建立缓存）...")
        resp1 = client.chat.completions.create(model=model, messages=messages, temperature=0.0)
        u1 = getattr(resp1, "usage", None)
        print(f"第 1 次调用 Usage: {u1}")

        print("发起第 2 次相同前缀调用（验证命中）...")
        resp2 = client.chat.completions.create(model=model, messages=messages, temperature=0.0)
        u2 = getattr(resp2, "usage", None)
        print(f"第 2 次调用 Usage: {u2}")
        if u2:
            hit_tokens = getattr(u2, "prompt_cache_hit_tokens", None)
            if hit_tokens is None and hasattr(u2, "prompt_tokens_details"):
                hit_tokens = getattr(u2.prompt_tokens_details, "cached_tokens", None)
            print(f"检测到缓存命中 Token: {hit_tokens}")
        print(f"模型回复: {resp2.choices[0].message.content[:80]}...")


if __name__ == "__main__":
    main()
