"""SLA：判断工单是否已超过截止时间。"""
from __future__ import annotations

from datetime import datetime

from .models import Ticket


def is_overdue(ticket: Ticket, now: datetime) -> bool:
    """now 必须是带时区的时间；截止时间已过返回 True。"""
    if now.tzinfo is None:
        raise ValueError("now 必须带时区")
    return now.replace(tzinfo=None) > ticket.due_at.replace(tzinfo=None)
