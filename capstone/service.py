"""统一业务入口：所有用户请求共享身份、安全、缓存和结果契约。"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

from . import config as C
from .cache import AnswerCache, CachedAnswer, answer_cache
from .contracts import (
    AssistRequest,
    AssistResult,
    CapabilityUnavailable,
    ResolvedMode,
)
from .permissions import User
from .security import redact, validate_question
from .telemetry import tool_span


class KnowledgeRegistry(Protocol):
    def get(self, tenant_id: str): ...


class ContentSafety(Protocol):
    def check_input(self, text: str, *, request_id: str) -> None: ...

    def check_output(self, text: str, *, request_id: str) -> None: ...


class QueryTool(Protocol):
    def execute(self, query_id: str, identity: User) -> list[tuple[Any, ...]]: ...


class MemoryTool(Protocol):
    def handles(self, message: str) -> bool: ...

    def apply(self, message: str, identity: User) -> str: ...

    def context(self, identity: User) -> str: ...


class ApprovalTool(Protocol):
    def start(
        self,
        *,
        action: str,
        question: str,
        identity: User,
        request_id: str,
        thread_id: str | None,
    ) -> tuple[str, str]: ...


class NoopContentSafety:
    """本地最小策略；生产部署可注入失败关闭的外部审核网关。"""

    def check_input(self, text: str, *, request_id: str) -> None:
        _ = request_id
        validate_question(text)

    def check_output(self, text: str, *, request_id: str) -> None:
        _ = text, request_id


class AssistantService:
    """模块化单体的应用服务；不信任请求提供的身份或租户。"""

    def __init__(
        self,
        registry: KnowledgeRegistry,
        *,
        cache: AnswerCache = answer_cache,
        safety: ContentSafety | None = None,
        query_tool: QueryTool | None = None,
        memory_tool: MemoryTool | None = None,
        approval_tool: ApprovalTool | None = None,
        model_selector: Callable[[str], str] = C.select_model,
    ) -> None:
        self.registry = registry
        self.cache = cache
        self.safety = safety or NoopContentSafety()
        self.query_tool = query_tool
        self.memory_tool = memory_tool
        self.approval_tool = approval_tool
        self.model_selector = model_selector

    def _mode(self, request: AssistRequest, question: str) -> ResolvedMode:
        if request.mode != "auto":
            return request.mode
        if self.memory_tool is not None and self.memory_tool.handles(question):
            return "memory"
        if request.query_id:
            return "data_query"
        if request.action:
            return "action"
        return "knowledge"

    def assist(self, request: AssistRequest, identity: User) -> AssistResult:
        question = validate_question(request.question)
        self.safety.check_input(question, request_id=request.request_id)
        mode = self._mode(request, question)

        if mode == "memory":
            if self.memory_tool is None:
                raise CapabilityUnavailable("当前部署未启用长期记忆")
            answer = self.memory_tool.apply(question, identity)
            self.safety.check_output(answer, request_id=request.request_id)
            return AssistResult(
                redact(answer), mode, request.request_id, identity.tenant_id
            )

        if mode == "data_query":
            if self.query_tool is None or not request.query_id:
                raise CapabilityUnavailable("当前部署未启用该受控查询")
            with tool_span("catalog_query", request.request_id):
                rows = self.query_tool.execute(request.query_id, identity)
            answer = json.dumps(
                {"query_id": request.query_id, "rows": rows},
                ensure_ascii=False,
            )
            self.safety.check_output(answer, request_id=request.request_id)
            return AssistResult(
                redact(answer), mode, request.request_id, identity.tenant_id
            )

        if mode == "action":
            if self.approval_tool is None or not request.action:
                raise CapabilityUnavailable("当前部署未启用高风险动作工作流")
            with tool_span("approval_workflow", request.request_id):
                approval_id, draft = self.approval_tool.start(
                    action=request.action,
                    question=question,
                    identity=identity,
                    request_id=request.request_id,
                    thread_id=request.thread_id,
                )
            self.safety.check_output(draft, request_id=request.request_id)
            return AssistResult(
                redact(draft),
                mode,
                request.request_id,
                identity.tenant_id,
                approval_id=approval_id,
                status="pending_approval",
            )

        model = self.model_selector(question)
        kb = self.registry.get(identity.tenant_id)
        cache_key = self.cache.key(
            tenant_id=identity.tenant_id,
            user=identity,
            question=question,
            model=model,
            knowledge_version=kb.version,
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            cached_answer = (
                cached if isinstance(cached, CachedAnswer) else CachedAnswer(cached)
            )
            self.safety.check_output(
                cached_answer.answer, request_id=request.request_id
            )
            return AssistResult(
                redact(cached_answer.answer),
                "knowledge",
                request.request_id,
                identity.tenant_id,
                model=model,
                cache_hit=True,
                citations=cached_answer.citations,
            )

        preferences = (
            self.memory_tool.context(identity) if self.memory_tool is not None else ""
        )
        result = kb.answer_with_usage(
            question,
            user=identity,
            model=model,
            request_id=request.request_id,
            response_preferences=preferences,
        )
        self.safety.check_output(result.text, request_id=request.request_id)
        answer = redact(result.text)
        if not result.degraded:  # 备用模型的回答不进缓存，免得后来的用户在不知情时拿到降级答案
            self.cache.set(cache_key, CachedAnswer(answer, result.citations))
        return AssistResult(
            answer,
            "knowledge",
            request.request_id,
            identity.tenant_id,
            model=model,
            cache_hit=False,
            citations=result.citations,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            degraded=result.degraded,
        )
