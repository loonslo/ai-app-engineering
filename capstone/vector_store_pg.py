"""可选的 pgvector 后端，强调迁移、幂等与租户边界。

直接用 psycopg 执行 SQL（pgvector 扩展），不依赖 LangChain。表结构由迁移/DBA 创建
（见 migration 命令输出）；应用账号只读写数据，不自动安装扩展或改表结构。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from capstone.config import tenant_key
from capstone.contracts import Document
from capstone.permissions import User, attach_acl


@dataclass(frozen=True)
class PgVectorSettings:
    connection: str
    collection: str
    dimensions: int
    tenant_id: str

    @classmethod
    def from_env(cls, *, require_connection: bool = True) -> "PgVectorSettings":
        connection = os.getenv("PG_CONN", "").strip()
        if require_connection and not connection:
            raise RuntimeError(
                "缺少 PG_CONN；不要在源码里提供带默认密码的连接串"
            )
        base_collection = os.getenv("PG_COLLECTION", "capstone_kb").strip()
        if not base_collection.replace("_", "").isalnum():
            raise ValueError("PG_COLLECTION 只能包含字母、数字和下划线")
        tenant_id = os.getenv("PG_TENANT_ID", "default").strip().lower()
        dimensions = int(os.getenv("PGVECTOR_DIMENSIONS", "512"))
        if dimensions <= 0:
            raise ValueError("PGVECTOR_DIMENSIONS 必须大于 0")
        return cls(
            connection=connection,
            collection=f"{base_collection}_{tenant_key(tenant_id)}",
            dimensions=dimensions,
            tenant_id=tenant_id,
        )

    @property
    def table(self) -> str:
        """表名由 collection 派生，collection 已限制为字母、数字、下划线和租户哈希，可以安全拼进 SQL。"""
        name = self.collection.replace("-", "_")
        if not name.replace("_", "").isalnum():
            raise ValueError("非法的表名")
        return f"pgv_{name}"


def deterministic_document_id(document: Document, storage_namespace: str) -> str:
    source = str(document.metadata.get("source", ""))
    page = str(document.metadata.get("page", ""))
    chunk_index = str(document.metadata.get("chunk_index", ""))
    material = (
        f"{storage_namespace}\0{source}\0{page}\0{chunk_index}\0"
        f"{document.page_content}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_pg_filter(user: User, *, topic: str | None = None) -> dict[str, object]:
    """在 SQL 查询前限制租户和 ACL；不能先召回再在 Python 中删结果。"""
    access: list[dict[str, object]] = [
        {"visibility": {"$eq": "public"}},
        {"owner_id": {"$eq": user.user_id}},
    ]
    if user.dept:
        access.append({"dept": {"$eq": user.dept}})
    access.extend(
        {f"acl_role_{role}": {"$eq": True}} for role in sorted(user.roles)
    )
    clauses: list[dict[str, object]] = [
        {"tenant_id": {"$eq": user.tenant_id}},
        {"$or": access},
    ]
    if topic:
        clauses.append({"topic": {"$eq": topic}})
    return {"$and": clauses}


def filter_to_sql(where: dict[str, Any]) -> tuple[str, list[Any]]:
    """把 Chroma 风格的 where（$and / $or / $eq）翻译成 jsonb 条件与参数。

    所有值都走参数绑定；键名只允许字母、数字、下划线，避免把用户输入拼进 SQL。
    """
    if len(where) != 1:
        raise ValueError("where 的每一层只能有一个运算符或字段")
    ((key, value),) = where.items()
    if key in ("$and", "$or"):
        parts = [filter_to_sql(item) for item in value]
        if not parts:
            raise ValueError(f"{key} 不能为空")
        joiner = " AND " if key == "$and" else " OR "
        return "(" + joiner.join(sql for sql, _ in parts) + ")", [p for _, params in parts for p in params]
    if not key.replace("_", "").isalnum():
        raise ValueError(f"非法的 metadata 字段名：{key!r}")
    ((operator, operand),) = value.items()
    if operator != "$eq":
        raise ValueError(f"暂不支持运算符 {operator}")
    return "metadata @> %s::jsonb", [json.dumps({key: operand}, ensure_ascii=False)]


def sample_documents(settings: PgVectorSettings) -> list[Document]:
    rows = (
        ("RAG 通过检索外部文档再生成，减少无依据回答。", "rag"),
        ("pgvector 是 Postgres 的向量扩展，支持 HNSW 等索引。", "infra"),
        ("向量库选型取决于规模、延迟、隔离、备份和团队运维能力。", "infra"),
    )
    documents = []
    for index, (content, topic) in enumerate(rows, 1):
        document = Document(
            page_content=content,
            metadata={
                "source": f"pgvector-sample-{index}",
                "topic": topic,
                "tenant_id": settings.tenant_id,
            },
        )
        documents.append(attach_acl(document, visibility="public"))
    return documents


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8g}" for value in vector) + "]"


class PgVectorStore:
    """connection 是 psycopg 连接（或测试替身）；embeddings 提供 embed_documents / embed_query。"""

    def __init__(self, connection: Any, table: str, embeddings: Any) -> None:
        if not table.replace("_", "").isalnum():
            raise ValueError("非法的表名")
        self._connection = connection
        self._table = table
        self._embeddings = embeddings

    def add_documents(self, documents: list[Document], *, ids: list[str]) -> None:
        """按确定性 id 幂等写入。"""
        if len(ids) != len(documents):
            raise ValueError("ids 与 documents 数量必须一致")
        vectors = self._embeddings.embed_documents([d.page_content for d in documents])
        sql = (
            f"INSERT INTO {self._table} (id, content, metadata, embedding) "
            "VALUES (%s, %s, %s::jsonb, %s::vector) "
            "ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content, "
            "metadata = EXCLUDED.metadata, embedding = EXCLUDED.embedding"
        )
        with self._connection.cursor() as cursor:
            for doc_id, document, vector in zip(ids, documents, vectors):
                cursor.execute(
                    sql,
                    (doc_id, document.page_content, json.dumps(document.metadata, ensure_ascii=False), _vector_literal(vector)),
                )
        self._connection.commit()

    def similarity_search(self, query: str, *, k: int, filter: dict[str, Any]) -> list[Document]:
        where_sql, params = filter_to_sql(filter)
        sql = (
            f"SELECT content, metadata FROM {self._table} WHERE {where_sql} "
            "ORDER BY embedding <=> %s::vector LIMIT %s"
        )
        params = [*params, _vector_literal(self._embeddings.embed_query(query)), int(k)]
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [Document(content, dict(metadata if isinstance(metadata, dict) else json.loads(metadata))) for content, metadata in rows]


def build_store(settings: PgVectorSettings):
    """扩展安装和 schema 迁移由 DBA/迁移工具完成，应用账号不自动提权。"""
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "缺少可选依赖；安装 requirements-pgvector.txt"
        ) from exc
    from capstone.embedding import get_embeddings

    store = PgVectorStore(psycopg.connect(settings.connection), settings.table, get_embeddings())
    documents = sample_documents(settings)
    ids = [
        deterministic_document_id(document, settings.collection)
        for document in documents
    ]
    store.add_documents(documents, ids=ids)
    return store, len(documents)


def query(store, question: str, user: User, *, topic: str | None = None):
    if not question.strip():
        raise ValueError("question 不能为空")
    return store.similarity_search(
        question,
        k=3,
        filter=build_pg_filter(user, topic=topic),
    )


def migration_sql(settings: PgVectorSettings) -> str:
    """返回迁移模板，由迁移/DBA 账号执行；应用账号不执行。"""
    suffix = hashlib.sha256(settings.table.encode("utf-8")).hexdigest()[:12]
    return (
        "-- 以下由迁移/DBA 账号执行，不由应用启动时自动执行：\n"
        "CREATE EXTENSION IF NOT EXISTS vector;\n\n"
        f"CREATE TABLE IF NOT EXISTS {settings.table} (\n"
        "  id text PRIMARY KEY,\n"
        "  content text NOT NULL,\n"
        "  metadata jsonb NOT NULL,\n"
        f"  embedding vector({settings.dimensions}) NOT NULL\n"
        ");\n\n"
        f"CREATE INDEX IF NOT EXISTS {settings.table}_meta_{suffix} ON {settings.table} USING gin (metadata);\n"
        "-- CREATE INDEX CONCURRENTLY 不能放在事务块内，大表请单独执行：\n"
        f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {settings.table}_hnsw_{suffix} "
        f"ON {settings.table} USING hnsw (embedding vector_cosine_ops);"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("diagnose", "migration", "build", "query"),
        nargs="?",
        default="diagnose",
    )
    parser.add_argument("--question", default="生产向量库如何选型？")
    parser.add_argument("--topic")
    parser.add_argument("--user-id", default="public-reader")
    parser.add_argument("--dept", default="")
    parser.add_argument("--role", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = PgVectorSettings.from_env(
        require_connection=args.command in {"build", "query"}
    )
    print(
        f"tenant={settings.tenant_id}, collection={settings.collection}, "
        f"dimensions={settings.dimensions}, PG_CONN={'configured' if settings.connection else 'missing'}"
    )
    if args.command == "diagnose":
        return 0 if settings.connection else 2
    if args.command == "migration":
        print(migration_sql(settings))
        return 0

    store, count = build_store(settings)
    print(f"幂等写入 {count} 条文档（确定性 ID）")
    if args.command == "build":
        return 0
    user = User(
        args.user_id,
        tenant_id=settings.tenant_id,
        dept=args.dept,
        roles=frozenset(args.role),
    )
    for document in query(store, args.question, user, topic=args.topic):
        print(
            f"[{document.metadata.get('source', 'unknown')}] "
            f"{document.page_content}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
