"""
公共配置与工厂（各章节共用）
==========================================================
集中管理各章节都要用的配置：共享资料路径、本地模型路径、LLM 工厂、中文分隔符。
换机器、换模型、换密钥只改这一处或 .env，不必逐个修改章节脚本。

初学者只需先认识四个名字（第 2 篇起会用到）：
- SAMPLE_DOC       多章共用的短示例文档（RAG 与评测的问答都基于它）
- LONG_DOC         长文章，用来观察切分、混合检索的效果
- get_embeddings() 本地中文 embedding 模型
- get_llm()        聊天模型；temperature 默认 0，评测结果才可复现
- ZH_SEPARATORS    中文文本切分用的分隔符

其余（provider 校验、可靠性包装、按问题选模型）在第 4–5 篇之后才需要读。
==========================================================
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values, load_dotenv

if TYPE_CHECKING:
    import openai

_DOTENV_PATH = Path(__file__).resolve().with_name(".env")
_DOTENV_DEEPSEEK_API_KEY = (
    str(dotenv_values(_DOTENV_PATH).get("DEEPSEEK_API_KEY") or "").strip()
    or None
)
_PROCESS_DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
load_dotenv(_DOTENV_PATH)

# ---- 共享资料：多章共用的示例文档和评测集放在 chapters/shared-data/ ----
SHARED_DATA_DIR = Path(__file__).resolve().parent / "chapters" / "shared-data"
SAMPLE_DOC = SHARED_DATA_DIR / "test_doc.txt"      # 短文档：评测集的问题和标准答案都基于它
LONG_DOC = SHARED_DATA_DIR / "long_article.txt"    # 长文章：文档够长，切分策略的差异才看得出来

# ---- 模型路径：优先读环境变量；没配就用 ModelScope 的默认缓存目录 ----
# 下载方法见根目录 README“准备本地 embedding 模型”；换机器时在 .env 里设置 EMBED_MODEL_PATH 即可。
_MODELSCOPE_HUB = Path.home() / ".cache" / "modelscope" / "hub" / "models" / "BAAI"
EMBED_MODEL_PATH = os.getenv(
    "EMBED_MODEL_PATH", str(_MODELSCOPE_HUB / "bge-small-zh-v1___5")
)
RERANKER_MODEL_PATH = os.getenv(
    "RERANKER_MODEL_PATH", str(_MODELSCOPE_HUB / "bge-reranker-base")
)

# 中文友好的递归切割分隔符：段落 > 换行 > 句号 > 逗号 > 空格 > 逐字兜底
ZH_SEPARATORS = ["\n\n", "\n", "。", "，", " ", ""]

# ---- LLM provider：兼容 DeepSeek 官方 API、本地 OpenAI-compatible 服务和 Ollama ----
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
DEEPSEEK_SIMPLE_MODEL = os.getenv("DEEPSEEK_SIMPLE_MODEL", "").strip()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:7b")
SUPPORTED_LLM_PROVIDERS = {
    "azure",
    "bedrock",
    "deepseek",
    "ollama",
    "openai",
    "openai_compatible",
}


@dataclass(frozen=True)
class ModelCapabilities:
    provider: str
    model: str
    structured_output: bool
    tool_calling: bool
    local: bool


def _is_local_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def _windows_user_environment(name: str) -> str | None:
    """读取进程启动后才更新的 Windows 用户变量；其他平台直接跳过。"""
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
    except (FileNotFoundError, OSError):
        return None
    return str(value).strip() or None


def _deepseek_api_key() -> str | None:
    """显式进程变量优先；识别并绕过 pytest 插件预加载的旧 .env 值。"""
    process_value = (_PROCESS_DEEPSEEK_API_KEY or "").strip() or None
    if process_value and process_value != _DOTENV_DEEPSEEK_API_KEY:
        return process_value
    return (
        _windows_user_environment("DEEPSEEK_API_KEY")
        or process_value
        or os.getenv("DEEPSEEK_API_KEY")
    )


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少必需环境变量 {name}")
    return value


def active_model_name() -> str:
    if LLM_PROVIDER == "ollama":
        return OLLAMA_MODEL
    if LLM_PROVIDER == "deepseek":
        return DEEPSEEK_MODEL
    if LLM_PROVIDER == "openai_compatible":
        return os.getenv("OPENAI_COMPATIBLE_MODEL", "").strip()
    if LLM_PROVIDER == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-6-luna")
    if LLM_PROVIDER == "azure":
        return os.getenv("AZURE_DEPLOYMENT", "")
    if LLM_PROVIDER == "bedrock":
        return os.getenv("BEDROCK_MODEL", "")
    raise ValueError(f"未知 LLM_PROVIDER：{LLM_PROVIDER}")


def provider_capabilities() -> ModelCapabilities:
    """返回保守能力声明；调用方不能假设所有 provider 完全等价。"""
    model = active_model_name()
    local = LLM_PROVIDER == "ollama" or (
        LLM_PROVIDER in {"deepseek", "openai_compatible"}
        and _is_local_url(
            DEEPSEEK_BASE_URL
            if LLM_PROVIDER == "deepseek"
            else os.getenv("OPENAI_COMPATIBLE_BASE_URL", DEEPSEEK_BASE_URL)
        )
    )
    structured = LLM_PROVIDER in {"azure", "deepseek", "openai"}
    tools = LLM_PROVIDER in {"azure", "bedrock", "deepseek", "openai"}
    return ModelCapabilities(LLM_PROVIDER, model, structured, tools, local)


def validate_provider_configuration() -> list[str]:
    errors: list[str] = []
    if LLM_PROVIDER not in SUPPORTED_LLM_PROVIDERS:
        return [f"不支持的 LLM_PROVIDER：{LLM_PROVIDER}"]
    try:
        model = active_model_name()
    except ValueError as exc:
        return [str(exc)]
    if not model:
        errors.append(f"{LLM_PROVIDER} 未配置模型/部署名")
    if LLM_PROVIDER == "deepseek":
        if not _deepseek_api_key() and not _is_local_url(DEEPSEEK_BASE_URL):
            errors.append("DeepSeek 远程接口缺少 DEEPSEEK_API_KEY")
    elif LLM_PROVIDER == "openai_compatible":
        base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "").strip()
        if not base_url:
            errors.append("缺少 OPENAI_COMPATIBLE_BASE_URL")
        elif not os.getenv("OPENAI_COMPATIBLE_API_KEY") and not _is_local_url(
            base_url
        ):
            errors.append("远程兼容接口缺少 OPENAI_COMPATIBLE_API_KEY")
    elif LLM_PROVIDER == "openai" and not os.getenv("OPENAI_API_KEY"):
        errors.append("缺少 OPENAI_API_KEY")
    elif LLM_PROVIDER == "azure":
        for name in ("AZURE_DEPLOYMENT", "AZURE_ENDPOINT", "AZURE_API_KEY"):
            if not os.getenv(name):
                errors.append(f"缺少 {name}")
    elif LLM_PROVIDER == "bedrock":
        if not os.getenv("BEDROCK_MODEL"):
            errors.append("缺少 BEDROCK_MODEL")
        if not os.getenv("AWS_REGION"):
            errors.append("缺少 AWS_REGION")
    return errors


@lru_cache(maxsize=1)
def get_embeddings():
    """本地 bge 中文 embedding。进程内只加载一次（lru_cache 缓存），避免重复 load。"""
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=EMBED_MODEL_PATH)


def get_llm(temperature: float = 0.0, model: str | None = None, **kwargs):
    """按统一接口创建模型，但保留 provider 能力差异。"""
    errors = validate_provider_configuration()
    if errors:
        raise RuntimeError("；".join(errors))
    if LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama

        timeout = kwargs.pop("timeout", None)
        kwargs.pop("max_retries", None)
        client_kwargs = dict(kwargs.pop("client_kwargs", {}))
        if timeout is not None:
            client_kwargs.setdefault("timeout", timeout)
        return ChatOllama(
            model=model or OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=temperature,
            client_kwargs=client_kwargs,
            **kwargs,
        )
    if LLM_PROVIDER == "azure":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_deployment=model or _required_environment("AZURE_DEPLOYMENT"),
            azure_endpoint=_required_environment("AZURE_ENDPOINT"),
            api_key=_required_environment("AZURE_API_KEY"),
            api_version=os.getenv("AZURE_API_VERSION", "2024-10-21"),
            temperature=temperature,
            **kwargs,
        )
    if LLM_PROVIDER == "bedrock":
        from langchain_aws import ChatBedrockConverse
        from botocore.config import Config

        timeout = kwargs.pop("timeout", None)
        kwargs.pop("max_retries", None)
        client_config = kwargs.pop("config", None)
        if client_config is None and timeout is not None:
            client_config = Config(
                connect_timeout=min(timeout, 10),
                read_timeout=timeout,
                retries={"max_attempts": 0},
            )

        return ChatBedrockConverse(
            model=model or _required_environment("BEDROCK_MODEL"),
            region_name=_required_environment("AWS_REGION"),
            temperature=temperature,
            config=client_config,
            **kwargs,
        )

    from langchain_openai import ChatOpenAI

    if LLM_PROVIDER == "openai":
        return ChatOpenAI(
            model=model or active_model_name(),
            api_key=_required_environment("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
            temperature=temperature,
            **kwargs,
        )
    if LLM_PROVIDER == "openai_compatible":
        base_url = _required_environment("OPENAI_COMPATIBLE_BASE_URL").rstrip("/")
        api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY")
        if not api_key and _is_local_url(base_url):
            api_key = "local-model"
    else:
        base_url = DEEPSEEK_BASE_URL
        api_key = _deepseek_api_key()
        if not api_key and _is_local_url(base_url):
            api_key = "local-model"
    return ChatOpenAI(
        model=model or active_model_name(),
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        **kwargs,
    )


def get_reliable_llm(temperature: float = 0.0, model: str | None = None,
                      backup_model: str | None = None, timeout: int = 20, **kwargs):
    """生产用 LLM 工厂：timeout + 指数退避重试（+ 可选主备 fallback）。

    这是服务可靠性策略落地的地方——不是 demo，是全项目对外问答链路
    真正在用的入口。capstone/knowledge_base.py 的 chain()、
    capstone/permissions.py 的 permission_chain() 都调用它。

    - timeout：单次请求最多等 20s，不让一次卡住的调用拖垮整个请求
    - with_retry：LangChain 内置指数退避 + jitter，只需一行，不用手写
    - backup_model：可选，配置后主模型重试耗尽仍失败时自动切备用模型。
      backup_model 使用当前 provider 的另一模型名；它不能解决整个供应商故障。
      跨 provider 容灾需要独立工厂、凭据、能力契约和切换演练，当前未交付。
    """
    if LLM_PROVIDER not in {"bedrock", "ollama"}:
        kwargs.setdefault("max_retries", 0)
    llm = get_llm(temperature=temperature, model=model, timeout=timeout, **kwargs).with_retry(
        stop_after_attempt=4,
        wait_exponential_jitter=True,
    )
    if backup_model:
        backup = get_llm(temperature=temperature, model=backup_model,
                          timeout=timeout, **kwargs).with_retry(stop_after_attempt=2)
        llm = llm.with_fallbacks([backup])
    return llm


def select_model(question: str) -> str:
    """在配置了轻量模型时，为短且低风险的问题选择它。"""
    primary = active_model_name()
    simple_variables = {
        "azure": "AZURE_SIMPLE_DEPLOYMENT",
        "bedrock": "BEDROCK_SIMPLE_MODEL",
        "deepseek": "DEEPSEEK_SIMPLE_MODEL",
        "ollama": "OLLAMA_SIMPLE_MODEL",
        "openai": "OPENAI_SIMPLE_MODEL",
        "openai_compatible": "OPENAI_COMPATIBLE_SIMPLE_MODEL",
    }
    simple = os.getenv(simple_variables[LLM_PROVIDER], "").strip()
    if simple and len(question.strip()) <= 80:
        return simple
    return primary


# ---- v3 原生模型与嵌入工厂（不依赖 LangChain） ----


def _resolve_openai_client_kwargs(
    *, timeout: float = 30.0, max_retries: int = 0
) -> tuple[str, dict[str, Any]]:
    """解析当前 LLM_PROVIDER 的客户端类型与构造参数（内部共用 helper）。"""
    provider = LLM_PROVIDER
    if provider == "bedrock":
        raise RuntimeError(
            "Bedrock 不支持直接返回 OpenAI 客户端；请改用 OpenAI 兼容网关或旧接口 get_llm()"
        )
    if provider not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(f"未知 LLM_PROVIDER：{provider}")

    if provider == "azure":
        endpoint = os.getenv("AZURE_ENDPOINT", "").strip()
        if not endpoint:
            raise RuntimeError("缺少必需环境变量 AZURE_ENDPOINT")
        api_key = os.getenv("AZURE_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("缺少必需环境变量 AZURE_API_KEY")
        api_version = os.getenv("AZURE_API_VERSION", "2024-10-21").strip()
        return "azure", {
            "azure_endpoint": endpoint,
            "api_key": api_key,
            "api_version": api_version,
            "timeout": timeout,
            "max_retries": max_retries,
        }

    if provider == "deepseek":
        base_url = DEEPSEEK_BASE_URL
        api_key = _deepseek_api_key()
        if not api_key:
            if _is_local_url(base_url):
                api_key = "local-model"
            else:
                raise RuntimeError("缺少必需环境变量 DEEPSEEK_API_KEY")
    elif provider == "openai":
        base_url = os.getenv("OPENAI_BASE_URL") or None
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("缺少必需环境变量 OPENAI_API_KEY")
    elif provider == "openai_compatible":
        base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "").strip().rstrip("/")
        if not base_url:
            raise RuntimeError("缺少必需环境变量 OPENAI_COMPATIBLE_BASE_URL")
        api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", "").strip()
        if not api_key:
            if _is_local_url(base_url):
                api_key = "local-model"
            else:
                raise RuntimeError("缺少必需环境变量 OPENAI_COMPATIBLE_API_KEY")
    elif provider == "ollama":
        base_url = f"{OLLAMA_BASE_URL}/v1"
        api_key = "ollama"

    return "openai", {
        "base_url": base_url,
        "api_key": api_key,
        "timeout": timeout,
        "max_retries": max_retries,
    }


def get_openai_client(
    *, timeout: float = 30.0, max_retries: int = 0
) -> openai.OpenAI:
    """按 LLM_PROVIDER 返回 OpenAI 兼容的客户端。

    v3 章节应使用本函数创建客户端，而不是使用 get_llm()。
    构造时不发送网络请求。
    """
    import openai

    client_type, kwargs = _resolve_openai_client_kwargs(
        timeout=timeout, max_retries=max_retries
    )
    if client_type == "azure":
        return openai.AzureOpenAI(**kwargs)
    return openai.OpenAI(**kwargs)


def get_async_openai_client(
    *, timeout: float = 30.0, max_retries: int = 0
) -> openai.AsyncOpenAI:
    """按 LLM_PROVIDER 返回 OpenAI 兼容的异步客户端。

    v3 章节应使用本函数创建异步客户端，而不是使用 get_llm()。
    构造时不发送网络请求。
    """
    import openai

    client_type, kwargs = _resolve_openai_client_kwargs(
        timeout=timeout, max_retries=max_retries
    )
    if client_type == "azure":
        return openai.AsyncAzureOpenAI(**kwargs)
    return openai.AsyncOpenAI(**kwargs)


def chat_model_name(model: str | None = None) -> str:
    """获取当前配置的聊天模型名称。

    v3 章节应使用本函数获取模型 ID，而不是硬编码模型名称或直接调用 active_model_name()。
    """
    selected = (model or "").strip() or active_model_name().strip()
    if not selected:
        env_map = {
            "deepseek": "DEEPSEEK_MODEL",
            "openai": "OPENAI_MODEL",
            "openai_compatible": "OPENAI_COMPATIBLE_MODEL",
            "ollama": "OLLAMA_MODEL",
            "azure": "AZURE_DEPLOYMENT",
            "bedrock": "BEDROCK_MODEL",
        }
        env_var = env_map.get(LLM_PROVIDER, "MODEL")
        raise RuntimeError(f"未配置模型名称，请设置环境变量 {env_var}")
    return selected


@lru_cache(maxsize=1)
def get_sentence_embedder():
    """本地 sentence_transformers embedding 模型工厂。进程内只加载一次（lru_cache 缓存）。

    v3 章节应使用本函数或 embed_texts()，而不是 get_embeddings()。
    """
    model_path = EMBED_MODEL_PATH
    if not Path(model_path).exists():
        raise RuntimeError(
            f"本地 embedding 模型路径不存在：{model_path}。"
            "准备方法见根目录 README“准备本地 embedding 模型”（如使用 ModelScope 下载 "
            "BAAI/bge-small-zh-v1.5 或在 .env 中设置 EMBED_MODEL_PATH）。"
        )
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_path)


def embed_texts(texts: list[str], *, normalize: bool = True) -> list[list[float]]:
    """使用本地 embedding 模型将文本列表向量化。

    v3 章节文本向量化统一入口。空列表直接返回 []。
    """
    if not texts:
        return []
    embedder = get_sentence_embedder()
    vectors = embedder.encode(texts, normalize_embeddings=normalize)
    if hasattr(vectors, "tolist"):
        return vectors.tolist()
    return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]


@lru_cache(maxsize=1)
def get_cross_encoder():
    """本地 sentence_transformers CrossEncoder 重排模型工厂。进程内只加载一次（lru_cache 缓存）。

    v3 检索重排章节统一入口。
    """
    model_path = RERANKER_MODEL_PATH
    if not Path(model_path).exists():
        raise RuntimeError(
            f"本地 reranker 模型路径不存在：{model_path}。"
            "准备方法见根目录 README“准备本地 embedding 模型”（如使用 ModelScope 下载 "
            "BAAI/bge-reranker-base 或在 .env 中设置 RERANKER_MODEL_PATH）。"
        )
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_path)
