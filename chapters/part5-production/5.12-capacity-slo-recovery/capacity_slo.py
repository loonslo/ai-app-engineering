"""
章节 5.12（L5.9）· 容量、SLO 与恢复
==========================================================
上线前要回答四个问题：
  ① 压测结果达标吗？           → 延迟分位数、错误率，对照 SLO
  ② 还能容忍多少次失败？       → 错误预算
  ③ 要几个实例、模型限额够吗？ → 容量规划（RPM / TPM）
  ④ 数据丢了能不能恢复？       → 备份恢复演练：恢复多快（RTO）、丢多少（RPO）

本文件是 gate 的参考实现，外加一个演示：读取仓库里已有的 reports/loadtest_*.json 汇总，
对照 SLO，并用示例数字走一遍错误预算、容量规划和恢复演练判定。

**这些压测报告来自本地假上游的小规模运行（2 个用户、5 秒），不代表线上容量**：
它们只能证明压测与统计链路可运行，不能用来推断真实服务能扛多少流量。

运行：python tools/run_chapter.py 5.12
==========================================================
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RequestResult:
    latency_ms: int
    status: int            # HTTP 状态码；0 表示超时


def percentile(values: list[int], q: float) -> int:
    """最近秩法：排序后取第 ceil(q*n) 个。q*n 先四舍五入再 ceil，否则 0.7*10 会被算成 7.000000000000001 → 8。"""
    if not values or not 0 < q <= 1:
        raise ValueError("values 不能为空，q 必须在 (0, 1] 内")
    ordered = sorted(values)
    rank = math.ceil(round(q * len(ordered), 9))
    return ordered[rank - 1]


def summarize_load(results: list[RequestResult], duration_s: float) -> dict:
    if not results or duration_s <= 0:
        raise ValueError("results 不能为空，duration_s 必须为正")
    latencies = [r.latency_ms for r in results]
    timeouts = sum(r.status == 0 for r in results)
    limited = sum(r.status == 429 for r in results)
    server_errors = sum(r.status >= 500 for r in results)
    return {
        "p50": percentile(latencies, 0.50), "p95": percentile(latencies, 0.95), "p99": percentile(latencies, 0.99),
        "error_rate": (timeouts + limited + server_errors) / len(results),
        "rps": len(results) / duration_s,
        "counts": {"429": limited, "5xx": server_errors, "timeout": timeouts},
    }


def check_slo(summary: dict, slo: dict) -> list[str]:
    failed = []
    if summary["p95"] > slo["p95_ms"]:
        failed.append("p95_ms")
    if summary["error_rate"] > slo["error_rate"]:
        failed.append("error_rate")
    return failed


def error_budget(slo_target: float, total: int, failed: int) -> dict:
    if not 0 < slo_target <= 1 or total < 0 or failed < 0 or failed > total:
        raise ValueError("slo_target 须在 (0,1]，0 <= failed <= total")
    allowed = math.floor(round((1 - slo_target) * total, 9))
    if allowed == 0:
        used = 0.0 if failed == 0 else 1.0
    else:
        used = failed / allowed
    return {"allowed_failures": allowed, "used_ratio": used, "exhausted": failed > allowed}


def plan_capacity(peak_rps: float, per_instance_rps: float, headroom: float, *,
                  tokens_per_req: int, rpm_limit: int | None, tpm_limit: int | None) -> dict:
    if peak_rps <= 0 or per_instance_rps <= 0 or headroom < 0 or tokens_per_req < 0:
        raise ValueError("峰值与单实例吞吐必须为正，余量与 token 数不能为负")
    instances = math.ceil(round(peak_rps * (1 + headroom) / per_instance_rps, 9))
    rpm_needed = peak_rps * 60
    tpm_needed = rpm_needed * tokens_per_req
    over = {}
    if rpm_limit is not None and rpm_needed > rpm_limit:
        over["rpm"] = rpm_needed / rpm_limit
    if tpm_limit is not None and tpm_needed > tpm_limit:
        over["tpm"] = tpm_needed / tpm_limit
    bottleneck = "none" if not over else max(over, key=lambda name: (over[name], name == "rpm"))
    return {"instances": instances, "rpm_needed": rpm_needed, "tpm_needed": tpm_needed, "bottleneck": bottleneck}


REQUIRED_DRILL_FIELDS = ("backup_exists", "restore_minutes", "rto_minutes", "data_loss_minutes", "rpo_minutes", "smoke_passed")


def restore_drill(results: dict) -> dict:
    missing = [name for name in REQUIRED_DRILL_FIELDS if name not in results]
    if missing:
        raise ValueError(f"演练记录缺少字段：{', '.join(missing)}")
    failed = []
    if not results["backup_exists"]:
        failed.append("backup_exists")
    if results["restore_minutes"] > results["rto_minutes"]:
        failed.append("rto")
    if results["data_loss_minutes"] > results["rpo_minutes"]:
        failed.append("rpo")
    if not results["smoke_passed"]:
        failed.append("smoke")
    return {"passed": not failed, "failed_items": failed}


# ---------------------------------------------------------------- 演示 ----
def load_local_reports() -> list[Path]:
    return sorted((REPO_ROOT / "reports").glob("loadtest_*.json"))


def main() -> int:
    print("===== 1) 本地压测报告对照 SLO（来自本地假上游，不代表线上容量）=====")
    reports = load_local_reports()
    if not reports:
        print("  没找到 reports/loadtest_*.json；先用 5.8 / capstone 的压测脚本生成，或跳过这一节。")
    slo = {"p95_ms": 2000, "error_rate": 0.01}
    for path in reports:
        data = json.loads(path.read_text(encoding="utf-8"))
        client = data["client"]
        summary = {"p95": client["p95_ms"], "error_rate": client["error_rate_pct"] / 100}
        print(f"  {path.name}：{client['requests']} 个请求，{data['users']} 个用户，{data['duration']}；"
              f"p95={summary['p95']}ms，错误率={summary['error_rate']:.2%}；未达标项：{check_slo(summary, slo) or '无'}")
    print("  注意：2 个用户 5 秒的小样本，p95 只由很少几个请求决定。")

    print("\n===== 2) 一次含限流的压测样例（脚本化数据）=====")
    sample = ([RequestResult(80 + i, 200) for i in range(90)] + [RequestResult(120, 429)] * 6
              + [RequestResult(900, 503)] * 3 + [RequestResult(5000, 0)])
    summary = summarize_load(sample, duration_s=10)
    print("  汇总：", summary)
    print("  对照 SLO（p95≤2000ms，错误率≤1%）：未达标项 →", check_slo(summary, slo))

    print("\n===== 3) 错误预算 =====")
    print("  99.9% 目标、10 万请求、已失败 60：", error_budget(0.999, 100_000, 60))
    print("  99.9% 目标、10 万请求、已失败 140：", error_budget(0.999, 100_000, 140))

    print("\n===== 4) 容量规划（限额数字为示例，请换成你的模型当前真实限额）=====")
    print("  峰值 20 rps、单实例 8 rps、余量 30%、每请求 3000 token、RPM 限额 1500、TPM 限额 4_000_000：")
    print("  ", plan_capacity(20, 8, 0.3, tokens_per_req=3000, rpm_limit=1500, tpm_limit=4_000_000))

    print("\n===== 5) 备份恢复演练判定（演练记录为示例）=====")
    print("  ", restore_drill({"backup_exists": True, "restore_minutes": 12, "rto_minutes": 30,
                              "data_loss_minutes": 8, "rpo_minutes": 5, "smoke_passed": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ----------------------------------------------------------
# 小结：
# - 分位数要用"最近秩"并注意浮点；p95、p99 比平均值更接近用户感受。
# - 429、5xx、超时都算失败；限流要单独计数，因为它指向容量而不是 bug。
# - 错误预算把"可用性目标"变成"还能失败几次"，用完就该停止发布、先修稳定性。
# - 容量规划要同时看实例数和模型限额：很多时候先撞上的是厂商的 RPM/TPM，而不是你的 CPU。
# - 恢复演练只写"有备份"不算数：要实际恢复一次，量恢复时间（RTO）与丢失数据（RPO），再跑冒烟检查。
# ----------------------------------------------------------
