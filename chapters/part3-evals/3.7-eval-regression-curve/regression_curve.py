"""章节 3.7 · 回归对比：Baseline、Candidate 与质量门禁（原生实现）
======================================================================
核心能力：
1. 为什么平均分上升仍可能隐藏严重退化？
   - 全局指标（如平均准确率）容易被部分高分题掩盖，导致局部高危用例（如合规拒答、鉴权）全面退化；
   - 回归对比必须在同一批测试用例上并排评估，同时监控质量、P50/P99 尾部延迟与运行时异常率（Error Rate）。
2. pass@k 与 pass^k（pass-all-k）：
   - pass@k：在 k 次独立尝试中至少成功 1 次的无偏估计，适合探索容错场景；
   - pass^k：单次成功率为 p 时连续 k 次独立尝试全部成功的概率（p^k），适合面向终端用户的生产稳定性保障。
3. 评测套件拆分（split_suites）：
   - 回归套件（Regression Suite）：高通过率（如 >=95%）核心功能，作为 CI 强卡点门禁；
   - 能力套件（Capability Suite）：探索性高难任务，纳入质量看板持续跟踪。

运行模式：
  默认离线确定性演练（输出回归对比、告警与套件拆分）：
    python tools/run_chapter.py 3.7
  开启 CI 回归门禁（退化时以非 0 退出）：
    python tools/run_chapter.py 3.7 --fail-on-regression
  写出失败用例库（供 3.10 失败诊断使用）：
    python tools/run_chapter.py 3.7 --write-failures
  指定外部测试集：
    python tools/run_chapter.py 3.7 --cases chapters/shared-data/eval_set_full.json
  真实大模型在线回归对比（需配置 API Key）：
    python tools/run_chapter.py 3.7 --live
======================================================================
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

# 兼容模块导入路径
try:
    from common import (
        SAMPLE_DOC,
        SHARED_DATA_DIR,
        chat_model_name,
        get_openai_client,
    )
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from common import (
        SAMPLE_DOC,
        SHARED_DATA_DIR,
        chat_model_name,
        get_openai_client,
    )

# 默认拒答关键词列表
REFUSE_KEYWORDS = ["无法回答", "没有提到", "信息不足", "不知道", "无相关", "资料未提供"]

# 内置兜底回归测试集
INLINE_CASES = [
    {
        "id": "case_01",
        "type": "rag_fact",
        "question": "LangChain 是什么？",
        "reference": "LangChain 是构建 LLM 应用的开源开发框架。",
        "keywords": ["框架", "LLM"],
        "expected_sources": ["test_doc.txt"],
        "should_refuse": False,
    },
    {
        "id": "case_02",
        "type": "rag_fact",
        "question": "什么是 RAG？",
        "reference": "RAG 是检索增强生成，先检索相关分块再生成回答。",
        "keywords": ["检索", "生成"],
        "expected_sources": ["test_doc.txt"],
        "should_refuse": False,
    },
    {
        "id": "case_03",
        "type": "refusal",
        "question": "公司明年的财务预算是多少？",
        "reference": "文档未提供财务预算信息，助手应明确拒答。",
        "keywords": [],
        "expected_sources": [],
        "should_refuse": True,
    },
]


# --------------------------- 核心算法与统计纯函数 ---------------------------

def percentile(values: list[float], pct: int) -> float:
    """线性插值分位数（与 NumPy/pandas percentile 对齐）；空列表返回 0.0。"""
    if not (0 <= pct <= 100):
        raise ValueError(f"分位数百分比 pct 必须在 0 到 100 之间，收到：{pct}")
    if not values:
        return 0.0

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])

    k = (n - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])

    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return float(d0 + d1)


def score_case(case: dict, outputs: dict) -> dict:
    """给单条回答评测打分。"""
    answer = outputs.get("answer", "")
    keywords = case.get("keywords", [])
    expected_sources = case.get("expected_sources")
    if expected_sources is None:
        expect_src = case.get("expect_source")
        expected_sources = [expect_src] if expect_src else []
    should_refuse = case.get("should_refuse", False)

    # 1. 关键词命中率
    if not keywords:
        keyword_score = 1.0
    else:
        hits = sum(1 for kw in keywords if kw.lower() in answer.lower())
        keyword_score = hits / len(keywords)

    # 2. 引用来源标注
    if not expected_sources:
        citation_score = 1.0
    else:
        hits = sum(1 for src in expected_sources if src in answer)
        citation_score = hits / len(expected_sources)

    # 3. 拒答行为对齐
    has_refusal = any(hint in answer for hint in REFUSE_KEYWORDS)
    if should_refuse:
        refusal_ok = 1.0 if has_refusal else 0.0
    else:
        refusal_ok = 1.0 if not has_refusal else 0.0

    passed = (keyword_score >= 0.67) and (citation_score >= 0.67) and (refusal_ok == 1.0)

    return {
        "keyword_score": keyword_score,
        "citation_score": citation_score,
        "refusal_ok": refusal_ok,
        "passed": passed,
    }


def summarize(rows: list[dict]) -> dict:
    """汇总测试批次指标与耗时分布。"""
    if not rows:
        return {
            "cases": 0,
            "error_rate": 0.0,
            "p50_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "pass_rate": 0.0,
            "keyword_score": 0.0,
            "citation_score": 0.0,
            "refusal_ok": 0.0,
            "failures": [],
        }

    total = len(rows)
    runtime_errors = sum(1 for r in rows if r.get("runtime_error"))
    error_rate = runtime_errors / total

    latencies = [float(r.get("latency_ms", 0.0)) for r in rows]
    p50 = percentile(latencies, 50)
    p99 = percentile(latencies, 99)

    passed_count = sum(1 for r in rows if r.get("passed"))
    pass_rate = passed_count / total

    keyword_sum = sum(r.get("keyword_score", 0.0) for r in rows)
    citation_sum = sum(r.get("citation_score", 0.0) for r in rows)
    refusal_sum = sum(r.get("refusal_ok", 0.0) for r in rows)

    failures = [r for r in rows if not r.get("passed")]

    return {
        "cases": total,
        "error_rate": error_rate,
        "p50_latency_ms": p50,
        "p99_latency_ms": p99,
        "pass_rate": pass_rate,
        "keyword_score": keyword_sum / total,
        "citation_score": citation_sum / total,
        "refusal_ok": refusal_sum / total,
        "failures": failures,
    }


def regression_alerts(baseline: dict, candidate: dict) -> list[str]:
    """比较 baseline/candidate 指标并识别质量退化告警。"""
    alerts = []
    if candidate.get("error_rate", 0.0) - baseline.get("error_rate", 0.0) > 1e-9:
        alerts.append("error_rate 退化：运行时异常率升高")

    if candidate.get("p99_latency_ms", 0.0) - baseline.get("p99_latency_ms", 0.0) > 2000.0:
        alerts.append("p99_latency 退化：P99 延迟恶化超过 2000ms")

    if baseline.get("pass_rate", 0.0) - candidate.get("pass_rate", 0.0) > 0.02 + 1e-9:
        alerts.append("pass_rate 退化：整体通过率下降超过 2%")

    if baseline.get("citation_score", 0.0) - candidate.get("citation_score", 0.0) > 0.02 + 1e-9:
        alerts.append("citation_score 退化：引用准确率下降超过 2%")

    if baseline.get("refusal_ok", 0.0) - candidate.get("refusal_ok", 0.0) > 1e-9:
        alerts.append("refusal_ok 退化：拒答对齐度下降")

    return alerts


def pass_at_k(n: int, c: int, k: int) -> float:
    """n 次独立尝试中有 c 次成功时，“k 次里至少成功 1 次”的无偏估计：1 - C(n-c, k) / C(n, k)。"""
    if n < 0 or c < 0 or k < 1 or k > n or c > n:
        raise ValueError(f"非法参数：n={n}, c={c}, k={k}")
    if n - c < k:
        return 1.0
    return 1.0 - (math.comb(n - c, k) / math.comb(n, k))


def pass_all_k(success_rate: float, k: int) -> float:
    """单次成功率为 p 时，连续 k 次全部成功的概率 p**k；p 不在 [0, 1] 或 k < 1 时抛 ValueError。"""
    if not (0.0 <= success_rate <= 1.0) or k < 1:
        raise ValueError(f"非法参数：success_rate={success_rate}, k={k}")
    return float(success_rate ** k)


def empirical_pass_all(results: dict[str, list[bool]], k: int) -> float:
    """每个任务取前 k 次记录，统计“k 次全部通过”的任务占比；空字典返回 0.0；某任务记录不足 k 次或 k < 1 时抛 ValueError。"""
    if k < 1:
        raise ValueError(f"k 必须大于等于 1，实际为 {k}")
    if not results:
        return 0.0
    passed_count = 0
    total = len(results)
    for task_name, runs in results.items():
        if len(runs) < k:
            raise ValueError(f"任务 {task_name} 的执行记录不足 {k} 次（仅有 {len(runs)} 次）")
        if all(runs[:k]):
            passed_count += 1
    return passed_count / total


def split_suites(
    results: dict[str, list[bool]], regression_floor: float = 0.95
) -> tuple[list[str], list[str]]:
    """通过率 >= regression_floor 的任务归入回归集，其余归入能力集；两个列表都按任务名排序。"""
    if not (0.0 <= regression_floor <= 1.0):
        raise ValueError(f"regression_floor 必须在 [0, 1] 之间，实际为 {regression_floor}")
    regression_suite: list[str] = []
    capability_suite: list[str] = []
    for task_name, runs in results.items():
        rate = (sum(1 for r in runs if r) / len(runs)) if runs else 0.0
        if rate >= regression_floor:
            regression_suite.append(task_name)
        else:
            capability_suite.append(task_name)
    regression_suite.sort()
    capability_suite.sort()
    return regression_suite, capability_suite


# --------------------------- 本地轻量原生检索与生成 ---------------------------

def retrieve_chunks(query: str, top_k: int = 2) -> list[str]:
    """从本地 SAMPLE_DOC 检索相关文本块。"""
    if not SAMPLE_DOC.exists():
        return ["RAG 是检索增强生成，先从外部知识库检索相关分块，再拼装上下文交由模型生成回答。"]
    raw = SAMPLE_DOC.read_text(encoding="utf-8")
    chunks = [c.strip() for c in raw.split("\n\n") if c.strip()]
    q_words = set(re.findall(r"\w+", query.lower()))
    scored = []
    for c in chunks:
        score = sum(1 for w in q_words if w in c.lower())
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for s, c in scored[:top_k] if s > 0] or chunks[:1]


def run_system_live(
    client: Any,
    model: str,
    case: dict,
    is_candidate: bool = False,
) -> dict[str, Any]:
    """在 live 模式下发起单次系统调用并捕获可能出现的异常。"""
    q = case["question"]
    chunks = retrieve_chunks(q)
    context = "\n".join(chunks)

    if not is_candidate:
        # Baseline：要求严格依据上下文并标注来源
        prompt = (
            f"请严格依据以下检索上下文回答问题。答案必须在句末标注【来源：{SAMPLE_DOC.name}】。\n"
            f"若上下文信息不足，请明确回复：“信息不足，无法回答。”\n"
            f"上下文：\n{context}\n问题：{q}"
        )
        temp = 0.0
    else:
        # Candidate：放宽了来源标注与拒答约束
        prompt = f"请根据以下上下文回答问题。上下文：\n{context}\n问题：{q}"
        temp = 0.7

    t0 = time.perf_counter()
    runtime_error = None
    answer = ""
    try:
        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
        )
        answer = res.choices[0].message.content or ""
    except Exception as exc:
        runtime_error = f"{type(exc).__name__}: {exc}"

    dur_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "answer": answer,
        "retrieval_context": context,
        "latency_ms": dur_ms,
        "runtime_error": runtime_error,
    }


def run_system_offline(
    case: dict,
    is_candidate: bool = False,
) -> dict[str, Any]:
    """在离线模式下提供按题目编写的确定性输出，对比 Baseline 与 Candidate 的指标差异。"""
    q = case["question"]
    chunks = retrieve_chunks(q)
    context = "\n".join(chunks)
    should_refuse = case.get("should_refuse", False)
    case_id = case.get("id") or case.get("case_id", "")

    if not is_candidate:
        # Baseline：高质量稳定版本（严格引用、按需拒答）
        if should_refuse:
            ans = "文档中没有提到相关信息，信息不足，无法回答。"
        else:
            ans = f"根据资料显示，{case['reference']}【来源：{SAMPLE_DOC.name}】"
        latency = 120.0
        err = None
    else:
        # Candidate：存在局部质量退化（如漏掉来源引用、未按要求拒答）
        if should_refuse:
            # 退化点：未遵从拒答约定，强行胡乱回答
            ans = "明年的预算大约在数千万元左右，具体数额由管理层确定。"
        elif case_id in ("case_01", "f01", "f02"):
            # 退化点：回答遗漏了来源标注
            ans = f"{case['reference']}"
        else:
            ans = f"根据资料显示，{case['reference']}【来源：{SAMPLE_DOC.name}】"
        latency = 160.0
        err = None

    return {
        "answer": ans,
        "retrieval_context": context,
        "latency_ms": latency,
        "runtime_error": err,
    }


def write_failures_to_file(failures: list[dict], output_path: Path) -> Path:
    """将包含完整诊断字段的失败用例库写入 JSON，供 3.10 失败诊断使用。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


# --------------------------- 主程序 ---------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="L3.6 回归对比与发布门禁")
    parser.add_argument("--live", action="store_true", help="显式开启真实大模型在线评测")
    parser.add_argument("--fail-on-regression", action="store_true", help="检测到退化告警时以非 0 退出（用于 CI 质量卡点）")
    parser.add_argument("--write-failures", action="store_true", help="将候选版本失败用例写入 shared-data/failures.json 供 3.10 诊断")
    parser.add_argument("--cases", type=str, default=None, help="自定义评测用例集路径")
    parser.add_argument("--no-upload", action="store_true", help="向后兼容选项：跳过远程上传")
    args = parser.parse_args()

    print("==========================================================")
    print("  L3.6 RAG 回归对比、pass@k 与质量门禁（原生实现）")
    print("==========================================================")

    # 1. 加载评测集
    cases = INLINE_CASES
    if args.cases:
        p = Path(args.cases)
        if p.exists():
            cases = json.loads(p.read_text(encoding="utf-8"))
            print(f"已加载指定评测集: {p}（共 {len(cases)} 条）")
        else:
            print(f"[警告] 指定的评测集文件不存在: {p}，使用内置兜底集", file=sys.stderr)
    else:
        shared_cases = SHARED_DATA_DIR / "eval_set_full.json"
        if shared_cases.exists():
            cases = json.loads(shared_cases.read_text(encoding="utf-8"))[:10]
            print(f"已加载标准评测集: {shared_cases}（抽取前 {len(cases)} 条评测）")
        else:
            print(f"未找到共享评测集，使用内置示例评测集（共 {len(cases)} 条）")

    # 2. 执行评测
    client = None
    model = ""
    if args.live:
        print("\n[在线模式] 正在初始化原生 OpenAI 客户端...")
        try:
            client = get_openai_client(timeout=30.0, max_retries=1)
            model = chat_model_name()
            print(f"使用模型: {model}，正在发起真实模型在线对比...")
        except Exception as exc:
            print(f"[配置错误] 无法获取模型客户端：{exc}", file=sys.stderr)
            return 1
    else:
        print("\n[模式说明] 当前为默认【离线确定性演练】模式（未加 --live）。")
        print("[离线演示] 采用确定性离线生成对比 Baseline 与 Candidate 的回归表现。")
        print("[离线演示] 延迟指标采用模拟固定时钟值，真实物理耗时见 --live 模式。\n")

    baseline_rows = []
    candidate_rows = []

    for idx, case in enumerate(cases, start=1):
        c_id = case.get("id") or case.get("case_id", f"case_{idx:02d}")
        c_type = case.get("type", "rag_fact")
        q = case["question"]
        ref = case.get("reference", "")

        # 运行 Baseline
        if args.live:
            base_out = run_system_live(client, model, case, is_candidate=False)
            if base_out["runtime_error"] and any(k in base_out["runtime_error"] for k in ("ConnectError", "Connection", "ConnectTimeout")):
                print(f"[网络错误] 在线调用模型失败（模型不可达或连接拒绝）：{base_out['runtime_error']}", file=sys.stderr)
                return 1
        else:
            base_out = run_system_offline(case, is_candidate=False)

        score_b = score_case(case, base_out)
        baseline_rows.append({
            "case_id": c_id,
            "type": c_type,
            "question": q,
            "reference": ref,
            "retrieval_context": base_out.get("retrieval_context", ""),
            "answer": base_out["answer"],
            "latency_ms": base_out["latency_ms"],
            "runtime_error": base_out["runtime_error"],
            "keyword_score": score_b["keyword_score"],
            "citation_score": score_b["citation_score"],
            "refusal_ok": score_b["refusal_ok"],
            "passed": score_b["passed"],
        })

        # 运行 Candidate
        if args.live:
            cand_out = run_system_live(client, model, case, is_candidate=True)
            if cand_out["runtime_error"] and any(k in cand_out["runtime_error"] for k in ("ConnectError", "Connection", "ConnectTimeout")):
                print(f"[网络错误] 在线调用模型失败（模型不可达或连接拒绝）：{cand_out['runtime_error']}", file=sys.stderr)
                return 1
        else:
            cand_out = run_system_offline(case, is_candidate=True)

        score_c = score_case(case, cand_out)
        candidate_rows.append({
            "case_id": c_id,
            "type": c_type,
            "question": q,
            "reference": ref,
            "retrieval_context": cand_out.get("retrieval_context", ""),
            "answer": cand_out["answer"],
            "latency_ms": cand_out["latency_ms"],
            "runtime_error": cand_out["runtime_error"],
            "keyword_score": score_c["keyword_score"],
            "citation_score": score_c["citation_score"],
            "refusal_ok": score_c["refusal_ok"],
            "passed": score_c["passed"],
        })

    # 3. 汇总与回归对比
    sum_baseline = summarize(baseline_rows)
    sum_candidate = summarize(candidate_rows)
    alerts = regression_alerts(sum_baseline, sum_candidate)

    print("--- Baseline (生产稳定基线) ---")
    print(
        f"用例: {sum_baseline['cases']}, 通过率: {sum_baseline['pass_rate'] * 100:.2f}%, "
        f"引用分: {sum_baseline['citation_score'] * 100:.2f}%, 拒答对齐: {sum_baseline['refusal_ok'] * 100:.2f}%, "
        f"P99: {sum_baseline['p99_latency_ms']:.1f}ms, ErrorRate: {sum_baseline['error_rate'] * 100:.2f}%"
    )

    print("\n--- Candidate (候选变更版本) ---")
    print(
        f"用例: {sum_candidate['cases']}, 通过率: {sum_candidate['pass_rate'] * 100:.2f}%, "
        f"引用分: {sum_candidate['citation_score'] * 100:.2f}%, 拒答对齐: {sum_candidate['refusal_ok'] * 100:.2f}%, "
        f"P99: {sum_candidate['p99_latency_ms']:.1f}ms, ErrorRate: {sum_candidate['error_rate'] * 100:.2f}%"
    )

    print("\n--- 回归告警检测 ---")
    if alerts:
        print("[FAIL] 检测到质量回归退化告警：")
        for alert in alerts:
            print(f"  - [ALARM] {alert}")
    else:
        print("[PASS] 未检测到明显质量回归，各项指标符合门禁基线。")

    # 4. 统计指标计算演示 (pass@k vs pass^k 与套件拆分)
    print("\n--- 稳定性指标 (pass@k 与 pass^k) ---")
    p1 = pass_at_k(10, 3, 1)
    p2 = pass_at_k(10, 3, 2)
    p_all = pass_all_k(0.75, 3)
    print(f"pass@1 (10 次尝试成功 3 次时，任抽 1 次成功概率): {p1 * 100:.2f}%")
    print(f"pass@2 (10 次尝试成功 3 次时，任选 2 次至少成功 1 次): {p2 * 100:.2f}%")
    print(f"pass^3 (单次成功率 75% 时，连续 3 次全部成功概率): {p_all * 100:.2f}%")

    suite_data = {
        "auth_guard": [True, True, True, True],
        "complex_rag": [True, False, True, False],
        "doc_search": [True, True, True, False],
    }
    reg_suite, cap_suite = split_suites(suite_data, regression_floor=0.95)
    print("\n--- 评测套件拆分 (split_suites floor=0.95) ---")
    print(f"回归套件 (Regression Suite，强卡点): {reg_suite}")
    print(f"能力套件 (Capability Suite，持续迭代): {cap_suite}")

    # 5. 写出失败库
    if args.write_failures:
        failures_path = SHARED_DATA_DIR / "failures.json"
        write_failures_to_file(sum_candidate["failures"], failures_path)
        print(f"\n[失败库] 候选版本的 {len(sum_candidate['failures'])} 条失败样本已写入：{failures_path}")

    # 6. CI 门禁卡点逻辑
    if args.fail_on_regression and alerts:
        print("\n[门禁拦截] candidate 比 baseline 出现退化，--fail-on-regression 触发退出码 1。", file=sys.stderr)
        return 1

    # 7. 在线模式网络/服务完全失败时退出非 0
    if args.live and (sum_baseline["error_rate"] >= 1.0 or sum_candidate["error_rate"] >= 1.0):
        print("\n[评测失败] 在线调用模型全部失败（模型不可达或网络中断）。", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
