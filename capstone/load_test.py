"""对当前企业 API 做可重复的 Locust 压测和 SLO 判定。

fake 模式复用 ``capstone.api_enterprise`` 的认证、中间件、缓存和指标写入，
只替换知识库/模型边界；real 模式必须从环境变量读取现成 Bearer token。
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import re
import secrets
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
_DURATION = re.compile(r"[1-9]\d*[smh]")
_UNDER_LOCUST = "locust" in sys.modules

SLO = {
    "p95_ms": float(os.getenv("SLO_P95_MS", "3000")),
    "error_rate_pct": float(os.getenv("SLO_ERROR_PCT", "1.0")),
    "min_rps": float(os.getenv("SLO_MIN_RPS", "3")),
}


if _UNDER_LOCUST:
    from locust import HttpUser, between, events, task

    _TOKEN = os.getenv("LOADTEST_BEARER_TOKEN", "").strip()
    if not _TOKEN:
        raise RuntimeError("Locust 缺少 LOADTEST_BEARER_TOKEN")
    _CACHE_BUST = (
        os.getenv("LOADTEST_CACHE_BUST", "false").strip().lower() == "true"
    )
    _QUESTIONS = (
        "RAG 为什么能减少幻觉？",
        "向量检索和关键词检索有什么区别？",
        "怎么评估知识库问答系统？",
        "文档更新后索引怎么同步？",
    )

    class ChatUser(HttpUser):
        """按 10:1:1:1 混合访问聊天、指标、存活和就绪端点。"""

        wait_time = between(
            float(os.getenv("LOADTEST_WAIT_MIN", "0.1")),
            float(os.getenv("LOADTEST_WAIT_MAX", "0.5")),
        )
        _users = itertools.count()

        def on_start(self) -> None:
            self.user_number = next(self._users)
            self.request_number = 0
            self.headers = {"Authorization": f"Bearer {_TOKEN}"}

        @task(10)
        def chat(self) -> None:
            question = random.choice(_QUESTIONS)
            if _CACHE_BUST:
                question += (
                    f" [loadtest-{self.user_number}-{self.request_number}]"
                )
            self.request_number += 1
            with self.client.post(
                "/v1/chat",
                headers=self.headers,
                json={"question": question},
                name="/v1/chat",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    detail = response.text.replace("\n", " ")[:240]
                    response.failure(f"HTTP {response.status_code}: {detail}")
                    return
                try:
                    body = response.json()
                except ValueError:
                    response.failure("响应不是 JSON")
                    return
                required = {"answer", "tenant", "model", "cache_hit", "request_id"}
                if not required.issubset(body):
                    response.failure("响应 schema 不完整")
                    return
                response.success()

        @task(1)
        def metrics(self) -> None:
            self.client.get(
                "/v1/metrics",
                headers=self.headers,
                name="/v1/metrics",
            )

        @task(1)
        def health(self) -> None:
            self.client.get("/health", name="/health")

        @task(1)
        def ready(self) -> None:
            self.client.get("/ready", name="/ready")

    @events.test_stop.add_listener
    def write_final_stats(environment, **_kwargs) -> None:
        """直接从 Locust 内存统计写最终快照，避免周期 CSV 落后于停止时刻。"""
        output = os.getenv("LOADTEST_FINAL_STATS_FILE", "").strip()
        if not output:
            return
        total = environment.stats.total
        endpoints = {}
        for entry in environment.stats.entries.values():
            endpoints[entry.name] = {
                "requests": entry.num_requests,
                "failures": entry.num_failures,
                "p95_ms": round(entry.get_response_time_percentile(0.95) or 0),
            }
        requests = total.num_requests
        failures = total.num_failures
        payload = {
            "requests": requests,
            "failures": failures,
            "error_rate_pct": round(failures / requests * 100, 3)
            if requests
            else 100.0,
            "rps": round(total.total_rps, 3),
            "p95_ms": round(total.get_response_time_percentile(0.95) or 0),
            "max_ms": round(total.max_response_time or 0),
            "endpoints": endpoints,
        }
        Path(output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def make_fake_app():
    """Uvicorn factory：保留真实 HTTP 路径，只替换昂贵的知识库边界。"""
    from capstone.api_enterprise import app, registry
    from capstone.knowledge_base import AnswerResult

    delay = int(os.getenv("FAKE_UPSTREAM_MS", "200")) / 1000
    if delay < 0:
        raise ValueError("FAKE_UPSTREAM_MS 不能小于 0")

    class FakeKnowledgeBase:
        version = "loadtest-v1"

        def answer_with_usage(self, question, **_kwargs):
            time.sleep(delay)
            return AnswerResult(
                f"压测固定回答：{question[:40]}【来源：loadtest.md】",
                input_tokens=100,
                output_tokens=30,
            )

    fake = FakeKnowledgeBase()
    registry.get = lambda _tenant_id: fake  # type: ignore[method-assign]
    return app


def _client(timeout: float = 5):
    import httpx

    return httpx.Client(trust_env=False, timeout=timeout)


def _get(
    url: str,
    *,
    token: str | None = None,
    timeout: float = 5,
):
    headers = {"Authorization": f"Bearer {token}"} if token else None
    with _client(timeout) as client:
        return client.get(url, headers=headers)


def _server_metrics(host: str, token: str) -> dict[str, int | float]:
    response = _get(f"{host}/v1/metrics", token=token)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("/v1/metrics 未返回对象")
    return payload


def _read_locust_result(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Locust 未生成最终统计 {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "requests" not in payload:
        raise RuntimeError("Locust 最终统计格式无效")
    return payload


def _metric_cost(metrics: dict[str, int | float]) -> float:
    return float(metrics.get("总成本", 0))


def run(
    host: str,
    *,
    users: int,
    spawn_rate: int,
    duration: str,
    bearer_token: str,
    cache_bust: bool,
) -> dict[str, object]:
    REPORTS.mkdir(exist_ok=True)
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    final_stats_path = REPORTS / f"loadtest-{run_id}-final.json"
    metrics_before = _server_metrics(host, bearer_token)
    command = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(Path(__file__).resolve()),
        "--host",
        host,
        "--headless",
        "-u",
        str(users),
        "-r",
        str(spawn_rate),
        "-t",
        duration,
        "--only-summary",
        "--exit-code-on-error",
        "0",
    ]
    environment = {
        key: value
        for key, value in os.environ.items()
        if "proxy" not in key.lower()
    }
    environment.update(
        {
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
            "LOADTEST_BEARER_TOKEN": bearer_token,
            "LOADTEST_CACHE_BUST": str(cache_bust).lower(),
            "LOADTEST_FINAL_STATS_FILE": str(final_stats_path),
        }
    )
    print(
        f"运行 Locust：users={users}, spawn_rate={spawn_rate}, "
        f"duration={duration}, host={host}"
    )
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    metrics_after = _server_metrics(host, bearer_token)
    client = _read_locust_result(final_stats_path)
    endpoints = client["endpoints"]
    assert isinstance(endpoints, dict)
    chat = endpoints.get("/v1/chat", {})
    client_chat_p95 = int(chat.get("p95_ms", 0)) if isinstance(chat, dict) else 0
    server_p95 = float(metrics_after.get("p95延迟ms", 0))
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": host,
        "users": users,
        "spawn_rate": spawn_rate,
        "duration": duration,
        "cache_bust": cache_bust,
        "client": client,
        "server_metrics_after": metrics_after,
        "client_chat_p95_ms": client_chat_p95,
        "server_chat_p95_ms": server_p95,
        "transport_queue_estimate_ms": max(0, round(client_chat_p95 - server_p95)),
        "estimated_cost_delta": round(
            _metric_cost(metrics_after) - _metric_cost(metrics_before),
            6,
        ),
        "measurement_note": (
            "客户端与服务端 p95 是两个分布的分位数，相减只可作为网络/排队"
            "开销线索，不是逐请求的精确排队时长。真实模式还可能混入同租户其他流量。"
        ),
    }


def judge(
    report: dict[str, object],
    *,
    slo: dict[str, float] | None = None,
) -> tuple[bool, list[str]]:
    active_slo = slo or SLO
    client = report["client"]
    if not isinstance(client, dict):
        raise TypeError("report.client 必须是对象")
    violations = []
    chat_p95 = float(report.get("client_chat_p95_ms", 0))
    error_rate = float(client["error_rate_pct"])
    rps = float(client["rps"])
    if chat_p95 > active_slo["p95_ms"]:
        violations.append(
            f"/v1/chat p95 {chat_p95:g}ms > {active_slo['p95_ms']:g}ms"
        )
    if error_rate > active_slo["error_rate_pct"]:
        violations.append(
            f"错误率 {error_rate:g}% > {active_slo['error_rate_pct']:g}%"
        )
    if rps < active_slo["min_rps"]:
        violations.append(f"吞吐 {rps:g}rps < {active_slo['min_rps']:g}rps")
    return not violations, violations


def _issue_load_token(secret: str, tenant: str) -> str:
    import jwt

    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "loadtest-user",
            "tenant": tenant,
            "roles": ["employee"],
            "dept": "",
            "iss": os.getenv("JWT_ISSUER", "capstone-local"),
            "aud": os.getenv("JWT_AUDIENCE", "capstone-api"),
            "iat": now,
            "exp": now + timedelta(hours=1),
            "jti": secrets.token_urlsafe(16),
        },
        secret,
        algorithm="HS256",
    )


def _validate_args(args: argparse.Namespace) -> None:
    if args.users <= 0 or args.spawn_rate <= 0:
        raise SystemExit("users 和 spawn-rate 必须大于 0")
    if args.upstream_ms < 0:
        raise SystemExit("upstream-ms 不能小于 0")
    if not _DURATION.fullmatch(args.duration):
        raise SystemExit("time 必须是正整数加 s/m/h，例如 30s")
    if not 1 <= args.port <= 65535:
        raise SystemExit("port 必须在 1-65535")
    parsed = urlparse(args.host)
    if not args.fake and (
        parsed.scheme not in {"http", "https"} or not parsed.hostname
    ):
        raise SystemExit("host 必须是有效的 http(s) URL")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--spawn-rate", type=int, default=5)
    parser.add_argument("--time", dest="duration", default="30s")
    parser.add_argument("--fake", action="store_true")
    parser.add_argument("--upstream-ms", type=int, default=200)
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument(
        "--cache-bust",
        action="store_true",
        help="给问题添加唯一后缀，避免缓存掩盖上游容量",
    )
    return parser.parse_args()


def _wait_ready(host: str, process: subprocess.Popen[bytes]) -> None:
    last_error = "尚未探活"
    for _ in range(60):
        if process.poll() is not None:
            raise RuntimeError(f"假服务提前退出，exit={process.returncode}")
        try:
            response = _get(f"{host}/ready", timeout=1)
            if response.status_code == 200:
                return
            last_error = f"HTTP {response.status_code}: {response.text[:120]}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.5)
    raise TimeoutError(f"假服务 30 秒内未就绪：{last_error}")


def _save_report(report: dict[str, object]) -> Path:
    path = REPORTS / f"loadtest_{time.strftime('%Y%m%d_%H%M%S')}.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def main() -> int:
    args = parse_args()
    _validate_args(args)
    server: subprocess.Popen[bytes] | None = None
    temporary_data: tempfile.TemporaryDirectory[str] | None = None
    if args.fake:
        temporary_data = tempfile.TemporaryDirectory(
            prefix="capstone-loadtest-", ignore_cleanup_errors=True
        )
        host = f"http://127.0.0.1:{args.port}"
        secret = secrets.token_urlsafe(48)
        tenant = f"loadtest-{int(time.time())}-{os.getpid()}"
        token = _issue_load_token(secret, tenant)
        environment = os.environ.copy()
        environment.update(
            {
                "APP_ENV": "development",
                "CAPSTONE_DATA_DIR": temporary_data.name,
                "CAPSTONE_ENABLE_DEV_LOGIN": "false",
                "FAKE_UPSTREAM_MS": str(args.upstream_ms),
                "JWT_SECRET": secret,
                "LLM_PROVIDER": "openai_compatible",
                "OPENAI_COMPATIBLE_BASE_URL": "http://127.0.0.1:1/v1",
                "OPENAI_COMPATIBLE_MODEL": "loadtest-model",
                "RATE_LIMIT_PER_MINUTE": "100000",
            }
        )
        creationflags = (
            subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "capstone.load_test:make_fake_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
                "--log-level",
                "warning",
            ],
            cwd=ROOT,
            env=environment,
            creationflags=creationflags,
        )
        try:
            _wait_ready(host, server)
        except Exception:
            server.terminate()
            server.wait(timeout=10)
            temporary_data.cleanup()
            raise
        cache_bust = True
    else:
        host = args.host.rstrip("/")
        token = os.getenv("LOADTEST_BEARER_TOKEN", "").strip()
        if not token:
            raise SystemExit(
                "real 模式缺少 LOADTEST_BEARER_TOKEN；token 只从环境变量读取"
            )
        cache_bust = args.cache_bust

    try:
        report = run(
            host,
            users=args.users,
            spawn_rate=args.spawn_rate,
            duration=args.duration,
            bearer_token=token,
            cache_bust=cache_bust,
        )
        passed, violations = judge(report)
        report["slo"] = SLO
        report["passed"] = passed
        report["violations"] = violations
        path = _save_report(report)
        client = report["client"]
        assert isinstance(client, dict)
        print(
            f"requests={client['requests']}, failures={client['failures']}, "
            f"rps={client['rps']}, chat_p95={report['client_chat_p95_ms']}ms"
        )
        print("SLO: " + ("PASS" if passed else "FAIL"))
        for violation in violations:
            print(f"  - {violation}")
        print(f"报告：{path}")
        return 0 if passed else 1
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        if temporary_data is not None:
            temporary_data.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
