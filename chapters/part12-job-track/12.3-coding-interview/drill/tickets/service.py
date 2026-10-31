"""服务层：提交（幂等）→ 分队列 → 查询（分页、超时）。"""
from __future__ import annotations

from datetime import datetime

from .models import Ticket
from .router import route
from .sla import is_overdue
from .store import TicketStore


class TicketService:
    def __init__(self) -> None:
        self.store = TicketStore()

    def submit(self, key: str, ticket: Ticket) -> tuple[Ticket, bool]:
        ticket.queue = route(ticket)
        return self.store.submit(key, ticket)

    def page(self, page: int, page_size: int = 10) -> list[Ticket]:
        return self.store.list_page(page, page_size)

    def overdue(self, now: datetime) -> list[Ticket]:
        return [t for t in self.store.list_page(1, max(self.store.count(), 1)) if is_overdue(t, now)]
