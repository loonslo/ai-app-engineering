"""L4.5 Pydantic AI · 闭卷骨架。

只读本文件、本章 README 与官方 SDK 文档；通过前不要打开参考实现。
运行：python chapters/part4-agents-langgraph/4.16-pydantic-ai-agent/gate/gate_check.py
不允许修改 gate_check.py。指定 SDK：pydantic-ai-slim[openai]==2.31.1。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model


@dataclass
class SupportDeps:
    """每次运行由可信调用方注入；orders 按租户分区，refunds 是可观察的执行记录。"""
    tenant_id: str
    user_id: str
    orders: dict[str, dict[str, dict]]
    refunds: list[dict]


class SupportAnswer(BaseModel):
    reply: str
    order_id: str | None
    action: Literal["none", "refund_requested"]
    needs_human: bool


def build_support_agent(model: Model) -> Agent:
    """返回真实 SDK Agent，deps_type=SupportDeps，支持 SupportAnswer 与 DeferredToolRequests。

    get_order(ctx, order_id)：只查当前 tenant_id；不存在返回包含“未找到”的说明，不抛异常。
    request_refund(ctx, order_id, amount, idempotency_key)：标记 requires_approval=True；
    只有批准后才向 deps.refunds 追加记录，记录含 tenant_id/user_id/order_id/amount/idempotency_key。
    不存在于当前租户的订单不能退款；同一租户、同一幂等键只执行一次，即使重放暂停历史。
    输出 validator：空白 reply、action=refund_requested 却无 order_id 时抛 ModelRetry；
    允许模型纠正至少两次。DeferredToolRequests 不能当作 SupportAnswer 校验。
    禁用 SDK 自带埋点。模型参数必须原样注入，支持 Agent.override。
    """
    raise NotImplementedError("实现带工具、审批与输出校验的 SDK Agent")


def run_turn(
    agent: Agent, deps: SupportDeps, prompt: str, history: list[ModelMessage], *, request_limit: int
) -> dict:
    """执行真实 SDK 循环，传入 deps、prompt 和此前的完整历史。

    返回四键：output（SupportAnswer 或 None）、pending_approvals（待审调用 ID 列表）、
    history（含旧历史的新完整 SDK 消息）、error（None 或 usage_limit）。
    待审时 output=None，不执行退款。UsageLimits 的 request_limit 和 tool_calls_limit
    均设为 request_limit（本轮预算，续跑重新计数）；UsageLimitExceeded 转为 usage_limit，
    保留失败前已产生的历史。其他异常不在本接口吞掉。gate 使用正整数预算。
    """
    raise NotImplementedError("实现单轮运行与预算出口")


def resume_after_approval(
    agent: Agent,
    deps: SupportDeps,
    history: list[ModelMessage],
    approvals: dict[str, bool],
    *,
    request_limit: int,
) -> dict:
    """用暂停时的完整历史和 {待审调用ID: 是否批准} 构造 DeferredToolResults 续跑。

    不重复发送用户 prompt。调用方提供全部待审 ID 的决定；False 必须让模型看到包含
    “人工拒绝退款”的拒绝原因且不执行工具。返回结构与预算契约同 run_turn。
    允许重复使用同一暂停历史与审批；退款防重必须由 tenant_id+idempotency_key 实现，
    不是靠历史中已经有工具结果。审批来源与历史均假设为可信服务端。
    """
    raise NotImplementedError("实现审批续跑")


def dump_history(messages: list[ModelMessage]) -> str:
    """用 SDK ModelMessagesTypeAdapter 导出 JSON 字符串；不丢工具 ID、消息种类或时间。"""
    raise NotImplementedError("实现消息序列化")


def load_history(text: str) -> list[ModelMessage]:
    """用同一适配器从 JSON 恢复 SDK 消息；非法 JSON/消息由 Pydantic 抛校验异常。"""
    raise NotImplementedError("实现消息恢复")
