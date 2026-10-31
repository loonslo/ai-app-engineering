"""原生的递归字符切分：先按最粗的分隔符切，放不下的块再用更细的分隔符切，最后带重叠地合并。

行为对齐常见的 RecursiveCharacterTextSplitter（保留分隔符在块首、去掉首尾空白），
这样“去掉 LangChain”之后，同一份文档切出的块边界尽量保持一致。
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from .contracts import Document


def _split_keep_separator(text: str, separator: str) -> list[str]:
    if separator == "":
        return list(text)
    parts = re.split(f"({re.escape(separator)})", text)
    pieces = [parts[0]] + [parts[i] + parts[i + 1] for i in range(1, len(parts) - 1, 2)]
    if len(parts) % 2 == 0:
        pieces.append(parts[-1])
    return [piece for piece in pieces if piece != ""]


def _join(pieces: list[str]) -> str | None:
    text = "".join(pieces).strip()
    return text or None


def _merge(pieces: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """把小块合并到不超过 chunk_size；相邻块之间保留不超过 chunk_overlap 的重叠。"""
    chunks: list[str] = []
    current: list[str] = []
    total = 0
    for piece in pieces:
        length = len(piece)
        if total + length > chunk_size and current:
            joined = _join(current)
            if joined is not None:
                chunks.append(joined)
            while total > chunk_overlap or (total + length > chunk_size and total > 0):
                total -= len(current[0])
                current = current[1:]
        current.append(piece)
        total += length
    joined = _join(current)
    if joined is not None:
        chunks.append(joined)
    return chunks


def split_text(text: str, *, chunk_size: int, chunk_overlap: int, separators: Sequence[str]) -> list[str]:
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_size 必须为正，chunk_overlap 必须在 [0, chunk_size) 内")
    return _recurse(text, list(separators), chunk_size, chunk_overlap)


def _recurse(text: str, separators: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    separator, rest = separators[-1], []
    for index, candidate in enumerate(separators):
        if candidate == "":
            separator = candidate
            break
        if re.search(re.escape(candidate), text):
            separator, rest = candidate, separators[index + 1 :]
            break
    result: list[str] = []
    small: list[str] = []
    for piece in _split_keep_separator(text, separator):
        if len(piece) < chunk_size:
            small.append(piece)
            continue
        if small:
            result.extend(_merge(small, chunk_size, chunk_overlap))
            small = []
        result.extend(_recurse(piece, rest, chunk_size, chunk_overlap) if rest else [piece])
    if small:
        result.extend(_merge(small, chunk_size, chunk_overlap))
    return result


def split_documents(
    documents: list[Document], *, chunk_size: int, chunk_overlap: int, separators: Sequence[str]
) -> list[Document]:
    """每个切出来的块继承原文档 metadata 的副本。"""
    chunks: list[Document] = []
    for document in documents:
        for piece in split_text(
            document.page_content, chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=separators
        ):
            chunks.append(Document(piece, dict(document.metadata)))
    return chunks
