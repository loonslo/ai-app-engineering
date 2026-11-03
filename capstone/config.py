"""Capstone 的集中式、环境可覆盖配置。"""

from __future__ import annotations

import os
from pathlib import Path

from common import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    EMBED_MODEL_PATH,
    LLM_PROVIDER,
    ZH_SEPARATORS,
    select_model,
    validate_provider_configuration,
)
from .embedding import get_embeddings
from .llm import get_chat

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
DATA_DIR = Path(os.getenv("CAPSTONE_DATA_DIR", HERE / "data")).resolve()
DOCS_DIR = Path(os.getenv("CAPSTONE_DOCS_DIR", DATA_DIR / "docs")).resolve()
CHROMA_DIR = str(DATA_DIR / "chroma")
DB_PATH = str(DATA_DIR / "app.db")
METRICS_DB_PATH = str(DATA_DIR / "metrics.db")
MEMORY_DB_PATH = str(DATA_DIR / "memory.db")
APPROVAL_DB_PATH = str(DATA_DIR / "approvals.db")
EVAL_SET = Path(os.getenv("CAPSTONE_EVAL_SET", DATA_DIR / "eval_set.json")).resolve()
REPORT_PATH = DATA_DIR / "eval_report.md"
FAILURES_PATH = DATA_DIR / "failures.json"

CHUNK_SIZE = int(os.getenv("CAPSTONE_CHUNK_SIZE", "300"))
CHUNK_OVERLAP = int(os.getenv("CAPSTONE_CHUNK_OVERLAP", "50"))
TOP_K = int(os.getenv("CAPSTONE_TOP_K", "4"))
CONTEXT_TOTAL_UNITS = int(os.getenv("CAPSTONE_CONTEXT_TOTAL_UNITS", "16000"))
CONTEXT_INSTRUCTION_UNITS = int(os.getenv("CAPSTONE_CONTEXT_INSTRUCTION_UNITS", "2000"))
CONTEXT_OUTPUT_RESERVE_UNITS = int(
    os.getenv("CAPSTONE_CONTEXT_OUTPUT_RESERVE_UNITS", "4000")
)
CONTEXT_SAFETY_MARGIN_UNITS = int(
    os.getenv("CAPSTONE_CONTEXT_SAFETY_MARGIN_UNITS", "1000")
)
MAX_QUESTION_CHARS = int(os.getenv("CAPSTONE_MAX_QUESTION_CHARS", "4000"))
CACHE_TTL_SECONDS = int(os.getenv("CAPSTONE_CACHE_TTL_SECONDS", "300"))
CACHE_MAX_ENTRIES = int(os.getenv("CAPSTONE_CACHE_MAX_ENTRIES", "1024"))
INPUT_COST_PER_MILLION = float(
    os.getenv(
        "LLM_INPUT_COST_PER_MILLION",
        os.getenv("DEEPSEEK_INPUT_COST_PER_MILLION", "0"),
    )
)
OUTPUT_COST_PER_MILLION = float(
    os.getenv(
        "LLM_OUTPUT_COST_PER_MILLION",
        os.getenv("DEEPSEEK_OUTPUT_COST_PER_MILLION", "0"),
    )
)
DEFAULT_DOCUMENT_VISIBILITY = (
    os.getenv(
        "CAPSTONE_DEFAULT_DOCUMENT_VISIBILITY",
        "restricted" if APP_ENV == "production" else "public",
    )
    .strip()
    .lower()
)
ENABLE_MEMORY = os.getenv("CAPSTONE_ENABLE_MEMORY", "true").strip().lower() == "true"
ENABLE_ACTIONS = os.getenv("CAPSTONE_ENABLE_ACTIONS", "true").strip().lower() == "true"
ENABLE_QUERY_TOOL = (
    os.getenv("CAPSTONE_ENABLE_QUERY_TOOL", "false").strip().lower() == "true"
)


def tenant_key(tenant_id: str) -> str:
    """返回无碰撞风险且不暴露原始租户名的存储键。"""
    import hashlib
    import re

    normalized = tenant_id.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", normalized):
        raise ValueError("tenant_id 必须是 1-64 位小写字母、数字、_ 或 -")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"{normalized[:24]}-{digest}"


def tenant_data_dir(tenant_id: str) -> Path:
    return DATA_DIR / "tenants" / tenant_key(tenant_id)


def tenant_chroma_dir(tenant_id: str) -> Path:
    return tenant_data_dir(tenant_id) / "chroma"


def tenant_docs_dir(tenant_id: str) -> Path:
    return tenant_data_dir(tenant_id) / "docs"


def ensure_runtime_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * INPUT_COST_PER_MILLION + output_tokens * OUTPUT_COST_PER_MILLION
    ) / 1_000_000


def validate_settings(*, production: bool | None = None) -> list[str]:
    """返回配置错误列表；调用方决定启动失败还是展示诊断。"""
    errors: list[str] = list(validate_provider_configuration())
    is_production = APP_ENV == "production" if production is None else production
    if CHUNK_SIZE <= 0:
        errors.append("CAPSTONE_CHUNK_SIZE 必须大于 0")
    if not 0 <= CHUNK_OVERLAP < CHUNK_SIZE:
        errors.append("CAPSTONE_CHUNK_OVERLAP 必须在 [0, chunk_size) 内")
    if TOP_K <= 0:
        errors.append("CAPSTONE_TOP_K 必须大于 0")
    try:
        from .context import ContextBudget

        ContextBudget(
            CONTEXT_TOTAL_UNITS,
            CONTEXT_INSTRUCTION_UNITS,
            CONTEXT_OUTPUT_RESERVE_UNITS,
            CONTEXT_SAFETY_MARGIN_UNITS,
        ).document_units
    except (TypeError, ValueError) as exc:
        errors.append(f"上下文预算配置无效：{exc}")
    if DEFAULT_DOCUMENT_VISIBILITY not in {"public", "restricted"}:
        errors.append("CAPSTONE_DEFAULT_DOCUMENT_VISIBILITY 只能是 public/restricted")
    if LLM_PROVIDER == "bedrock":
        errors.append("capstone 使用原生 OpenAI 兼容客户端，不再直连 Bedrock；请经 OpenAI 兼容网关接入（LLM_PROVIDER=openai_compatible）")
    if is_production and not os.getenv("LLM_PROVIDER", "").strip():
        errors.append("生产环境必须显式配置 LLM_PROVIDER")
    return errors


__all__ = [
    "APP_ENV",
    "APPROVAL_DB_PATH",
    "CACHE_MAX_ENTRIES",
    "CACHE_TTL_SECONDS",
    "CHROMA_DIR",
    "CHUNK_OVERLAP",
    "CHUNK_SIZE",
    "CONTEXT_INSTRUCTION_UNITS",
    "CONTEXT_OUTPUT_RESERVE_UNITS",
    "CONTEXT_SAFETY_MARGIN_UNITS",
    "CONTEXT_TOTAL_UNITS",
    "DATA_DIR",
    "DB_PATH",
    "DEFAULT_DOCUMENT_VISIBILITY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "DOCS_DIR",
    "EVAL_SET",
    "EMBED_MODEL_PATH",
    "ENABLE_ACTIONS",
    "ENABLE_MEMORY",
    "ENABLE_QUERY_TOOL",
    "FAILURES_PATH",
    "HERE",
    "LLM_PROVIDER",
    "INPUT_COST_PER_MILLION",
    "MAX_QUESTION_CHARS",
    "METRICS_DB_PATH",
    "MEMORY_DB_PATH",
    "OUTPUT_COST_PER_MILLION",
    "REPORT_PATH",
    "ROOT",
    "TOP_K",
    "ZH_SEPARATORS",
    "ensure_runtime_directories",
    "estimate_cost",
    "get_chat",
    "get_embeddings",
    "select_model",
    "tenant_chroma_dir",
    "tenant_data_dir",
    "tenant_docs_dir",
    "tenant_key",
    "validate_settings",
]
