"""L5.7 控制面与执行面集成 · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
control_execution_plane.py。实现下面的接口，然后运行：

    python chapters/part5-production/5.10-control-execution-plane/gate/gate_check.py

不允许为了通过而修改 gate_check.py。gate 用 FastAPI TestClient 与下面的内存 store / queue，
不启动服务、不联网、不起线程。
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI


class MemoryStore:
    """内存任务表（已给出，不要改）。任务是字典，字段：
    task_id、tenant_id、status（"queued" 等）、cancel_requested、approvals（{阶段名: 是否批准}）。
    真实实现在 4.19 的 SQLiteStore 上做了同样形状的适配。
    """

    def __init__(self) -> None:
        self.tasks: dict[str, dict] = {}

    def find_by_key(self, tenant_id: str, idempotency_key: str) -> dict | None:
        return next((t for t in self.tasks.values()
                     if t["tenant_id"] == tenant_id and t["idempotency_key"] == idempotency_key), None)

    def create(self, tenant_id: str, idempotency_key: str, payload: dict) -> dict:
        task = {"task_id": f"task-{len(self.tasks) + 1}", "tenant_id": tenant_id, "idempotency_key": idempotency_key,
                "payload": payload, "status": "queued", "cancel_requested": False, "approvals": {}}
        self.tasks[task["task_id"]] = task
        return task

    def get(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    def request_cancel(self, task_id: str) -> None:
        self.tasks[task_id]["cancel_requested"] = True

    def record_approval(self, task_id: str, stage: str, approved: bool) -> None:
        self.tasks[task_id]["approvals"][stage] = approved


class MemoryQueue:
    """内存队列（已给出）：put 放入 task_id，worker 取走。"""

    def __init__(self) -> None:
        self.items: list[str] = []

    def put(self, task_id: str) -> None:
        self.items.append(task_id)


def create_app(store, queue, *, approver_role: str = "approver") -> FastAPI:
    """创建控制面 API。身份取自请求头 X-Tenant、X-Role（gate 的简化鉴权；真实系统用 L5.4 的认证）。

    - 所有接口：缺少 X-Tenant 返回 401；X-Role 缺省按 "member"。
    - POST /tasks：请求体 {"payload": {...}}；必须带 Idempotency-Key 头，缺失返回 400；
      新任务用 store.create 创建、queue.put(task_id) 入队，返回 202 和 {"task_id"}；
      同一租户的相同 key 返回同一个 task_id，不重复创建、不重复入队；不同租户的相同 key 是不同任务。
    - GET /tasks/{id}：从 store 读状态，返回 {"task_id", "status", "cancel_requested"}；
      任务不存在或属于其他租户都返回 404（不泄露其他租户的任务是否存在）。
    - POST /tasks/{id}/cancel：对本租户的任务调用 store.request_cancel，返回同样结构的当前状态；其他租户 404。
    - POST /tasks/{id}/approval：请求体 {"stage": str, "decision": "approve" 或 "reject"}；
      只有 X-Role == approver_role 才允许，否则 403（先检查角色，再查任务）；decision 取值非法返回 422；
      成功后用 store.record_approval 记录（approve 为 True），把 task_id 重新入队让 worker 继续，返回同样结构的当前状态；
      任务不存在或属于其他租户返回 404。
    """
    raise NotImplementedError("实现 create_app")


def sign_payload(body: bytes, secret: bytes) -> str:
    """HMAC-SHA256 十六进制摘要（小写）。接收方用同一个 secret 重算并比较，证明请求来自你、内容没被改。"""
    raise NotImplementedError("实现签名")


def send_webhook(task: dict, url: str, secret: bytes, http_post: Callable[[str, bytes, dict], int],
                 delivered: set[str], *, max_attempts: int = 3) -> bool:
    """把任务结果回调给调用方。

    - 请求体 body = json.dumps(task, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")；
    - 请求头带 X-Signature = sign_payload(body, secret)；
    - 通过 http_post(url, body, headers) -> HTTP 状态码 发送（由调用方注入，gate 不联网）；
    - 状态码 2xx 视为成功：把 task["task_id"] 加入 delivered，返回 True；
    - 5xx 或 http_post 抛 ConnectionError 时重试，最多调用 max_attempts 次，仍失败返回 False；
    - 4xx 不重试（请求本身有问题，重试没用），直接返回 False；
    - 同一 task_id 已在 delivered 中：不再发送，直接返回 True（已经投递过了）；
    - max_attempts < 1 抛 ValueError。
    本函数不做退避等待；真实系统要加退避与抖动（见 5.2）。
    """
    raise NotImplementedError("实现 webhook 投递")
