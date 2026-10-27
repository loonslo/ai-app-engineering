"""
章节 2.5 · 裸 SDK 手写 RAG + agent loop（理解 harness）
==========================================================
前面 2.1–2.3 用 LangChain 快速搭了 RAG。本章故意不用 LangChain，只用：
- 标准库做文档切块、关键词检索
- OpenAI 兼容 HTTP 接口调用 DeepSeek
- 手写最小 ReAct 风格 agent loop

目的不是追求效果最好，而是看清 harness：模型之外那层工程代码，包括
检索、prompt 拼接、工具解析、循环控制、停止条件、错误兜底。

前置：2.3
运行：python tools/run_chapter.py 2.5；没有 DEEPSEEK_API_KEY 时 chat() 返回固定的离线提示，配置后调用真实模型
输出：一次手写 RAG 的回答，和一次最多 4 步的 agent loop 过程
==========================================================
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.request
from collections import Counter
from dataclasses import dataclass
from typing import Callable

import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common import DEEPSEEK_BASE_URL, SAMPLE_DOC, _deepseek_api_key, chat_model_name

load_dotenv()

API_URL = DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
MODEL = chat_model_name()


@dataclass
class Chunk:
    text: str
    source: str
    index: int


def tokenize(text: str) -> list[str]:
    """极简 tokenizer：中文按连续字块/英文数字按词，够演示检索逻辑。"""
    return re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", text.lower())


def split_text(text: str, source: str, chunk_size: int = 180, overlap: int = 30) -> list[Chunk]:
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        piece = text[start:start + chunk_size].strip()
        if piece:
            chunks.append(Chunk(text=piece, source=source, index=len(chunks) + 1))
        start += max(1, chunk_size - overlap)
    return chunks


def score(query: str, chunk: Chunk) -> float:
    """用 TF 重叠近似相似度。真实项目换 embedding；这里为了裸写 harness。"""
    q = Counter(tokenize(query))
    d = Counter(tokenize(chunk.text))
    if not q or not d:
        return 0.0
    dot = sum(q[t] * d[t] for t in q)
    q_norm = math.sqrt(sum(v * v for v in q.values()))
    d_norm = math.sqrt(sum(v * v for v in d.values()))
    return dot / (q_norm * d_norm)


def retrieve(query: str, chunks: list[Chunk], k: int = 3) -> list[Chunk]:
    ranked = sorted(chunks, key=lambda c: score(query, c), reverse=True)
    return [c for c in ranked[:k] if score(query, c) > 0]


def chat(messages: list[dict[str, str]], temperature: float = 0.0) -> str:
    """直接调 OpenAI 兼容接口。没有 key 时返回离线提示，保证文件可读可跑。"""
    api_key = _deepseek_api_key()
    if not api_key:
        return "（离线模式）未配置 DEEPSEEK_API_KEY；这里会发送 messages 给模型并返回 content。"

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def raw_rag_answer(question: str, chunks: list[Chunk]) -> str:
    hits = retrieve(question, chunks)
    if not hits:
        return "文档中没有提到。"
    context = "\n\n".join(
        f"[{c.source}#{c.index}]\n{c.text}" for c in hits
    )
    messages = [
        {"role": "system", "content": "你是严谨的知识库助手，只依据上下文回答；无依据就拒答。"},
        {"role": "user", "content": f"上下文：\n{context}\n\n问题：{question}"},
    ]
    return chat(messages)


# 演示用工具表。受限的 eval 只是降低误用风险，不是沙箱，不能执行不可信输入（见 5.7）。
TOOLS: dict[str, Callable[[str], str]] = {
    "calculator": lambda expr: str(eval(expr, {"__builtins__": {}}, {})),
    "lookup": lambda q: f"本地工具结果：{q} 与 RAG/Agent harness 有关。",
}


def parse_action(text: str) -> tuple[str, str] | None:
    """约定模型如果要调工具，就输出 Action: tool_name[argument]。"""
    match = re.search(r"Action:\s*(\w+)\[(.*?)\]", text, flags=re.S)
    if not match:
        return None
    return match.group(1), match.group(2).strip()


def agent_loop(task: str, max_steps: int = 4) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "你是最小 ReAct Agent。需要工具时只输出 Action: calculator[1+1] "
                "或 Action: lookup[关键词]；能回答时输出 Final: 答案。"
            ),
        },
        {"role": "user", "content": task},
    ]

    for step in range(1, max_steps + 1):
        thought = chat(messages)
        print(f"[step {step}] model: {thought}")
        if thought.strip().startswith("Final:"):
            return thought.split("Final:", 1)[1].strip()

        action = parse_action(thought)
        if not action:
            return thought
        tool_name, arg = action
        tool = TOOLS.get(tool_name)
        observation = tool(arg) if tool else f"未知工具：{tool_name}"
        print(f"[step {step}] observation: {observation}")
        messages.append({"role": "assistant", "content": thought})
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return "达到最大步数，停止执行。"


if __name__ == "__main__":
    text = SAMPLE_DOC.read_text(encoding="utf-8")
    chunks = split_text(text, source=SAMPLE_DOC.name)
    print("=== 裸写 RAG ===")
    print(raw_rag_answer("RAG 是什么？", chunks))

    print("\n=== 裸写 agent loop ===")
    print(agent_loop("先查一下 harness 是什么，再计算 12*7。"))


# ----------------------------------------------------------
# 小结：
# - LangChain 帮你封装的不是魔法，而是这类 harness：检索、拼 prompt、解析工具、
#   循环控制、停止条件、错误兜底、日志。
# - 裸写一次后，再用框架就知道自己在借力哪一层。
# ----------------------------------------------------------
