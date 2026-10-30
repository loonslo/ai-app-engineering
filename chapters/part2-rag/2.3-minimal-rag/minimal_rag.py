"""章节 2.3 · 最小 RAG：引用与拒答（原生实现）

==========================================================
本章把检索与大模型生成串成完整问答：
1. 原生流程：检索 → 预算过滤与组装上下文 → OpenAI-compatible SDK 聊天补全
2. 引用格式规范：引用来源标记 `source#index`（如 test_doc.txt#1）
3. 严格拒答：当检索结果为空或相似度不足时，直接拒答且不附带来源
4. 纯原生实现，不依赖 LangChain LCEL 黑盒包装；真实调用由 --live 开启

运行：python tools/run_chapter.py 2.3 minimal_rag.py [--live]
==========================================================
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

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

# 复用 2.2 向量检索索引与 2.12 上下文装配组件
EMBED_DIR = Path(__file__).resolve().parents[1] / "2.2-embed-retrieve"
CONTEXT_ENG_DIR = Path(__file__).resolve().parents[1] / "2.12-context-engineering"
if str(EMBED_DIR) not in sys.path:
    sys.path.insert(0, str(EMBED_DIR))
if str(CONTEXT_ENG_DIR) not in sys.path:
    sys.path.insert(0, str(CONTEXT_ENG_DIR))
from context_engineering import Section, assemble_context  # noqa: E402
from embed_retrieve import VectorIndex  # noqa: E402


# ----------------------------------------------------------
# 1. Gate 闭卷规范函数
# ----------------------------------------------------------


def format_context(docs: list[dict], max_chars: int | None = None) -> str:
    """把检索片段拼成带来源标记的上下文。"""
    if max_chars is not None and max_chars < 0:
        raise ValueError("max_chars 不能小于 0")
    if not isinstance(docs, list):
        raise ValueError("docs 必须是列表")

    for d in docs:
        if not isinstance(d, dict):
            raise ValueError("doc 必须是字典")
        if "text" not in d or "source" not in d:
            raise ValueError("doc 缺少 text 或 source 字段")
        if not isinstance(d["text"], str) or not isinstance(d["source"], str):
            raise ValueError("text 和 source 必须是字符串")

    if not docs:
        return ""

    parts: list[str] = []
    total_len = 0
    for d in docs:
        block = f"[{d['source']}]\n{d['text']}"
        needed = len(block) + (2 if parts else 0)
        if max_chars is not None and total_len + needed > max_chars:
            continue
        parts.append(block)
        total_len += needed

    return "\n\n".join(parts)


def answer_with_rag(
    question: str,
    retrieve_fn: Callable[[str], list[dict]],
    chat_fn: Callable[[list[dict]], str],
    max_context_chars: int = 1000,
) -> dict:
    """最小 RAG：检索 → 拼上下文 → 生成 → 引用/拒答。"""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("问题不能为空")

    try:
        retrieved = retrieve_fn(question)
    except Exception:
        return {
            "answer": "检索发生异常，暂时无法回答。",
            "sources": [],
            "refused": True,
            "error": "retrieval_error",
        }

    if not retrieved:
        return {
            "answer": "文档中没有提到。",
            "sources": [],
            "refused": True,
            "error": None,
        }

    # 按预算容纳片段
    included_docs: list[dict] = []
    total_len = 0
    for d in retrieved:
        if not isinstance(d, dict) or "text" not in d or "source" not in d:
            continue
        block = f"[{d['source']}]\n{d['text']}"
        needed = len(block) + (2 if included_docs else 0)
        if total_len + needed <= max_context_chars:
            included_docs.append(d)
            total_len += needed
        else:
            break

    if not included_docs:
        return {
            "answer": "文档中没有提到。",
            "sources": [],
            "refused": True,
            "error": None,
        }

    sources: list[str] = []
    for d in included_docs:
        src = d["source"]
        if src not in sources:
            sources.append(src)

    # 复用 2.12 assemble_context 组装上下文
    sections = [
        Section(
            name=d["source"],
            text=f"[{d['source']}]\n{d['text']}",
            kind="dynamic",
            priority=100 - i,
        )
        for i, d in enumerate(included_docs)
    ]
    assembled = assemble_context(sections, budget=max_context_chars)
    context_str = assembled.text
    system_prompt = (
        "你是严谨的知识库问答助手。\n"
        "请依据上下文回答问题。如果上下文没有提供足够证据，必须明确拒答回答'文档中没有提到。'，不编造内容。\n"
        "当有明确依据时，回答结尾请标注引用片段，格式形如 [source#index] 或直接列出来源。"
    )
    user_prompt = f"上下文：\n{context_str}\n\n问题：{question}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw_ans = chat_fn(messages)
    except TimeoutError:
        return {
            "answer": "模型调用超时，请稍后重试。",
            "sources": [],
            "refused": True,
            "error": "timeout",
        }
    except Exception as exc:
        return {
            "answer": f"模型调用失败：{exc}",
            "sources": [],
            "refused": True,
            "error": "model_error",
        }

    if not isinstance(raw_ans, str) or not raw_ans.strip():
        return {
            "answer": "模型返回为空。",
            "sources": [],
            "refused": True,
            "error": "empty_response",
        }

    cleaned = raw_ans.strip()
    is_refused = "没有提到" in cleaned or "无法回答" in cleaned
    return {
        "answer": cleaned,
        "sources": [] if is_refused else sources,
        "refused": is_refused,
        "error": None,
    }


# ----------------------------------------------------------
# 2. 真实/离线端到端 RAG 问答演示 (复用 2.2 VectorIndex)
# ----------------------------------------------------------


class KnowledgeBase:
    """基于 2.2 VectorIndex 向量索引的轻量原生知识库。"""

    def __init__(self, doc_path: str | Path):
        self.doc_path = Path(doc_path)
        self.chunks: list[dict] = []
        self.index = VectorIndex()
        self._build_index()

    def _build_index(self) -> None:
        text = self.doc_path.read_text(encoding="utf-8")
        step = 100
        idx = 1
        ids: list[str] = []
        texts: list[str] = []
        for start in range(0, len(text), step):
            piece = text[start : start + 120]
            if piece.strip():
                cid = f"{self.doc_path.name}#{idx}"
                self.chunks.append({
                    "text": piece,
                    "source": cid,
                    "index": idx,
                })
                ids.append(cid)
                texts.append(piece)
                idx += 1
        if texts:
            vecs = embed_texts(texts)
            self.index.add(ids, vecs)

    def retrieve(self, query: str, k: int = 3, min_score: float = 0.35) -> list[dict]:
        if not self.chunks:
            return []
        q_vec = embed_texts([query])[0]
        results = self.index.search(q_vec, k=k)
        chunk_map = {c["source"]: c for c in self.chunks}
        hits = []
        for r in results:
            if r["score"] >= min_score:
                hits.append(chunk_map[r["id"]])
        return hits


def make_chat_fn(live: bool) -> Callable[[list[dict]], str]:
    """根据是否开启 --live 返回在线模型调用或清晰离线提取函数。"""
    if live:
        try:
            client = get_openai_client()
        except Exception as exc:
            print(f"[可读提示] 未能初始化客户端（未配置有效 API 密钥）：{exc}")
            sys.exit(1)
        model = chat_model_name()

        def live_chat(messages: list[dict]) -> str:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    temperature=0.0,
                    messages=messages,
                )
                return resp.choices[0].message.content or ""
            except Exception as exc:
                print(f"[可读提示] 在线模型调用失败（{type(exc).__name__}: {exc}），请检查网络连接或 API 代理配置。")
                sys.exit(1)

        return live_chat

    def offline_chat(messages: list[dict]) -> str:
        # 离线演示模式：从装配消息中清晰指出未调用模型
        return "[离线演示] 依据上下文匹配成功，已装配 Prompt；使用 --live 参数可调用真实模型生成。"

    return offline_chat


def main() -> None:
    parser = argparse.ArgumentParser(description="2.3 最小 RAG 原生问答演示")
    parser.add_argument("--live", action="store_true", help="启用真实在线模型调用")
    args = parser.parse_args()

    print("=== 2.3 最小 RAG 原生问答演示 ===")
    if args.live:
        print("[模式] 正在使用 --live 在线调用模型。")
    else:
        print("[模式] 默认离线模式（未发起在线模型调用，可通过 --live 开启）。")

    kb = KnowledgeBase(SAMPLE_DOC)
    print(f"知识库构建完成，共包含 {len(kb.chunks)} 个片段。")

    chat_fn = make_chat_fn(live=args.live)

    test_questions = [
        "RAG 是什么？",
        "向量化有什么作用？",
        "今天北京的天气怎么样？",  # 资料外问题，应触发拒答
    ]

    for q in test_questions:
        print("\n" + "=" * 50)
        print("问题：", q)
        res = answer_with_rag(q, kb.retrieve, chat_fn)
        print("回答：", res["answer"])
        print("引用来源：", res["sources"])
        print("是否拒答：", res["refused"])


if __name__ == "__main__":
    main()
