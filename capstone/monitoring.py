"""不保存明文问题的请求指标与 trace 关联。"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import closing
from datetime import UTC, datetime, timedelta

from . import config as C

_initialized_dbs: set[str] = set()
_init_lock = threading.Lock()


def _ensure_schema(connection: sqlite3.Connection, db_path: str) -> None:
    if db_path in _initialized_dbs:
        return
    with _init_lock:
        if db_path in _initialized_dbs:
            return
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS request_metrics(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                request_id TEXT NOT NULL,
                tenant TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                is_error INTEGER NOT NULL,
                tokens INTEGER NOT NULL DEFAULT 0,
                cost REAL NOT NULL DEFAULT 0,
                model TEXT NOT NULL DEFAULT '',
                cache_hit INTEGER NOT NULL DEFAULT 0,
                question_fingerprint TEXT NOT NULL DEFAULT ''
            )"""
        )
        _initialized_dbs.add(db_path)


def _connect() -> sqlite3.Connection:
    C.ensure_runtime_directories()
    db_path = str(C.METRICS_DB_PATH)
    if db_path in _initialized_dbs and not os.path.exists(db_path):
        with _init_lock:
            _initialized_dbs.discard(db_path)
    connection = sqlite3.connect(db_path, timeout=5)
    _ensure_schema(connection, db_path)
    return connection


def record(
    tenant: str,
    latency_ms: float,
    is_error: bool,
    *,
    request_id: str,
    tokens: int = 0,
    cost: float = 0.0,
    model: str = "",
    cache_hit: bool = False,
    question_fingerprint: str = "",
) -> None:
    with closing(_connect()) as connection:
        with connection:
            connection.execute(
                """INSERT INTO request_metrics(
                    ts, request_id, tenant, latency_ms, is_error, tokens, cost,
                    model, cache_hit, question_fingerprint
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    datetime.now(UTC).isoformat(timespec="seconds"),
                    request_id,
                    tenant,
                    latency_ms,
                    int(is_error),
                    tokens,
                    cost,
                    model,
                    int(cache_hit),
                    question_fingerprint,
                ),
            )


def _percentile(values: list[float], percentile: int) -> float:
    """线性插值分位数（与 numpy 默认一致），保留 1 位小数；没有样本时返回 0.0。小样本下比 nearest-rank 略乐观。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return round(
        ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower),
        1,
    )


def health(
    window_minutes: int = 60,
    *,
    tenant: str | None = None,
) -> dict[str, int | float]:
    if window_minutes <= 0:
        raise ValueError("window_minutes 必须大于 0")
    since = (
        datetime.now(UTC) - timedelta(minutes=window_minutes)
    ).isoformat(timespec="seconds")
    sql = (
        "SELECT latency_ms,is_error,tokens,cost,cache_hit "
        "FROM request_metrics WHERE ts>=?"
    )
    parameters: list[object] = [since]
    if tenant is not None:
        sql += " AND tenant=?"
        parameters.append(tenant)
    with closing(_connect()) as connection:
        rows = connection.execute(sql, parameters).fetchall()
    if not rows:
        return {"样本数": 0}
    latency = [float(row[0]) for row in rows]
    count = len(rows)
    return {
        "样本数": count,
        "p50延迟ms": _percentile(latency, 50),
        "p95延迟ms": _percentile(latency, 95),
        "p99延迟ms": _percentile(latency, 99),
        "错误率": round(sum(row[1] for row in rows) / count, 4),
        "总token": sum(row[2] for row in rows),
        "总成本": round(sum(row[3] for row in rows), 4),
        "缓存命中率": round(sum(row[4] for row in rows) / count, 4),
    }


def daily_cost_trend(
    days: int = 7,
    *,
    tenant: str | None = None,
) -> list[tuple[str, float, int]]:
    """返回最近若干个有流量的 UTC 自然日成本，不泄露请求正文。"""
    if days <= 0:
        raise ValueError("days 必须大于 0")
    sql = (
        "SELECT substr(ts,1,10) AS day, ROUND(SUM(cost),6), COUNT(*) "
        "FROM request_metrics"
    )
    parameters: list[object] = []
    if tenant is not None:
        sql += " WHERE tenant=?"
        parameters.append(tenant)
    sql += " GROUP BY day ORDER BY day DESC LIMIT ?"
    parameters.append(days)
    with closing(_connect()) as connection:
        rows = connection.execute(sql, parameters).fetchall()
    return [(str(day), float(cost), int(count)) for day, cost, count in rows]
