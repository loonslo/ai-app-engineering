"""1.10 Pydantic AI Gate · 学习者闭卷骨架。

请在不修改函数签名的前提下实现 build_agent 与 extract_with_agent。
运行验证：
    python gate_check_pai.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic_ai import Agent


def build_agent(model: Any) -> Agent:
    """构建 Pydantic AI Agent。
    - deps_type 注入 tenant_id, user_id, order_exists 等契约字段；
    - output_type 绑定 Pydantic 模型；
    - 提供 check_order(ctx, order_id) 工具函数，通过 ctx.deps 查询；
    - 输出校验失败时使用 ModelRetry 触发模型重试。
    """
    raise NotImplementedError("请实现 build_agent")


def extract_with_agent(agent: Agent, ticket_text: str, deps: Any) -> Any:
    """使用 Pydantic AI Agent 抽取工单洞察并转为业务 DTO。
    - 调用 agent.run_sync；
    - 输出再经过与原生版一致的业务校验规则；
    - 重试用尽或失败时安全降级到规则回退。
    """
    raise NotImplementedError("请实现 extract_with_agent")
