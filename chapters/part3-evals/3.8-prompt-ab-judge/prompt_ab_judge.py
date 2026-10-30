"""章节 3.8 · Prompt A/B 对比与质量指标评测
==========================================================
核心能力与架构演进：
1. 为什么做 Prompt A/B 测试？
   同一批业务评测用例，用两版不同风格或约束的 Prompt 分别执行问答，通过可量化的客观硬指标
   （关键词覆盖率、来源引用率、拒答对齐率）和语义评估，用数据而不是主观直觉做 Prompt 选型。
2. 本章采用原生 Python + OpenAI SDK（去除 LangChain LCEL 依赖）：
   - Strict Prompt：追求严格事实、限制在 50 字以内、强制句末【来源：<source>】、无证据即拒答；
   - Helpful Prompt：追求详尽通俗、允许合理背景补充、引用可灵活内联、拒答时解释原因；
   - 评测指标：
     * normalize：大小写与空白字符归一化；
     * looks_refused：拒答特征短语识别；
     * keyword_score：关键词命中比例（无关键词记 1.0）；
     * citation_score：预期来源标识命中比例（无来源记 1.0）；
     * refusal_alignment：拒答行为与用例预期对齐度（1.0 / 0.0）。

运行模式：
  默认离线模式（无需外部 API Key，运行确定性样本评估与指标计算）：
    python tools/run_chapter.py 3.8
  在线真实模型调用（显式开启 --live，需配置模型环境变量）：
    python tools/run_chapter.py 3.8 --live
==========================================================
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

# 兼容模块导入路径
try:
    from common import (
        chat_model_name,
        get_openai_client,
    )
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from common import (
        chat_model_name,
        get_openai_client,
    )

SOURCE_NAME = "prompt_comparison_notes"
REFUSE_HINTS = ["没有提到", "信息不足", "无法回答", "不知道", "无相关"]

# 知识库
KNOWLEDGE_BASE = [
    {
        "source": SOURCE_NAME,
        "keywords": ["rag", "检索", "生成", "知识库", "上下文"],
        "content": (
            "RAG 是检索增强生成：先从知识库检索相关内容，再把检索到的上下文交给模型生成答案。"
            "它适合知识常更新、需要溯源、不能只靠模型记忆回答的场景。"
        ),
    },
    {
        "source": SOURCE_NAME,
        "keywords": ["prompt", "a/b", "ab", "评测", "指标", "选择"],
        "content": (
            "prompt A/B 的核心是在同一份评测集上比较两版 prompt 的指标，"
            "例如关键词命中、引用正确性、拒答一致性和 LLM-as-judge 分数。"
            "这样选 prompt 靠数据，不靠主观感觉。"
        ),
    },
    {
        "source": SOURCE_NAME,
        "keywords": ["judge", "裁判", "人工", "一致性", "可信"],
        "content": (
            "LLM-as-judge 会有偏差，所以需要拿人工抽样标注做一致性检查。"
            "如果 judge 通过/不通过的判断和人工标签一致率太低，就不能直接相信它的分数。"
        ),
    },
    {
        "source": SOURCE_NAME,
        "keywords": ["成本", "质量", "优化", "下降", "验证"],
        "content": (
            "成本优化不能只看便宜，还要验证质量没有明显下降。"
            "常见做法是记录成本、延迟、通过率和失败用例，确保省钱没有破坏核心效果。"
        ),
    },
    {
        "source": SOURCE_NAME,
        "keywords": ["回归", "曲线", "退化", "指标", "变化"],
        "content": (
            "回归曲线展示每次改动后的指标变化，帮助发现质量退化。"
            "失败用例库则把问题沉淀成可重复验证的资产。"
        ),
    },
    {
        "source": SOURCE_NAME,
        "keywords": ["上下文不足", "不足", "拒答", "不知道", "无法回答"],
        "content": (
            "当上下文不足时，RAG 助手应该明确说明信息不足或无法回答，"
            "而不是补常识、猜测或编造没有依据的内容。"
        ),
    },
]

# A/B 评测集
PROMPT_AB_CASES = [
    {
        "id": "ab_046",
        "type": "prompt_ab",
        "question": "用一句话说明 RAG 是什么。",
        "reference": "RAG 是检索增强生成，先检索相关内容，再交给模型生成答案。",
        "keywords": ["检索", "生成", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "expected_winner": "strict",
    },
    {
        "id": "ab_047",
        "type": "prompt_ab",
        "question": "RAG 适合哪些场景？请结合上下文详细说明。",
        "reference": "适合知识常更新、需要溯源、不能只靠模型记忆的场景。",
        "keywords": ["知识更新", "溯源", "模型记忆", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "expected_winner": "helpful",
    },
    {
        "id": "ab_048",
        "type": "prompt_ab",
        "question": "上下文不足时应该怎么回答？",
        "reference": "应拒答或说明信息不足，不能编造。",
        "keywords": ["不足", "无法回答", "编造"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "expected_winner": "tie",
    },
    {
        "id": "ab_053",
        "type": "prompt_ab",
        "question": "LangChain 0.3 版本有哪些新特性？",
        "reference": "上下文没有相关信息，应说明信息不足。",
        "keywords": ["信息不足", "无法回答"],
        "expected_sources": [],
        "should_refuse": True,
        "expected_winner": "strict",
    },
]


# --------------------------- 评测基础函数（Gate 接口） ---------------------------

def normalize(text: str) -> str:
    """小写并去掉所有空白字符。"""
    return re.sub(r"\s+", "", text.lower())


def looks_refused(answer: str) -> bool:
    """出现任一拒答提示词即判定为触发拒答。"""
    return any(hint in answer for hint in REFUSE_HINTS)


def keyword_score(answer: str, keywords: list[str]) -> float:
    """计算关键词命中比例；若无关键词要求则默认 1.0。"""
    if not keywords:
        return 1.0
    norm_ans = normalize(answer)
    hits = sum(1 for kw in keywords if normalize(kw) in norm_ans)
    return hits / len(keywords)


def citation_score(answer: str, sources: list[str]) -> float:
    """计算来源引用命中比例；若无来源要求则默认 1.0。"""
    if not sources:
        return 1.0
    hits = sum(1 for src in sources if src in answer)
    return hits / len(sources)


def refusal_alignment(answer: str, should_refuse: bool) -> float:
    """模型实际拒答行为与期望是否对齐（对齐记 1.0，否则 0.0）。"""
    refused = looks_refused(answer)
    return 1.0 if refused == should_refuse else 0.0


# --------------------------- 检索与上下文格式化 ---------------------------

def retrieve_docs(question: str, top_k: int = 2) -> list[dict]:
    """根据问题关键词匹配知识库文档。"""
    query = normalize(question)
    ranked = []
    for doc in KNOWLEDGE_BASE:
        score = sum(1 for keyword in doc["keywords"] if normalize(keyword) in query)
        if score > 0:
            ranked.append((score, doc))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in ranked[:top_k]]


def format_docs(docs: list[dict]) -> str:
    """将检索分块格式化为上文字符串。"""
    if not docs:
        return "没有检索到相关上下文。"
    parts = []
    for doc in docs:
        parts.append(f"[来源：{doc['source']}]\n{doc['content']}")
    return "\n\n".join(parts)


# --------------------------- 原生 OpenAI SDK A/B 生成 ---------------------------

def answer_with_strict(client: Any, model: str, question: str, context: str) -> str:
    """Strict 版 Prompt：极简、必须标注【来源：xxx】、不足时直接拒答。"""
    prompt = f"""你是严格的知识库问答助手。必须遵守以下规则：
1. 只依据【上下文】回答，禁止补充任何常识、例子或额外解释。
2. 答案必须简洁，通常不超过 50 个字。
3. 只要答案涉及文档内容，必须在句末标注【来源：{SOURCE_NAME}】。
4. 如果上下文不足以回答问题，只回复：“信息不足，无法回答。”不要多说一个字。

上下文：
{context}

问题：
{question}
"""
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return res.choices[0].message.content or ""


def answer_with_helpful(client: Any, model: str, question: str, context: str) -> str:
    """Helpful 版 Prompt：更详尽完整、语气自然、说明原因。"""
    prompt = f"""你是乐于助人的知识库问答助手。必须遵守以下规则：
1. 优先依据【上下文】回答，可以用通俗易懂的方式补充背景，帮助用户理解。
2. 如果上下文有相关内容，要在答案中标注来源，例如“根据 [来源：{SOURCE_NAME}]”。
3. 如果上下文信息不足，要明确指出“信息不足”，并说明原因（但不能编造具体事实）。
4. 回答可以适当详细，但要保持条理清晰。

上下文：
{context}

问题：
{question}
"""
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return res.choices[0].message.content or ""


# --------------------------- 主程序 ---------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="L3.6 原生 Prompt A/B 对比评测")
    parser.add_argument("--live", action="store_true", help="显式开启真实大模型在线调用")
    parser.add_argument("--limit", type=int, default=4, help="运行用例数量限制")
    args = parser.parse_args()

    print("==========================================================")
    print("  L3.6 Prompt A/B 对比评测（原生 OpenAI SDK 实现）")
    print("==========================================================")

    cases = PROMPT_AB_CASES[: args.limit]
    print(f"已加载 A/B 对比用例：{len(cases)} 条。\n")

    if not args.live:
        print("[模式说明] 当前为默认【离线确定性演练】模式（未附加 --live）。")
        print("展示 Strict 与 Helpful 两版 Prompt 在不同指标上的量化差异：\n")

        strict_results = []
        helpful_results = []

        for c in cases:
            q = c["question"]
            should_refuse = c.get("should_refuse", False)

            if should_refuse:
                s_ans = "信息不足，无法回答。"
                h_ans = "抱歉，关于该版本的新特性，当前知识库中信息不足，无法为您提供准确说明。"
            elif c["id"] == "ab_046":
                s_ans = f"RAG 是检索增强生成，先检索相关资料再交由模型生成答案。【来源：{SOURCE_NAME}】"
                h_ans = f"RAG（检索增强生成）是一种先进技术，根据 [来源：{SOURCE_NAME}]，它先从向量库中召回上下文，再生成答案。"
            else:
                s_ans = f"基于上下文，该方法用于在同一评测集上量化对比指标。【来源：{SOURCE_NAME}】"
                h_ans = f"根据 [来源：{SOURCE_NAME}]，在同一评测集上进行 A/B 测试能消除数据偏差，科学客观地评估 Prompt 效果。"

            # 打分
            s_kw = keyword_score(s_ans, c.get("keywords", []))
            s_cite = citation_score(s_ans, c.get("expected_sources", []))
            s_ref = refusal_alignment(s_ans, should_refuse)
            strict_results.append({"kw": s_kw, "cite": s_cite, "ref": s_ref, "len": len(s_ans)})

            h_kw = keyword_score(h_ans, c.get("keywords", []))
            h_cite = citation_score(h_ans, c.get("expected_sources", []))
            h_ref = refusal_alignment(h_ans, should_refuse)
            helpful_results.append({"kw": h_kw, "cite": h_cite, "ref": h_ref, "len": len(h_ans)})

            print(f"Q: {q}")
            print(f"  [Strict ] ({len(s_ans)}字) {s_ans}")
            print(f"            关键词={s_kw:.2f}, 引用={s_cite:.2f}, 拒答对齐={s_ref:.2f}")
            print(f"  [Helpful] ({len(h_ans)}字) {h_ans}")
            print(f"            关键词={h_kw:.2f}, 引用={h_cite:.2f}, 拒答对齐={h_ref:.2f}\n")

        s_avg_kw = sum(r["kw"] for r in strict_results) / len(strict_results)
        s_avg_cite = sum(r["cite"] for r in strict_results) / len(strict_results)
        s_avg_ref = sum(r["ref"] for r in strict_results) / len(strict_results)
        s_avg_len = sum(r["len"] for r in strict_results) / len(strict_results)

        h_avg_kw = sum(r["kw"] for r in helpful_results) / len(helpful_results)
        h_avg_cite = sum(r["cite"] for r in helpful_results) / len(helpful_results)
        h_avg_ref = sum(r["ref"] for r in helpful_results) / len(helpful_results)
        h_avg_len = sum(r["len"] for r in helpful_results) / len(helpful_results)

        print("=== A/B 综合量化看板 ===")
        print(f"Strict  版: 平均字数={s_avg_len:.1f}, 关键词覆盖率={s_avg_kw:.2%}, 来源引用率={s_avg_cite:.2%}, 拒答对齐率={s_avg_ref:.2%}")
        print(f"Helpful 版: 平均字数={h_avg_len:.1f}, 关键词覆盖率={h_avg_kw:.2%}, 来源引用率={h_avg_cite:.2%}, 拒答对齐率={h_avg_ref:.2%}")
        print("\n[工程结论] Strict 版在简洁度与拒答干净度上优势突出；Helpful 版在复杂问答的解释充分度上更占优。")
        return 0

    # 在线真实调用模式
    print("[在线模式] 正在初始化原生 OpenAI 客户端...")
    try:
        client = get_openai_client(timeout=30.0, max_retries=1)
        model = chat_model_name()
    except Exception as exc:
        print(f"[配置错误] 无法获取模型客户端或模型名称：{exc}", file=sys.stderr)
        print("请检查环境变量或 .env 配置。", file=sys.stderr)
        return 1

    try:
        print(f"使用模型：{model}\n")
        for idx, case in enumerate(cases, 1):
            q = case["question"]
            docs = retrieve_docs(q)
            context = format_docs(docs)

            print(f"[{idx}/{len(cases)}] 问题：{q}")
            t0 = time.perf_counter()
            s_ans = answer_with_strict(client, model, q, context)
            s_ms = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            h_ans = answer_with_helpful(client, model, q, context)
            h_ms = (time.perf_counter() - t0) * 1000.0

            s_kw = keyword_score(s_ans, case.get("keywords", []))
            s_cite = citation_score(s_ans, case.get("expected_sources", []))
            s_ref = refusal_alignment(s_ans, case.get("should_refuse", False))

            h_kw = keyword_score(h_ans, case.get("keywords", []))
            h_cite = citation_score(h_ans, case.get("expected_sources", []))
            h_ref = refusal_alignment(h_ans, case.get("should_refuse", False))

            print(f"  Strict  ({s_ms:.0f}ms): {s_ans}")
            print(f"          关键词={s_kw:.2f}, 引用={s_cite:.2f}, 拒答对齐={s_ref:.2f}")
            print(f"  Helpful ({h_ms:.0f}ms): {h_ans}")
            print(f"          关键词={h_kw:.2f}, 引用={h_cite:.2f}, 拒答对齐={h_ref:.2f}\n")

    except Exception as exc:
        print(f"\n[运行失败] 在线请求过程中发生网络或模型错误：{exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
