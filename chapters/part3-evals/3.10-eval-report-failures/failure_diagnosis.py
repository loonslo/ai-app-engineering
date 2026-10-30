"""
章节 3.10 · 失败诊断：这条失败坏在哪一层
==========================================================
职责边界：本文件只做一件事，诊断，即回答"这条失败坏在哪一层"。
发布判决（门禁）不在这里做，由 capstone/ci_gate.py 和 CI 工作流负责（7.6 / step1）：
诊断给出证据，门禁据此拦截；两套判决就会分叉。

两层诊断：
  一级分流：用已算好的硬指标（refusal_ok / keyword_score / citation_score）给失败分组，
            标注"疑似层"。硬指标比对的是字符串，测不准语义，所以只分组、不下结论。
            便宜，不需要 key。
  二级复核：DeepEval 维度分（仅 live 模式，需要真实的 retrieval_context）
     Faithfulness        答案是否忠于召回的上下文（揪出幻觉）
     AnswerRelevancy     答案是否切题（揪出答非所问）
     ContextualPrecision 召回内容是否真相关（揪出检索层问题）
       需要参考答案；case 缺 reference 时跳过该指标并明确标注，绝不拿空字符串算出垃圾分。
     DeepEval 也是 LLM-as-judge，有固有的漏检，结论一律标为"证据 / 建议"。

失败库的来源（按优先级）：
  1. --input 指定的文件
  2. chapters/shared-data/failures.json：运行 3.7 时加 --write-failures 生成，含真实 retrieval_context
  3. 本章自带的合成样本 failures_sample.json：离线，只做一级分流

前置：3.7（可选）；live 模式另需 pip install deepeval 和 DEEPSEEK_API_KEY
运行：
  python tools/run_chapter.py 3.10                      自动选择失败库并推断模式
  python tools/run_chapter.py 3.10 --input 路径          指定失败库
  python tools/run_chapter.py 3.10 --limit 5            live 模式下最多复核 5 条（控制 token 成本）
输出：reports/failure_diagnosis.json（失败根因分布 + 每条证据），写在本章目录
==========================================================
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from common import SHARED_DATA_DIR
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from common import SHARED_DATA_DIR

REPORTS = Path(__file__).resolve().parent / "reports"
DIAGNOSIS = REPORTS / "failure_diagnosis.json"
SAMPLE_FAILURES = Path(__file__).with_name("failures_sample.json")   # 本章自带的合成样本

# 与 run_eval_platform 一致的硬指标阈值（仅用于一级弱信号分流）
CITE_THRESHOLD = 0.67
KEYWORD_THRESHOLD = 0.67
# DeepEval 维度分低于此值时，在证据里标注「疑似」（只是标注，不是判决）
DIM_FLAG = 0.7


# ═══════════════════════════════════════════════════════════════
# 一、加载失败库（带真实 retrieval_context 才可信）
# ═══════════════════════════════════════════════════════════════

def default_failures_path() -> Path:
    """优先用 3.7 生成的真实失败库，没有就用本章自带的合成样本。"""
    real = SHARED_DATA_DIR / "failures.json"
    return real if real.exists() else SAMPLE_FAILURES


def load_failures(path: Path | str) -> tuple[list[dict], str]:
    """返回 (失败列表, 失败库来源模式)。

    来源模式通过是否携带真实 retrieval_context 推断：
      - 任一失败 case 带非空 retrieval_context → live 产物（维度分可信）
      - 否则 → offline 产物（只能做一级分流）
    """
    p = Path(path)
    if not p.exists():
        raise ValueError(f"未找到失败库：{p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"JSON 解析失败：{exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"顶层结构必须为列表：{type(data).__name__}")
    failures = [d for d in data if isinstance(d, dict) and not d.get("passed", True)]
    is_live = any(bool((f.get("retrieval_context") or "").strip()) for f in failures)
    return failures, ("live" if is_live else "offline")


def summarize_layers(results: list[dict]) -> dict[str, int]:
    """统计各 layer_suspected 的数量，返回 {layer: count}。"""
    summary: dict[str, int] = {}
    for r in results:
        layer = r.get("layer_suspected", "未知")
        summary[layer] = summary.get(layer, 0) + 1
    return summary


# ═══════════════════════════════════════════════════════════════
# 二、一级分流：硬指标弱信号分组（零依赖，明确标注「疑似/待复核」）
# ═══════════════════════════════════════════════════════════════

def classify_by_hard_metrics(failure: dict) -> tuple[str, str]:
    """用硬指标做「弱信号」分组。只分组，不判决——判决靠二级复核。"""
    refusal_ok = failure.get("refusal_ok", True)
    keyword = failure.get("keyword_score", 1.0)
    citation = failure.get("citation_score", 1.0)

    if not refusal_ok:
        return ("拒答逻辑层(疑似)", "refusal_ok=False：建议复核拒答决策是否正确")
    if citation < CITE_THRESHOLD:
        return ("检索/引用层(疑似)", f"citation_score={citation:.2f} < {CITE_THRESHOLD}：建议用 ContextualPrecision 复核")
    if keyword < KEYWORD_THRESHOLD:
        return ("生成层(疑似)", f"keyword_score={keyword:.2f} < {KEYWORD_THRESHOLD}：建议用 Faithfulness/AnswerRelevancy 复核")
    return ("其他/未覆盖(疑似)", "硬指标通过但整体未通过，需人工复核（如工具调用约束）")


# ═══════════════════════════════════════════════════════════════
# 三、二级复核：DeepEval 维度分（成熟框架，吃真实 retrieval_context）
# ═══════════════════════════════════════════════════════════════

def measure_with_deepeval(failure: dict) -> dict:
    """对单条失败 case 调 DeepEval 算维度分。需 DEEPSEEK_API_KEY。

    诚实规则：
      - 无 retrieval_context → 上游数据不完整，直接不算（调用方已拦）
      - 无 reference/expected_output → ContextualPrecision 跳过并标注，
        不喂空 ground truth 算垃圾分
    """
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from deepeval.models.llms.deepseek_model import DeepSeekModel
        from deepeval.metrics import (
            FaithfulnessMetric,
            AnswerRelevancyMetric,
            ContextualPrecisionMetric,
        )
        from deepeval.test_case import LLMTestCase
    except ImportError as e:
        return {"error": f"deepeval 未安装: {e}"}

    try:
        eval_model = DeepSeekModel(model="deepseek-chat")
    except Exception as exc:
        return {"error": f"初始化 DeepSeekModel 失败: {exc}"}
    retrieval_context = failure.get("retrieval_context") or ""
    expected_output = failure.get("reference") or failure.get("expected_output") or ""

    tc = LLMTestCase(
        input=failure.get("question", failure.get("case_id", "")),
        actual_output=failure.get("answer", ""),
        expected_output=expected_output,
        retrieval_context=[retrieval_context] if retrieval_context else [],
    )

    out = {}
    # 每条指标独立 try，单条失败不拖垮整轮诊断
    try:
        m = FaithfulnessMetric(model=eval_model, async_mode=False)
        out["faithfulness"] = round(m.measure(tc), 3)
    except Exception as e:
        out["faithfulness"] = f"error:{e}"
    try:
        m = AnswerRelevancyMetric(model=eval_model, async_mode=False)
        out["answer_relevancy"] = round(m.measure(tc), 3)
    except Exception as e:
        out["answer_relevancy"] = f"error:{e}"
    if expected_output.strip():
        try:
            m = ContextualPrecisionMetric(model=eval_model, async_mode=False)
            out["contextual_precision"] = round(m.measure(tc), 3)
        except Exception as e:
            out["contextual_precision"] = f"error:{e}"
    else:
        out["contextual_precision"] = "skipped:缺参考答案(reference)，不喂空 ground truth"
    return out


def dims_to_evidence(dims: dict) -> str:
    """把维度分翻译成可读证据（标注为建议，非判决）。"""
    if "error" in dims:
        return f"跳过框架复核（{dims['error']}）"
    ev = []
    for key, label in [
        ("faithfulness", "答案不忠于上下文(疑似幻觉)"),
        ("answer_relevancy", "答案不切题(疑似答非所问)"),
        ("contextual_precision", "召回不相关(疑似检索层问题)"),
    ]:
        val = dims.get(key)
        if isinstance(val, (int, float)) and val < DIM_FLAG:
            ev.append(f"{label}({key}={val})")
    return "；".join(ev) if ev else "框架维度分均正常（或部分指标跳过，见明细）"


# ═══════════════════════════════════════════════════════════════
# 四、主诊断流程
# ═══════════════════════════════════════════════════════════════

def run_diagnosis(failures: list[dict], mode: str, source_mode: str, limit: int | None, source: Path) -> list[dict]:
    if not failures:
        print("[OK] 失败库为空，无需诊断。")
        return []

    print("=" * 64)
    print(f"  章节 3.10 失败诊断 · 模式={mode} · 失败数={len(failures)}"
          + (f" · 本轮框架复核前 {limit} 条（--limit 控成本）" if limit else ""))
    print(f"  失败库: {source} 推断为 [{source_mode}]"
          + ("（含真实 retrieval_context，维度分可信）" if source_mode == "live"
             else "（无 retrieval_context，只做一级分流；真实数据请用 3.7 --write-failures 生成）"))
    print("=" * 64)
    print()

    results = []
    measured = 0
    for f in failures:
        layer, reason = classify_by_hard_metrics(f)

        ctx = (f.get("retrieval_context") or "").strip()
        if mode == "live" and ctx and (limit is None or measured < limit):
            dims = measure_with_deepeval(f)
            measured += 1
            evidence = dims_to_evidence(dims)
        elif mode == "live" and not ctx:
            dims = {}
            evidence = "⚠ 无 retrieval_context：请用 3.7 --write-failures 生成含真实召回上下文的失败库"
        elif mode == "live":
            dims = {}
            evidence = f"超出 --limit={limit}，本轮未做框架复核（一级分流仍有效）"
        else:
            dims = {}
            evidence = "offline：仅一级分流，未调框架（--mode live 复核）"

        print(f"  [{layer}] {f['case_id']} ({f['type']})")
        print(f"      keyword={f.get('keyword_score')}  citation={f.get('citation_score')}  refusal_ok={f.get('refusal_ok')}")
        print(f"      -> {reason}")
        print(f"      问题    : {f.get('question', '')}")
        print(f"      真实回答: {f.get('answer', '')}")
        print(f"      参考答案: {f.get('reference', '')}")
        if ctx:
            shown = ctx[:400] + (" …(已截断)" if len(ctx) > 400 else "")
            print(f"      召回上下文({len(ctx)}字): {shown}")
        else:
            print("      召回上下文: (空)")
        if dims:
            print(f"      DeepEval维度分: {dims}")
        print(f"      证据: {evidence}")
        print()

        results.append({
            "case_id": f["case_id"],
            "type": f["type"],
            "layer_suspected": layer,
            "reason": reason,
            "keyword_score": f.get("keyword_score"),
            "citation_score": f.get("citation_score"),
            "refusal_ok": f.get("refusal_ok"),
            "deepeval": dims,
            "evidence": evidence,
        })

    summary = {}
    for r in results:
        summary[r["layer_suspected"]] = summary.get(r["layer_suspected"], 0) + 1

    print("=" * 64)
    print("  失败根因分布（一级弱信号分流 + 二级框架证据）")
    print("=" * 64)
    for layer, cnt in summary.items():
        print(f"  {layer}: {cnt} 条")

    REPORTS.mkdir(exist_ok=True)
    DIAGNOSIS.write_text(
        json.dumps({"mode": mode, "summary": summary, "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n  诊断结果已写入 {DIAGNOSIS}")
    print("  发布判决（门禁）见 capstone/ci_gate.py（7.6 / step1）")
    return results


# ═══════════════════════════════════════════════════════════════
# 五、入口
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="章节 3.10 失败诊断（只诊断，发布门禁见 capstone/ci_gate.py）")
    parser.add_argument("--input", type=Path, default=None,
                        help="失败库 JSON。默认：shared-data/failures.json，没有则用本章 failures_sample.json")
    parser.add_argument("--mode", choices=["offline", "live"], default=None,
                        help="offline=仅一级分流（无 key）；live=DeepEval 维度分复核。"
                             "默认由失败库是否含真实 retrieval_context 自动推断。")
    parser.add_argument("--limit", type=int, default=None,
                        help="live 模式下最多对前 N 条做框架复核（控制 token 成本）")
    args = parser.parse_args()

    source = args.input or default_failures_path()
    try:
        failures, source_mode = load_failures(source)
    except (ValueError, FileNotFoundError) as exc:
        print(f"[错误] 加载失败库失败：{exc}", file=sys.stderr)
        print("  可先运行 3.7 并加 --write-failures 生成，或用 --input 指定有效文件。", file=sys.stderr)
        sys.exit(2)
    mode = args.mode or source_mode
    if args.mode and args.mode != source_mode:
        print(f"[WARN] 显式 --mode={args.mode}，但失败库推断为 {source_mode} 产物。"
              f"将以 {mode} 逻辑执行（维度分可信度以数据为准）。")

    run_diagnosis(failures, mode, source_mode, args.limit, source)


if __name__ == "__main__":
    main()
