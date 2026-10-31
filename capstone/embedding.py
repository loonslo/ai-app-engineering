"""本地 embedding：对 common.embed_texts 的薄封装，提供 embed_documents / embed_query 两个方法。"""

from __future__ import annotations

from functools import lru_cache


class LocalEmbedder:
    """模型在第一次调用时才加载，进程内只加载一次（见 common.get_sentence_embedder）。"""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        from common import embed_texts

        return embed_texts(list(texts))

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache(maxsize=1)
def get_embeddings() -> LocalEmbedder:
    return LocalEmbedder()
