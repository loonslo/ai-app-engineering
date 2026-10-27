from __future__ import annotations

try:
    from .models import Ticket
    from .storage import INITIAL_TICKETS
except ImportError:
    from models import Ticket
    from storage import INITIAL_TICKETS


class TicketService:
    def __init__(self, tickets: list[Ticket] | None = None) -> None:
        self._tickets: list[Ticket] = list(
            tickets if tickets is not None else INITIAL_TICKETS
        )

    def list_tickets(
        self,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """根据状态筛选工单并进行分页。

        待实现：
        1. status 筛选：有效状态过滤，忽略大小写；无效状态抛 ValueError；None 时不过滤。
        2. 参数校验：page_size <= 0 或 page < 1 时抛 ValueError。
        3. 分页逻辑：正确计算 total、page、page_size、total_pages、items。
        """
        # 原件未实现筛选与分页：直接返回全部工单
        return {
            "total": len(self._tickets),
            "items": self._tickets,
        }
