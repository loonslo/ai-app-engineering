"""样例现有服务 · FastAPI 路由与依赖注入接入。"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

try:
    from .domain import Ticket
    from .store import TicketStore
except ImportError:
    from domain import Ticket  # type: ignore
    from store import TicketStore  # type: ignore

app = FastAPI(title="Ticket Core Service")
store = TicketStore()


class CreateTicketRequest(BaseModel):
    title: str
    description: str


def get_current_tenant(x_tenant_id: str = Header(default="tenant_a")) -> str:
    """从 HTTP 头部注入租户身份，绝不信任请求体或模型输出。"""
    return x_tenant_id


def get_current_user(x_user_id: str = Header(default="user_dev_01")) -> str:
    """从 HTTP 头部注入用户身份。"""
    return x_user_id


def get_store() -> TicketStore:
    return store


@app.post("/tickets", status_code=201)
def create_ticket(
    req: CreateTicketRequest,
    tenant_id: str = Depends(get_current_tenant),
    user_id: str = Depends(get_current_user),
    db: TicketStore = Depends(get_store),
) -> dict[str, Any]:
    ticket_id = f"t-{uuid.uuid4().hex[:8]}"
    ticket = Ticket(
        id=ticket_id,
        tenant_id=tenant_id,
        user_id=user_id,
        title=req.title,
        description=req.description,
    )
    db.save_ticket(ticket)
    return {"ticket_id": ticket_id, "status": "created"}


@app.get("/tickets/{ticket_id}")
def get_ticket(
    ticket_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: TicketStore = Depends(get_store),
) -> dict[str, Any]:
    ticket = db.get_ticket(tenant_id, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return {
        "id": ticket.id,
        "tenant_id": ticket.tenant_id,
        "user_id": ticket.user_id,
        "title": ticket.title,
        "description": ticket.description,
    }
