"""0.4 Python 工程底座 · 离线自动化 Gate 检查。

总计 12 项断言检查，覆盖：
- Pydantic 模型校验与错误脱敏（1-4）
- 带指数退避与假时钟注入的异步重试（5-7）
- 基于信号量的有序受限并发调度（8-9）
- 基于 httpx.MockTransport 的离线网络异常封装（10-12）

运行方式：
    python gate_check.py
    或传入具体实现模块路径：python gate_check.py /path/to/impl.py
退出码：通过为 0，失败为 1。
"""

from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from typing import Any

import httpx

# 确定加载模块
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

target_module: Any = None
if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
    target_path = Path(sys.argv[1]).resolve()
    loader = importlib.machinery.SourceFileLoader("target_impl", str(target_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec and spec.loader:
        target_module = importlib.util.module_from_spec(spec)
        sys.modules[loader.name] = target_module
        spec.loader.exec_module(target_module)
else:
    try:
        import starter as target_module  # type: ignore
    except ImportError:
        target_module = None


def test_1_provider_invalid(mod: Any) -> None:
    env = {
        "LLM_PROVIDER": "foo",
        "MODEL": "deepseek-flash",
        "TIMEOUT_S": "30",
        "MAX_RETRIES": "2",
    }
    try:
        mod.load_settings(env)
    except mod.SettingsError as exc:
        assert "provider" in str(exc).lower(), f"异常信息中未提及 provider 字段: {exc}"
        return
    raise AssertionError("传入非法 provider 应抛出 SettingsError")


def test_2_model_blank(mod: Any) -> None:
    env = {
        "LLM_PROVIDER": "deepseek",
        "MODEL": "   ",
        "TIMEOUT_S": "30",
        "MAX_RETRIES": "2",
    }
    try:
        mod.load_settings(env)
    except mod.SettingsError as exc:
        assert "model" in str(exc).lower(), f"异常信息中未提及 model 字段: {exc}"
        return
    raise AssertionError("MODEL 为空白时应抛出 SettingsError")


def test_3_timeout_range(mod: Any) -> None:
    for invalid_timeout in ("0", "-1", "121", "200"):
        env = {
            "LLM_PROVIDER": "deepseek",
            "MODEL": "deepseek-flash",
            "TIMEOUT_S": invalid_timeout,
            "MAX_RETRIES": "2",
        }
        try:
            mod.load_settings(env)
        except mod.SettingsError:
            continue
        raise AssertionError(f"TIMEOUT_S={invalid_timeout} 超出 (0, 120] 范围应抛出 SettingsError")


def test_4_error_message_no_secrets(mod: Any) -> None:
    secret_value = "sk-super-secret-password-xyz123"
    env = {
        "LLM_PROVIDER": "invalid_provider",
        "MODEL": "deepseek-flash",
        "TIMEOUT_S": "30",
        "MAX_RETRIES": "2",
        "OPENAI_API_KEY": secret_value,
        "DEEPSEEK_API_KEY": secret_value,
    }
    try:
        mod.load_settings(env)
    except mod.SettingsError as exc:
        err_msg = str(exc)
        assert secret_value not in err_msg, f"SettingsError 消息中泄露了敏感密钥内容: {err_msg}"
        return
    raise AssertionError("应抛出 SettingsError")


def test_5_retry_success_with_backoff(mod: Any) -> None:
    calls = 0
    sleep_records: list[float] = []

    async def mock_fn() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError(f"fail {calls}")
        return "success"

    async def fake_sleep(duration: float) -> None:
        sleep_records.append(duration)

    async def runner() -> None:
        res = await mod.retry_async(
            mock_fn,
            attempts=4,
            base_delay=1.5,
            sleep=fake_sleep,
            retry_on=(RuntimeError,),
        )
        assert res == "success", f"期望返回 success，实际: {res}"
        assert calls == 3, f"期望调用 3 次，实际: {calls}"
        # 第 0 次失败等 1.5 * 2^0 = 1.5；第 1 次失败等 1.5 * 2^1 = 3.0
        assert sleep_records == [1.5, 3.0], f"sleep 记录不符: {sleep_records}"

    asyncio.run(runner())


def test_6_retry_unhandled_exception(mod: Any) -> None:
    sleep_records: list[float] = []

    async def mock_fn() -> None:
        raise KeyError("fatal config missing")

    async def fake_sleep(duration: float) -> None:
        sleep_records.append(duration)

    async def runner() -> None:
        try:
            await mod.retry_async(
                mock_fn,
                attempts=3,
                base_delay=1.0,
                sleep=fake_sleep,
                retry_on=(RuntimeError,),
            )
        except KeyError:
            assert len(sleep_records) == 0, f"不可重试异常不应触发 sleep，实际: {sleep_records}"
            return
        raise AssertionError("未在 retry_on 中的异常应立即抛出")

    asyncio.run(runner())


def test_7_retry_exhausted(mod: Any) -> None:
    calls = 0

    async def mock_fn() -> None:
        nonlocal calls
        calls += 1
        raise ValueError(f"call_{calls}")

    async def fake_sleep(duration: float) -> None:
        pass

    async def runner() -> None:
        try:
            await mod.retry_async(
                mock_fn,
                attempts=3,
                base_delay=0.1,
                sleep=fake_sleep,
                retry_on=(ValueError,),
            )
        except ValueError as exc:
            assert str(exc) == "call_3", f"应抛出最后一次调用的异常，实际: {exc}"
            assert calls == 3
            return
        raise AssertionError("重试次数用尽应抛出最后一次的异常")

    asyncio.run(runner())


def test_8_gather_limited_concurrency_and_order(mod: Any) -> None:
    concurrent_count = 0
    max_concurrent_seen = 0

    def make_factory(idx: int) -> Any:
        async def task() -> int:
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            if concurrent_count > max_concurrent_seen:
                max_concurrent_seen = concurrent_count
            # 让出事件循环
            await asyncio.sleep(0.001)
            concurrent_count -= 1
            return idx

        return task

    factories = [make_factory(i) for i in range(10)]

    async def runner() -> None:
        results = await mod.gather_limited(factories, limit=3)
        assert results == list(range(10)), f"结果顺序与输入不一致: {results}"
        assert max_concurrent_seen <= 3, f"并发数超限: 最大看到 {max_concurrent_seen}"
        assert max_concurrent_seen > 1, f"应当并发运行，实际最大并发仅为: {max_concurrent_seen}"

    asyncio.run(runner())


def test_9_gather_limited_invalid_limit(mod: Any) -> None:
    async def dummy() -> None:
        pass

    async def runner() -> None:
        for invalid_limit in (0, -1):
            try:
                await mod.gather_limited([dummy], limit=invalid_limit)
            except ValueError:
                continue
            raise AssertionError(f"limit={invalid_limit} 应抛出 ValueError")

    asyncio.run(runner())


def test_10_fetch_json_http_status_error(mod: Any) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server error"})

    transport = httpx.MockTransport(handler)

    async def runner() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            try:
                await mod.fetch_json(client, "http://offline.local/api", timeout_s=5.0)
            except mod.HttpError as exc:
                assert exc.kind == "status:500", f"期望 kind 为 'status:500'，实际: {exc.kind}"
                return
        raise AssertionError("HTTP 500 应抛出 HttpError('status:500')")

    asyncio.run(runner())


def test_11_fetch_json_invalid_json(mod: Any) -> None:
    # 场景 A: 返回纯文本 HTML 不是 JSON
    async def text_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>502 Bad Gateway</html>")

    # 场景 B: 返回 JSON 数组而不是对象 dict
    async def list_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[1, 2, 3])

    async def runner() -> None:
        for handler in (text_handler, list_handler):
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport) as client:
                try:
                    await mod.fetch_json(client, "http://offline.local/api", timeout_s=5.0)
                except mod.HttpError as exc:
                    assert exc.kind == "invalid_json", f"期望 kind 为 'invalid_json'，实际: {exc.kind}"
                    continue
                raise AssertionError("非 dict JSON 响应应抛出 HttpError('invalid_json')")

    asyncio.run(runner())


def test_12_fetch_json_timeout(mod: Any) -> None:
    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timeout", request=request)

    transport = httpx.MockTransport(timeout_handler)

    async def runner() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            try:
                await mod.fetch_json(client, "http://offline.local/api", timeout_s=1.0)
            except mod.HttpError as exc:
                assert exc.kind == "timeout", f"期望 kind 为 'timeout'，实际: {exc.kind}"
                return
        raise AssertionError("请求超时应抛出 HttpError('timeout')")

    asyncio.run(runner())


ALL_CHECKS = [
    ("1. 非法 Provider 报错并指出字段", test_1_provider_invalid),
    ("2. 空白 Model 报错并指出字段", test_2_model_blank),
    ("3. TIMEOUT_S 超出 (0, 120] 范围报错", test_3_timeout_range),
    ("4. SettingsError 脱敏（不含敏感密钥内容）", test_4_error_message_no_secrets),
    ("5. retry_async 指数退避与假时钟注入", test_5_retry_success_with_backoff),
    ("6. retry_async 不可重试异常立即抛出且不 sleep", test_6_retry_unhandled_exception),
    ("7. retry_async 次数用尽抛出最后异常", test_7_retry_exhausted),
    ("8. gather_limited 并发限流与结果保序", test_8_gather_limited_concurrency_and_order),
    ("9. gather_limited limit<=0 抛 ValueError", test_9_gather_limited_invalid_limit),
    ("10. fetch_json HTTP 非 2xx 封装 HttpError('status:<code>')", test_10_fetch_json_http_status_error),
    ("11. fetch_json 非字典 JSON 响应封装 HttpError('invalid_json')", test_11_fetch_json_invalid_json),
    ("12. fetch_json 超时封装 HttpError('timeout')", test_12_fetch_json_timeout),
]


def run_checks(mod: Any) -> bool:
    print(f"=== 开始执行 0.4 Gate 检查（共 {len(ALL_CHECKS)} 项，目标模块: {getattr(mod, '__name__', str(mod))}）===")
    all_passed = True
    for title, check_fn in ALL_CHECKS:
        try:
            check_fn(mod)
            print(f"  [PASS] {title}")
        except Exception as exc:
            print(f"  [FAIL] {title} -> {exc}", file=sys.stderr)
            all_passed = False
    return all_passed


def main() -> int:
    if target_module is None:
        print("[FAIL] 无法加载待测试模块", file=sys.stderr)
        return 1

    passed = run_checks(target_module)
    if passed:
        print("[PASS] 0.4 全部 12 项工程底座断言通过！")
        return 0
    else:
        print("[FAIL] 0.4 存在未通过检查项，请检查实现。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
