"""v3 课程章节的离线纯函数与基础设施测试。

不联网、不调用真实模型、不读取本地 .env。
后续批次为换实现章节添加的离线测试同样追加到本文件。
"""

from __future__ import annotations

import openai
import pytest

import common


def test_deepseek_client_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(common, "LLM_PROVIDER", "deepseek")
    monkeypatch.setattr(common, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setattr(common, "_deepseek_api_key", lambda: "ds-test-key")

    client = common.get_openai_client(timeout=15.0, max_retries=2)
    assert isinstance(client, openai.OpenAI)
    assert str(client.base_url).rstrip("/") == "https://api.deepseek.com"
    assert client.api_key == "ds-test-key"
    assert client.timeout == 15.0
    assert client.max_retries == 2

    # 本地 URL 且无密钥时应使用 "local-model"
    monkeypatch.setattr(common, "DEEPSEEK_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(common, "_deepseek_api_key", lambda: None)
    local_client = common.get_openai_client()
    assert local_client.api_key == "local-model"

    # 远程 URL 且无密钥时抛 RuntimeError，消息包含变量名且不含密钥值
    monkeypatch.setattr(common, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setattr(common, "_deepseek_api_key", lambda: None)
    with pytest.raises(RuntimeError) as exc_info:
        common.get_openai_client()
    assert "DEEPSEEK_API_KEY" in str(exc_info.value)
    assert "ds-test-key" not in str(exc_info.value)


def test_openai_client_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(common, "LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.custom-openai.com/v1")

    client = common.get_openai_client(timeout=25.0, max_retries=1)
    assert isinstance(client, openai.OpenAI)
    assert client.api_key == "sk-openai-test-key"
    assert "custom-openai.com" in str(client.base_url)
    assert client.timeout == 25.0
    assert client.max_retries == 1

    # 缺少 OPENAI_API_KEY 时报错
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        common.get_openai_client()
    assert "OPENAI_API_KEY" in str(exc_info.value)
    assert "sk-openai-test-key" not in str(exc_info.value)


def test_openai_compatible_client_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(common, "LLM_PROVIDER", "openai_compatible")

    # 缺少 base_url 时报错
    monkeypatch.delenv("OPENAI_COMPATIBLE_BASE_URL", raising=False)
    with pytest.raises(RuntimeError) as exc_base:
        common.get_openai_client()
    assert "OPENAI_COMPATIBLE_BASE_URL" in str(exc_base.value)

    # 本地 base_url 且无密钥时应使用 "local-model"
    monkeypatch.setenv(
        "OPENAI_COMPATIBLE_BASE_URL", "http://127.0.0.1:11434/v1"
    )
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    local_client = common.get_openai_client()
    assert local_client.api_key == "local-model"

    # 远程 base_url 缺少密钥时报错
    monkeypatch.setenv(
        "OPENAI_COMPATIBLE_BASE_URL", "https://my-gateway.example.com/v1"
    )
    with pytest.raises(RuntimeError) as exc_key:
        common.get_openai_client()
    assert "OPENAI_COMPATIBLE_API_KEY" in str(exc_key.value)

    # 远程正常提供密钥
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "my-gateway-key")
    remote_client = common.get_openai_client()
    assert remote_client.api_key == "my-gateway-key"


def test_ollama_client_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(common, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(common, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    client = common.get_openai_client()
    assert isinstance(client, openai.OpenAI)
    # base_url 必须以 /v1 或 /v1/ 结尾
    assert str(client.base_url).rstrip("/").endswith("/v1")
    assert client.api_key == "ollama"


def test_azure_client_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(common, "LLM_PROVIDER", "azure")
    monkeypatch.setenv("AZURE_ENDPOINT", "https://test-resource.openai.azure.com")
    monkeypatch.setenv("AZURE_API_KEY", "azure-secret-token")
    monkeypatch.setenv("AZURE_API_VERSION", "2024-10-21")

    client = common.get_openai_client(timeout=20.0, max_retries=1)
    assert isinstance(client, openai.AzureOpenAI)
    assert client.timeout == 20.0
    assert client.max_retries == 1

    async_client = common.get_async_openai_client(timeout=18.0, max_retries=0)
    assert isinstance(async_client, openai.AsyncAzureOpenAI)

    # 缺少必需环境变量时报错
    monkeypatch.delenv("AZURE_ENDPOINT", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        common.get_openai_client()
    assert "AZURE_ENDPOINT" in str(exc_info.value)
    assert "azure-secret-token" not in str(exc_info.value)


def test_bedrock_client_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(common, "LLM_PROVIDER", "bedrock")

    with pytest.raises(RuntimeError) as exc_sync:
        common.get_openai_client()
    assert "Bedrock 不支持直接返回 OpenAI 客户端" in str(exc_sync.value)

    with pytest.raises(RuntimeError) as exc_async:
        common.get_async_openai_client()
    assert "Bedrock 不支持直接返回 OpenAI 客户端" in str(exc_async.value)


def test_async_openai_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(common, "LLM_PROVIDER", "deepseek")
    monkeypatch.setattr(common, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setattr(common, "_deepseek_api_key", lambda: "ds-async-key")

    async_client = common.get_async_openai_client(timeout=40.0, max_retries=0)
    assert isinstance(async_client, openai.AsyncOpenAI)
    assert async_client.api_key == "ds-async-key"
    assert async_client.timeout == 40.0


def test_chat_model_name(monkeypatch: pytest.MonkeyPatch):
    # 显式传参优先
    assert common.chat_model_name("custom-override-model") == "custom-override-model"

    # 读取默认配置
    monkeypatch.setattr(common, "LLM_PROVIDER", "deepseek")
    monkeypatch.setattr(common, "DEEPSEEK_MODEL", "deepseek-flash")
    assert common.chat_model_name() == "deepseek-flash"

    # 模型名称为空时抛出带变量名提示的 RuntimeError
    monkeypatch.setattr(common, "LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("OPENAI_COMPATIBLE_MODEL", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        common.chat_model_name()
    assert "OPENAI_COMPATIBLE_MODEL" in str(exc_info.value)


def test_sentence_embedder_missing_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(common, "EMBED_MODEL_PATH", "non_existent_embed_path_v3")
    common.get_sentence_embedder.cache_clear()

    with pytest.raises(RuntimeError) as exc_info:
        common.get_sentence_embedder()
    assert "本地 embedding 模型路径不存在" in str(exc_info.value)
    assert "准备本地 embedding 模型" in str(exc_info.value)


def test_cross_encoder_missing_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(common, "RERANKER_MODEL_PATH", "non_existent_reranker_path_v3")
    common.get_cross_encoder.cache_clear()

    with pytest.raises(RuntimeError) as exc_info:
        common.get_cross_encoder()
    assert "本地 reranker 模型路径不存在" in str(exc_info.value)
    assert "准备本地 embedding 模型" in str(exc_info.value)


def test_embed_texts(monkeypatch: pytest.MonkeyPatch):
    # 空列表直接返回 []，不调用 embedder
    assert common.embed_texts([]) == []

    class FakeEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr(common, "get_sentence_embedder", lambda: FakeEmbedder())
    result = common.embed_texts(["hello", "world"])
    assert result == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
