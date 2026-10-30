"""L3.6 回归对比 · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
regression_curve.py。实现下面的函数，然后运行：

    python chapters/part3-evals/3.7-eval-regression-curve/gate/gate_check.py
"""

from __future__ import annotations


def percentile(values: list[float], pct: int) -> float:
    """线性插值分位数；空列表返回 0.0。

    要求：pct 在 0–100；越界 -> ValueError。
    """
    raise NotImplementedError("实现分位数")


def score_case(case: dict, outputs: dict) -> dict:
    """给一条结果打分。

    case 字段：reference/keywords/expected_sources/should_refuse。
    outputs 字段：answer。
    返回：keyword_score/citation_score/refusal_ok/passed。
    规则：
    - 无 keywords -> keyword_score=1.0；否则命中比例；
    - 无 expected_sources -> citation_score=1.0；否则命中比例；
    - refusal_ok：拒答词是否与 should_refuse 一致（0/1）；
    - passed：keyword>=0.67 且 citation>=0.67 且 refusal_ok==1.0。
    """
    raise NotImplementedError("实现单条评分")


def summarize(rows: list[dict]) -> dict:
    """汇总回归指标。

    rows 每行含 latency_ms、runtime_error、keyword_score、citation_score、refusal_ok、passed。
    返回 cases/error_rate/p50_latency_ms/p99_latency_ms/pass_rate/keyword_score/
    citation_score/refusal_ok/failures。
    空 rows -> 全 0，failures=[]。
    """
    raise NotImplementedError("实现回归汇总")


def regression_alerts(baseline: dict, candidate: dict) -> list[str]:
    """比较 baseline/candidate，返回退化告警。

    触发条件：
    - error_rate 上升 > 0；
    - p99 上升 > 2000ms；
    - pass_rate 下降 > 0.02；
    - citation_score 下降 > 0.02；
    - refusal_ok 下降 > 0。
    没有退化 -> []。
    """
    raise NotImplementedError("实现回归告警")


def pass_at_k(n: int, c: int, k: int) -> float:
    """n 次独立尝试中有 c 次成功时，“k 次里至少成功 1 次”的无偏估计：1 - C(n-c, k) / C(n, k)。

    k > n、c > n 或任一参数为负时抛 ValueError；n - c < k 时返回 1.0。
    """
    raise NotImplementedError("实现 pass@k 无偏估计")


def pass_all_k(success_rate: float, k: int) -> float:
    """单次成功率为 p 时，连续 k 次全部成功的概率 p**k；p 不在 [0, 1] 或 k < 1 时抛 ValueError。"""
    raise NotImplementedError("实现 pass^k 概率计算")


def empirical_pass_all(results: dict[str, list[bool]], k: int) -> float:
    """每个任务取前 k 次记录，统计“k 次全部通过”的任务占比；某任务记录不足 k 次时抛 ValueError。"""
    raise NotImplementedError("实现经验 pass^all 统计")


def split_suites(
    results: dict[str, list[bool]], regression_floor: float = 0.95
) -> tuple[list[str], list[str]]:
    """通过率 >= regression_floor 的任务归入回归集，其余归入能力集；两个列表都按任务名排序。"""
    raise NotImplementedError("实现评测套件拆分")
