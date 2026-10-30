"""章节 3.3 · 用大模型当裁判：LLM-as-Judge、校准与偏差缓解
==========================================================
核心能力与架构演进：
1. 关键词与规则评测过于死板，无法识别同义表达。LLM-as-Judge 能进行语义级评测，
   但裁判模型自身存在幻觉、格式波动、长度偏差（Verbosity Bias）与位置偏差（Position Bias）。
2. 本章采用原生 OpenAI SDK（无重型框架黑盒）实现生产级 Judge：
   - 双维度 Rubric 评分：语义正确性（Correctness）与证据忠实度（Faithfulness）；
   - 工具即输出（Tool-as-Output）：通过函数调用严格约束 JSON 结构化输出；
   - 候选位置互换（Position Swap）：双向评测减轻位置偏好与裁判自洽性核对；
   - 人工校准与一致性评估：计算混淆矩阵、一致率与 Cohen's Kappa（κ）系数。

运行模式：
  默认离线模式（无需 API Key，使用离线确定性替身与内置样本完整演练）：
    python tools/run_chapter.py 3.3
  在线真实模型调用（显式开启 --live，需配置模型环境变量）：
    python tools/run_chapter.py 3.3 --live
==========================================================
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
        SHARED_DATA_DIR,
        chat_model_name,
        get_openai_client,
    )
except ImportError:
    # 兼容直接从本章目录运行
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from common import (
        SHARED_DATA_DIR,
        chat_model_name,
        get_openai_client,
    )


# --------------------------- 异常与数据结构 ---------------------------

class JudgeFormatError(ValueError):
    """裁判输出不可解析、分数越界或理由为空。"""


REQUIRED_SAMPLE_KEYS = {"id", "human_pass", "judge_score"}

# 裁判工具契约（Tool-as-Output）
JUDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_verdict",
        "description": "提交评测裁判打分与理由",
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

# 内置兜底示范集
INLINE_DEMO = [
    {
        "id": "demo_01",
        "question": "RAG 是什么",
        "reference": "RAG 是检索增强生成，先检索相关内容再生成回答",
        "context": "检索增强生成（RAG）结合了外部检索系统与大语言模型，先从向量知识库中召回相关分块，再拼装上下文辅助生成准确答案。",
        "human_pass": True,
        "judge_score": 5,
    },
    {
        "id": "demo_02",
        "question": "FAISS 有什么作用",
        "reference": "FAISS 用来存向量并做相似度检索",
        "context": "FAISS 是 Facebook AI 开发的高性能向量相似度检索库，常用于密集向量索引构建与最近邻召回。",
        "human_pass": True,
        "judge_score": 4,
    },
    {
        "id": "demo_03",
        "question": "Python 默认的全局解释器锁是什么",
        "reference": "CPython 中的全局解释器锁（GIL）确保同一时刻只有一个线程执行 Python 字节码",
        "context": "SQLite 是一个自包含、无服务器的嵌入式 SQL 数据库引擎，不需要配置独立的守护进程。",
        "human_pass": False,
        "judge_score": 1,
    },
]


# --------------------------- Prompt 与解析逻辑 ---------------------------

def build_prompt(
    question: str,
    answer: str,
    reference: str,
    context: str,
) -> str:
    """构造标准 1–5 分 Rubric 裁判 prompt。"""
    return f"""你是一名资深 AI 评测专家与质量裁判。
请评估【模型答案】的语义正确性（与标准答案对比）和忠实度（与上下文对比）。

【问题】
{question}

【标准答案】
{reference}

【模型答案】
{answer}

【参考上下文】
{context}

【评分规则与 Rubric】
1. 评分范围：1 到 5 分（1分完全错误或严重幻觉，5分完全正确且证据充分）。
2. 语义对齐：只看意思，不纠结用词或表述风格差异。
3. 事实约束：模型答案必须严格依据上下文得出，不能编造无依据的信息。
4. 请输出 JSON 对象：{{"score": 1~5整数, "reason": "一句话理由"}}。
"""


def parse_verdict(text: str) -> dict[str, Any]:
    """解析裁判输出为 {"score": int, "reason": str}。"""
    if not isinstance(text, str):
        raise JudgeFormatError("输入必须为字符串")

    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if match:
        payload = match.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            payload = cleaned[start : end + 1]
        else:
            raise JudgeFormatError(f"未在裁判输出中找到有效 JSON 内容：{text[:100]}")

    try:
        data = json.loads(payload)
    except Exception as exc:
        raise JudgeFormatError(f"JSON 反序列化失败：{exc}") from exc

    if not isinstance(data, dict):
        raise JudgeFormatError("JSON 顶级数据结构必须为字典")

    if "score" not in data or "reason" not in data:
        raise JudgeFormatError("裁判输出缺少必需键 score 或 reason")

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
    question: str,
    answer: str,
    reference: str,
    context: str,
) -> dict[str, Any]:
    """使用 OpenAI 兼容 Tool-Calling（工具即输出）执行裁判打分。"""
    prompt = build_prompt(question, answer, reference, context)
    messages = [
        {"role": "system", "content": "你是一名公正的 AI 问答评测裁判，严格基于事实打分。请调用 submit_verdict 工具提交结构化打分。"},
        {"role": "user", "content": prompt},
    ]

    def _call(with_thinking_disabled: bool, force_tool: bool) -> Any:
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
        if with_thinking_disabled:
            kw["extra_body"] = {"thinking": {"type": "disabled"}}
        return client.chat.completions.create(**kw)

    try:
        try:
            # 优先显式关闭思考以允许强制工具调用（DeepSeek 等兼容）
            response = _call(with_thinking_disabled=True, force_tool=True)
        except Exception:
            try:
                response = _call(with_thinking_disabled=False, force_tool=False)
            except Exception:
                # 兜底直接生成
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.0,
                )

        choice = response.choices[0]
        if choice.message.tool_calls:
            call = choice.message.tool_calls[0]
            args = json.loads(call.function.arguments)
            score = int(args.get("score", 0))
            reason = str(args.get("reason", "")).strip()
            if 1 <= score <= 5 and reason:
                return {"score": score, "reason": reason, "method": "tool_calling"}
        # 回退至文本解析
        text = choice.message.content or ""
        parsed = parse_verdict(text)
        parsed["method"] = "text_fallback"
        return parsed
    except Exception as exc:
        raise RuntimeError(f"在线裁判模型调用失败：{exc}") from exc


def run_pairwise_comparison_with_position_swap(
    client: Any,
    model: str,
    question: str,
    answer_a: str,
    answer_b: str,
    reference: str,
) -> dict[str, Any]:
    """候选位置互换（Position Swap）：减轻大模型对首位（Position A）的系统性偏好。"""
    system_msg = "你是一名公正的对比评测裁判。请对比两位助手的回答，挑选更准确完整的一方；若质量无明显差异则判为 tie。"

    def _call_compare(ans_1: str, ans_2: str) -> dict[str, str]:
        prompt = f"""【用户问题】
{question}

【参考标准】
{reference}

【回答 1】
{ans_1}

【回答 2】
{ans_2}

请调用 compare_answers 工具指定优胜方（A 表示回答 1 更好，B 表示回答 2 更好，tie 表示两者水平相当）。"""
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]
        try:
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                tools=[PAIRWISE_TOOL],
                tool_choice="auto",
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception:
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                tools=[PAIRWISE_TOOL],
                tool_choice="auto",
            )
        choice = res.choices[0]
        if choice.message.tool_calls:
            args = json.loads(choice.message.tool_calls[0].function.arguments)
            return {"winner": args.get("winner", "tie"), "reason": args.get("reason", "")}
        # 简单正则解析
        content = choice.message.content or ""
        m = re.search(r"\b(A|B|tie)\b", content, re.IGNORECASE)
        w = m.group(1).upper() if m else "tie"
        return {"winner": w, "reason": content[:80]}

    # 轮次 1：正序 [A, B]
    round_1 = _call_compare(answer_a, answer_b)
    # 轮次 2：位置交换 [B, A]
    round_2 = _call_compare(answer_b, answer_a)

    w1 = round_1["winner"]  # 'A', 'B', 'tie'
    w2 = round_2["winner"]  # 'A', 'B', 'tie' (此处的 A 对应实际的 answer_b)

    # 映射回全局对象 A / B
    actual_winner_2 = "B" if w2 == "A" else ("A" if w2 == "B" else "tie")

    consistent = (w1 == actual_winner_2)
    position_bias_detected = (w1 == "A" and w2 == "A") or (w1 == "B" and w2 == "B")

    consensus = w1 if consistent else ("tie" if "tie" in (w1, actual_winner_2) else "inconsistent")

    return {
        "round_1_winner": w1,
        "round_2_winner": w2,
        "actual_round_2_preference": actual_winner_2,
        "consensus_winner": consensus,
        "consistent": consistent,
        "position_bias_detected": position_bias_detected,
        "round_1_reason": round_1["reason"],
        "round_2_reason": round_2["reason"],
    }


# --------------------------- 统计指标与 Cohen's Kappa ---------------------------

def calculate_agreement(human_labels: list[bool], judge_labels: list[bool]) -> float:
    """计算人工标注与裁判判定的一致率（Accuracy / Agreement Rate）。"""
    if not human_labels:
        return 0.0
    matches = sum(1 for h, j in zip(human_labels, judge_labels) if h == j)
    return matches / len(human_labels)


def calculate_cohens_kappa(human_labels: list[bool], judge_labels: list[bool]) -> float:
    """计算 Cohen's Kappa (κ) 系数，衡量超越随机巧合的一致性水平。

    κ = (Po - Pe) / (1 - Pe)
    其中 Po 为实测一致率，Pe 为双方边际概率相乘得到的偶然一致率。
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
    """使用带人工标签的金标准数据集校准裁判表现。"""
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

        s_id = s["id"]
        if s_id in seen_ids:
            raise ValueError(f"样本 ID 重复：{s_id}")
        seen_ids.add(s_id)

        h_pass = s["human_pass"]
        if not isinstance(h_pass, bool):
            raise ValueError(f"human_pass 必须为 bool：{h_pass}")

        j_score = s["judge_score"]
        if isinstance(j_score, bool) or not isinstance(j_score, int) or not (1 <= j_score <= 5):
            raise ValueError(f"judge_score 必须在 1-5 之间：{j_score}")

        validated_samples.append(s)

    total = len(validated_samples)
    scores = []
    tp = tn = fp = fn = 0
    disagreements = []
    human_flags = []
    judge_flags = []

    for s in validated_samples:
        score = judge_fn(s)
        scores.append(score)
        pred_pass = score >= threshold
        human_pass = s["human_pass"]

        human_flags.append(human_pass)
        judge_flags.append(pred_pass)

        if pred_pass and human_pass:
            tp += 1
        elif not pred_pass and not human_pass:
            tn += 1
        elif pred_pass and not human_pass:
            fp += 1
            disagreements.append(s["id"])
        else:
            fn += 1
            disagreements.append(s["id"])

    agreement = calculate_agreement(human_flags, judge_flags)
    kappa = calculate_cohens_kappa(human_flags, judge_flags)
    mean_score = sum(scores) / total

    return {
        "total": total,
        "threshold": threshold,
        "agreement": agreement,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "disagreements": disagreements,
        "mean_score": mean_score,
        "cohens_kappa": round(kappa, 4),
    }


# --------------------------- 评测集加载 ---------------------------

def load_eval_cases() -> list[dict[str, Any]]:
    """加载 3.4/3.5 生成的黄金测试集；若不存在则使用内置示范集。"""
    for name in ("eval_set_full.json", "eval_set.json"):
        p = SHARED_DATA_DIR / name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                filtered = [
                    r for r in data
                    if not r.get("should_refuse") and r.get("reference")
                ]
                if filtered:
                    return filtered
            except Exception:
                pass
    return INLINE_DEMO


# --------------------------- 主执行流程 ---------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="L3.4 原生 LLM-as-Judge 与校准演示")
    parser.add_argument("--live", action="store_true", help="显式开启真实模型调用")
    parser.add_argument("--limit", type=int, default=3, help="评测题目最大数量限制")
    args = parser.parse_args()

    print("==========================================================")
    print("  L3.4 LLM Judge、校准与偏差缓解（原生 OpenAI SDK 实现）")
    print("==========================================================")

    cases = load_eval_cases()[: args.limit]
    print(f"已加载 {len(cases)} 题进行裁判示范评测。")

    if not args.live:
        print("\n[模式说明] 当前为默认【离线确定性演练】模式（未指定 --live）。")
        print("展示离线替身裁判、Rubric 评分、位置互换防偏算法与 Cohen's κ 统计：\n")

        # 1. 单条 Rubric 评分示范
        demo_case = cases[0]
        q = demo_case["question"]
        ref = demo_case.get("reference", "检索增强生成标准参考")
        ans = "RAG 结合了检索和大模型生成，能根据知识库内容进行可靠作答。"
        ctx = demo_case.get("context", "RAG 能够通过语义相似度召回文档并输入给生成模型。")

        # 离线确定性打分替身
        def offline_scripted_llm(p: str) -> str:
            return json.dumps({
                "score": 5,
                "reason": "[离线确定性模拟] 模型答案完整涵盖检索与生成双要素，与参考答案高度吻合且忠于上下文。"
            }, ensure_ascii=False)

        verdict = judge(q, ans, ref, ctx, offline_scripted_llm)
        print(f"题目：{q}")
        print(f"模型回答：{ans}")
        print(f"裁判打分：{verdict['score']}/5 分")
        print(f"裁判理由：{verdict['reason']}（调用尝试次数：{verdict['attempts']}）\n")

        # 2. 候选位置互换（Position Swap）演示
        ans_a = "RAG 架构先检索向量数据库，再由生成模型总结。"
        ans_b = "RAG 是检索系统。"
        print("--- 候选位置互换（Position Bias 防御演示）---")
        print(f"回答 A: {ans_a}")
        print(f"回答 B: {ans_b}")
        print("模拟第 1 轮 [A, B] 评判：获胜方 A（理由：A 更加详尽完整）")
        print("模拟第 2 轮 [B, A] 互换评判：获胜方 B（对应实际 A；理由：回答 2 准确）")
        print("→ 双向一致性校验通过：消除首位偏见（Position Bias），确认共识胜出者为 A。\n")

        # 3. 人工校准与 Cohen's Kappa 统计
        calibration_set = [
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
        cal_report = calibrate(calibration_set, lambda s: s["judge_score"], threshold=4)
        print("--- 裁判人工校准报告（金标准校准集）---")
        print(f"校准样本总量: {cal_report['total']} 条")
        print(f"判定阈值: score >= {cal_report['threshold']}")
        print(f"一致率 (Agreement Rate): {cal_report['agreement']:.2%} ({cal_report['confusion']['tp'] + cal_report['confusion']['tn']}/{cal_report['total']})")
        print(f"Cohen's Kappa (κ): {cal_report['cohens_kappa']} (衡量剔除随机偶然性后的一致度)")
        print(f"混淆矩阵: TP={cal_report['confusion']['tp']}, TN={cal_report['confusion']['tn']}, FP={cal_report['confusion']['fp']}, FN={cal_report['confusion']['fn']}")
        print(f"分歧用例 ID: {cal_report['disagreements']}")
        print("\n[离线演练完成] 如需调用商用大模型，请配置 API 密钥并附加 --live 参数运行。")
        return 0

    # 在线真实调用模式
    print("\n[在线模式] 正在初始化原生 OpenAI 客户端...")
    try:
        client = get_openai_client(timeout=20.0, max_retries=1)
        model = chat_model_name()
    except Exception as exc:
        print(f"[配置错误] 无法获取模型客户端或模型名称：{exc}", file=sys.stderr)
        print("请检查环境变量（如 DEEPSEEK_API_KEY / OPENAI_API_KEY）或本地 .env 配置。", file=sys.stderr)
        return 1

    try:
        print(f"使用模型：{model}")
        for idx, case in enumerate(cases, 1):
            q = case["question"]
            ref = case.get("reference", "")
            ctx = case.get("context", ref)
            mock_ans = f"依据提供的资料，{ref}。"

            print(f"\n--- 用例 {idx}/{len(cases)}: {q} ---")
            verdict = run_native_judge_eval(client, model, q, mock_ans, ref, ctx)
            print(f"裁判打分: {verdict['score']}/5 分 [{verdict.get('method')}]")
            print(f"理由: {verdict['reason']}")

            # 位置互换示例
            swap_res = run_pairwise_comparison_with_position_swap(
                client, model, q,
                answer_a=mock_ans,
                answer_b="信息不详，未能明确找到对应答案。",
                reference=ref
            )
            print(f"位置互换共识: 优胜方={swap_res['consensus_winner']}, 自洽性={swap_res['consistent']}")
    except Exception as exc:
        print(f"\n[运行失败] 在线模型请求发生网络或认证错误：{exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
