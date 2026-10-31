"""
章节 5.10（L5.7）· 控制面与执行面集成：任务 API + 后台 worker + 签名 webhook
==========================================================
控制面（这个 FastAPI 服务）只做四件事：收任务、查状态、取消、转交审批。
执行面（4.19 的 execution_plane）负责真正跑：worker 从队列取 task_id，按阶段执行，
状态写数据库。两边只通过"任务表 + 队列"交流，所以 API 进程重启不会丢任务。

    客户端 ──POST /tasks──▶ 控制面 ──入队──▶ 队列 ──▶ worker(执行面) ──▶ 任务表
        ▲                       │                                         │
        └──── webhook（签名、重试、去重）◀───────── 任务终态 ───────────────┘

本文件包含：
1. gate 对应的三个接口：create_app / sign_payload / send_webhook；
2. PlaneStore：把 4.19 的 SQLiteStore 适配成控制面用的字典形状（每次操作新开连接，线程安全）；
3. 演示：用 TestClient 在进程内提交任务，后台线程当 worker，审批后继续，最后回调 webhook（假的 HTTP，不联网）。

运行：python tools/run_chapter.py 5.10
前置：4.19（执行面）、5.1（FastAPI）
==========================================================
"""

from __future__ import annotations

import hashlib
import hmac
import json
import queue as queue_module
import tempfile
import threading
import time
from collections.abc import Callable
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from execution_plane import (  # 4.19：执行面
    TERMINAL,
    Budget,
    SQLiteEffects,
    SQLiteStore,
    Stage,
    StageOutput,
    approve,
    cancel,
    run_until_blocked,
    submit,
)


class TaskRequest(BaseModel):
    payload: dict


class ApprovalRequest(BaseModel):
    stage: str
    decision: Literal["approve", "reject"]


def _view(task: dict) -> dict:
    return {"task_id": task["task_id"], "status": task["status"], "cancel_requested": task["cancel_requested"]}


def create_app(store, queue, *, approver_role: str = "approver") -> FastAPI:
    app = FastAPI(title="任务控制面")

    def identity(tenant: str | None, role: str | None) -> tuple[str, str]:
        if not tenant:
            raise HTTPException(401, "缺少 X-Tenant")
        return tenant, role or "member"

    def own_task(task_id: str, tenant: str) -> dict:
        task = store.get(task_id)
        # 不存在和属于别的租户都回 404：不泄露"这个 id 存在，只是不是你的"
        if task is None or task["tenant_id"] != tenant:
            raise HTTPException(404, "任务不存在")
        return task

    @app.post("/tasks", status_code=202)
    def submit_task(body: TaskRequest, x_tenant: str | None = Header(None), x_role: str | None = Header(None),
                    idempotency_key: str | None = Header(None)):
        tenant, _ = identity(x_tenant, x_role)
        if not idempotency_key:
            raise HTTPException(400, "必须带 Idempotency-Key 头")
        existing = store.find_by_key(tenant, idempotency_key)
        if existing is not None:  # 客户端超时重发同一个请求：返回同一个任务，不重复入队
            return {"task_id": existing["task_id"]}
        task = store.create(tenant, idempotency_key, body.payload)
        queue.put(task["task_id"])
        return {"task_id": task["task_id"]}

    @app.get("/tasks/{task_id}")
    def get_task(task_id: str, x_tenant: str | None = Header(None), x_role: str | None = Header(None)):
        tenant, _ = identity(x_tenant, x_role)
        return _view(own_task(task_id, tenant))

    @app.post("/tasks/{task_id}/cancel")
    def cancel_task(task_id: str, x_tenant: str | None = Header(None), x_role: str | None = Header(None)):
        tenant, _ = identity(x_tenant, x_role)
        own_task(task_id, tenant)
        store.request_cancel(task_id)  # 只置标志；worker 在阶段之间读到它再停
        return _view(store.get(task_id))

    @app.post("/tasks/{task_id}/approval")
    def approve_task(task_id: str, body: ApprovalRequest, x_tenant: str | None = Header(None),
                     x_role: str | None = Header(None)):
        tenant, role = identity(x_tenant, x_role)
        if role != approver_role:  # 先查角色再查任务：审批权限不取决于任务是否存在
            raise HTTPException(403, "无审批权限")
        own_task(task_id, tenant)
        store.record_approval(task_id, body.stage, body.decision == "approve")
        queue.put(task_id)  # 审批后让 worker 继续
        return _view(store.get(task_id))

    return app


def sign_payload(body: bytes, secret: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def send_webhook(task: dict, url: str, secret: bytes, http_post: Callable[[str, bytes, dict], int],
                 delivered: set[str], *, max_attempts: int = 3) -> bool:
    if max_attempts < 1:
        raise ValueError("max_attempts 必须大于等于 1")
    if task["task_id"] in delivered:  # 重复触发（比如 worker 重跑）不会让客户端收到两次
        return True
    body = json.dumps(task, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {"X-Signature": sign_payload(body, secret), "Content-Type": "application/json"}
    for _ in range(max_attempts):
        try:
            status = http_post(url, body, headers)
        except ConnectionError:
            continue
        if 200 <= status < 300:
            delivered.add(task["task_id"])
            return True
        if 400 <= status < 500:
            return False  # 4xx：请求本身有问题，重试没用
    return False


# ---------------------------------------------------------------- 适配 4.19 ----
class PlaneStore:
    """把 4.19 的 SQLiteStore 适配成控制面的字典协议。每次操作新开一个连接，线程之间互不干扰。"""

    def __init__(self, path: str | Path, budget: Budget | None = None) -> None:
        self.path = str(path)
        self.budget = budget or Budget(max_steps=10, max_tokens=1000, max_wall_ms=60_000)
        with closing(SQLiteStore(self.path)):
            pass  # 建表

    @staticmethod
    def _dict(task) -> dict:
        data = asdict(task)
        return {"task_id": task.id, "tenant_id": task.tenant_id, "status": task.status,
                "cancel_requested": task.cancel_requested, "approvals": data["approvals"]}

    def find_by_key(self, tenant_id: str, idempotency_key: str) -> dict | None:
        with closing(SQLiteStore(self.path)) as db:
            task = db.find_by_key(tenant_id, idempotency_key)
            return self._dict(task) if task else None

    def create(self, tenant_id: str, idempotency_key: str, payload: dict) -> dict:
        with closing(SQLiteStore(self.path)) as db:
            task_id = submit(db, tenant_id, payload, idempotency_key, self.budget)
            return self._dict(db.get(task_id))

    def get(self, task_id: str) -> dict | None:
        with closing(SQLiteStore(self.path)) as db:
            try:
                return self._dict(db.get(task_id))
            except KeyError:
                return None

    def request_cancel(self, task_id: str) -> None:
        with closing(SQLiteStore(self.path)) as db:
            cancel(db, task_id)

    def record_approval(self, task_id: str, stage: str, approved: bool) -> None:
        with closing(SQLiteStore(self.path)) as db:
            approve(db, task_id, stage, approved)


def demo_stages() -> list[Stage]:
    """脚本化的三个阶段：调研 → 需要人工审批的发布。不调用模型。"""
    return [
        Stage("research", lambda task: StageOutput("调研完成：" + str(task.payload.get("topic")), 20), side_effect=True),
        Stage("approve_publish", lambda task: StageOutput("已批准", 0), needs_approval=True),
        Stage("publish", lambda task: StageOutput("已发布到本地演示账本", 0), side_effect=True),
    ]


def worker_loop(path: str, jobs: queue_module.Queue, on_terminal: Callable[[dict], None], stop: threading.Event) -> None:
    """后台线程充当 worker：取 task_id → 跑到阻塞或终态 → 终态时触发回调。"""
    while not stop.is_set():
        try:
            task_id = jobs.get(timeout=0.1)
        except queue_module.Empty:
            continue
        with closing(SQLiteStore(path)) as db:
            task = run_until_blocked(db, task_id, demo_stages(), clock=lambda: int(time.monotonic() * 1000),
                                     side_effect_log=SQLiteEffects(db))
            if task.status in TERMINAL:
                on_terminal({"task_id": task.id, "status": task.status,
                             "steps": [step.stage for step in task.steps if step.ok]})


def main() -> int:
    from fastapi.testclient import TestClient

    secret = b"demo-secret"
    delivered: set[str] = set()
    received: list[dict] = []
    attempts = {"n": 0}

    def fake_http_post(url: str, body: bytes, headers: dict) -> int:
        """假的接收方：第一次回 503 模拟抖动；收到的请求验证签名。"""
        attempts["n"] += 1
        if attempts["n"] == 1:
            return 503
        ok = hmac.compare_digest(headers["X-Signature"], sign_payload(body, secret))
        received.append({"signature_ok": ok, "body": json.loads(body)})
        return 200

    with tempfile.TemporaryDirectory(prefix="control-plane-") as directory:
        path = str(Path(directory) / "tasks.sqlite")
        store = PlaneStore(path)
        jobs: queue_module.Queue = queue_module.Queue()
        stop = threading.Event()
        worker = threading.Thread(
            target=worker_loop, daemon=True,
            args=(path, jobs, lambda t: send_webhook(t, "https://client.example/hook", secret, fake_http_post, delivered), stop))
        worker.start()
        client = TestClient(create_app(store, jobs))
        tenant = {"X-Tenant": "tenant-a"}

        def wait_for(task_id: str, status: str) -> dict:
            for _ in range(100):
                view = client.get(f"/tasks/{task_id}", headers=tenant).json()
                if view["status"] == status:
                    return view
                time.sleep(0.05)
            raise TimeoutError(f"任务没有进入 {status}")

        response = client.post("/tasks", json={"payload": {"topic": "RAG 评测"}}, headers={**tenant, "Idempotency-Key": "req-1"})
        task_id = response.json()["task_id"]
        print("提交：", response.status_code, response.json())
        again = client.post("/tasks", json={"payload": {"topic": "RAG 评测"}}, headers={**tenant, "Idempotency-Key": "req-1"})
        print("同一个幂等键再提交：同一个 task_id？", again.json()["task_id"] == task_id)
        print("等待审批：", wait_for(task_id, "waiting_approval"))
        print("非审批角色批准：", client.post(f"/tasks/{task_id}/approval", json={"stage": "approve_publish", "decision": "approve"},
                                         headers={**tenant, "X-Role": "member"}).status_code)
        print("其他租户查询：", client.get(f"/tasks/{task_id}", headers={"X-Tenant": "tenant-b"}).status_code)
        client.post(f"/tasks/{task_id}/approval", json={"stage": "approve_publish", "decision": "approve"},
                    headers={**tenant, "X-Role": "approver"})
        print("批准后：", wait_for(task_id, "succeeded"))
        for _ in range(100):
            if received:
                break
            time.sleep(0.05)
        print("webhook：第 1 次 503 被重试，共调用", attempts["n"], "次；收到：", received)
        stop.set()
        worker.join(timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ----------------------------------------------------------
# 小结：
# - 控制面不跑任务，只收、查、取消、转交审批；执行面不暴露 HTTP，只读任务表。
# - 幂等键让"客户端超时重发"不变成两个任务；键按租户隔离。
# - 跨租户访问回 404，不回 403：不泄露别人的任务存在。
# - 审批是权限问题：先查角色，再查任务；批准后重新入队，worker 从上次阻塞处继续。
# - webhook：签名证明来源、有限重试扛抖动、4xx 不重试、按 task_id 去重。
# - 本章的 worker 是同进程线程，只为演示；真实系统用独立进程与持久队列（见 L5.8 之后）。
# ----------------------------------------------------------
