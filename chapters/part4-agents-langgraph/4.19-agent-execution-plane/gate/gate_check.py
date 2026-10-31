"""L4.11：内存快照与假时钟，不启动后台服务或真实模型。"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(path: Path):
    sys.path.insert(0, str(HERE.parent))
    spec = importlib.util.spec_from_file_location("candidate", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate"] = module
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class MemoryStore:
    def __init__(self):
        self.tasks, self.keys, self.saved = {}, {}, []

    def get(self, task_id):
        return copy.deepcopy(self.tasks[task_id])

    def find_by_key(self, tenant_id, key):
        task_id = self.keys.get((tenant_id, key))
        return self.get(task_id) if task_id else None

    def put(self, task, *, idempotency_key=None):
        self.tasks[task.id] = copy.deepcopy(task)
        self.saved.append(copy.deepcopy(task))
        if idempotency_key is not None:
            self.keys[task.tenant_id, idempotency_key] = task.id


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now


class Crash(BaseException):
    pass


class Gate:
    def __init__(self):
        self.rows = []

    def check(self, name, fn):
        try:
            fn()
        except Exception as exc:
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, path):
        passed = sum(row["ok"] for row in self.rows)
        for row in self.rows:
            print(f"[{'PASS' if row['ok'] else 'FAIL'}] {row['name']} {row['error']}")
        print(f"{passed}/{len(self.rows)} passed")
        report = {"gate": "L4.11-agent-execution-plane", "module": str(path), "passed": passed,
                  "total": len(self.rows), "ok": passed == len(self.rows), "checks": self.rows}
        (HERE / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if report["ok"] else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    path = Path(parser.parse_args().module).resolve()
    core = load_module(path)
    gate = Gate()

    def setup(budget=None):
        store, clock, effects = MemoryStore(), Clock(), {}
        task_id = core.submit(store, "t1", {"topic": "报告"}, "k1", budget or core.Budget(20, 100, 1000))
        return store, task_id, clock, effects

    def run(store, task_id, stages, clock, effects):
        return core.run_until_blocked(store, task_id, stages, clock=clock, side_effect_log=effects)

    def stage(name, **kwargs):
        return core.Stage(name, lambda task: core.StageOutput(name, 2), **kwargs)

    def submit_check():
        store, task_id, _, _ = setup()
        same = core.submit(store, "t1", {}, "k1", core.Budget(1, 1, 1))
        other = core.submit(store, "t2", {}, "k1", core.Budget(1, 1, 1))
        expect(same == task_id and other != task_id and store.get(task_id).status == "queued", "期望同租户幂等、跨租户隔离、初始queued")
    gate.check("01 提交幂等与租户隔离", submit_check)

    def normal():
        store, task_id, clock, effects = setup()
        task = run(store, task_id, [stage("plan"), stage("draft")], clock, effects)
        expect(task.status == "succeeded" and task.current_stage == 2 and len(task.steps) == 2, "期望两个阶段成功且游标为2")
    gate.check("02 正常阶段全部完成", normal)

    def crash_resume():
        store, task_id, clock, effects = setup()
        calls = []
        def gather(task):
            calls.append("gather")
            return core.StageOutput("资料", 2)
        def crash(task):
            raise Crash()
        stages = [core.Stage("gather", gather, side_effect=True), core.Stage("draft", crash)]
        try:
            run(store, task_id, stages, clock, effects)
        except Crash:
            pass
        expect(store.get(task_id).current_stage == 1, "崩溃前成功游标须落盘")
        stages[1] = stage("draft")
        task = run(store, task_id, stages, clock, effects)
        expect(task.status == "succeeded" and calls == ["gather"], "续跑不得重复gather")
    gate.check("03 进程崩溃续跑不重复成功副作用", crash_resume)

    def cached_effect():
        store, task_id, clock, effects = setup()
        effects[f"{task_id}:publish"] = core.StageOutput("已有回执", 3)
        def forbidden(task):
            raise AssertionError("不得重调")
        task = run(store, task_id, [core.Stage("publish", forbidden, side_effect=True)], clock, effects)
        expect(task.status == "succeeded" and task.steps[0].output == "已有回执", "期望从独立副作用缓存恢复")
    gate.check("04 快照前崩溃已有回执复用", cached_effect)

    def approval(decision):
        store, task_id, clock, effects = setup()
        calls = []
        stages = [core.Stage("approve", lambda task: calls.append(1) or core.StageOutput("通过", 0), needs_approval=True)]
        waiting = run(store, task_id, stages, clock, effects)
        expect(waiting.status == "waiting_approval" and not calls, "无决定应停且不执行工具")
        core.approve(store, task_id, "approve", decision)
        task = run(store, task_id, stages, clock, effects)
        expect(task.status == ("succeeded" if decision else "failed"), "批准或拒绝状态不符")
        expect(len(calls) == int(decision), "拒绝不得调用阶段")
        if not decision:
            expect("审批" in task.steps[-1].error, "拒绝需可读审批原因")
    gate.check("05 等待审批再批准继续", lambda: approval(True))
    gate.check("06 拒绝审批失败且不调用", lambda: approval(False))

    def budget_check(kind):
        budget = core.Budget(1 if kind == "steps" else 20, 2 if kind == "tokens" else 100, 5 if kind == "wall" else 1000)
        store, task_id, clock, effects = setup(budget)
        def first(task):
            clock.now = 6
            return core.StageOutput("first", 2)
        task = run(store, task_id, [core.Stage("first", first), stage("second")], clock, effects)
        expect(task.status == "budget_exceeded" and task.current_stage == 1, "消耗达预算后第二阶段须不执行")
    gate.check("07 步数预算阻断下一阶段", lambda: budget_check("steps"))
    gate.check("08 token预算阻断下一阶段", lambda: budget_check("tokens"))
    gate.check("09 墙钟预算阻断下一阶段", lambda: budget_check("wall"))

    def cancellation():
        store, task_id, clock, effects = setup()
        def first(task):
            core.cancel(store, task_id)
            return core.StageOutput("first", 1)
        task = run(store, task_id, [core.Stage("first", first), stage("forbidden")], clock, effects)
        expect(task.status == "cancelled" and task.current_stage == 1, "阶段间取消须保留且阻断后续")
    gate.check("10 阶段之间取消生效", cancellation)

    def retry(exhaust=False):
        store, task_id, clock, effects = setup()
        calls = []
        def flaky(task):
            calls.append(1)
            if len(calls) == 1 or exhaust:
                raise core.RetryableError("临时超时")
            return core.StageOutput("恢复", 2)
        task = run(store, task_id, [core.Stage("fetch", flaky)], clock, effects)
        expect(task.status == ("failed" if exhaust else "succeeded") and len(calls) == 2, "可重试错误次数/状态不符")
        expect([record.attempt for record in task.steps] == [1, 2], "每次尝试须落盘并累计编号")
    gate.check("11 可重试错误第二次成功", retry)
    gate.check("12 重试用尽失败", lambda: retry(True))

    def permanent_error():
        store, task_id, clock, effects = setup()
        def bad(task):
            raise ValueError("非法输入")
        task = run(store, task_id, [core.Stage("bad", bad)], clock, effects)
        expect(task.status == "failed" and len(task.steps) == 1 and "非法输入" in task.steps[0].error, "不可重试错误应一次失败并保存原因")
    gate.check("13 不可重试错误直接失败", permanent_error)

    def persisted():
        store, task_id, clock, effects = setup()
        task = run(store, task_id, [stage("one"), stage("two")], clock, effects)
        expect(task.status == "succeeded", "正常任务应成功")
        expect(any(len(item.steps) == 1 for item in store.saved) and any(len(item.steps) == 2 for item in store.saved), "每个阶段结束立即有快照，不得最后一次性写入")
    gate.check("14 每阶段记录立即持久化", persisted)

    def webhook():
        store, task_id, clock, effects = setup()
        task, delivered, calls = store.get(task_id), set(), []
        expect(core.deliver_result(task, lambda task: calls.append(1), delivered) is False, "非终态不能投递")
        task = run(store, task_id, [], clock, effects)
        first = core.deliver_result(task, lambda task: calls.append(1), delivered)
        second = core.deliver_result(task, lambda task: calls.append(1), delivered)
        expect(first and not second and calls == [1], "终态重复投递只能成功一次")
    gate.check("15 webhook终态去重", webhook)

    def webhook_failure():
        store, task_id, clock, effects = setup()
        task = run(store, task_id, [], clock, effects)
        delivered = set()
        def bad(task):
            raise TimeoutError()
        expect(not core.deliver_result(task, bad, delivered) and not delivered, "失败不得记为已投递")
        expect(core.deliver_result(task, lambda task: None, delivered), "失败后须可重投")
    gate.check("16 webhook失败可重投", webhook_failure)
    return gate.report(path)


if __name__ == "__main__":
    raise SystemExit(main())
