"""章节 3.4 · LLM Judge 与校准：双维度 Rubric 评分、位置偏见缓解与一致性校准
======================================================================
核心能力：
1. 为什么需要大模型当裁判（LLM-as-judge）？
   - 规则与字符串匹配（如包含关键字）过于死板，无法处理“同义不同词”；
   - 评测阶梯原则：优先使用确定性代码/规则判分，在需要语义理解和灵活表达判断时
     引入 LLM 裁判，并用人工标注集定期校准裁判。
2. 双维度 Rubric（评分量表）设计：
   - 答案正确性（Correctness）：对比标准答案（Reference），判断核心语义是否一致；
   - 忠实度（Faithfulness）：对比检索上下文（Context），判断是否完全基于事实、有无幻觉。
3. 位置偏见（Position Bias）缓解：
   - 模型在成对对比（Pairwise Comparison）时往往系统性偏向排在首位的候选回答；
   - 采用位置互换机制（Position Swap）：正序 [A, B] 与逆序 [B, A] 双轮对比，识别并缓解偏见。
4. 校准与统计指标：
   - 裁判输出结构化结果（分数 + 理由），避免模糊自由文本；
   - 一致率（Agreement Rate）与 Cohen's Kappa（κ）系数，排除偶然一致后的真实相关度。

运行模式：
  默认离线确定性演练（包含真实执行的脚本化位置互换与合成示范集校准）：
    python tools/run_chapter.py 3.3
  显式在线真实大模型评测（需配置 API Key）：
    python tools/run_chapter.py 3.3 --live
======================================================================
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

# 优先导入 common 模块
try:
    from common import (
        SAMPLE_DOC,
        chat_model_name,
        get_openai_client,
    )
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from common import (
        SAMPLE_DOC,
        chat_model_name,
        get_openai_client,
    )


# --------------------------- 异常与数据结构 ---------------------------

class JudgeFormatError(ValueError):
    """裁判输出无法解析为结构化评分或字段校验失败。"""


# 必需样本字段
REQUIRED_SAMPLE_KEYS = {"id", "human_pass", "judge_score"}

# 裁判工具契约（Tool-as-Output）：约束模型输出严格的 JSON Schema 结构
JUDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_verdict",
        "description": "提交评测裁判的打分结果与理由",
        "parameters": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "integer",
                    "description": "1 到 5 分的整数评分，5 分最好",
                    "minimum": 1,
                    "maximum": 5,
                },
                "reason": {
                    "type": "string",
                    "description": "打分理由，简明陈述打分依据与优缺点",
                },
            },
            "required": ["score", "reason"],
        },
    },
}

# 候选两两对比工具契约（Pairwise Comparison）
PAIRWISE_TOOL = {
    "type": "function",
    "function": {
        "name": "compare_answers",
        "description": "对比候选回答 A 与候选回答 B 并给出优胜方",
        "parameters": {
            "type": "object",
            "properties": {
                "winner": {
                    "type": "string",
                    "enum": ["A", "B", "tie"],
                    "description": "更优回答：A、B 或 tie（平局）",
                },
                "reason": {
                    "type": "string",
                    "description": "胜出或平局的核心理由",
                },
            },
            "required": ["winner", "reason"],
        },
    },
}

# 本章内置合成示范集（仅用于离线教学与门禁验证，非真实生产金标准）
INLINE_CALIBRATION_SAMPLES = [
    {"id": "c01", "human_pass": True, "judge_score": 5},
    {"id": "c02", "human_pass": True, "judge_score": 4},
    {"id": "c03", "human_pass": True, "judge_score": 3},
    {"id": "c04", "human_pass": True, "judge_score": 2},
    {"id": "c05", "human_pass": False, "judge_score": 1},
    {"id": "c06", "human_pass": False, "judge_score": 2},
    {"id": "c07", "human_pass": False, "judge_score": 5},
    {"id": "c08", "human_pass": False, "judge_score": 4},
    {"id": "c09", "human_pass": True, "judge_score": 5},
    {"id": "c10", "human_pass": False, "judge_score": 1},
    {"id": "c11", "human_pass": True, "judge_score": 4},
    {"id": "c12", "human_pass": False, "judge_score": 3},
]


# --------------------------- Prompt 构建与解析 ---------------------------

def build_prompt(question: str, answer: str, reference: str, context: str) -> str:
    """构建综合评测裁判 Prompt，明确 Rubric 评分标准与约束。"""
    return f"""你是一名严格、客观的 AI 问答评测裁判。请基于以下材料对【模型回答】打分。

【用户问题】
{question}

【参考标准答案】
{reference}

【检索上下文】
{context}

【待评测模型回答】
{answer}

【打分 Rubric 量表 (1-5 分)】
5分：完全正确且忠实。回答与标准答案核心意思完全一致（只看意思，不纠结用词），且内容严格依据上下文，无任何编造。
4分：核心正确。重要信息无遗漏，个别非关键细节微小欠缺，无编造虚假信息。
3分：部分正确。包含部分有效事实，但存在轻微偏差或遗漏了重要要点。
2分：大部分错误或不忠实。核心事实出现严重偏差，或脱离检索上下文编造信息（幻觉）。
1分：完全错误、严重幻觉或完全未回答问题。

请只看意思、不纠结措辞；必须严格核查回答是否依据上下文，严防编造信息。
请输出包含 "score"（1-5 整数）和 "reason"（非空说明字符串）的结构化 JSON。"""


def build_correctness_prompt(question: str, answer: str, reference: str) -> str:
    """构建【正确性】单维度裁判 Prompt：对比标准答案，只看意思不纠结措辞。"""
    return f"""你是答案正确性评测裁判。请对比【模型回答】与【参考标准】，按 1-5 分打分（只看意思，不纠结用词措辞）。

【用户问题】
{question}

【参考标准】
{reference}

【模型回答】
{answer}

打分规则：5分=意思完全一致；3分=部分一致但有缺失；1分=完全不一致。请调用 submit_verdict 提交结果。"""


def build_faithfulness_prompt(question: str, answer: str, context: str) -> str:
    """构建【忠实度】单维度裁判 Prompt：检查是否依据上下文，杜绝编造幻觉。"""
    return f"""你是忠实度评测裁判。请检查【模型回答】是否严格依据【检索上下文】得出，判断有无编造未提及的内容（防幻觉）。

【用户问题】
{question}

【检索上下文】
{context}

【模型回答】
{answer}

打分规则：5分=完全源自上下文且无编造；3分=部分事实未经上下文证实；1分=严重脱离事实编造。请调用 submit_verdict 提交结果。"""


def parse_verdict(raw_reply: str) -> dict[str, Any]:
    """从大模型原始文本中稳健提取并校验 score 与 reason。"""
    if not isinstance(raw_reply, str):
        raise JudgeFormatError(f"raw_reply 必须为字符串，收到：{type(raw_reply).__name__}")

    text = raw_reply.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    candidate_json = text
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}")
        candidate_json = text[start : end + 1]

    try:
        data = json.loads(candidate_json)
    except Exception as exc:
        raise JudgeFormatError(f"输出无法解析为合法 JSON：{text[:100]}") from exc

    if not isinstance(data, dict):
        raise JudgeFormatError(f"JSON 顶层必须为字典对象，收到：{type(data).__name__}")

    if "score" not in data:
        raise JudgeFormatError("JSON 缺少必需字段 'score'")
    if "reason" not in data:
        raise JudgeFormatError("JSON 缺少必需字段 'reason'")

    score = data["score"]
    reason = data["reason"]

    if isinstance(score, bool) or not isinstance(score, int):
        raise JudgeFormatError(f"score 必须为整数类型，实际收到 {type(score).__name__}: {score}")

    if not (1 <= score <= 5):
        raise JudgeFormatError(f"score 评分越界（需为 1~5），实际收到 {score}")

    if not isinstance(reason, str) or not reason.strip():
        raise JudgeFormatError("reason 必须为非空字符串")

    return {"score": score, "reason": reason.strip()}


def judge(
    question: str,
    answer: str,
    reference: str,
    context: str,
    llm_fn: Callable[[str], str],
    attempts: int = 2,
) -> dict[str, Any]:
    """调用裁判并执行自动重试与格式校验。"""
    if attempts < 1:
        raise ValueError(f"attempts 必须大于等于 1，实际为 {attempts}")

    prompt = build_prompt(question, answer, reference, context)
    last_err: Exception | None = None

    for attempt_idx in range(1, attempts + 1):
        try:
            raw_reply = llm_fn(prompt)
            verdict = parse_verdict(raw_reply)
            return {
                "score": verdict["score"],
                "reason": verdict["reason"],
                "attempts": attempt_idx,
            }
        except (JudgeFormatError, Exception) as exc:
            last_err = exc

    raise JudgeFormatError(f"裁判重试 {attempts} 次后仍未获得合法格式输出，最后原因：{last_err}")


# --------------------------- 原生 OpenAI SDK 裁判调用 ---------------------------

def run_native_judge_eval(
    client: Any,
    model: str,
    prompt: str,
    attempts: int = 2,
) -> dict[str, Any]:
    """使用 OpenAI 兼容 Tool-Calling 执行单项裁判打分，支持重试与格式校验。"""
    if attempts < 1:
        raise ValueError(f"attempts 必须大于等于 1，实际为 {attempts}")

    messages = [
        {"role": "system", "content": "你是一名公正的 AI 问答评测裁判，严格基于事实打分。请调用 submit_verdict 工具提交打分。"},
        {"role": "user", "content": prompt},
    ]

    def _call(force_tool: bool, disable_thinking: bool) -> Any:
        kw: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "tools": [JUDGE_TOOL],
        }
        if force_tool:
            kw["tool_choice"] = {"type": "function", "function": {"name": "submit_verdict"}}
        else:
            kw["tool_choice"] = "auto"
        if disable_thinking:
            kw["extra_body"] = {"thinking": {"type": "disabled"}}
        return client.chat.completions.create(**kw)

    last_err: Exception | None = None

    for attempt_idx in range(1, attempts + 1):
        try:
            # 优先显式关闭思考以允许强制工具调用（对齐 DeepSeek 等平台规范）
            try:
                response = _call(force_tool=True, disable_thinking=True)
            except Exception as exc:
                # 仅针对特定的 400 思考模式冲突错误进行安全降级
                err_str = str(exc).lower()
                is_thinking_conflict = (
                    getattr(exc, "status_code", None) == 400
                    and ("thinking" in err_str or "tool_choice" in err_str)
                )
                if is_thinking_conflict:
                    response = _call(force_tool=False, disable_thinking=False)
                else:
                    raise  # 鉴权 401、网络不可达等直接抛出，不盲目重试

            choice = response.choices[0]
            if choice.message.tool_calls:
                call = choice.message.tool_calls[0]
                args = json.loads(call.function.arguments)
                score = int(args.get("score", 0))
                reason = str(args.get("reason", "")).strip()
                if 1 <= score <= 5 and reason:
                    return {"score": score, "reason": reason, "attempts": attempt_idx, "method": "tool_calling"}

            # 回退至从文本内容解析
            text = choice.message.content or ""
            parsed = parse_verdict(text)
            parsed["attempts"] = attempt_idx
            parsed["method"] = "text_fallback"
            return parsed
        except (JudgeFormatError, json.JSONDecodeError) as exc:
            last_err = exc
        except Exception:
            raise

    raise JudgeFormatError(f"裁判重试 {attempts} 次后仍未获得合法格式输出，最后原因：{last_err}")


# --------------------------- 候选位置互换（Position Swap） ---------------------------

def run_pairwise_comparison_with_position_swap(
    compare_fn: Callable[[str, str], dict[str, str]],
    question: str,
    answer_a: str,
    answer_b: str,
    reference: str,
) -> dict[str, Any]:
    """候选位置互换（Position Swap）：减轻大模型对首位（Position A）的系统性偏好。

    compare_fn 签名为 compare_fn(ans_1, ans_2) -> {"winner": "A"|"B"|"tie", "reason": str}。
    """
    # 轮次 1：正序呈现 [Candidate A, Candidate B]
    round_1 = compare_fn(answer_a, answer_b)
    # 轮次 2：逆序呈现 [Candidate B, Candidate A]
    round_2 = compare_fn(answer_b, answer_a)

    w1 = round_1.get("winner", "tie")
    w2 = round_2.get("winner", "tie")

    # 映射回全局对象 A / B
    # 在轮次 2 中：位置 1 为 candidate B，位置 2 为 candidate A
    # 因此若轮次 2 选择位置 1 (即 'A')，代表偏好 Candidate B；若选择位置 2 (即 'B')，代表偏好 Candidate A
    if w2 == "A":
        actual_winner_2 = "B"
    elif w2 == "B":
        actual_winner_2 = "A"
    else:
        actual_winner_2 = "tie"

    consistent = (w1 == actual_winner_2)
    # 首位偏见检测：两轮评测均偏好出现在第 1 个位置的选项（轮次 1 选 A，轮次 2 选 A）
    position_bias_detected = (w1 == "A" and w2 == "A") or (w1 == "B" and w2 == "B")

    if consistent:
        consensus = w1
    elif "tie" in (w1, actual_winner_2):
        consensus = "tie"
    else:
        consensus = "inconsistent"

    return {
        "round_1_winner": w1,
        "round_2_winner": w2,
        "actual_round_2_preference": actual_winner_2,
        "consensus_winner": consensus,
        "consistent": consistent,
        "position_bias_detected": position_bias_detected,
        "round_1_reason": round_1.get("reason", ""),
        "round_2_reason": round_2.get("reason", ""),
    }


# --------------------------- 统计指标与 Cohen's Kappa ---------------------------

def calculate_agreement(human_labels: list[bool], judge_labels: list[bool]) -> float:
    """计算人工标注与裁判判定的一致率（Agreement Rate）。"""
    if not human_labels or len(human_labels) != len(judge_labels):
        return 0.0
    matches = sum(1 for h, j in zip(human_labels, judge_labels) if h == j)
    return matches / len(human_labels)


def calculate_cohens_kappa(human_labels: list[bool], judge_labels: list[bool]) -> float:
    """计算 Cohen's Kappa (κ) 系数，衡量超越偶然一致性的真实一致水平。

    κ = (Po - Pe) / (1 - Pe)
    Po 为观察一致率，Pe 为双方边际概率相乘得到的偶然期望一致率。
    """
    if not human_labels or len(human_labels) != len(judge_labels):
        return 0.0

    n = len(human_labels)
    tp = sum(1 for h, j in zip(human_labels, judge_labels) if h and j)
    tn = sum(1 for h, j in zip(human_labels, judge_labels) if not h and not j)
    fp = sum(1 for h, j in zip(human_labels, judge_labels) if not h and j)
    fn = sum(1 for h, j in zip(human_labels, judge_labels) if h and not j)

    po = (tp + tn) / n

    p_human_pos = (tp + fn) / n
    p_human_neg = (tn + fp) / n
    p_judge_pos = (tp + fp) / n
    p_judge_neg = (tn + fn) / n

    pe = (p_human_pos * p_judge_pos) + (p_human_neg * p_judge_neg)

    if abs(1.0 - pe) < 1e-9:
        return 1.0 if abs(po - 1.0) < 1e-9 else 0.0

    return (po - pe) / (1.0 - pe)


def calibrate(
    samples: list[dict],
    judge_fn: Callable[[dict], int],
    threshold: int = 4,
) -> dict[str, Any]:
    """使用带人工标签的校准集评估裁判表现并计算混淆矩阵。"""
    if not isinstance(samples, list):
        raise ValueError("samples 必须为列表")

    if not samples:
        return {
            "total": 0,
            "threshold": threshold,
            "agreement": 0.0,
            "confusion": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
            "disagreements": [],
            "mean_score": 0.0,
            "cohens_kappa": 0.0,
        }

    seen_ids = set()
    validated_samples = []

    for s in samples:
        if not isinstance(s, dict):
            raise ValueError(f"样本必须为字典：{s}")
        if not REQUIRED_SAMPLE_KEYS.issubset(s.keys()):
            raise ValueError(f"样本缺少必需字段：{s}")

        if not isinstance(s["human_pass"], bool):
            raise ValueError(f"human_pass 必须为 bool 类型：{s}")

        score_val = s["judge_score"]
        if isinstance(score_val, bool) or not isinstance(score_val, int) or not (1 <= score_val <= 5):
            raise ValueError(f"judge_score 必须在 1-5 之间：{s}")

        s_id = s["id"]
        if s_id in seen_ids:
            raise ValueError(f"样本 id 重复：{s_id}")
        seen_ids.add(s_id)
        validated_samples.append(s)

    human_labels: list[bool] = []
    judge_labels: list[bool] = []
    scores: list[int] = []
    disagreements: list[str] = []

    tp = tn = fp = fn = 0

    for s in validated_samples:
        score = judge_fn(s)
        scores.append(score)

        h_pass = bool(s["human_pass"])
        j_pass = (score >= threshold)

        human_labels.append(h_pass)
        judge_labels.append(j_pass)

        if h_pass and j_pass:
            tp += 1
        elif (not h_pass) and (not j_pass):
            tn += 1
        elif (not h_pass) and j_pass:
            fp += 1
            disagreements.append(s["id"])
        else:
            fn += 1
            disagreements.append(s["id"])

    agreement = calculate_agreement(human_labels, judge_labels)
    kappa = calculate_cohens_kappa(human_labels, judge_labels)
    mean_score = sum(scores) / len(scores)

    return {
        "total": len(validated_samples),
        "threshold": threshold,
        "agreement": agreement,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "disagreements": disagreements,
        "mean_score": mean_score,
        "cohens_kappa": kappa,
    }


# --------------------------- 本地轻量原生 RAG 生成与检索 ---------------------------

def retrieve_context_offline(question: str) -> str:
    """从本地样本知识库读取检索上下文。"""
    if SAMPLE_DOC.exists():
        raw = SAMPLE_DOC.read_text(encoding="utf-8")
        # 简单按段落检索
        paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
        q_words = set(re.findall(r"\w+", question.lower()))
        scored = []
        for p in paragraphs:
            score = sum(1 for w in q_words if w in p.lower())
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored and scored[0][0] > 0 else raw[:300]
    return "检索增强生成（RAG）结合外部向量知识库与大语言模型，先召回相关分块再回答。"


def generate_rag_answer_live(client: Any, model: str, question: str, context: str) -> str:
    """在 live 模式下真实请求被测系统生成回答。"""
    prompt = f"请严格基于以下上下文回答问题。上下文：\n{context}\n问题：{question}"
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return res.choices[0].message.content or ""


# --------------------------- 主程序 ---------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="L3.4 LLM Judge 评测、双维度 Rubric 与位置偏见校准")
    parser.add_argument("--live", action="store_true", help="显式开启真实大模型在线评测")
    args = parser.parse_args()

    print("==========================================================")
    print("  L3.4 LLM Judge：双维度 Rubric、位置偏见与校准（原生实现）")
    print("==========================================================")

    # 1. 离线确定性演练
    if not args.live:
        print("[模式说明] 当前为默认【离线确定性演练】模式（未指定 --live）。")
        print("展示双维度 Rubric 判分、执行位置偏见（Position Swap）算法与合成示范集校准：\n")

        q = "什么是检索增强生成（RAG）？"
        ref = "RAG 是检索增强生成，先从外部知识库检索相关分块，再拼装上下文交由模型生成准确答案。"
        ctx = retrieve_context_offline(q)
        ans = "RAG 是检索增强生成技术。它先检索知识库中的文档片段，再利用这些片段生成回答，能显著减少幻觉。"

        print(f"【被测题目】: {q}")
        print(f"【检索上下文】: {ctx[:60]}...")
        print(f"【参考答案】: {ref}")
        print(f"【待评回答】: {ans}")

        # 离线模拟裁判打分
        print("\n--- 1. 双维度 Rubric 打分演示 ---")
        _ = build_correctness_prompt(q, ans, ref)
        _ = build_faithfulness_prompt(q, ans, ctx)
        v_c = parse_verdict('{"score": 5, "reason": "回答准确概括了先检索后生成的机制，与参考标准核心意思一致。"}')
        v_f = parse_verdict('{"score": 5, "reason": "回答内容完全依据所给上下文，无额外虚构。"}')
        print(f"[正确性 Correctness]: {v_c['score']}/5 —— {v_c['reason']}")
        print(f"[忠实度 Faithfulness]: {v_f['score']}/5 —— {v_f['reason']}")

        # 真实执行脚本化位置互换（Position Swap）演示
        print("\n--- 2. 候选位置互换（Position Swap）真实执行演示 ---")
        cand_a = "RAG 能够先检索外部数据库，再交由大语言模型总结回答。"
        cand_b = "RAG 是一种结合了检索与生成的现代化系统架构。"

        # 构造脚本化评测客户端模拟具有首位偏好（Position Bias）的裁判
        def scripted_compare_bias(a: str, b: str) -> dict[str, str]:
            # 模拟偏向排在首位的选项
            return {"winner": "A", "reason": "首位回答表达更简洁"}

        swap_res = run_pairwise_comparison_with_position_swap(
            scripted_compare_bias, q, cand_a, cand_b, ref
        )
        print(f"候选 A: {cand_a}")
        print(f"候选 B: {cand_b}")
        print(f"轮次 1 正序 [A, B] 优胜方: {swap_res['round_1_winner']}")
        print(f"轮次 2 逆序 [B, A] 优胜方: {swap_res['round_2_winner']} (映射对应候选: {swap_res['actual_round_2_preference']})")
        print(f"判定结果: consistent={swap_res['consistent']}, position_bias_detected={swap_res['position_bias_detected']}")
        print(f"最终共识判决: {swap_res['consensus_winner']}（检测到首位偏见，有效避免误判 A 为绝对优胜）")

        # 合成示范集校准
        print("\n--- 3. 裁判校准评估报告（合成示范集）---")
        cal_report = calibrate(
            INLINE_CALIBRATION_SAMPLES,
            lambda s: s["judge_score"],
            threshold=4,
        )
        print(f"校准样本量: {cal_report['total']} 条（注：此为教学合成数据）")
        print(f"一致率 (Agreement Rate): {cal_report['agreement'] * 100:.2f}%")
        print(f"Cohen's Kappa (κ): {cal_report['cohens_kappa']:.4f}")
        print(f"混淆矩阵: {cal_report['confusion']}")
        print(f"分歧用例 ID: {cal_report['disagreements']}")
        print("\n[离线演练完成] 如需调用真实大模型进行在线评测，请添加 --live 参数。")
        return 0

    # 2. 在线真实评测模式
    print("[在线模式] 正在初始化原生 OpenAI 客户端...")
    try:
        client = get_openai_client(timeout=30.0, max_retries=1)
        model = chat_model_name()
    except Exception as exc:
        print(f"[配置错误] 无法获取模型客户端或模型名称：{exc}", file=sys.stderr)
        print("请检查环境变量或 .env 配置。", file=sys.stderr)
        return 1

    # 读取测试样本
    eval_cases = [
        {
            "question": "RAG 是什么？",
            "reference": "RAG 是检索增强生成，先从外部知识库检索相关内容，再拼装上下文交由大模型生成回答。",
        },
        {
            "question": "向量检索在 RAG 中起到什么作用？",
            "reference": "向量检索将文本转化为高维向量，通过计算相似度在知识库中快速召回语义相关的文档分块。",
        },
    ]

    print(f"使用模型: {model}，正在评测 {len(eval_cases)} 条真实 RAG 用例（双维度打分）...\n")

    for idx, c in enumerate(eval_cases, start=1):
        q = c["question"]
        ref = c["reference"]
        ctx = retrieve_context_offline(q)

        try:
            print(f"--- 用例 {idx}/{len(eval_cases)}: {q} ---")
            ans = generate_rag_answer_live(client, model, q, ctx)
            print(f"被测系统回答: {ans[:80]}...")

            # 1. 答案正确性评测
            p_correct = build_correctness_prompt(q, ans, ref)
            verdict_c = run_native_judge_eval(client, model, p_correct)
            print(f"  [正确性 Correctness]: {verdict_c['score']}/5 —— {verdict_c['reason']}")

            # 2. 忠实度评测
            p_faith = build_faithfulness_prompt(q, ans, ctx)
            verdict_f = run_native_judge_eval(client, model, p_faith)
            print(f"  [忠实度 Faithfulness]: {verdict_f['score']}/5 —— {verdict_f['reason']}\n")
        except Exception as exc:
            print(f"[评测失败] 用例 '{q}' 请求模型或打分出错：{exc}", file=sys.stderr)
            return 1

    print("[在线评测完成] 真实大模型裁判双维度打分执行完毕。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
