from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass(frozen=True)
class Ticket:
    id: int
    title: str
    status: TicketStatus
    priority: str
