"""演练检查脚本：断言式，不是 pytest 用例（不命名为 test_*.py）。

修复前应当有 3 项失败，修复后全部通过：
    python chapters/part12-job-track/12.3-coding-interview/drill/check_drill.py
用 --root 指定要检查的目录（里面有 tickets 包），默认是本目录。
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
UTC = timezone.utc
CST = timezone(timedelta(hours=8))


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(HERE))
    root = Path(parser.parse_args().root).resolve()
    sys.path.insert(0, str(root))
    from tickets.models import Ticket
    from tickets.service import TicketService

    def make(i: int, title: str = "普通问题", priority: int = 2, due: datetime | None = None) -> Ticket:
        created = datetime(2026, 1, 1, 0, 0, tzinfo=UTC) + timedelta(minutes=i)
        return Ticket(f"T{i}", title, priority, created, due or created + timedelta(hours=4))

    def pagination() -> None:
        service = TicketService()
        for i in range(1, 8):
            service.submit(f"k{i}", make(i))
        expect([t.id for t in service.page(1, 3)] == ["T1", "T2", "T3"], f"第 1 页应是 T1–T3，实际 {[t.id for t in service.page(1, 3)]}")
        expect([t.id for t in service.page(3, 3)] == ["T7"], "最后一页应只有 T7")
        expect(service.page(4, 3) == [], "超出范围应返回空列表")
        try:
            service.page(0, 3)
        except ValueError:
            return
        raise AssertionError("page=0 应抛 ValueError")

    def timezone_compare() -> None:
        service = TicketService()
        # 东八区 2026-01-01 10:00 = UTC 02:00
        due = datetime(2026, 1, 1, 10, 0, tzinfo=CST)
        ticket, _ = service.submit("k", make(1, due=due))
        expect(service.overdue(datetime(2026, 1, 1, 5, 0, tzinfo=UTC)) == [ticket], "UTC 05:00 已超过东八区 10:00（= UTC 02:00），应超时")
        expect(service.overdue(datetime(2026, 1, 1, 1, 0, tzinfo=UTC)) == [], "UTC 01:00 未到 UTC 02:00，不应超时")
        try:
            service.overdue(datetime(2026, 1, 1, 5, 0))
        except ValueError:
            return
        raise AssertionError("没有时区的 now 应抛 ValueError")

    def idempotency() -> None:
        service = TicketService()
        first, created_first = service.submit("same-key", make(1))
        again, created_again = service.submit("same-key", make(2))
        expect(created_first is True, "第一次提交应 created=True")
        expect(created_again is False, "相同幂等键重复提交应 created=False")
        expect(again.id == first.id == "T1", f"重复提交应返回已有工单 T1，实际 {again.id}")
        expect(service.store.count() == 1, f"重复提交不应创建第二张工单，实际 {service.store.count()} 张")

    def routing() -> None:
        service = TicketService()
        queues = {
            "urgent-by-priority": service.submit("a", make(1, priority=1))[0].queue,
            "urgent-by-title": service.submit("b", make(2, title="系统宕机了"))[0].queue,
            "billing": service.submit("c", make(3, title="申请退款"))[0].queue,
            "general": service.submit("d", make(4))[0].queue,
        }
        expect(queues == {"urgent-by-priority": "urgent", "urgent-by-title": "urgent", "billing": "billing", "general": "general"}, f"分队列不对：{queues}")

    checks = [("分页边界", pagination), ("时区比较", timezone_compare), ("幂等判断", idempotency), ("分队列（无预埋 bug，作对照）", routing)]
    failed = 0
    for name, fn in checks:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"[PASS] {name}")
    print(f"{len(checks) - failed}/{len(checks)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
