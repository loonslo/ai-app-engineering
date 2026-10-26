"""认证、租户隔离、ACL、缓存、安全和可观测性完整接入的 FastAPI 服务。"""

from __future__ import annotations

import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from threading import RLock

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from . import config as C
from . import monitoring
from .approval import ApprovalWorkflow
from .auth import (
    ENABLE_DEV_LOGIN,
    auth_configuration_errors,
    guard,
    issue_token,
)
from .cache import answer_cache
from .content_safety import (
    ContentRejected,
    SafetyUnavailable,
    configuration_errors as safety_configuration_errors,
    from_environment as content_safety_from_environment,
)
from .contracts import AssistMode, AssistRequest, CapabilityUnavailable
from .knowledge_base import KnowledgeBase, SUPPORTED_SUFFIXES
from .memory import PreferenceMemory
from .permissions import User
from .query_catalog import CatalogQueryTool
from .readiness import check as readiness_errors
from .security import SecurityViolation, fingerprint, validate_question
from .service import AssistantService

LOG = logging.getLogger(__name__)
REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="")
_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{8,128}")


class TenantKBRegistry:
    """按租户延迟加载并物理隔离 Chroma；不会在模块 import 时加载模型。"""

    def __init__(self) -> None:
        self._items: dict[str, KnowledgeBase] = {}
        self._sync_mtimes: dict[str, int] = {}
        self._lock = RLock()
        self._tenant_locks: dict[str, RLock] = {}

    def _get_tenant_lock(self, tenant_id: str) -> RLock:
        with self._lock:
            lock = self._tenant_locks.get(tenant_id)
            if lock is None:
                lock = RLock()
                self._tenant_locks[tenant_id] = lock
            return lock

    @staticmethod
    def _sync_mtime(tenant_id: str) -> int:
        state = C.tenant_data_dir(tenant_id) / "sync_state.json"
        return state.stat().st_mtime_ns if state.is_file() else 0

    @staticmethod
    def _docs_dir(tenant_id: str) -> Path:
        tenant_docs = C.tenant_docs_dir(tenant_id)
        if tenant_docs.is_dir() and any(
            path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
            for path in tenant_docs.rglob("*")
        ):
            return tenant_docs
        return C.DOCS_DIR

    def get(self, tenant_id: str) -> KnowledgeBase:
        sync_mtime = self._sync_mtime(tenant_id)
        with self._lock:
            existing = self._items.get(tenant_id)
            if (
                existing is not None
                and self._sync_mtimes.get(tenant_id, 0) == sync_mtime
            ):
                return existing

        tenant_lock = self._get_tenant_lock(tenant_id)
        with tenant_lock:
            with self._lock:
                existing = self._items.get(tenant_id)
                sync_mtime = self._sync_mtime(tenant_id)
                if (
                    existing is not None
                    and self._sync_mtimes.get(tenant_id, 0) == sync_mtime
                ):
                    return existing

            kb = KnowledgeBase(
                tenant_id=tenant_id,
                docs_dir=self._docs_dir(tenant_id),
                persist_dir=C.tenant_chroma_dir(tenant_id),
            ).build()
            with self._lock:
                self._items[tenant_id] = kb
                self._sync_mtimes[tenant_id] = sync_mtime
            answer_cache.invalidate_tenant(tenant_id)
            return kb

    def reload(self, tenant_id: str) -> KnowledgeBase:
        tenant_lock = self._get_tenant_lock(tenant_id)
        with tenant_lock:
            kb = KnowledgeBase(
                tenant_id=tenant_id,
                docs_dir=self._docs_dir(tenant_id),
                persist_dir=C.tenant_chroma_dir(tenant_id),
            ).build(rebuild=True)
            with self._lock:
                self._items[tenant_id] = kb
                self._sync_mtimes[tenant_id] = self._sync_mtime(tenant_id)
            answer_cache.invalidate_tenant(tenant_id)
            return kb


registry = TenantKBRegistry()
approval_workflow = (
    ApprovalWorkflow(Path(C.APPROVAL_DB_PATH)) if C.ENABLE_ACTIONS else None
)
preference_memory = (
    PreferenceMemory(Path(C.MEMORY_DB_PATH)) if C.ENABLE_MEMORY else None
)
catalog_query_tool = CatalogQueryTool(Path(C.DB_PATH)) if C.ENABLE_QUERY_TOOL else None
assistant_service = AssistantService(
    registry,
    safety=content_safety_from_environment(),
    query_tool=catalog_query_tool,
    memory_tool=preference_memory,
    approval_tool=approval_workflow,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    errors = [
        *C.validate_settings(),
        *auth_configuration_errors(),
        *safety_configuration_errors(),
    ]
    if errors:
        raise RuntimeError("启动配置不安全：" + "；".join(errors))
    C.ensure_runtime_directories()
    yield


app = FastAPI(
    title="企业知识库 Agent",
    version="2.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied = request.headers.get("X-Request-ID", "")
    request_id = supplied if _REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex
    token = REQUEST_ID.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        LOG.info(
            "request_id=%s method=%s path=%s latency_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        REQUEST_ID.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


class DevLoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    tenant: str = Field(min_length=1, max_length=64)
    roles: list[str] = Field(default_factory=lambda: ["employee"], max_length=20)
    dept: str = Field(default="", max_length=64)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=C.MAX_QUESTION_CHARS)
    mode: AssistMode = "auto"
    query_id: str | None = Field(default=None, max_length=64)
    action: str | None = Field(default=None, max_length=64)
    thread_id: str | None = Field(default=None, max_length=128)


class CitationResponse(BaseModel):
    source_id: str
    chunk_id: str
    page: int | None = None


class ApprovalDecision(BaseModel):
    approved: bool


class ChatResponse(BaseModel):
    answer: str
    mode: str = "knowledge"
    tenant: str
    model: str
    cache_hit: bool
    request_id: str
    citations: list[CitationResponse] = Field(default_factory=list)
    approval_id: str | None = None
    status: str = "completed"


@app.post("/v1/dev-login", include_in_schema=ENABLE_DEV_LOGIN)
def dev_login(payload: DevLoginRequest):
    if not ENABLE_DEV_LOGIN or C.APP_ENV == "production":
        raise HTTPException(status_code=404, detail="not found")
    token = issue_token(
        payload.user_id,
        payload.tenant,
        payload.roles,
        payload.dept,
    )
    return {"access_token": token, "token_type": "bearer"}


@app.post("/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, identity: User = Depends(guard)):
    request_id = REQUEST_ID.get() or uuid.uuid4().hex
    started = time.perf_counter()
    is_error = False
    cache_hit = False
    model = ""
    question_fingerprint = ""
    input_tokens = 0
    output_tokens = 0
    try:
        question = validate_question(payload.question)
        question_fingerprint = fingerprint(question)
        result = assistant_service.assist(
            AssistRequest(
                question=question,
                request_id=request_id,
                mode=payload.mode,
                query_id=payload.query_id,
                action=payload.action,
                thread_id=payload.thread_id,
            ),
            identity,
        )
        answer = result.answer
        model = result.model
        cache_hit = result.cache_hit
        input_tokens = result.input_tokens
        output_tokens = result.output_tokens
    except ContentRejected as exc:
        is_error = True
        status = 400 if exc.stage == "input" else 503
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except SecurityViolation as exc:
        is_error = True
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SafetyUnavailable as exc:
        is_error = True
        raise HTTPException(status_code=503, detail="内容安全服务暂时不可用") from exc
    except CapabilityUnavailable as exc:
        is_error = True
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PermissionError as exc:
        is_error = True
        raise HTTPException(status_code=403, detail="无权访问该租户") from exc
    except Exception as exc:
        is_error = True
        LOG.exception("request_id=%s knowledge query failed", request_id)
        raise HTTPException(status_code=503, detail="服务暂时不可用") from exc
    finally:
        try:
            monitoring.record(
                identity.tenant_id,
                (time.perf_counter() - started) * 1000,
                is_error,
                request_id=request_id,
                tokens=input_tokens + output_tokens,
                cost=C.estimate_cost(input_tokens, output_tokens),
                model=model,
                cache_hit=cache_hit,
                question_fingerprint=question_fingerprint,
            )
        except Exception:
            LOG.exception("request_id=%s metrics write failed", request_id)
    return ChatResponse(
        answer=answer,
        mode=result.mode,
        tenant=identity.tenant_id,
        model=model,
        cache_hit=cache_hit,
        request_id=request_id,
        citations=[
            CitationResponse(
                source_id=citation.source_id,
                chunk_id=citation.chunk_id,
                page=citation.page,
            )
            for citation in result.citations
        ],
        approval_id=result.approval_id,
        status=result.status,
    )


@app.post("/v1/admin/reload")
def reload_tenant(identity: User = Depends(guard)):
    if "admin" not in identity.roles:
        raise HTTPException(status_code=403, detail="需要 admin 角色")
    kb = registry.reload(identity.tenant_id)
    return {"tenant": identity.tenant_id, "knowledge_version": kb.version}


@app.post("/v1/approvals/{approval_id}/decision")
def decide_approval(
    approval_id: str,
    payload: ApprovalDecision,
    identity: User = Depends(guard),
):
    if approval_workflow is None:
        raise HTTPException(status_code=503, detail="当前部署未启用审批工作流")
    try:
        result = approval_workflow.decide(
            approval_id,
            identity,
            approved=payload.approved,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, TimeoutError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "approval_id": approval_id,
        "status": "approved" if payload.approved else "rejected",
        "result": result,
    }


@app.get("/v1/metrics")
def metrics(identity: User = Depends(guard)):
    return monitoring.health(tenant=identity.tenant_id)


@app.get("/live")
def live():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    errors = readiness_errors()
    if errors:
        raise HTTPException(status_code=503, detail={"errors": errors})
    return {
        "status": "ready",
        "provider": C.LLM_PROVIDER,
        "query_tool": C.ENABLE_QUERY_TOOL,
        "memory": C.ENABLE_MEMORY,
        "actions": C.ENABLE_ACTIONS,
    }


@app.get("/health")
def health():
    """部署平台兼容端点；仅表示进程存活，不触发模型调用。"""
    return {"status": "ok"}
