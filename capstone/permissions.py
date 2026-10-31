"""文档 ACL：默认拒绝，并在向量查询发出前构造存储层过滤条件。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .contracts import Document

_PRINCIPAL = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def _principal(value: str, field_name: str, *, allow_empty: bool = True) -> str:
    normalized = value.strip().lower()
    if not normalized and allow_empty:
        return ""
    if not _PRINCIPAL.fullmatch(normalized):
        raise ValueError(f"{field_name} 格式非法")
    return normalized


@dataclass(frozen=True)
class User:
    """由可信 token claims 构造的当前身份。"""

    user_id: str
    tenant_id: str = "default"
    dept: str = ""
    roles: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "user_id", _principal(self.user_id, "user_id", allow_empty=False)
        )
        object.__setattr__(
            self,
            "tenant_id",
            _principal(self.tenant_id, "tenant_id", allow_empty=False),
        )
        object.__setattr__(self, "dept", _principal(self.dept, "dept"))
        object.__setattr__(
            self,
            "roles",
            frozenset(_principal(role, "role", allow_empty=False) for role in self.roles),
        )


PUBLIC_USER = User("public-reader", roles=frozenset({"public"}))


def attach_acl(
    doc: Document,
    *,
    visibility: str = "restricted",
    dept: str = "",
    allow_roles: tuple[str, ...] | list[str] = (),
    owner_id: str = "",
) -> Document:
    """把可供 Chroma 过滤的标量 ACL 写入 metadata。"""
    visibility = visibility.strip().lower()
    if visibility not in {"public", "restricted"}:
        raise ValueError("visibility 只能是 public 或 restricted")
    normalized_dept = _principal(dept, "dept")
    normalized_owner = _principal(owner_id, "owner_id")
    normalized_roles = sorted(
        {_principal(role, "role", allow_empty=False) for role in allow_roles}
    )
    metadata = dict(doc.metadata)
    metadata.update(
        {
            "visibility": visibility,
            "dept": normalized_dept,
            "owner_id": normalized_owner,
            "allow_roles": ",".join(normalized_roles),
        }
    )
    for role in normalized_roles:
        metadata[f"acl_role_{role}"] = True
    doc.metadata = metadata
    return doc


def can_see(meta: dict[str, Any], user: User) -> bool:
    """与存储层过滤器相同语义的本地判定，用于 BM25 预筛选和测试。"""
    if meta.get("visibility") == "public":
        return True
    if meta.get("visibility") != "restricted":
        return False
    if meta.get("owner_id") and meta["owner_id"] == user.user_id:
        return True
    if user.dept and meta.get("dept") == user.dept:
        return True
    return any(meta.get(f"acl_role_{role}") is True for role in user.roles)


def build_chroma_filter(user: User) -> dict[str, Any]:
    """在相似度查询前应用的 Chroma `where` 过滤器。"""
    rules: list[dict[str, Any]] = [{"visibility": {"$eq": "public"}}]
    rules.append({"owner_id": {"$eq": user.user_id}})
    if user.dept:
        rules.append({"dept": {"$eq": user.dept}})
    rules.extend(
        {f"acl_role_{role}": {"$eq": True}} for role in sorted(user.roles)
    )
    return {"$or": rules}


class PermissionRetriever:
    """兼容旧接口；实际查询由 KnowledgeBase 在存储层预过滤。"""

    def __init__(self, kb: Any, user: User, top_k: int = 4) -> None:
        self.kb = kb
        self.user = user
        self.top_k = top_k

    def invoke(self, query: str) -> list[Document]:
        return self.kb.retrieve(query, user=self.user, top_k=self.top_k)


def permission_chain(kb: Any, user: User):
    """返回 ask(question) -> 回答文本 的普通函数：以 user 的身份问知识库。"""

    def ask(question: str) -> str:
        return kb.answer(question, user=user)

    return ask


if __name__ == "__main__":
    finance = attach_acl(
        Document(page_content="财务"),
        dept="finance",
        allow_roles=("finance",),
    )
    public = attach_acl(Document(page_content="公开"), visibility="public")
    alice = User(
        "alice",
        tenant_id="acme",
        dept="finance",
        roles=frozenset({"employee", "finance"}),
    )
    bob = User(
        "bob",
        tenant_id="acme",
        dept="marketing",
        roles=frozenset({"employee"}),
    )
    print("财务文档 → alice 可见：", can_see(finance.metadata, alice))
    print("财务文档 → bob   可见：", can_see(finance.metadata, bob))
    print("公开文档 → bob   可见：", can_see(public.metadata, bob))
    print("存储层过滤条件：", build_chroma_filter(alice))
