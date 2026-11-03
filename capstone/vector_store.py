"""原生 Chroma 向量库封装：写入、按 where 删除、带 ACL 过滤的相似度检索。

只暴露知识库用到的几个方法，方法名保持 add_documents / similarity_search / delete，
便于测试替身与既有调用点（增量同步）直接使用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import Document

COLLECTION = "capstone_v4"


class ChromaStore:
    def __init__(self, persist_directory: str | Path, embedding: Any) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=str(persist_directory))
        self._embedding = embedding
        self._collection = self._client.get_or_create_collection(COLLECTION)

    def count(self) -> int:
        return int(self._collection.count())

    def add_documents(self, documents: list[Document], *, ids: list[str]) -> None:
        """按 id 幂等写入（同 id 覆盖）。"""
        if not documents:
            return
        if len(ids) != len(documents):
            raise ValueError("ids 与 documents 数量必须一致")
        texts = [document.page_content for document in documents]
        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=self._embedding.embed_documents(texts),
            metadatas=[dict(document.metadata) for document in documents],
        )

    def delete(self, *, where: dict[str, Any]) -> None:
        self._collection.delete(where=where)

    def similarity_search(self, query: str, *, k: int, filter: dict[str, Any] | None = None) -> list[Document]:
        """查询前就带上 where 过滤条件：不满足 ACL 的块根本不会被召回。"""
        total = self.count()
        if total == 0:
            return []
        result = self._collection.query(
            query_embeddings=[self._embedding.embed_query(query)],
            n_results=min(k, total),
            where=filter or None,
            include=["documents", "metadatas"],
        )
        texts = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        return [Document(text, dict(metadata or {})) for text, metadata in zip(texts, metadatas)]

    def reset(self) -> None:
        """删除并重建集合（用于 rebuild）。"""
        self._client.delete_collection(COLLECTION)
        self._collection = self._client.get_or_create_collection(COLLECTION)
