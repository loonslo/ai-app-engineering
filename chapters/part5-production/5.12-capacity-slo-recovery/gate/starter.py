"""L5.9 容量、SLO 与恢复 · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
capacity_slo.py。实现下面的接口，然后运行：

    python chapters/part5-production/5.12-capacity-slo-recovery/gate/gate_check.py

不允许为了通过而修改 gate_check.py。全部是纯计算：不读文件、不联网、不跑压测。
注意浮点数：例如 0.7 * 10 在 Python 里是 7.000000000000001，直接 ceil 会多算一位。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestResult:
    latency_ms: int
    status: int            # HTTP 状态码；0 表示超时


def percentile(values: list[int], q: float) -> int:
    """最近秩法：先排序，取第 ceil(q * n) 个值（从 1 开始计数）。

    values 为空，或 q 不在 (0, 1] 内时抛 ValueError。
    先把 q * n 四舍五入到 9 位小数再 ceil，避免浮点误差让结果多出一位。
    """
    raise NotImplementedError("实现 percentile")


def summarize_load(results: list[RequestResult], duration_s: float) -> dict:
    """汇总一次压测，返回：

    {"p50": int, "p95": int, "p99": int,            # 毫秒；对全部请求（含失败）用 percentile 计算
     "error_rate": float,                           # 0~1；status 为 0、>= 500 或 == 429 都算失败
     "rps": float,                                  # 请求总数 / duration_s
     "counts": {"429": int, "5xx": int, "timeout": int}}   # 5xx 指 status >= 500；timeout 指 status == 0

    results 为空或 duration_s <= 0 时抛 ValueError。
    """
    raise NotImplementedError("实现 summarize_load")


def check_slo(summary: dict, slo: dict) -> list[str]:
    """slo = {"p95_ms": 数值, "error_rate": 0~1 的数值}；summary 是 summarize_load 的返回值。

    返回未达标项的名字列表，顺序固定为 ["p95_ms", "error_rate"] 中不达标的那些；
    p95 大于 slo["p95_ms"] 或错误率大于 slo["error_rate"] 才算不达标（恰好等于算达标）；全部达标返回 []。
    """
    raise NotImplementedError("实现 check_slo")


def error_budget(slo_target: float, total: int, failed: int) -> dict:
    """错误预算。slo_target 是可用性目标，如 0.999；total 是请求总数；failed 是失败数。

    返回 {"allowed_failures": int, "used_ratio": float, "exhausted": bool}：
    - allowed_failures = floor((1 - slo_target) * total)，先四舍五入到 9 位小数再 floor（(1-0.9)*10 不是整数 1）；
    - used_ratio = failed / allowed_failures；allowed_failures 为 0 时，failed 为 0 则 0.0，否则 1.0；
    - exhausted = failed > allowed_failures（用满不算超出，超过才算耗尽）。
    slo_target 不在 (0, 1] 内、total < 0、failed < 0 或 failed > total 时抛 ValueError。
    """
    raise NotImplementedError("实现 error_budget")


def plan_capacity(peak_rps: float, per_instance_rps: float, headroom: float, *,
                  tokens_per_req: int, rpm_limit: int | None, tpm_limit: int | None) -> dict:
    """按峰值流量规划实例数，并判断会不会先撞上模型厂商的限额。

    - instances = ceil(peak_rps * (1 + headroom) / per_instance_rps)，同样先四舍五入到 9 位小数再 ceil；
    - rpm_needed = peak_rps * 60（每分钟请求数，不含余量）；tpm_needed = rpm_needed * tokens_per_req；
    - 返回 {"instances": int, "rpm_needed": float, "tpm_needed": float, "bottleneck": "none" | "rpm" | "tpm"}；
    - limit 为 None 表示没有该限额；某项需求大于限额才算撞上；
    - 两项都撞上时，选"需求/限额"比值更大的那项；比值相等选 "rpm"；都没撞上是 "none"；
    - peak_rps <= 0、per_instance_rps <= 0、headroom < 0 或 tokens_per_req < 0 时抛 ValueError。
    """
    raise NotImplementedError("实现 plan_capacity")


def restore_drill(results: dict) -> dict:
    """备份恢复演练的判定。results 必须包含：
    backup_exists (bool)、restore_minutes、rto_minutes、data_loss_minutes、rpo_minutes、smoke_passed (bool)。

    返回 {"passed": bool, "failed_items": list[str]}；failed_items 的顺序固定为：
    - "backup_exists"：没有备份；
    - "rto"：restore_minutes > rto_minutes（恢复太慢）；
    - "rpo"：data_loss_minutes > rpo_minutes（丢数据太多）；
    - "smoke"：恢复后的冒烟检查没通过。
    缺少任何字段抛 ValueError。
    """
    raise NotImplementedError("实现 restore_drill")
