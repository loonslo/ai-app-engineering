"""L5.9 容量、SLO 与恢复 gate：纯计算，不读文件、不联网、不跑压测。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    if spec is None or spec.loader is None:
        raise ValueError("无法加载候选模块")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate"] = module
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def raises(fn, error=ValueError) -> bool:
    try:
        fn()
    except error:
        return True
    return False


class Gate:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, path: Path) -> int:
        passed = sum(row["ok"] for row in self.rows)
        for row in self.rows:
            print(f"[{'PASS' if row['ok'] else 'FAIL'}] {row['name']} {row['error']}")
        print(f"{passed}/{len(self.rows)} passed")
        report = {"gate": "L5.9-capacity-slo-recovery", "module": str(path), "passed": passed,
                  "total": len(self.rows), "ok": passed == len(self.rows), "checks": self.rows}
        (HERE / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    path = Path(parser.parse_args().module).resolve()
    core = load_module(path)
    gate = Gate()
    R = core.RequestResult

    def test_percentile_known():
        values = [50, 10, 40, 20, 30, 60, 90, 70, 80, 100]  # 故意乱序
        expect(core.percentile(values, 0.5) == 50, "p50 应取第 5 个值 50")
        expect(core.percentile(values, 0.95) == 100, "p95 应取第 10 个值 100")
        expect(core.percentile([7], 0.99) == 7, "单个值的任何分位数都是它本身")
        expect(core.percentile(values, 1.0) == 100, "q=1 取最大值")

    def test_percentile_float():
        values = list(range(10, 110, 10))  # 10..100，共 10 个
        expect(core.percentile(values, 0.7) == 70, f"0.7*10 应取第 7 个值 70（注意浮点误差），实际 {core.percentile(values, 0.7)}")
        expect(core.percentile(values, 0.9) == 90, f"p90 应为 90，实际 {core.percentile(values, 0.9)}")

    def test_percentile_errors():
        expect(raises(lambda: core.percentile([], 0.5)), "空输入应抛 ValueError")
        for q in (0, -0.1, 1.01):
            expect(raises(lambda q=q: core.percentile([1, 2], q)), f"q={q} 应抛 ValueError")

    def test_summary():
        results = [R(100, 200)] * 90 + [R(200, 429)] * 4 + [R(300, 503)] * 3 + [R(5000, 0)] * 3
        summary = core.summarize_load(results, 20)
        expect(summary["error_rate"] == 0.10, f"429、5xx、超时都算失败，错误率应为 0.10，实际 {summary['error_rate']}")
        expect(summary["counts"] == {"429": 4, "5xx": 3, "timeout": 3}, f"计数不对：{summary['counts']}")
        expect(summary["rps"] == 5.0, f"rps 应为 100/20=5.0，实际 {summary['rps']}")
        expect((summary["p50"], summary["p95"], summary["p99"]) == (100, 300, 5000), f"分位数不对：{summary}")
        expect(raises(lambda: core.summarize_load([], 10)) and raises(lambda: core.summarize_load([R(1, 200)], 0)), "空结果与非正时长应抛 ValueError")

    def test_slo():
        slo = {"p95_ms": 500, "error_rate": 0.01}
        expect(core.check_slo({"p95": 500, "error_rate": 0.01}, slo) == [], "恰好等于 SLO 算达标")
        expect(core.check_slo({"p95": 501, "error_rate": 0.0}, slo) == ["p95_ms"], "p95 超标")
        expect(core.check_slo({"p95": 100, "error_rate": 0.02}, slo) == ["error_rate"], "错误率超标")
        expect(core.check_slo({"p95": 900, "error_rate": 0.5}, slo) == ["p95_ms", "error_rate"], "两项都超标时顺序固定")

    def test_budget():
        budget = core.error_budget(0.999, 100_000, 60)
        expect(budget == {"allowed_failures": 100, "used_ratio": 0.6, "exhausted": False}, f"预算不对：{budget}")
        expect(core.error_budget(0.9, 10, 1)["allowed_failures"] == 1, "(1-0.9)*10 应允许 1 次失败（注意浮点误差）")
        expect(core.error_budget(0.95, 100, 5)["exhausted"] is False, "用满恰好等于允许数不算耗尽")
        expect(core.error_budget(0.95, 100, 6)["exhausted"] is True, "超过允许数才算耗尽")

    def test_budget_edges():
        expect(core.error_budget(1.0, 50, 0) == {"allowed_failures": 0, "used_ratio": 0.0, "exhausted": False}, "目标 100% 且无失败")
        expect(core.error_budget(1.0, 50, 1) == {"allowed_failures": 0, "used_ratio": 1.0, "exhausted": True}, "目标 100% 出现失败即耗尽")
        for args in ((0, 10, 0), (1.1, 10, 0), (0.9, -1, 0), (0.9, 10, -1), (0.9, 10, 11)):
            expect(raises(lambda args=args: core.error_budget(*args)), f"非法参数应抛 ValueError：{args}")

    def plan(**kwargs):
        base = {"peak_rps": 10, "per_instance_rps": 4, "headroom": 0.2, "tokens_per_req": 1000, "rpm_limit": None, "tpm_limit": None}
        base.update(kwargs)
        return core.plan_capacity(base.pop("peak_rps"), base.pop("per_instance_rps"), base.pop("headroom"), **base)

    def test_instances():
        expect(plan()["instances"] == 3, f"10*1.2/4=3 个实例，实际 {plan()['instances']}")
        expect(plan(peak_rps=3, per_instance_rps=1.1, headroom=0.1)["instances"] == 3, "3*1.1/1.1 应是 3 而不是 4（注意浮点误差）")
        expect(plan(peak_rps=10, per_instance_rps=4, headroom=0.3)["instances"] == 4, "13/4=3.25 应向上取整为 4")
        expect(plan()["bottleneck"] == "none", "没有限额时瓶颈为 none")

    def test_rpm():
        result = plan(rpm_limit=500, tpm_limit=10_000_000)
        expect(result["rpm_needed"] == 600 and result["tpm_needed"] == 600_000, f"需求不对：{result}")
        expect(result["bottleneck"] == "rpm", "600 RPM > 500 限额，瓶颈应为 rpm")
        expect(plan(rpm_limit=600)["bottleneck"] == "none", "恰好等于限额不算撞上")

    def test_tpm():
        expect(plan(rpm_limit=1000, tpm_limit=500_000)["bottleneck"] == "tpm", "600000 TPM > 500000 限额，瓶颈应为 tpm")
        expect(plan(rpm_limit=500, tpm_limit=300_000)["bottleneck"] == "tpm", "两项都撞上时取比值更大的：tpm 2.0 > rpm 1.2")
        expect(plan(rpm_limit=300, tpm_limit=500_000)["bottleneck"] == "rpm", "rpm 比值 2.0 > tpm 1.2")
        expect(plan(rpm_limit=300, tpm_limit=300_000)["bottleneck"] == "rpm", "比值相等选 rpm")
        expect(raises(lambda: plan(peak_rps=0)) and raises(lambda: plan(per_instance_rps=0)) and raises(lambda: plan(headroom=-0.1)), "非法参数应抛 ValueError")

    good = {"backup_exists": True, "restore_minutes": 20, "rto_minutes": 30, "data_loss_minutes": 5, "rpo_minutes": 5, "smoke_passed": True}

    def test_drill_pass():
        expect(core.restore_drill(good) == {"passed": True, "failed_items": []}, "恰好等于 RTO/RPO 算通过")

    def test_drill_fail():
        bad = {**good, "backup_exists": False, "restore_minutes": 31, "data_loss_minutes": 6, "smoke_passed": False}
        result = core.restore_drill(bad)
        expect(result == {"passed": False, "failed_items": ["backup_exists", "rto", "rpo", "smoke"]}, f"失败项与顺序不对：{result}")
        expect(core.restore_drill({**good, "restore_minutes": 45})["failed_items"] == ["rto"], "只有恢复太慢时只列 rto")
        expect(raises(lambda: core.restore_drill({k: v for k, v in good.items() if k != "rpo_minutes"})), "缺字段应抛 ValueError")

    gate.check("01 分位数的已知数值", test_percentile_known)
    gate.check("02 分位数不被浮点误差带偏", test_percentile_float)
    gate.check("03 空输入与非法 q 报错", test_percentile_errors)
    gate.check("04 错误率包含 429 与超时，并汇总计数与 rps", test_summary)
    gate.check("05 SLO 判断", test_slo)
    gate.check("06 错误预算计算", test_budget)
    gate.check("07 错误预算边界与参数校验", test_budget_edges)
    gate.check("08 容量规划的实例数", test_instances)
    gate.check("09 RPM 瓶颈", test_rpm)
    gate.check("10 TPM 瓶颈与两项都撞上", test_tpm)
    gate.check("11 恢复演练通过", test_drill_pass)
    gate.check("12 恢复演练失败时列出失败项", test_drill_fail)
    return gate.report(path)


if __name__ == "__main__":
    raise SystemExit(main())
