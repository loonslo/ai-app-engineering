"""把工单分到队列：高优先级或含"宕机"进 urgent；含"退款"进 billing；其余 general。"""
from __future__ import annotations

from .models import Ticket


def route(ticket: Ticket) -> str:
    if ticket.priority == 1 or "宕机" in ticket.title:
        return "urgent"
    if "退款" in ticket.title:
        return "billing"
    return "general"
