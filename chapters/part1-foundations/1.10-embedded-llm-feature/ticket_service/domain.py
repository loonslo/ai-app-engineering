"""样例现有服务 · 领域数据契约（不含 LLM 依赖）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Ticket:
    """工单核心实体。"""

    id: str
    tenant_id: str
    user_id: str
    title: str
    description: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class TicketInsightDTO:
    """对外返回的工单洞察数据传输对象。"""

    ticket_id: str
    category: str
    priority: str
    order_id: str | None
    amount: float | None
    needs_human: bool
    source: str
    reasons: tuple[str, ...]
