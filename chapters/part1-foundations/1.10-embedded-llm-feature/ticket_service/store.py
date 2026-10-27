"""样例现有服务 · 内存多租户存储仓库。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .domain import Ticket


class TicketStore:
    """按 tenant_id 隔离存储工单与订单白名单。"""

    def __init__(self) -> None:
        # {tenant_id: {ticket_id: Ticket}}
        self._tickets: dict[str, dict[str, Ticket]] = {}
        # {tenant_id: set(order_ids)}
        self._orders: dict[str, set[str]] = {
            "tenant_a": {"ORD-100001", "ORD-100002", "ORD-100003"},
            "tenant_b": {"ORD-200001", "ORD-200002"},
        }

    def save_ticket(self, ticket: Ticket) -> None:
        if ticket.tenant_id not in self._tickets:
            self._tickets[ticket.tenant_id] = {}
        self._tickets[ticket.tenant_id][ticket.id] = ticket

    def get_ticket(self, tenant_id: str, ticket_id: str) -> Ticket | None:
        return self._tickets.get(tenant_id, {}).get(ticket_id)

    def order_exists(self, tenant_id: str, order_id: str) -> bool:
        """校验特定租户下是否存在该订单号。"""
        return order_id in self._orders.get(tenant_id, set())

    def clear(self) -> None:
        self._tickets.clear()
