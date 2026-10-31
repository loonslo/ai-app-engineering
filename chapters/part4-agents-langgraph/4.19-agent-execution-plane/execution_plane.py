"""L4.11：数据库保存任务与步骤；worker 可退出，状态与副作用结果不能随它消失。"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import uuid
from collections.abc import Callable, MutableMapping
from dataclasses import asdict, dataclass
from pathlib import Path

TERMINAL = {"succeeded", "failed", "cancelled", "budget_exceeded"}


@dataclass
class StepRecord:
    stage: str
    ok: bool
    output: str
    tokens: int
    duration_ms: int
    attempt: int
    error: str | None = None


@dataclass
class Budget:
    max_steps: int
    max_tokens: int
    max_wall_ms: int


@dataclass
class Task:
    id: str
    tenant_id: str
    payload: dict
    status: str
    current_stage: int
    steps: list[StepRecord]
    budget: Budget
    approvals: dict[str, bool]
    cancel_requested: bool = False
    started_ms: int | None = None


@dataclass(frozen=True)
class StageOutput:
    output: str
    tokens: int


@dataclass(frozen=True)
class Stage:
    name: str
    fn: Callable[[Task], StageOutput]
    side_effect: bool = False
    needs_approval: bool = False
    max_attempts: int = 2


class RetryableError(Exception):
    """只有明确标为可重试的错误才在本阶段内重试。"""


def submit(store, tenant_id: str, payload: dict, idempotency_key: str, budget: Budget) -> str:
    existing = store.find_by_key(tenant_id, idempotency_key)
    if existing is not None:
        return existing.id
    task_id = uuid.uuid5(uuid.NAMESPACE_URL, json.dumps([tenant_id, idempotency_key])).hex
    task = Task(task_id, tenant_id, payload, "queued", 0, [], budget, {})
    store.put(task, idempotency_key=idempotency_key)
    return task_id


def _exhausted(task: Task, clock: Callable[[], int]) -> bool:
    return (len(task.steps) >= task.budget.max_steps
            or sum(step.tokens for step in task.steps) >= task.budget.max_tokens
            or clock() - task.started_ms >= task.budget.max_wall_ms)


def run_until_blocked(store, task_id: str, stages: list[Stage], *, clock,
                      side_effect_log: MutableMapping[str, StageOutput]) -> Task:
    task = store.get(task_id)
    if task.status in TERMINAL:
        return task
    if task.started_ms is None:
        task.started_ms = clock()
    task.status = "running"
    store.put(task)
    while task.current_stage < len(stages):
        # 重新读取取消/审批，调用方不用修改 worker 持有的对象。
        task = store.get(task_id)
        if task.cancel_requested:
            task.status = "cancelled"
            store.put(task)
            return task
        if _exhausted(task, clock):
            task.status = "budget_exceeded"
            store.put(task)
            return task
        stage = stages[task.current_stage]
        if stage.needs_approval:
            decision = task.approvals.get(stage.name)
            if decision is None:
                task.status = "waiting_approval"
                store.put(task)
                return task
            if not decision:
                task.steps.append(StepRecord(stage.name, False, "", 0, 0, 0, "审批被拒绝"))
                task.status = "failed"
                store.put(task)
                return task
        attempt = 1 + sum(step.stage == stage.name for step in task.steps)
        started = clock()
        try:
            key = f"{task.id}:{stage.name}"
            if stage.side_effect and key in side_effect_log:
                result = side_effect_log[key]
            else:
                result = stage.fn(task)
                if stage.side_effect:
                    # 缓存独立于任务快照；快照落盘前退出也能复用结果。
                    side_effect_log[key] = result
        except Exception as exc:
            task.steps.append(StepRecord(stage.name, False, "", 0, clock() - started,
                                         attempt, f"{type(exc).__name__}: {exc}"))
            retry = isinstance(exc, RetryableError) and attempt < stage.max_attempts
            task.status = "running" if retry else "failed"
            store.put(task)
            if retry:
                continue
            return task
        # BaseException 不被吞掉：真实进程退出不等同于一次可读的业务失败。
        task.steps.append(StepRecord(stage.name, True, result.output, result.tokens,
                                     clock() - started, attempt))
        task.current_stage += 1
        # 阶段执行期间发生的取消不能被旧快照覆盖。
        task.cancel_requested = store.get(task_id).cancel_requested
        store.put(task)
    task.status = "cancelled" if task.cancel_requested else "succeeded"
    store.put(task)
    return task


def approve(store, task_id: str, stage: str, decision: bool) -> Task:
    task = store.get(task_id)
    if task.status not in TERMINAL:
        task.approvals[stage] = decision
        if task.status == "waiting_approval":
            task.status = "queued"
        store.put(task)
    return task


def cancel(store, task_id: str) -> Task:
    task = store.get(task_id)
    if task.status not in TERMINAL:
        task.cancel_requested = True
        store.put(task)
    return task


def deliver_result(task: Task, webhook_fn, delivered: set[str]) -> bool:
    if task.status not in TERMINAL or task.id in delivered:
        return False
    try:
        webhook_fn(task)
    except Exception:
        return False
    delivered.add(task.id)
    return True


class SQLiteStore:
    """单 worker 教学存储：任务快照与步骤表在同一事务提交。"""

    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(path)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, tenant TEXT NOT NULL, request_key TEXT NOT NULL,
                snapshot TEXT NOT NULL, UNIQUE(tenant, request_key));
            CREATE TABLE IF NOT EXISTS steps (
                task_id TEXT NOT NULL, ordinal INTEGER NOT NULL, record TEXT NOT NULL,
                PRIMARY KEY(task_id, ordinal));
            CREATE TABLE IF NOT EXISTS effects (key TEXT PRIMARY KEY, result TEXT NOT NULL);
        """)

    def get(self, task_id: str) -> Task:
        row = self.db.execute("SELECT snapshot FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        data = json.loads(row[0])
        data["budget"] = Budget(**data["budget"])
        data["steps"] = [StepRecord(**step) for step in data["steps"]]
        return Task(**data)

    def find_by_key(self, tenant_id: str, idempotency_key: str) -> Task | None:
        row = self.db.execute("SELECT id FROM tasks WHERE tenant=? AND request_key=?",
                              (tenant_id, idempotency_key)).fetchone()
        return self.get(row[0]) if row else None

    def put(self, task: Task, *, idempotency_key: str | None = None) -> None:
        snapshot = json.dumps(asdict(task), ensure_ascii=False)
        with self.db:
            if idempotency_key is not None:
                self.db.execute("INSERT INTO tasks VALUES(?,?,?,?)",
                                (task.id, task.tenant_id, idempotency_key, snapshot))
            else:
                self.db.execute("UPDATE tasks SET snapshot=? WHERE id=?", (snapshot, task.id))
            self.db.executemany("INSERT OR REPLACE INTO steps VALUES(?,?,?)",
                                [(task.id, index, json.dumps(asdict(step), ensure_ascii=False))
                                 for index, step in enumerate(task.steps)])

    def close(self) -> None:
        self.db.close()


class SQLiteEffects(MutableMapping):
    """与任务快照分开落盘；真实远端工具仍须接受同一个业务幂等键。"""

    def __init__(self, store: SQLiteStore):
        self.store = store

    def __getitem__(self, key: str) -> StageOutput:
        row = self.store.db.execute("SELECT result FROM effects WHERE key=?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return StageOutput(**json.loads(row[0]))

    def __setitem__(self, key: str, value: StageOutput) -> None:
        with self.store.db:
            self.store.db.execute("INSERT OR REPLACE INTO effects VALUES(?,?)",
                                  (key, json.dumps(asdict(value), ensure_ascii=False)))

    def __delitem__(self, key: str) -> None:
        with self.store.db:
            self.store.db.execute("DELETE FROM effects WHERE key=?", (key,))

    def __iter__(self):
        return iter(row[0] for row in self.store.db.execute("SELECT key FROM effects ORDER BY key"))

    def __len__(self) -> int:
        return self.store.db.execute("SELECT count(*) FROM effects").fetchone()[0]


class SimulatedCrash(BaseException):
    """只在演示中模拟进程消失，不当作可重试业务异常。"""


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="execution-plane-") as directory:
        path = Path(directory) / "tasks.sqlite"
        store = SQLiteStore(path)
        task_id = submit(store, "tenant-a", {"topic": "调研报告"}, "report-1", Budget(10, 1000, 60000))
        print("提交即返回 task_id；状态：", store.get(task_id).status)
        calls = []

        def gather(_task):
            calls.append("gather")
            return StageOutput("固定资料：异步任务应保存状态", 8)

        def crash(_task):
            raise SimulatedCrash()

        stages = [Stage("gather", gather, side_effect=True), Stage("draft", crash),
                  Stage("approve", lambda task: StageOutput("人工已批准", 0), needs_approval=True),
                  Stage("publish", lambda task: StageOutput("已发布到本地演示账本", 0), side_effect=True)]
        def clock() -> int:
            return int(time.monotonic() * 1000)
        try:
            run_until_blocked(store, task_id, stages, clock=clock, side_effect_log=SQLiteEffects(store))
        except SimulatedCrash:
            print("模拟崩溃；成功步骤已落盘：", [step.stage for step in store.get(task_id).steps])
        store.close()
        # 关闭连接再打开，不能依赖旧 Python 对象续跑。
        store = SQLiteStore(path)
        stages[1] = Stage("draft", lambda task: StageOutput("调研报告草稿", 12))
        task = run_until_blocked(store, task_id, stages, clock=clock, side_effect_log=SQLiteEffects(store))
        print("重新打开数据库续跑：", task.status, "gather调用次数：", len(calls))
        approve(store, task_id, "approve", True)
        task = run_until_blocked(store, task_id, stages, clock=clock, side_effect_log=SQLiteEffects(store))
        print("批准后：", task.status, "步骤：", [step.stage for step in task.steps])
        delivered = set()
        print("投递：", deliver_result(task, lambda result: print("本地webhook：", result.status), delivered))
        print("重复投递：", deliver_result(task, lambda result: None, delivered))
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
