"""章节 3.7 · 回归对比：baseline、candidate、pass@k 与 pass^k
==========================================================
核心能力与架构演进：
1. 优化改动可能使平均分微升，却在特定类别上造成不可逆的静默退化（Regression）。
2. 本章采用原生 Python + OpenAI SDK（去除 LCEL 管道与重型框架依赖）构建回归评估套件：
   - baseline（稳定生产版）：严谨 prompt、严格来源溯源【来源：xxx】、无证据强制拒答；
   - candidate（候选修改版）：松弛 prompt、可能漏标来源或基于常识脑补；
   - 指标维度：P50/P99 真实调用物理延迟、运行时异常率（Error Rate）、关键词命中、引用准确率、拒答对齐；
   - 生产稳定性指标：
     * pass@k：无偏估计在 k 次尝试中至少成功 1 次的概率（探索型/代码生成场景）；
     * pass^k（pass-all-k）：单次成功率为 p 时连续 k 次全部成功的概率（面向企业高可用/零事故场景）；
     * empirical_pass_all：实际任务在多次评测中连续全通比例；
     * split_suites：按高通过率门槛划分回归测试集（Regression Suite）与能力提升集（Capability Suite）。

运行模式：
  默认离线模式（无需外部 API Key，运行确定性样本评估与指标计算）：
    python tools/run_chapter.py 3.7
  在线真实模型调用（显式开启 --live，需配置模型环境变量）：
    python tools/run_chapter.py 3.7 --live
==========================================================
"""

from __future__ import annotations

import argparse
import json
import math
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


# --------------------------- 常量与评测集 ---------------------------

DATA_FILE = SHARED_DATA_DIR / "eval_set_full.json"
FAILURES_FILE = SHARED_DATA_DIR / "failures.json"
REFUSE_KEYWORDS = ["没有提到", "信息不足", "无法回答", "不知道", "无相关", "没有足够信息"]
SOURCE_NAME = "test_doc.txt"

# 内置兜底示范用例
INLINE_CASES = [
    {
        "id": "reg_01",
        "question": "RAG 的全称与基本定义是什么？",
        "reference": "RAG 是检索增强生成，先从外部知识库检索相关内容，再拼装上下文交给大模型生成准确答案。",
        "keywords": ["检索", "生成", "外部"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
    },
    {
        "id": "reg_02",
        "question": "知识库中关于向量检索的作用是如何说明的？",
        "reference": "向量检索用于在嵌入空间计算语义相似度，实现 Top-K 语义召回。",
        "keywords": ["语义", "相似度", "召回"],
        "expected_sources": [SOURCE_NAME],
        "should_refuse": False,
    },
    {
        "id": "reg_03",
        "question": "请详细说明本系统采用的量子通信纠缠加密算法。",
        "reference": "上下文未包含相关信息，应明确说明无法回答。",
        "keywords": [],
        "expected_sources": [],
        "should_refuse": True,
    },
]


# --------------------------- 核心数学指标与门禁算法 ---------------------------

def percentile(values: list[float], pct: int) -> float:
    """线性插值分位数；空列表返回 0.0。"""
    if not (0 <= pct <= 100):
        raise ValueError(f"pct 越界（需为 0~100）：{pct}")
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
    expected_sources = case.get("expected_sources", [])
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
    """每个任务取前 k 次记录，统计“k 次全部通过”的任务占比；某任务记录不足 k 次时抛 ValueError。"""
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


# --------------------------- 原生 RAG 调用实现 ---------------------------

def call_baseline_rag(
    client: Any,
    model: str,
    question: str,
    context: str,
) -> str:
    """稳定版 Baseline：严格约束依据上下文并标明来源。"""
    prompt = f"""你是一名严格的企业知识库助手。请根据下方上下文回答问题。
要求：
1. 必须完全依据上下文，若上下文未提及请明确回复“信息不足，无法回答”，绝不能编造。
2. 回答结尾必须附上来源标注：【来源：{SOURCE_NAME}】。

【上下文】
{context}

【用户问题】
{question}
"""
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return res.choices[0].message.content or ""


def call_candidate_rag(
    client: Any,
    model: str,
    question: str,
    context: str,
) -> str:
    """候选版 Candidate：prompt 放宽约束，可能导致漏标来源或胡乱解答。"""
    prompt = f"""你是一个随和自然的问答助手。请根据上下文回答问题。
如果上下文没有，你可以根据通用常识直接发挥。回答简短即可，不需要强制标注来源。

【上下文】
{context}

【用户问题】
{question}
"""
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return res.choices[0].message.content or ""


# --------------------------- 评测集加载 ---------------------------

def load_cases(path: Path = DATA_FILE) -> list[dict[str, Any]]:
    """从本地或共享数据目录加载评测集。"""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data and isinstance(data, list):
                formatted = []
                for item in data:
                    c = dict(item)
                    if "expected_sources" not in c:
                        c["expected_sources"] = [c["expect_source"]] if c.get("expect_source") else []
                    formatted.append(c)
                return formatted
        except Exception:
            pass
    return INLINE_CASES


# --------------------------- 主程序 ---------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="L3.6 原生 RAG 回归对比与 pass@k / pass^k 评测")
    parser.add_argument("--live", action="store_true", help="显式开启真实模型调用")
    parser.add_argument("--limit", type=int, default=3, help="评测用例数量限制")
    parser.add_argument("--write-failures", action="store_true", help="将失败用例写出到 failures.json")
    args = parser.parse_args()

    print("==========================================================")
    print("  L3.6 RAG 回归对比、pass@k 与 pass^k（原生实现）")
    print("==========================================================")

    cases = load_cases()[: args.limit]
    print(f"已加载评测用例：{len(cases)} 条。\n")

    if not args.live:
        print("[模式说明] 当前为默认【离线确定性演练】模式（未附加 --live）。")
        print("展示 Baseline 与 Candidate 回归指标、退化告警、pass@k 与套件拆分计算：\n")

        # 模拟运行指标
        baseline_rows = []
        candidate_rows = []

        for c in cases:
            if c.get("should_refuse"):
                b_ans = f"依据提供的资料，信息不足，无法回答该问题。\n【来源：{SOURCE_NAME}】"
                c_ans = "这个加密算法非常先进，采用了超空间多维编码原理。"  # 幻觉且未拒答
            else:
                b_ans = f"RAG 是检索增强生成，先检索相关资料再生成回答。\n【来源：{SOURCE_NAME}】"
                c_ans = "RAG 是检索生成技术。"  # 缺来源标注

            b_scores = score_case(c, {"answer": b_ans})
            b_scores["latency_ms"] = 120.0
            b_scores["runtime_error"] = ""
            b_scores["id"] = c.get("id")
            baseline_rows.append(b_scores)

            c_scores = score_case(c, {"answer": c_ans})
            c_scores["latency_ms"] = 150.0
            c_scores["runtime_error"] = ""
            c_scores["id"] = c.get("id")
            candidate_rows.append(c_scores)

        b_summary = summarize(baseline_rows)
        c_summary = summarize(candidate_rows)

        print("--- Baseline (稳定生产版) 指标 ---")
        print(f"用例数: {b_summary['cases']}, 通过率: {b_summary['pass_rate']:.2%}, 引用分: {b_summary['citation_score']:.2%}, 拒答分: {b_summary['refusal_ok']:.2%}, P99: {b_summary['p99_latency_ms']:.1f}ms")

        print("\n--- Candidate (宽松候选版) 指标 ---")
        print(f"用例数: {c_summary['cases']}, 通过率: {c_summary['pass_rate']:.2%}, 引用分: {c_summary['citation_score']:.2%}, 拒答分: {c_summary['refusal_ok']:.2%}, P99: {c_summary['p99_latency_ms']:.1f}ms")

        alerts = regression_alerts(b_summary, c_summary)
        print("\n--- 回归退化告警分析 ---")
        if alerts:
            for alert in alerts:
                print(f"[ALARM] {alert}")
        else:
            print("[OK] 未发现指标退化。")

        # pass@k 与 pass^k 示范
        print("\n--- 稳定性与概率评测指标 (pass@k vs pass^k) ---")
        p_at_1 = pass_at_k(10, 3, 1)
        p_at_2 = pass_at_k(10, 3, 2)
        p_all_3 = pass_all_k(0.75, 3)
        print(f"pass@1 (10次尝试成功3次，选1次成功概率): {p_at_1:.2%}")
        print(f"pass@2 (10次尝试成功3次，选2次至少1次成功概率): {p_at_2:.2%}")
        print(f"pass^3 (单次成功率75%时连续3次全部成功概率): {p_all_3:.2%}")

        # 套件拆分演示
        multi_run_history = {
            "auth_check": [True, True, True, True, True],
            "doc_search": [True, True, True, True, False],
            "complex_sql": [True, False, False, True, False],
        }
        reg_suite, cap_suite = split_suites(multi_run_history, regression_floor=0.95)
        print("\n--- 任务分流拆分 (split_suites floor=0.95) ---")
        print(f"回归套件 (Regression Suite，基线必通): {reg_suite}")
        print(f"能力套件 (Capability Suite，探索提升): {cap_suite}")

        if args.write_failures:
            FAILURES_FILE.parent.mkdir(parents=True, exist_ok=True)
            FAILURES_FILE.write_text(
                json.dumps(c_summary["failures"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"\n已将 {len(c_summary['failures'])} 条失败样本写入 {FAILURES_FILE}")

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
        print(f"使用模型：{model}")
        sample_context = "这是系统内置知识库文档。RAG 结合了检索和生成两阶段。\n"
        if SAMPLE_DOC.exists():
            sample_context = SAMPLE_DOC.read_text(encoding="utf-8")[:1000]

        b_rows = []
        c_rows = []

        for idx, case in enumerate(cases, 1):
            q = case["question"]
            print(f"\n[{idx}/{len(cases)}] 正在评测用例：{q}")

            # 运行 Baseline
            t0 = time.perf_counter()
            b_ans = call_baseline_rag(client, model, q, sample_context)
            b_lat = (time.perf_counter() - t0) * 1000.0
            b_score = score_case(case, {"answer": b_ans})
            b_score["latency_ms"] = b_lat
            b_score["runtime_error"] = ""
            b_rows.append(b_score)

            # 运行 Candidate
            t0 = time.perf_counter()
            c_ans = call_candidate_rag(client, model, q, sample_context)
            c_lat = (time.perf_counter() - t0) * 1000.0
            c_score = score_case(case, {"answer": c_ans})
            c_score["latency_ms"] = c_lat
            c_score["runtime_error"] = ""
            c_rows.append(c_score)

        b_sum = summarize(b_rows)
        c_sum = summarize(c_rows)

        print("\n=== 在线回归对比摘要 ===")
        print(f"Baseline  通过率: {b_sum['pass_rate']:.2%}, P50: {b_sum['p50_latency_ms']:.1f}ms, P99: {b_sum['p99_latency_ms']:.1f}ms")
        print(f"Candidate 通过率: {c_sum['pass_rate']:.2%}, P50: {c_sum['p50_latency_ms']:.1f}ms, P99: {c_sum['p99_latency_ms']:.1f}ms")

        alarms = regression_alerts(b_sum, c_sum)
        if alarms:
            print("\n[退化告警]")
            for a in alarms:
                print(f"  * {a}")
        else:
            print("\n[通过] 未发现关键质量退化指标。")

    except Exception as exc:
        print(f"\n[运行失败] 在线请求过程中发生网络或模型错误：{exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
