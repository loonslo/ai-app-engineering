"""L2.1 上下文工程总论 · 闭卷骨架

实现 Section 优先级装配、Token 预算控制、静态缓存前缀哈希与上下文 Lint 检查。
闭卷规则：只读本文件与本章 README；通过 gate 之前不要打开参考实现。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


def count_tokens(text: str) -> int:
    """确定性近似 Token 计数：每个 CJK 字符记 1；其余部分按空白切分，每个非空片段记 1。

    Gate 只用本函数以保证跨平台与无模型依赖下的绝对确定性。
    """
    raise NotImplementedError("实现 count_tokens")


def assemble_context(sections: list[Section], budget: int) -> AssembledContext:
    """按预算组装上下文段落。

    契约规范：
    - 去重与预警：同名或文本完全重复的 section 只保留首次出现的实例，warnings 追加 "duplicate:<name>"；
    - 必需项保证：required=True 的段落必须全部纳入；若仅 required 段落 Token 计数之和即超出 budget，抛出 ContextBudgetError；
    - 优先级裁剪：非 required 段落按 priority 从高到低尝试纳入（同 priority 按输入相对顺序稳定排序）；
      放不下的 section 进入 dropped 列表；
    - 组装与排序：输出正文必须先按顺序输出全部纳入的 static 段落，随后按顺序输出全部纳入的 dynamic 段落；
      各段落之间以两个换行符 ("\\n\\n") 连接；
    - 静态前缀哈希：static_prefix_hash 为全部纳入 static 段落文本以 "\\n\\n" 连接后的 SHA-256 十六进制摘要
      （无 static 段落时为 sha256("".encode('utf-8'))）；
    - 总体 Token 计量：tokens 为最终组装后总文本的 count_tokens 计量。
    """
    raise NotImplementedError("实现 assemble_context")


def lint_context(sections: list[Section], budget: int) -> list[str]:
    """对上下文段落集合进行缓存破坏与体积膨胀静态审查。

    审查规则：
    - 静态易失性检查：static section 中若包含日期（如 2026-10-27）或时间戳（如 10:30:00），
      告警 "volatile_in_static:<name>"；
    - 单段超限检查：单个 section 自身 Token 消耗超过 budget 的 50% 时，
      告警 "oversized:<name>"。
    返回告警列表。
    """
    raise NotImplementedError("实现 lint_context")
