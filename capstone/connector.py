"""幂等、租户隔离的增量文档同步。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from . import config as C
from .knowledge_base import (
    SUPPORTED_SUFFIXES,
    _load_one,
    make_chunk_id,
    source_version,
)
from .text_split import split_documents
from .vector_store import ChromaStore


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _scan_source(docs_dir: Path) -> dict[str, str]:
    return {
        path.resolve().relative_to(docs_dir.resolve()).as_posix(): source_version(path)
        for path in sorted(docs_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    }


def _load_state(state_path: Path) -> dict[str, str]:
    if not state_path.exists():
        return {}
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in payload.items()
    ):
        raise ValueError(f"同步状态损坏：{state_path}")
    return payload


def _save_state(state_path: Path, state: dict[str, str]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_suffix(f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, state_path)


class SyncLock:
    """单机同步互斥锁；分布式部署应替换为队列分区或分布式锁。"""

    def __init__(self, path: Path, timeout_seconds: float = 30) -> None:
        self.path = path
        self.timeout_seconds = timeout_seconds
        self._fd: int | None = None

    def __enter__(self) -> "SyncLock":
        deadline = time.monotonic() + self.timeout_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self._fd = os.open(
                    self.path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                os.write(self._fd, str(os.getpid()).encode())
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"获取同步锁超时：{self.path}") from None
                time.sleep(0.1)

    def __exit__(self, *_: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
        self.path.unlink(missing_ok=True)


def _diff(
    old: dict[str, str],
    new: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    added = sorted(set(new) - set(old))
    deleted = sorted(set(old) - set(new))
    updated = sorted(
        source for source in set(old) & set(new) if old[source] != new[source]
    )
    return added, updated, deleted


def _chunks_of(
    *,
    source_id: str,
    content_hash: str,
    docs_dir: Path,
    tenant_id: str,
):
    documents = _load_one(
        docs_dir / Path(source_id),
        docs_root=docs_dir,
        tenant_id=tenant_id,
    )
    chunks = split_documents(
        documents,
        chunk_size=C.CHUNK_SIZE,
        chunk_overlap=C.CHUNK_OVERLAP,
        separators=C.ZH_SEPARATORS,
    )
    ids: list[str] = []
    page_indexes: dict[int, int] = {}
    for chunk in chunks:
        page = int(chunk.metadata.get("page", 0))
        index = page_indexes.get(page, 0)
        page_indexes[page] = index + 1
        chunk_id = make_chunk_id(
            tenant_id=tenant_id,
            source_id=source_id,
            content_hash=content_hash,
            page=page,
            chunk_index=index,
        )
        chunk.metadata.update(
            {
                "chunk_id": chunk_id,
                "chunk_index": index,
                "content_hash": content_hash,
            }
        )
        ids.append(chunk_id)
    return chunks, ids


def sync(
    *,
    tenant_id: str = "default",
    docs_dir: Path | None = None,
    persist_dir: Path | None = None,
) -> dict[str, int]:
    """写入新版本后清理旧版本，checkpoint 仅在全部操作成功后原子提交。"""
    C.tenant_key(tenant_id)
    source_dir = (docs_dir or C.DOCS_DIR).resolve()
    vector_dir = (persist_dir or C.tenant_chroma_dir(tenant_id)).resolve()
    tenant_dir = C.tenant_data_dir(tenant_id)
    state_path = tenant_dir / "sync_state.json"
    lock_path = tenant_dir / ".sync.lock"
    if not source_dir.is_dir():
        raise FileNotFoundError(f"文档目录不存在：{source_dir}")

    with SyncLock(lock_path):
        old = _load_state(state_path)
        new = _scan_source(source_dir)
        added, updated, deleted = _diff(old, new)
        vector_dir.parent.mkdir(parents=True, exist_ok=True)
        store = ChromaStore(vector_dir, C.get_embeddings())

        for source_id in added + updated:
            chunks, ids = _chunks_of(
                source_id=source_id,
                content_hash=new[source_id],
                docs_dir=source_dir,
                tenant_id=tenant_id,
            )
            if chunks:
                store.add_documents(chunks, ids=ids)
            if source_id in updated:
                store.delete(
                    where={
                        "$and": [
                            {"source_id": {"$eq": source_id}},
                            {"content_hash": {"$ne": new[source_id]}},
                        ]
                    }
                )

        for source_id in deleted:
            store.delete(where={"source_id": {"$eq": source_id}})

        _save_state(state_path, new)
        from .cache import answer_cache

        answer_cache.invalidate_tenant(tenant_id)
    stats = {"新增": len(added), "更新": len(updated), "删除": len(deleted)}
    print(f"租户 {tenant_id} 增量同步完成：{stats}")
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default="default")
    parser.add_argument("--docs-dir", type=Path)
    args = parser.parse_args(argv)
    sync(tenant_id=args.tenant, docs_dir=args.docs_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
