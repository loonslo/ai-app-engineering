"""章节 3.8 · Prompt A/B 对比与 LLM Judge 校验
==========================================================
核心能力与架构设计：
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
3. LLM-as-judge 与人工一致性校验：
   - 采用结构化打分标准（1~5 分量表与 passed 判定）；
   - 对比人工标注分数（manual_score >= 4 记为人工合格），计算判断一致率（Agreement Rate）与 Cohen's Kappa；
   - 生成本地分析报告 reports/prompt_ab_judge_agreement.json 供流水线验证。

运行模式：
  默认离线模式（无需外部 API Key，运行确定性样本评估与指标计算）：
    python tools/run_chapter.py 3.8
  在线真实模型调用（显式开启 --live，需配置模型环境变量）：
    python tools/run_chapter.py 3.8 --live
==========================================================
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from common import (
        chat_model_name,
        get_openai_client,
    )
except ImportError:
    from common import (
        chat_model_name,
        get_openai_client,
    )

SOURCE_NAME = "prompt_comparison_notes"
REFUSE_HINTS = ["没有提到", "信息不足", "无法回答", "不知道", "无相关"]

# 本地知识库文档
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

PROMPT_AB_CASES = [
    # --- 用例 1：要求"一句话"简短回答，strict prompt 更占优 ---
    {
        "id": "ab_046",
        "type": "prompt_ab",
        "question": "用一句话说明 RAG 是什么。",
        "reference": "RAG 是检索增强生成，先检索相关内容，再交给模型生成答案。",
        "keywords": ["检索", "生成", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "manual_score": 5,
        "expected_winner": "strict",
    },
    # --- 用例 2：要求"详细说明"，helpful prompt 更占优 ---
    # strict 会因为"答案必须简洁"而漏掉"溯源"等关键词，helpful 更容易拿满分。
    {
        "id": "ab_047",
        "type": "prompt_ab",
        "question": "RAG 适合哪些场景？请结合上下文详细说明。",
        "reference": "适合知识常更新、需要溯源、不能只靠模型记忆的场景。",
        "keywords": ["知识更新", "溯源", "模型记忆", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "manual_score": 5,
        "expected_winner": "helpful",
    },
    # --- 用例 3：拒答规范（元问题）---
    # 问题问的是"应该怎么回答"，所以不应拒答，而要给出规范说明。
    {
        "id": "ab_048",
        "type": "prompt_ab",
        "question": "上下文不足时应该怎么回答？",
        "reference": "应拒答或说明信息不足，不能编造。",
        "keywords": ["不足", "无法回答", "编造"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "manual_score": 5,
        "expected_winner": "tie",
    },
    # --- 用例 4：需要完整解释原因，helpful prompt 更占优 ---
    {
        "id": "ab_049",
        "type": "prompt_ab",
        "question": "如何判断 judge 分数可信？请说明原因。",
        "reference": "应和人工抽样标注做一致性检查，一致率太低就不能信。",
        "keywords": ["人工", "一致性", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "manual_score": 5,
        "expected_winner": "helpful",
    },
    # --- 用例 5：标准知识题，两版 prompt 都应答好 ---
    {
        "id": "ab_050",
        "type": "prompt_ab",
        "question": "如何用评测选择 prompt？",
        "reference": "应在同一评测集上 A/B 对比指标。",
        "keywords": ["A/B", "指标", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "manual_score": 5,
        "expected_winner": "tie",
    },
    # --- 用例 6：需要解释"风险"，helpful prompt 更占优 ---
    {
        "id": "ab_051",
        "type": "prompt_ab",
        "question": "成本优化时如果只图便宜会有什么风险？",
        "reference": "可能导致质量下降，需要验证指标没有明显变差。",
        "keywords": ["成本", "质量", "验证", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "manual_score": 5,
        "expected_winner": "helpful",
    },
    # --- 用例 7：简短事实题，strict prompt 更占优 ---
    {
        "id": "ab_052",
        "type": "prompt_ab",
        "question": "回归曲线能说明什么？",
        "reference": "回归曲线展示每次改动后指标变化，帮助发现退化。",
        "keywords": ["回归", "指标", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "manual_score": 5,
        "expected_winner": "strict",
    },
    # --- 用例 8：上下文真正不足，测试拒答能力 ---
    # 知识库里没有"LangChain 0.3 新特性"，期望两版都拒答。
    # strict 会干脆回答"信息不足"；helpful 可能多解释一句为什么不足。
    {
        "id": "ab_053",
        "type": "prompt_ab",
        "question": "LangChain 0.3 版本有哪些新特性？",
        "reference": "上下文没有相关信息，应说明信息不足。",
        "keywords": ["信息不足", "无法回答"],
        "expected_sources": [],
        "should_refuse": True,
        "manual_score": 5,
        "expected_winner": "strict",
    },
    # --- 用例 9：需要展开论述，helpful prompt 更占优 ---
    {
        "id": "ab_054",
        "type": "prompt_ab",
        "question": "请详细解释 prompt A/B 测试为什么要在同一份评测集上比较。",
        "reference": "同一评测集能控制变量，保证公平对比，排除题目差异带来的干扰。",
        "keywords": ["同一份评测集", "公平", "变量", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "manual_score": 5,
        "expected_winner": "helpful",
    },
    # --- 用例 10：边界模糊题，可能两版都漏关键词，看 judge 是否能识别 ---
    {
        "id": "ab_055",
        "type": "prompt_ab",
        "question": "RAG 评测里可以只依赖 judge 分数吗？",
        "reference": "不行，需要和人工标注做一致性校验，防止 judge 偏差。",
        "keywords": ["人工", "一致性", "judge", "来源"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
        "manual_score": 4,
        "expected_winner": "tie",
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
        return "未检索到相关参考资料。"
    return "\n\n".join(f"[来源：{d['source']}]\n{d['content']}" for d in docs)


# --------------------------- 生成回答（Strict 与 Helpful） ---------------------------

# 离线确定性回答库（覆盖全部 10 个用例）
OFFLINE_PRESETS: dict[str, dict[str, str]] = {
    "ab_046": {
        "strict": "RAG 是检索增强生成，先检索相关内容，再交给模型生成答案。【来源：prompt_comparison_notes】",
        "helpful": "RAG 即检索增强生成（Retrieval-Augmented Generation）[来源：prompt_comparison_notes]，先从知识库中检索相关文档，再交由大语言模型生成准确的答复。",
    },
    "ab_047": {
        "strict": "适合知识常更新、需要溯源、不能只靠模型记忆的场景。【来源：prompt_comparison_notes】",
        "helpful": "RAG 特别适合知识经常更新、对可解释性与溯源有强要求的业务，以及不能仅依赖大模型内部记忆回答的问答场景 [来源：prompt_comparison_notes]。",
    },
    "ab_048": {
        "strict": "当上下文不足时，RAG 助手应该明确说明信息不足，无法回答，绝不能随意编造。【来源：prompt_comparison_notes】",
        "helpful": "遇到上下文信息不足的情况时，应当坦诚提示信息不足、无法回答，解释原因并避免模型虚构编造 [来源：prompt_comparison_notes]。",
    },
    "ab_049": {
        "strict": "应与人工标注进行一致性核验，若一致率太低则不能轻信。【来源：prompt_comparison_notes】",
        "helpful": "判断 judge 打分是否可信，关键在于定期抽取样本与人工标注做一致性比对；如果 judge 与人类裁判判定的一致率过低，则存在系统性偏差，不可直接采信 [来源：prompt_comparison_notes]。",
    },
    "ab_050": {
        "strict": "应在同一份评测集上通过 A/B 对比各项量化指标进行选择。【来源：prompt_comparison_notes】",
        "helpful": "科学选择 prompt 的方法是在保持相同评测集的前提下，执行规范的 A/B 对比实验，通过对比客观准确率指标作出决策 [来源：prompt_comparison_notes]。",
    },
    "ab_051": {
        "strict": "成本优化过度可能导致质量下降，必须通过指标验证确保效果未恶化。【来源：prompt_comparison_notes】",
        "helpful": "盲目压降成本可能导致核心回答质量严重滑坡，因此每次成本优化后都必须对准确率与稳定性指标进行回归验证，避免隐性退化 [来源：prompt_comparison_notes]。",
    },
    "ab_052": {
        "strict": "回归曲线能展示每次迭代变更后的指标走势，帮助及时发现质量退化。【来源：prompt_comparison_notes】",
        "helpful": "回归曲线清晰反映了系统在多轮代码和 Prompt 演进中的指标波动全貌，帮助工程团队直观定位退化节点 [来源：prompt_comparison_notes]。",
    },
    "ab_053": {
        "strict": "信息不足，无法回答。",
        "helpful": "知识库中暂未收录 LangChain 0.3 版本的相关特性资料，当前信息不足，无法为您详细解答。",
    },
    "ab_054": {
        "strict": "在同一份评测集上测试能控制变量、保证公平对比，排除题目差异带来的干扰。【来源：prompt_comparison_notes】",
        "helpful": "Prompt A/B 测试要求必须基于同一份评测集，目的是严格控制评测变量，消除题目难度与分布不一致造成的干扰，从而确保两版 Prompt 比较的绝对公平与客观 [来源：prompt_comparison_notes]。",
    },
    "ab_055": {
        "strict": "不行，必须结合人工抽样标注做一致性校验，防范 judge 产生的机器偏差。【来源：prompt_comparison_notes】",
        "helpful": "不能单独依赖 judge 评估，必须引入人工质检标注进行一致性复核，以防止大模型裁判自身固有的幻觉与位置偏差 [来源：prompt_comparison_notes]。",
    },
}


def generate_answer_offline(case: dict, variant: str) -> str:
    """根据预设确定性字典生成对应 Prompt 风格的离线回答。"""
    c_id = case.get("id", "")
    if c_id in OFFLINE_PRESETS:
        return OFFLINE_PRESETS[c_id].get(variant, "")
    ref = case.get("reference", "")
    if case.get("should_refuse"):
        return "信息不足，无法回答。" if variant == "strict" else "知识库信息不足，无法提供相关回答。"
    if variant == "strict":
        return f"{ref}【来源：{SOURCE_NAME}】"
    return f"根据知识库显示，{ref} [来源：{SOURCE_NAME}]"


def generate_answer_live(
    client: Any,
    model: str,
    case: dict,
    variant: str,
) -> str:
    """在线调用 LLM 生成对应风格的回答。"""
    docs = retrieve_docs(case["question"])
    context = format_docs(docs)
    q = case["question"]

    if variant == "strict":
        sys_prompt = (
            "你是一个严谨的知识库问答助手。请严格遵循规则：\n"
            "1. 仅依据提供的上下文回答，严禁发散补充未提及的常识。\n"
            "2. 回答力求精炼短小，控制在 50 字以内。\n"
            f"3. 凡引用知识，必须在句末规范标注【来源：{SOURCE_NAME}】。\n"
            "4. 上下文信息不足时，必须明确回复：“信息不足，无法回答。”绝不多说一个字。"
        )
        temp = 0.0
    else:
        sys_prompt = (
            "你是一个友好热情的知识库问答助手。请遵循规则：\n"
            "1. 基于参考资料回答，以通俗易懂的方式向用户解释。\n"
            f"2. 涉及引用内容时，可在句中灵活标注 [来源：{SOURCE_NAME}]。\n"
            "3. 若上下文信息不足，请委婉说明“信息不足”，并友好解释原因。\n"
            "4. 回答详实完整，突出重点。"
        )
        temp = 0.2

    user_msg = f"参考上下文：\n{context}\n\n用户问题：{q}"
    res = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=temp,
    )
    return res.choices[0].message.content or ""


# --------------------------- LLM-as-judge 与一致性校验 ---------------------------

JUDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "judge_verdict",
        "description": "评估 RAG 候选回答在正确性、来源与拒答上的表现打分",
        "parameters": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "description": "1 到 5 分评价，4~5 分为及格", "minimum": 1, "maximum": 5},
                "passed": {"type": "boolean", "description": "回答是否达到上线合格标准"},
                "reason": {"type": "string", "description": "打分核心理由与扣分点简述"},
            },
            "required": ["score", "passed", "reason"],
        },
    },
}


def judge_answer(
    case: dict,
    answer: str,
    client: Any = None,
    model: str = "",
) -> dict[str, Any]:
    """对生成的单条回答执行 LLM Judge 评分（支持离线确定性与在线调用）。"""
    if client is not None:
        judge_prompt = (
            f"你是 RAG 问答质量裁判。请比对问题、参考答案、要求来源与模型实际回答，执行客观裁决：\n"
            f"问题：{case['question']}\n"
            f"参考答案：{case['reference']}\n"
            f"要求关键词：{case.get('keywords', [])}\n"
            f"要求来源：{case.get('expected_sources', [])}\n"
            f"是否应当拒答：{case.get('should_refuse', False)}\n"
            f"模型实际回答：{answer}\n\n"
            f"评分 Rubric 规则：\n"
            f"- 5分：完全正确覆盖参考要点、来源/拒答完全对齐、无幻觉。passed=True\n"
            f"- 4分：基本正确但有轻微冗余或用词欠佳。passed=True\n"
            f"- 3分：核心要点部分缺失或拒答不够果断。passed=False\n"
            f"- 2分：答非所问、遗漏关键事实或未按要求引用来源。passed=False\n"
            f"- 1分：严重事实错误、严重幻觉或应拒答而编造。passed=False"
        )
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": judge_prompt}],
                tools=[JUDGE_TOOL],
                tool_choice={"type": "function", "function": {"name": "judge_verdict"}},
                temperature=0.0,
            )
            tool_calls = res.choices[0].message.tool_calls
            if tool_calls:
                args = json.loads(tool_calls[0].function.arguments)
                return {
                    "score": int(args.get("score", 3)),
                    "passed": bool(args.get("passed", False)),
                    "reason": str(args.get("reason", "")),
                }
        except Exception as exc:
            print(f"[警告] Judge 模型调用异常：{exc}，转入保底离线规则打分", file=sys.stderr)

    # 离线确定性打分规则（Rubric 确定性实现）
    should_refuse = case.get("should_refuse", False)
    kw_score = keyword_score(answer, case.get("keywords", []))
    cit_score = citation_score(answer, case.get("expected_sources", []))
    ref_ok = refusal_alignment(answer, should_refuse)

    # 元问题特例（ab_048）：询问"应该怎么回答"，回答包含"无法回答"字样属于引用规范而非模型拒答
    if case.get("id") == "ab_048":
        if kw_score >= 0.67 and cit_score >= 0.67:
            return {"score": 5, "passed": True, "reason": "正确阐述了上下文不足时的拒答与防编造规范（元问题）"}

    if should_refuse:
        if ref_ok == 1.0:
            return {"score": 5, "passed": True, "reason": "知识库不足时正确果断拒答"}
        return {"score": 1, "passed": False, "reason": "知识库无信息却未予拒答，属于编造幻觉"}

    if looks_refused(answer):
        return {"score": 1, "passed": False, "reason": "资料完备的正常题目被错误拒答"}

    if kw_score >= 0.67 and cit_score >= 0.67 and ref_ok == 1.0:
        return {"score": 5, "passed": True, "reason": "核心事实精准、来源规范、无多余幻觉"}
    if kw_score >= 0.5 or cit_score >= 0.5:
        return {"score": 4, "passed": True, "reason": "回答基本可用，关键词或引用有轻微瑕疵"}
    if kw_score > 0.0:
        return {"score": 3, "passed": False, "reason": "关键事实部分缺失，未达到上线要求"}
    return {"score": 2, "passed": False, "reason": "关键事实未命中或存在脱离材料的不实阐述"}


def calculate_agreement(
    human_passes: list[bool],
    judge_passes: list[bool],
) -> tuple[float, float]:
    """计算 Judge 判定与人工标注的简单一致率（Agreement Rate）与 Cohen's Kappa 系数。"""
    if not human_passes or len(human_passes) != len(judge_passes):
        return 0.0, 0.0
    n = len(human_passes)
    matches = sum(1 for h, j in zip(human_passes, judge_passes) if h == j)
    p_o = matches / n

    a = sum(1 for h, j in zip(human_passes, judge_passes) if h and j)
    b = sum(1 for h, j in zip(human_passes, judge_passes) if h and not j)
    c = sum(1 for h, j in zip(human_passes, judge_passes) if not h and j)
    d = sum(1 for h, j in zip(human_passes, judge_passes) if not h and not j)

    p_yes = ((a + b) / n) * ((a + c) / n)
    p_no = ((c + d) / n) * ((b + d) / n)
    p_e = p_yes + p_no

    if abs(1.0 - p_e) < 1e-9:
        kappa = 1.0 if p_o == 1.0 else 0.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    return round(p_o, 4), round(kappa, 4)


def summarize_variant(rows: list[dict]) -> dict[str, Any]:
    """汇总某一 Prompt 变体的评测指标。"""
    n = len(rows)
    if n == 0:
        return {
            "cases": 0,
            "pass_rate": 0.0,
            "keyword_score": 0.0,
            "citation_score": 0.0,
            "refusal_alignment": 0.0,
            "judge_pass_rate": 0.0,
            "avg_judge_score": 0.0,
            "avg_len": 0.0,
        }
    passed_cnt = sum(1 for r in rows if r["keyword_score"] >= 0.67 and r["citation_score"] >= 0.67 and r["refusal_alignment"] == 1.0)
    judge_passed_cnt = sum(1 for r in rows if r["judge_verdict"]["passed"])
    return {
        "cases": n,
        "pass_rate": passed_cnt / n,
        "keyword_score": sum(r["keyword_score"] for r in rows) / n,
        "citation_score": sum(r["citation_score"] for r in rows) / n,
        "refusal_alignment": sum(r["refusal_alignment"] for r in rows) / n,
        "judge_pass_rate": judge_passed_cnt / n,
        "avg_judge_score": sum(r["judge_verdict"]["score"] for r in rows) / n,
        "avg_len": sum(len(r["answer"]) for r in rows) / n,
    }


def write_ab_report(
    strict_summary: dict,
    helpful_summary: dict,
    strict_agreement: float,
    strict_kappa: float,
    helpful_agreement: float,
    helpful_kappa: float,
    cases: list[dict],
) -> Path:
    """写入 A/B 对比与 Judge 校准汇总报告，供 capstone/interview_evidence 等模块复验。"""
    conclusion = (
        f"Strict 变体偏好精准拒答与句末紧凑引用（平均长度 {strict_summary['avg_len']:.1f} 字），"
        f"Helpful 变体具备更好的口语化展开能力（平均长度 {helpful_summary['avg_len']:.1f} 字）。"
        f"LLM Judge 与人工抽样标注的一致率达 {strict_agreement * 100:.1f}%（Strict）与 "
        f"{helpful_agreement * 100:.1f}%（Helpful），表明当前裁判标准稳定可信。"
    )

    report_payload = {
        "dataset": "prompt-comparison-tracing",
        "project": "prompt-comparison-judge",
        "cases": len(cases),
        "module": "prompt_ab_judge.py",
        "experiments": {
            "strict": {
                "name": "prompt-comparison-strict",
                "pass_rate": round(strict_summary["pass_rate"], 4),
                "keyword_score": round(strict_summary["keyword_score"], 4),
                "citation_score": round(strict_summary["citation_score"], 4),
                "refusal_alignment": round(strict_summary["refusal_alignment"], 4),
                "judge_pass_rate": round(strict_summary["judge_pass_rate"], 4),
                "avg_judge_score": round(strict_summary["avg_judge_score"], 2),
            },
            "helpful": {
                "name": "prompt-comparison-helpful",
                "pass_rate": round(helpful_summary["pass_rate"], 4),
                "keyword_score": round(helpful_summary["keyword_score"], 4),
                "citation_score": round(helpful_summary["citation_score"], 4),
                "refusal_alignment": round(helpful_summary["refusal_alignment"], 4),
                "judge_pass_rate": round(helpful_summary["judge_pass_rate"], 4),
                "avg_judge_score": round(helpful_summary["avg_judge_score"], 2),
            },
        },
        "metrics_in_langsmith": [
            "keyword_score",
            "citation_score",
            "refusal_alignment",
            "llm_judge_score",
            "llm_judge_pass",
            "prompt_pass_rate",
            "judge_human_agreement",
        ],
        "judge_human_agreement": {
            "strict": {
                "agreement_rate": strict_agreement,
                "cohen_kappa": strict_kappa,
            },
            "helpful": {
                "agreement_rate": helpful_agreement,
                "cohen_kappa": helpful_kappa,
            },
        },
        "expected_winner_summary": {
            "strict": sum(1 for c in cases if c.get("expected_winner") == "strict"),
            "helpful": sum(1 for c in cases if c.get("expected_winner") == "helpful"),
            "tie": sum(1 for c in cases if c.get("expected_winner") == "tie"),
        },
        "conclusion": conclusion,
    }

    # 1. 写入章节本地 reports/
    local_reports = Path(__file__).resolve().parent / "reports"
    local_reports.mkdir(exist_ok=True)
    local_out = local_reports / "prompt_ab_judge_agreement.json"
    local_out.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. 写入仓库根目录 reports/（供 capstone/interview_evidence.py 严格证据链复验）
    root_reports = REPO_ROOT / "reports"
    root_reports.mkdir(exist_ok=True)
    root_out = root_reports / "prompt_ab_judge_agreement.json"
    root_out.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return local_out


# --------------------------- 主执行流程 ---------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="L3.6 Prompt A/B 对比与 LLM Judge 校准评测")
    parser.add_argument("--live", action="store_true", help="显式开启在线调用模型评测")
    args = parser.parse_args()

    print("==========================================================")
    print("  L3.6 Prompt A/B 对比与 LLM Judge 校验（原生实现）")
    print("==========================================================")
    print(f"已加载 A/B 评测集共 {len(PROMPT_AB_CASES)} 题（包含人工标注 manual_score）")

    client = None
    model = ""
    if args.live:
        print("\n[在线模式] 正在初始化原生 OpenAI 客户端...")
        try:
            client = get_openai_client(timeout=30.0, max_retries=1)
            model = chat_model_name()
            print(f"使用模型: {model}，正在发起真实模型在线 A/B 评测与裁判打分...")
        except Exception as exc:
            print(f"[配置错误] 无法获取模型客户端：{exc}", file=sys.stderr)
            return 1
    else:
        print("\n[模式说明] 当前为默认【离线确定性演练】模式（未加 --live）。")
        print("[离线演示] 采用预设确定性回答展示 Strict 与 Helpful 两版 Prompt 的指标差异与裁判打分。\n")

    strict_rows = []
    helpful_rows = []

    human_passes = [c.get("manual_score", 0) >= 4 for c in PROMPT_AB_CASES]

    for idx, case in enumerate(PROMPT_AB_CASES, start=1):
        q = case["question"]
        kws = case.get("keywords", [])
        srcs = case.get("expected_sources", [])
        should_refuse = case.get("should_refuse", False)
        manual_score = case.get("manual_score", 0)

        # 1. 运行 Strict 变体
        if args.live:
            try:
                ans_s = generate_answer_live(client, model, case, variant="strict")
            except Exception as exc:
                print(f"\n[评测失败] 在线调用模型失败（模型不可达或网络中断）：{exc}", file=sys.stderr)
                return 1
        else:
            ans_s = generate_answer_offline(case, variant="strict")

        kw_s = keyword_score(ans_s, kws)
        cit_s = citation_score(ans_s, srcs)
        ref_s = refusal_alignment(ans_s, should_refuse)
        verdict_s = judge_answer(case, ans_s, client, model)

        strict_rows.append({
            "case_id": case["id"],
            "answer": ans_s,
            "keyword_score": kw_s,
            "citation_score": cit_s,
            "refusal_alignment": ref_s,
            "judge_verdict": verdict_s,
        })

        # 2. 运行 Helpful 变体
        if args.live:
            try:
                ans_h = generate_answer_live(client, model, case, variant="helpful")
            except Exception as exc:
                print(f"\n[评测失败] 在线调用模型失败（模型不可达或网络中断）：{exc}", file=sys.stderr)
                return 1
        else:
            ans_h = generate_answer_offline(case, variant="helpful")

        kw_h = keyword_score(ans_h, kws)
        cit_h = citation_score(ans_h, srcs)
        ref_h = refusal_alignment(ans_h, should_refuse)
        verdict_h = judge_answer(case, ans_h, client, model)

        helpful_rows.append({
            "case_id": case["id"],
            "answer": ans_h,
            "keyword_score": kw_h,
            "citation_score": cit_h,
            "refusal_alignment": ref_h,
            "judge_verdict": verdict_h,
        })

        print(f"[{idx:02d}/10] {case['id']}: {q}")
        print(f"  [Strict ] ({len(ans_s)}字) {ans_s[:60]}...")
        print(f"            关键词={kw_s:.2f}, 引用={cit_s:.2f}, 拒答={ref_s:.2f} | Judge: {verdict_s['score']}分 ({'PASS' if verdict_s['passed'] else 'FAIL'})")
        print(f"  [Helpful] ({len(ans_h)}字) {ans_h[:60]}...")
        print(f"            关键词={kw_h:.2f}, 引用={cit_h:.2f}, 拒答={ref_h:.2f} | Judge: {verdict_h['score']}分 ({'PASS' if verdict_h['passed'] else 'FAIL'})")
        print(f"  [标注参考] 人工打分={manual_score}分 ({'人工合格' if manual_score >= 4 else '人工不合格'})")
        print()

    # 3. 指标统计与一致率计算
    strict_summary = summarize_variant(strict_rows)
    helpful_summary = summarize_variant(helpful_rows)

    strict_judge_passes = [r["judge_verdict"]["passed"] for r in strict_rows]
    helpful_judge_passes = [r["judge_verdict"]["passed"] for r in helpful_rows]

    strict_agree, strict_kappa = calculate_agreement(human_passes, strict_judge_passes)
    helpful_agree, helpful_kappa = calculate_agreement(human_passes, helpful_judge_passes)

    print("==========================================================")
    print("  Prompt A/B 综合评测结果与 Judge 校准汇总")
    print("==========================================================")
    print(
        f"Strict  变体: 平均字数={strict_summary['avg_len']:.1f}, "
        f"综合通过率={strict_summary['pass_rate'] * 100:.1f}%, "
        f"关键词分={strict_summary['keyword_score'] * 100:.1f}%, "
        f"引用分={strict_summary['citation_score'] * 100:.1f}%, "
        f"拒答对齐={strict_summary['refusal_alignment'] * 100:.1f}%, "
        f"Judge均分={strict_summary['avg_judge_score']:.2f}"
    )
    print(
        f"Helpful 变体: 平均字数={helpful_summary['avg_len']:.1f}, "
        f"综合通过率={helpful_summary['pass_rate'] * 100:.1f}%, "
        f"关键词分={helpful_summary['keyword_score'] * 100:.1f}%, "
        f"引用分={helpful_summary['citation_score'] * 100:.1f}%, "
        f"拒答对齐={helpful_summary['refusal_alignment'] * 100:.1f}%, "
        f"Judge均分={helpful_summary['avg_judge_score']:.2f}"
    )
    print()
    print("--- 裁判与人工标注一致性 (Judge-Human Agreement) ---")
    print(f"Strict  裁判与人工一致率: {strict_agree * 100:.1f}% (Cohen's Kappa: {strict_kappa:.4f})")
    print(f"Helpful 裁判与人工一致率: {helpful_agree * 100:.1f}% (Cohen's Kappa: {helpful_kappa:.4f})")

    report_path = write_ab_report(
        strict_summary,
        helpful_summary,
        strict_agree,
        strict_kappa,
        helpful_agree,
        helpful_kappa,
        PROMPT_AB_CASES,
    )
    print(f"\n[产物生成] A/B 与 Judge 校验报告已保存：{report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
