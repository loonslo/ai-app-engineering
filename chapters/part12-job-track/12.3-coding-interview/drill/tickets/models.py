"""数据模型：时间一律是带时区的 datetime。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Ticket:
    id: str
    title: str
    priority: int            # 1 最高，3 最低
    created_at: datetime
    due_at: datetime         # 截止时间（SLA）
    queue: str | None = None
    status: str = "open"
