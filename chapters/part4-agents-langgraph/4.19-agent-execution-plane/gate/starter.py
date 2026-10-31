"""L4.11 专项 Agent 执行面 · 闭卷骨架。
只读 README、本文件与标准库文档；不允许修改 gate_check.py。
运行：python chapters/part4-agents-langgraph/4.19-agent-execution-plane/gate/gate_check.py
"""
from dataclasses import dataclass
from typing import Callable

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
    pass


def submit(store, tenant_id: str, payload: dict, idempotency_key: str, budget: Budget) -> str:
    """同(tenant_id,key)返回已有Task.id，否则创建queued、current_stage=0的新Task。
    store.find_by_key(tenant_id,key)返回Task或None；get(id)返回独立快照；
    put(task,idempotency_key=key)登记新任务，put(task)更新。id须不同租户隔离。
    """
    raise NotImplementedError("实现幂等提交")


def run_until_blocked(store, task_id: str, stages: list[Stage], *, clock, side_effect_log: dict[str, StageOutput]) -> Task:
    """终态原样返回；首次执行设置started_ms=clock()，从current_stage开始。
    每次尝试前重读任务，先取消、再预算、再审批。任一消耗达到上限即预算耗尽：
    len(steps)>=max_steps，sum(tokens)>=max_tokens，clock()-started_ms>=max_wall_ms。
    包括失败在内的每次尝试都计步；只在阶段开始前检查，不中断正在执行的函数。
    needs_approval无决定则waiting_approval；False则failed并记录error含'审批'的失败步骤。
    每次尝试成功/失败都追加StepRecord并立即put；attempt从1开始，按该阶段历史尝试累计。
    duration_ms=结束clock()-开始clock()；失败tokens=0。成功后current_stage加1。
    side_effect以f'{task_id}:{stage.name}'查缓存，已有则复用，无则成功后写缓存再put步骤。
    RetryableError在max_attempts内重试，其余Exception或用尽次数置failed；error含异常原因。
    BaseException模拟进程崩溃须向外传播，最后已保存的阶段仍可续跑；不重跑成功阶段。
    阶段间取消生效，保存步骤不可覆盖刚写入的cancel_requested。全部完成succeeded；
    最后阶段执行期间收到取消则cancelled。阶段名称唯一、预算正数、max_attempts>=1由调用方保证。
    """
    raise NotImplementedError("实现阶段推进")


def approve(store, task_id: str, stage: str, decision: bool) -> Task:
    """非终态保存审批决定；waiting_approval改queued供worker续跑；终态不变。"""
    raise NotImplementedError("实现审批")


def cancel(store, task_id: str) -> Task:
    """非终态置cancel_requested=True并保存，worker下次阶段前生效；终态不变。"""
    raise NotImplementedError("实现取消")


def deliver_result(task: Task, webhook_fn, delivered: set[str]) -> bool:
    """只有终态且id未在delivered时调用webhook_fn(task)；成功后登记id返回True。
    非终态、重复、webhook_fn抛Exception均False；失败不登记，可再次投递。
    """
    raise NotImplementedError("实现去重投递")
