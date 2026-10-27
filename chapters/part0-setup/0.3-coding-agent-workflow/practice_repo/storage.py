from __future__ import annotations

try:
    from .models import Ticket, TicketStatus
except ImportError:
    from models import Ticket, TicketStatus

INITIAL_TICKETS: list[Ticket] = [
    Ticket(1, "登录页面偶发 500 内部错误", TicketStatus.OPEN, "high"),
    Ticket(2, "支付超时未自动触发退款", TicketStatus.IN_PROGRESS, "critical"),
    Ticket(3, "用户信息导出格式不对齐", TicketStatus.RESOLVED, "medium"),
    Ticket(4, "搜索框缺少前端防抖", TicketStatus.OPEN, "low"),
    Ticket(5, "工单审批状态流转异常", TicketStatus.CLOSED, "high"),
    Ticket(6, "Token 刷新偶现 401 失败", TicketStatus.IN_PROGRESS, "critical"),
    Ticket(7, "手机号短信验证码发送频率无限制", TicketStatus.OPEN, "critical"),
    Ticket(8, "文档问答引用片段丢失", TicketStatus.RESOLVED, "high"),
]
