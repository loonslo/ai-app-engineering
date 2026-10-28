"""章节 2.1 · 多种文件格式的加载与切分（原生实现）

==========================================================
load_split.py 只读 txt。本文件把常见格式统一成一个入口 load_and_split(path)：

1. 加载：按文件扩展名选择原生加载器（txt、md、pdf、docx、csv、json）
2. 切分：原生递归字符切分器（基于 common.ZH_SEPARATORS），保留 source、page、index 元数据

依赖：
  已有：pypdf（标准课程依赖，按页解析 PDF）
  可选：.docx → docx2txt（缺失时给出友好提示）

运行：python tools/run_chapter.py 2.1 load_split_formats.py
==========================================================
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

try:
    from common import LONG_DOC, ZH_SEPARATORS
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from common import LONG_DOC, ZH_SEPARATORS


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    source: str
    page: int | None = None
    index: int = 1

    @property
    def page_content(self) -> str:
        return self.text

    @property
    def metadata(self) -> dict:
        m: dict = {"source": self.source, "index": self.index}
        if self.page is not None:
            m["page"] = self.page
        return m

    def __getitem__(self, item: str):
        if item == "text":
            return self.text
        if item == "source":
            return self.source
        if item == "page":
            return self.page
        if item == "index":
            return self.index
        raise KeyError(item)

    def get(self, item: str, default=None):
        try:
            return self[item]
        except KeyError:
            return default


def split_text_recursive(
    text: str,
    chunk_size: int = 120,
    overlap: int = 20,
    separators: list[str] | None = None,
) -> list[str]:
    """原生递归字符切分器。"""
    if separators is None:
        separators = list(ZH_SEPARATORS)

    if not text.strip():
        return []
    if len(text) <= chunk_size:
        return [text]

    chosen_sep = ""
    next_separators: list[str] = []
    for i, sep in enumerate(separators):
        if sep == "":
            chosen_sep = ""
            next_separators = []
            break
        if sep in text:
            chosen_sep = sep
            next_separators = separators[i + 1 :]
            break

    if chosen_sep == "":
        step = max(1, chunk_size - overlap)
        chunks: list[str] = []
        for start in range(0, len(text), step):
            piece = text[start : start + chunk_size]
            if piece.strip():
                chunks.append(piece)
            if start + chunk_size >= len(text):
                break
        return chunks

    splits = text.split(chosen_sep)
    docs: list[str] = []
    current_doc: list[str] = []
    current_len = 0

    for split in splits:
        if not split:
            continue
        split_len = len(split) + (len(chosen_sep) if current_doc else 0)
        if split_len > chunk_size:
            if current_doc:
                merged = chosen_sep.join(current_doc)
                if merged.strip():
                    docs.append(merged)
                current_doc = []
                current_len = 0
            sub_chunks = split_text_recursive(
                split, chunk_size, overlap, next_separators
            )
            docs.extend(sub_chunks)
        elif current_len + split_len <= chunk_size:
            current_doc.append(split)
            current_len += split_len
        else:
            if current_doc:
                merged = chosen_sep.join(current_doc)
                if merged.strip():
                    docs.append(merged)
            overlap_docs: list[str] = []
            overlap_len = 0
            for prev in reversed(current_doc):
                needed = len(prev) + (len(chosen_sep) if overlap_docs else 0)
                if overlap_len + needed <= overlap:
                    overlap_docs.insert(0, prev)
                    overlap_len += needed
                else:
                    break
            current_doc = overlap_docs + [split]
            current_len = sum(len(d) for d in current_doc) + len(chosen_sep) * max(
                0, len(current_doc) - 1
            )

    if current_doc:
        merged = chosen_sep.join(current_doc)
        if merged.strip():
            docs.append(merged)

    return docs


def load_raw_sections(path: str | Path) -> list[dict]:
    """按文件扩展名读取原始内容，返回列表 [{"text": str, "source": str, "page": int | None}]。"""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")

    ext = p.suffix.lower()
    source_name = p.name

    # .pdf：按页读取
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as err:
            raise RuntimeError("读取 PDF 需要 pypdf 库：pip install pypdf") from err
        reader = PdfReader(str(p))
        sections = []
        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                sections.append({"text": text, "source": source_name, "page": i})
        return sections

    # .docx：使用 docx2txt
    if ext == ".docx":
        try:
            import docx2txt

            text = docx2txt.process(str(p)) or ""
            return [{"text": text, "source": source_name, "page": None}]
        except ImportError as err:
            raise RuntimeError(
                "读取 .docx 文件需要安装 docx2txt：pip install docx2txt"
            ) from err

    # .csv：每行一条记录
    if ext == ".csv":
        sections = []
        with open(p, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                line_text = ", ".join(f"{k}: {v}" for k, v in row.items())
                if line_text.strip():
                    sections.append({
                        "text": line_text,
                        "source": source_name,
                        "page": None,
                    })
        return sections

    # .json / .jsonl
    if ext in (".json", ".jsonl"):
        with open(p, encoding="utf-8", errors="replace") as f:
            if ext == ".jsonl":
                data = [json.loads(line) for line in f if line.strip()]
            else:
                data = json.load(f)
        if isinstance(data, list):
            return [
                {
                    "text": json.dumps(item, ensure_ascii=False),
                    "source": source_name,
                    "page": None,
                }
                for item in data
            ]
        return [
            {
                "text": json.dumps(data, ensure_ascii=False),
                "source": source_name,
                "page": None,
            }
        ]

    # .md / .txt 及其他纯文本
    text = p.read_text(encoding="utf-8", errors="replace")
    return [{"text": text, "source": source_name, "page": None}]


def load_and_split(
    path: str | Path,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[DocumentChunk]:
    """统一入口：按格式加载并切分，保留 source, page, index 元数据。"""
    sections = load_raw_sections(path)
    print(f"[加载] {path} → {len(sections)} 个原始分段/页面")

    result_chunks: list[DocumentChunk] = []
    chunk_idx = 1
    for sec in sections:
        pieces = split_text_recursive(
            sec["text"],
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )
        for piece in pieces:
            result_chunks.append(
                DocumentChunk(
                    text=piece,
                    source=sec["source"],
                    page=sec["page"],
                    index=chunk_idx,
                )
            )
            chunk_idx += 1

    print(f"[切分] → {len(result_chunks)} 个 chunk（chunk_size={chunk_size}）")
    return result_chunks


if __name__ == "__main__":
    chunks = load_and_split(str(LONG_DOC), chunk_size=120, chunk_overlap=20)
    for c in chunks[:3]:
        print(f"\n--- 块 {c.index}（{len(c.text)} 字，source={c.source}）---")
        print(c.text[:80])

    readme_path = Path(__file__).with_name("README.md")
    md_chunks = load_and_split(str(readme_path), chunk_size=300)
    print("\n第一个 Markdown 块元数据：", md_chunks[0].metadata)
