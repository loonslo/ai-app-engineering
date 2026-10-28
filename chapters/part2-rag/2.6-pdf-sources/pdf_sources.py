"""章节 2.6 · 处理 PDF 并标注来源（原生实现）

==========================================================
本章把 RAG 升级为支持页码元数据与来源溯源的形式：
1. 支持 .txt 和 .pdf，按页加载提取文本并保留页码元数据
2. 原生实现 format_context 与 verify_citations，核对模型回答里的出处
3. 封装 build_retriever 与 build_rag_chain，供后续评测章节复用
4. 纯原生实现，不依赖 LangChain

运行：python tools/run_chapter.py 2.6
==========================================================
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from common import (
        SAMPLE_DOC,
        chat_model_name,
        embed_texts,
        get_openai_client,
    )
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from common import (
        SAMPLE_DOC,
        chat_model_name,
        embed_texts,
        get_openai_client,
    )


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


def _validate_docs(docs: list[dict]) -> None:
    if not isinstance(docs, list):
        raise ValueError("docs 必须是列表")
    for doc in docs:
        if not isinstance(doc, dict):
            raise ValueError("doc 必须是字典")
        if "text" not in doc or not isinstance(doc["text"], str):
            raise ValueError("doc 必须包含字符串类型的 text")
        if "source" not in doc or not isinstance(doc["source"], str):
            raise ValueError("doc 必须包含字符串类型的 source")
        page = doc.get("page")
        if page is not None and (not isinstance(page, int) or page < 1):
            raise ValueError("page 必须是 >= 1 的整数或 None")


def format_context(docs: list[dict]) -> str:
    """把片段拼成带页码标签的上下文。"""
    _validate_docs(docs)
    if not docs:
        return ""

    parts = []
    for d in docs:
        src = d["source"]
        page = d.get("page")
        if page is not None:
            tag = f"[来源：{src} 第{page}页]"
        else:
            tag = f"[来源：{src}]"
        parts.append(f"{tag}\n{d['text']}")
    return "\n\n".join(parts)


def verify_citations(answer: str, docs: list[dict]) -> dict:
    """核对答案里的【来源：...】标记是否都在 docs 中。"""
    if not isinstance(answer, str):
        raise ValueError("answer 必须是字符串")
    _validate_docs(docs)

    valid_tags = set()
    for d in docs:
        src = d["source"]
        page = d.get("page")
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
    """基于原生向量与余弦相似度的纯 Python 检索器。"""

    def __init__(self, chunks: list[dict], k: int = 4):
        self.chunks = chunks
        self.k = k
        self.texts = [c["text"] for c in chunks]
        self.vectors = embed_texts(self.texts) if self.texts else []

    def invoke(self, query: str) -> list[dict]:
        if not self.chunks or not self.vectors:
            return []
        q_vec = embed_texts([query])[0]
        # 计算余弦相似度（embed_texts 默认归一化，点积即余弦值）
        scores = []
        for idx, v in enumerate(self.vectors):
            dot = sum(a * b for a, b in zip(q_vec, v))
            scores.append((dot, idx))
        scores.sort(key=lambda x: x[0], reverse=True)
        top = [self.chunks[idx] for _, idx in scores[: self.k]]
        return top

    def __call__(self, query: str) -> list[dict]:
        return self.invoke(query)


def build_retriever(file_path: str | Path, k: int = 4) -> NativeRetriever:
    """加载 → 切分 → 向量化 → 返回检索器。"""
    docs = load_document(file_path)
    if not docs:
        raise ValueError("没解析出任何文本（PDF 可能是扫描件，没有文字层）")

    # 简单原生分块
    chunks: list[dict] = []
    chunk_idx = 1
    chunk_size = 300
    overlap = 50
    step = chunk_size - overlap
    for doc in docs:
        text = doc["text"]
        for start in range(0, len(text), step):
            piece = text[start : start + chunk_size]
            if piece.strip():
                chunks.append({
                    "text": piece,
                    "source": doc["source"],
                    "page": doc.get("page"),
                    "index": chunk_idx,
                })
                chunk_idx += 1
            if start + chunk_size >= len(text):
                break

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

        try:
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
            return resp.choices[0].message.content or "文档中没有提到"
        except Exception:
            # 离线环境或未配置模型时给出可读兜底，不崩溃
            return f"[离线模拟回答：依据检索到 {len(docs)} 个片段] 【来源：{docs[0]['source']}" + (
                f" 第{docs[0]['page']}页" if docs and docs[0].get("page") else ""
            ) + "】"


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

    # 尝试加载示例文档
    if Path(SAMPLE_DOC).is_file():
        retriever = build_retriever(SAMPLE_DOC, k=2)
        print(f"\n检索测试完成：建库索引了 {len(retriever.chunks)} 个片段。")
