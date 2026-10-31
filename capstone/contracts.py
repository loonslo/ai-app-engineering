"""企业 Copilot 的稳定业务契约；HTTP、CLI、评测和工作流共同使用。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AssistMode = Literal["auto", "knowledge", "data_query", "action", "memory"]
ResolvedMode = Literal["knowledge", "data_query", "action", "memory"]


@dataclass
class Document:
    """一段文本和它的 metadata；检索、ACL、上下文规划都围绕它。

    只保留 page_content 与 metadata 两个字段，不引入任何框架类型。
    """

    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Citation:
    """只能由实际召回记录构造，不能直接相信模型输出。"""

    source_id: str
    chunk_id: str
    page: int | None = None


@dataclass(frozen=True)
class AssistRequest:
    question: str
    request_id: str
    mode: AssistMode = "auto"
    query_id: str | None = None
    action: str | None = None
    thread_id: str | None = None


@dataclass(frozen=True)
class AssistResult:
    answer: str
    mode: ResolvedMode
    request_id: str
    tenant_id: str
    model: str = ""
    cache_hit: bool = False
    citations: tuple[Citation, ...] = field(default_factory=tuple)
    input_tokens: int = 0
    output_tokens: int = 0
    approval_id: str | None = None
    status: Literal["completed", "pending_approval"] = "completed"
    degraded: bool = False  # 主模型失败、由备用模型回答


class CapabilityUnavailable(RuntimeError):
    """请求了当前部署未启用的可选能力。"""
