"""内存工单存储：幂等提交与分页列表。"""
from __future__ import annotations

from .models import Ticket


class TicketStore:
    def __init__(self) -> None:
        self._tickets: dict[str, Ticket] = {}
        self._by_key: dict[str, str] = {}   # 幂等键 -> 工单 id

    def submit(self, key: str, ticket: Ticket) -> tuple[Ticket, bool]:
        """相同幂等键重复提交，返回已有工单，created=False；新键保存并返回 created=True。"""
        created = key in self._by_key
        self._tickets[ticket.id] = ticket
        self._by_key[key] = ticket.id
        return ticket, created

    def list_page(self, page: int, page_size: int) -> list[Ticket]:
        """第 page 页（从 1 开始），每页 page_size 条，按创建时间从早到晚。"""
        if page < 1 or page_size < 1:
            raise ValueError("page 与 page_size 必须 >= 1")
        ordered = sorted(self._tickets.values(), key=lambda t: t.created_at)
        start = page * page_size
        return ordered[start:start + page_size]

    def count(self) -> int:
        return len(self._tickets)
