"""L5.7 控制面与执行面 gate：FastAPI TestClient + 内存 store / queue，不联网、不起线程。"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib.util
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

HERE = Path(__file__).resolve().parent


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    if spec is None or spec.loader is None:
        raise ValueError("无法加载候选模块")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate"] = module
    spec.loader.exec_module(module)
    return module


def load_helpers():
    """MemoryStore / MemoryQueue 是 starter 里给出的固定代码，gate 始终用 starter 的版本。"""
    spec = importlib.util.spec_from_file_location("starter_helpers", HERE / "starter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MemoryStore, module.MemoryQueue


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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
        report = {"gate": "L5.7-control-execution-plane", "module": str(path), "passed": passed,
                  "total": len(self.rows), "ok": passed == len(self.rows), "checks": self.rows}
        (HERE / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    path = Path(parser.parse_args().module).resolve()
    core = load_module(path)
    MemoryStore, MemoryQueue = load_helpers()
    gate = Gate()

    A = {"X-Tenant": "tenant-a"}
    B = {"X-Tenant": "tenant-b"}

    def fresh():
        store, queue = MemoryStore(), MemoryQueue()
        return TestClient(core.create_app(store, queue)), store, queue

    def submit(client, headers=A, key="k1"):
        return client.post("/tasks", json={"payload": {"topic": "x"}}, headers={**headers, "Idempotency-Key": key})

    def test_submit():
        client, store, queue = fresh()
        response = submit(client)
        expect(response.status_code == 202, f"提交应返回 202，实际 {response.status_code}")
        task_id = response.json().get("task_id")
        expect(task_id in store.tasks, "task_id 应对应 store 里的任务")
        expect(queue.items == [task_id], f"新任务应入队一次，实际 {queue.items}")

    def test_idempotent():
        client, store, queue = fresh()
        first, second = submit(client).json(), submit(client).json()
        expect(first == second, f"相同 key 应返回同一个 task_id：{first} vs {second}")
        expect(len(store.tasks) == 1 and len(queue.items) == 1, "相同 key 不得重复创建或重复入队")
        other_tenant = submit(client, B).json()
        expect(other_tenant["task_id"] != first["task_id"], "不同租户的相同 key 应是不同任务")

    def test_missing_key():
        client, store, _ = fresh()
        response = client.post("/tasks", json={"payload": {}}, headers=A)
        expect(response.status_code == 400, f"缺少 Idempotency-Key 应返回 400，实际 {response.status_code}")
        expect(not store.tasks, "缺少幂等键时不得创建任务")

    def test_missing_tenant():
        client, _, _ = fresh()
        response = client.post("/tasks", json={"payload": {}}, headers={"Idempotency-Key": "k"})
        expect(response.status_code == 401, f"缺少 X-Tenant 应返回 401，实际 {response.status_code}")

    def test_cross_tenant():
        client, _, _ = fresh()
        task_id = submit(client).json()["task_id"]
        expect(client.get(f"/tasks/{task_id}", headers=B).status_code == 404, "其他租户查询应 404")
        expect(client.get("/tasks/missing", headers=A).status_code == 404, "不存在的任务应 404")
        expect(client.post(f"/tasks/{task_id}/cancel", headers=B).status_code == 404, "其他租户取消应 404")

    def test_status_from_store():
        client, store, _ = fresh()
        task_id = submit(client).json()["task_id"]
        expect(client.get(f"/tasks/{task_id}", headers=A).json()["status"] == "queued", "初始状态应为 queued")
        store.tasks[task_id]["status"] = "waiting_approval"  # 模拟执行面改了状态
        view = client.get(f"/tasks/{task_id}", headers=A).json()
        expect(view == {"task_id": task_id, "status": "waiting_approval", "cancel_requested": False}, f"状态应取自 store：{view}")

    def test_cancel():
        client, store, _ = fresh()
        task_id = submit(client).json()["task_id"]
        response = client.post(f"/tasks/{task_id}/cancel", headers=A)
        expect(response.status_code == 200 and response.json()["cancel_requested"] is True, f"取消应返回最新状态：{response.text}")
        expect(store.tasks[task_id]["cancel_requested"] is True, "取消标志应写入 store")

    def test_approval_forbidden():
        client, store, queue = fresh()
        task_id = submit(client).json()["task_id"]
        before = len(queue.items)
        body = {"stage": "publish", "decision": "approve"}
        for headers in (A, {**A, "X-Role": "member"}):
            response = client.post(f"/tasks/{task_id}/approval", json=body, headers=headers)
            expect(response.status_code == 403, f"非审批角色应返回 403，实际 {response.status_code}")
        expect(not store.tasks[task_id]["approvals"] and len(queue.items) == before, "被拒绝的审批不得写入或入队")

    def test_approval_ok():
        client, store, queue = fresh()
        task_id = submit(client).json()["task_id"]
        headers = {**A, "X-Role": "approver"}
        response = client.post(f"/tasks/{task_id}/approval", json={"stage": "publish", "decision": "approve"}, headers=headers)
        expect(response.status_code == 200, f"审批应返回 200，实际 {response.status_code}：{response.text}")
        expect(store.tasks[task_id]["approvals"] == {"publish": True}, "批准应记录为 True")
        expect(queue.items.count(task_id) == 2, "审批后应重新入队让 worker 继续")
        client.post(f"/tasks/{task_id}/approval", json={"stage": "publish", "decision": "reject"}, headers=headers)
        expect(store.tasks[task_id]["approvals"] == {"publish": False}, "拒绝应记录为 False")
        bad = client.post(f"/tasks/{task_id}/approval", json={"stage": "publish", "decision": "maybe"}, headers=headers)
        expect(bad.status_code == 422, f"decision 非法应返回 422，实际 {bad.status_code}")
        other = client.post(f"/tasks/{task_id}/approval", json={"stage": "publish", "decision": "approve"}, headers={**B, "X-Role": "approver"})
        expect(other.status_code == 404, "其他租户的审批人不能审批本租户的任务")

    def test_signature():
        body = '{"task_id":"t1"}'.encode()
        expected = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        expect(core.sign_payload(body, b"secret") == expected, "应为 HMAC-SHA256 十六进制摘要")
        expect(core.sign_payload(body, b"other") != expected, "不同密钥签名应不同")
        expect(core.sign_payload(b"{}", b"secret") != expected, "不同内容签名应不同")

    task = {"task_id": "t1", "status": "succeeded"}

    def recorder(statuses):
        calls = []

        def post(url, body, headers):
            calls.append({"url": url, "body": body, "headers": headers})
            result = statuses[min(len(calls) - 1, len(statuses) - 1)]
            if isinstance(result, Exception):
                raise result
            return result

        return post, calls

    def test_webhook_ok_and_headers():
        post, calls = recorder([200])
        delivered: set[str] = set()
        expect(core.send_webhook(task, "https://x/hook", b"s", post, delivered) is True, "2xx 应返回 True")
        expect(delivered == {"t1"}, "成功后应记入 delivered")
        call = calls[0]
        expect(call["url"] == "https://x/hook" and len(calls) == 1, "应只发送一次到指定 URL")
        expect(call["headers"].get("X-Signature") == core.sign_payload(call["body"], b"s"), "X-Signature 应是对请求体的签名")
        expect(json.loads(call["body"]) == task, "请求体应是任务的 JSON")

    def test_webhook_retry_5xx():
        post, calls = recorder([503, 502, 200])
        expect(core.send_webhook(task, "u", b"s", post, set(), max_attempts=3) is True, "第 3 次成功应返回 True")
        expect(len(calls) == 3, f"应重试到成功，调用 {len(calls)} 次")
        post, calls = recorder([500])
        expect(core.send_webhook(task, "u", b"s", post, set(), max_attempts=3) is False, "一直 5xx 应返回 False")
        expect(len(calls) == 3, f"重试次数应有上限 3，实际 {len(calls)}")
        post, calls = recorder([ConnectionError("down"), 200])
        expect(core.send_webhook(task, "u", b"s", post, set()) is True and len(calls) == 2, "连接错误应重试")

    def test_webhook_no_retry_4xx():
        post, calls = recorder([400, 200])
        delivered: set[str] = set()
        expect(core.send_webhook(task, "u", b"s", post, delivered) is False, "4xx 应返回 False")
        expect(len(calls) == 1 and not delivered, "4xx 不得重试，也不得记入 delivered")

    def test_webhook_dedup():
        post, calls = recorder([200])
        delivered: set[str] = set()
        core.send_webhook(task, "u", b"s", post, delivered)
        expect(core.send_webhook(task, "u", b"s", post, delivered) is True, "已投递过应返回 True")
        expect(len(calls) == 1, f"同一 task_id 只能投递一次，实际发送 {len(calls)} 次")
        try:
            core.send_webhook(task, "u", b"s", post, set(), max_attempts=0)
        except ValueError:
            return
        raise AssertionError("max_attempts < 1 应抛 ValueError")

    gate.check("01 提交返回 202 与 task_id 并入队", test_submit)
    gate.check("02 提交幂等且按租户隔离", test_idempotent)
    gate.check("03 缺少幂等键返回 400", test_missing_key)
    gate.check("04 缺少租户头返回 401", test_missing_tenant)
    gate.check("05 跨租户访问返回 404", test_cross_tenant)
    gate.check("06 状态取自 store", test_status_from_store)
    gate.check("07 取消写入 store", test_cancel)
    gate.check("08 非审批角色返回 403", test_approval_forbidden)
    gate.check("09 审批记录、重新入队与参数校验", test_approval_ok)
    gate.check("10 签名可验证", test_signature)
    gate.check("11 webhook 成功与请求头", test_webhook_ok_and_headers)
    gate.check("12 5xx 与连接错误重试且有上限", test_webhook_retry_5xx)
    gate.check("13 4xx 不重试", test_webhook_no_retry_4xx)
    gate.check("14 重复投递被去重", test_webhook_dedup)
    return gate.report(path)


if __name__ == "__main__":
    raise SystemExit(main())
