r"""1.10 Pydantic AI Gate · 学习者闭卷骨架。

本章使用 Pydantic AI 框架实现与原生工单洞察一致的业务契约。

【闭卷规范】
只读本页、gate/starter.py 和 Pydantic AI 官方文档；通过 gate 之前不要打开参考实现。

【依赖结构与字段说明】
1. 依赖注入对象 FeatureDeps（定义于 gate/starter.py）：
   - tenant_id: str - 租户标识（多租户边界，禁止从模型输出获取）
   - user_id: str - 用户标识
   - chat_fn: Callable - 模型调用函数
   - order_exists: Callable[[str, str], bool] - 校验指定租户的订单是否存在：(tenant_id, order_id) -> bool
   - clock: Callable[[], float] - 时钟函数
   - prompt_version: str = "v1" - Prompt 版本
   - refund_human_threshold: float = 500.0 - 退款人工审核阈值（>= 该金额强制 needs_human=True）

2. 模型结构化输出字段契约（建议用 Pydantic BaseModel 声明为 output_type）：
   - category: str - 必须属于 CATEGORIES ("refund", "shipping", "account", "technical", "other")
   - priority: str - 必须属于 PRIORITIES ("low", "medium", "high", "urgent")
   - order_id: str | None - 订单号（符合正则 ^ORD-\d{6}$，如 ORD-123456；不存在或非法时置 None）
   - amount: float | None - 涉及金额（< 0 时置 None）

3. 最终返回领域对象 TicketInsight（定义于 gate/starter.py）：
   - category: str
   - priority: str
   - order_id: str | None
   - amount: float | None
   - needs_human: bool（退款类且金额为 None 或 >= 500 时为 True；规则兜底退款类 fail-closed 为 True）
   - source: str（"llm" | "rules"）
   - reasons: tuple[str, ...]（校验失败或规则触发的原因标签，如 "order_not_found", "negative_amount", "rules_fallback"）

运行验证：
    python chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check_pai.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    from gate.starter import (
        CATEGORIES,
        PRIORITIES,
        FeatureDeps,
        TicketInsight,
        rules_fallback,
        to_dto,
    )
except ImportError:
    from starter import (
        CATEGORIES,
        PRIORITIES,
        FeatureDeps,
        TicketInsight,
        rules_fallback,
        to_dto,
    )

__all__ = [
    "CATEGORIES",
    "PRIORITIES",
    "FeatureDeps",
    "TicketInsight",
    "rules_fallback",
    "to_dto",
    "build_agent",
    "extract_with_agent",
]

if TYPE_CHECKING:
    from pydantic_ai import Agent


def build_agent(model: Any) -> Agent:
    """构建 Pydantic AI Agent。

    要求：
    - deps_type 绑定 FeatureDeps；
    - output_type 绑定包含 category, priority, order_id, amount 的结构化模型；
    - 注册 @agent.tool 工具 check_order(ctx: RunContext[FeatureDeps], order_id: str) -> bool，
      通过 ctx.deps.order_exists(ctx.deps.tenant_id, order_id) 核验；
    - 注册 @agent.output_validator，当 category 或 priority 不在枚举值时抛出 ModelRetry 触发纠偏。
    """
    raise NotImplementedError("实现 build_agent")


def extract_with_agent(agent: Agent, ticket_text: str, deps: FeatureDeps) -> TicketInsight:
    """使用 Pydantic AI Agent 抽取工单洞察并转为领域 TicketInsight DTO。

    要求：
    - 使用 agent.run_sync 执行抽取，传入 ticket_text 与 deps；
    - 输出经过 to_dto(parsed, deps) 校验与清洗；
    - 当模型重试耗尽或遭遇不可恢复异常时，安全回退到 rules_fallback(ticket_text)。
    """
    raise NotImplementedError("实现 extract_with_agent")
