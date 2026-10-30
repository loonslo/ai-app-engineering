"""章节 2.6 · 处理 PDF 并标注来源（原生实现）

==========================================================
本章把 RAG 升级为支持页码元数据与来源溯源的形式：
1. 支持 .txt 和 .pdf，按页加载提取文本并保留页码元数据
2. 原生实现 format_context 与 verify_citations，核对模型回答里的出处
3. 封装 build_retriever 与 build_rag_chain，产出带 page_content 与 metadata 的 Document 对象
4. 纯原生实现，下游评测章节完全兼容

运行：python tools/run_chapter.py 2.6
==========================================================
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 复用 2.1 递归切分与 2.2 向量检索索引组件
SPLIT_DIR = Path(__file__).resolve().parents[1] / "2.1-load-split"
EMBED_DIR = Path(__file__).resolve().parents[1] / "2.2-embed-retrieve"
if str(SPLIT_DIR) not in sys.path:
    sys.path.insert(0, str(SPLIT_DIR))
if str(EMBED_DIR) not in sys.path:
    sys.path.insert(0, str(EMBED_DIR))
from embed_retrieve import VectorIndex  # noqa: E402
from load_split import ZH_SEPARATORS, split_text_recursive  # noqa: E402

try:
    from common import (
        SAMPLE_DOC,
        chat_model_name,
        embed_texts,
        get_openai_client,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from common import (
        SAMPLE_DOC,
        chat_model_name,
        embed_texts,
        get_openai_client,
    )


# ----------------------------------------------------------
# 0. 轻量通用 Document 结构 (完全兼容下游 3.2, 3.3, 3.5, 5.1, 5.8)
# ----------------------------------------------------------


@dataclass
class Document:
    """轻量 Document 数据结构，提供 page_content 与 metadata 属性。"""

    page_content: str
    metadata: dict[str, Any]

    @property
    def text(self) -> str:
        return self.page_content

    @property
    def source(self) -> str:
        return self.metadata.get("source", "")

    @property
    def page(self) -> int | None:
        return self.metadata.get("page")

    def __getitem__(self, key: str) -> Any:
        if key in ("text", "page_content"):
            return self.page_content
        return self.metadata[key]

    def get(self, key: str, default: Any = None) -> Any:
        if key in ("text", "page_content"):
            return self.page_content
        return self.metadata.get(key, default)


# ----------------------------------------------------------
# 1. Gate 闭卷规范函数
# ----------------------------------------------------------


def load_pages(pages: list[tuple[int, str]], source: str) -> list[dict]:
    """把 (页码, 文本) 转成带来源的片段字典列表。"""
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source 必须是非空字符串")
    if not isinstance(pages, list):
        raise ValueError("pages 必须是列表")

    result = []
    for item in pages:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(f"页数据格式错误：{item}")
        page_num, text = item
        if not isinstance(page_num, int) or page_num < 1:
            raise ValueError(f"页码必须是 >= 1 的整数：{page_num}")
        if not isinstance(text, str):
            raise ValueError("页文本必须是字符串")
        if text.strip():
            result.append({"text": text, "source": source, "page": page_num})
    return result


def _extract_doc_fields(doc: Any) -> tuple[str, str, int | None]:
    if isinstance(doc, dict):
        if "text" not in doc or not isinstance(doc["text"], str):
            raise ValueError("doc 必须包含字符串类型的 text")
        if "source" not in doc or not isinstance(doc["source"], str):
            raise ValueError("doc 必须包含字符串类型的 source")
        page = doc.get("page")
        if page is not None and (not isinstance(page, int) or page < 1):
            raise ValueError("page 必须是 >= 1 的整数或 None")
        return doc["source"], doc["text"], page
    if hasattr(doc, "page_content") and hasattr(doc, "metadata"):
        metadata = getattr(doc, "metadata", {})
        src = metadata.get("source", "")
        page = metadata.get("page")
        text = getattr(doc, "page_content", "")
        if not isinstance(src, str):
            raise ValueError("source 必须是字符串")
        if not isinstance(text, str):
            raise ValueError("text 必须是字符串")
        if page is not None and (not isinstance(page, int) or page < 1):
            raise ValueError("page 必须是 >= 1 的整数或 None")
        return src, text, page
    raise ValueError(f"不受支持的 doc 类型：{type(doc)}")


def format_context(docs: list[Any]) -> str:
    """把片段拼成带页码标签的上下文。兼容 dict 与 Document。"""
    if not isinstance(docs, list):
        raise ValueError("docs 必须是列表")
    if not docs:
        return ""

    parts = []
    for d in docs:
        src, text, page = _extract_doc_fields(d)
        if page is not None:
            tag = f"[来源：{src} 第{page}页]"
        else:
            tag = f"[来源：{src}]"
        parts.append(f"{tag}\n{text}")
    return "\n\n".join(parts)


def verify_citations(answer: str, docs: list[Any]) -> dict:
    """核对答案里的【来源：...】标记是否都在 docs 中。兼容 dict 与 Document。"""
    if not isinstance(answer, str):
        raise ValueError("answer 必须是字符串")
    if not isinstance(docs, list):
        raise ValueError("docs 必须是列表")

    valid_tags = set()
    for d in docs:
        src, _, page = _extract_doc_fields(d)
        if page is not None:
            valid_tags.add(f"{src}#p{page}")
        else:
            valid_tags.add(src)

    raw_citations = re.findall(r"【来源：([^】]+)】", answer)
    cited: list[str] = []
    for raw in raw_citations:
        raw = raw.strip()
        m = re.match(r"^(\S+?)(?:\s+第(\d+)页)?$", raw)
        if m:
            src, page_str = m.group(1), m.group(2)
            tag = f"{src}#p{page_str}" if page_str else src
        else:
            tag = raw
        if tag not in cited:
            cited.append(tag)

    unknown = [t for t in cited if t not in valid_tags]
    ok = len(cited) > 0 and len(unknown) == 0
    return {"ok": ok, "cited": cited, "unknown": unknown}


# ----------------------------------------------------------
# 2. 原生文档解析与 RAG 检索器 / 链路
# ----------------------------------------------------------


def load_document(file_path: str | Path) -> list[dict]:
    """支持 .txt 和 .pdf，按页或段落返回 dict 列表，并带上来源 metadata。"""
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    ext = p.suffix.lower()
    source_name = p.name

    if ext == ".txt":
        text = p.read_text(encoding="utf-8", errors="replace")
        return [{"text": text, "source": source_name, "page": None}]
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("读取 PDF 需要安装 pypdf：pip install pypdf") from exc
        reader = PdfReader(str(p))
        docs = []
        for i, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                docs.append({"text": text, "source": source_name, "page": i})
        return docs
    raise ValueError(f"暂不支持的文件类型：{ext}")


class NativeRetriever:
    """基于 2.2 VectorIndex 向量索引的纯 Python 检索器。返回 list[Document]。"""

    def __init__(self, chunks: list[Document], k: int = 4):
        self.chunks = chunks
        self.k = k
        self.index = VectorIndex()
        if chunks:
            ids = [f"c_{i}" for i in range(len(chunks))]
            texts = [c.page_content for c in chunks]
            vectors = embed_texts(texts)
            self.index.add(ids, vectors)

    def invoke(self, query: str) -> list[Document]:
        if not self.chunks:
            return []
        q_vec = embed_texts([query])[0]
        results = self.index.search(q_vec, k=self.k)
        return [self.chunks[int(r["id"].split("_")[1])] for r in results]

    def __call__(self, query: str) -> list[Document]:
        return self.invoke(query)


def build_retriever(file_path: str | Path, k: int = 4) -> NativeRetriever:
    """加载 → 切分 → 向量化 → 返回原生 Document 检索器。"""
    docs = load_document(file_path)
    if not docs:
        raise ValueError("没解析出任何文本（PDF 可能是扫描件，没有文字层）")

    # 复用 2.1 split_text_recursive 与 ZH_SEPARATORS 进行保边界分块
    chunks: list[Document] = []
    chunk_idx = 1
    for doc in docs:
        text = doc["text"]
        pieces = split_text_recursive(
            text,
            chunk_size=300,
            overlap=50,
            separators=list(ZH_SEPARATORS),
        )
        for piece in pieces:
            if piece.strip():
                chunks.append(
                    Document(
                        page_content=piece,
                        metadata={
                            "source": doc["source"],
                            "page": doc.get("page"),
                            "index": chunk_idx,
                        },
                    )
                )
                chunk_idx += 1

    return NativeRetriever(chunks, k=k)


class NativeRagChain:
    """原生 RAG 问答链路。"""

    def __init__(self, retriever: NativeRetriever, temperature: float = 0.0):
        self.retriever = retriever
        self.temperature = temperature

    def invoke(self, question: str) -> str:
        docs = self.retriever.invoke(question)
        context = format_context(docs)

        system_prompt = (
            "你是严谨的知识库助手。请依据下面的上下文回答问题：\n"
            "- 只要有相关信息（哪怕只是部分），就基于它尽量回答，并在结尾用【来源：文件名 第X页】标注出处；\n"
            "- 只有完全没有相关信息时，才回答'文档中没有提到'。"
        )
        user_prompt = f"上下文：\n{context}\n\n问题：{question}"

        client = get_openai_client()
        model = chat_model_name()
        resp = client.chat.completions.create(
            model=model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = resp.choices[0].message.content
        return content if content is not None else ""


def build_rag_chain(retriever: Any, temperature: float = 0.0) -> NativeRagChain:
    """组装原生 RAG 链。"""
    return NativeRagChain(retriever, temperature=temperature)


if __name__ == "__main__":
    print("=== 2.6 PDF 与来源追踪演示 ===")
    demo_pages = [(1, "退款3个工作日到账。"), (2, "付款后48小时发货。")]
    loaded = load_pages(demo_pages, "manual.pdf")
    ctx = format_context(loaded)
    print("上下文格式化预览：\n" + ctx)

    test_ans = "退款一般3个工作日处理完毕。【来源：manual.pdf 第1页】"
    v = verify_citations(test_ans, loaded)
    print(f"\n引用核对结果：ok={v['ok']}, cited={v['cited']}, unknown={v['unknown']}")

    # 加载示例文档并测试 Retriever
    if Path(SAMPLE_DOC).is_file():
        retriever = build_retriever(SAMPLE_DOC, k=2)
        print(f"\n检索器构建完成：已索引 {len(retriever.chunks)} 个 Document 片段。")
        sample_hits = retriever.invoke("退款")
        print(f"示例文档检索测试（'退款'）：召回 {len(sample_hits)} 条片段")
        for i, hit in enumerate(sample_hits, 1):
            src = hit.metadata.get("source")
            pg = hit.metadata.get("page")
            print(f"  [{i}] source={src} page={pg}: {hit.page_content[:30]}...")
