# tests/test_0_1.py
import asyncio
import time
from decimal import Decimal
import httpx
import pytest
from invoice_models import RawInvoiceInput
from invoice_batch import (
    process_invoices_broken_async,
    process_invoices_async,
)


def test_negative_amount_is_rejected():
    """验证负数金额直接在本地被拦截"""
    dirty = {
        "invoice_id": "INV-001",
        "total_amount": Decimal("-10.00"),
        "items": [{"name": "文具", "amount": Decimal("-10.00")}],
    }
    with pytest.raises(Exception) as exc_info:
        RawInvoiceInput.model_validate(dirty)
    assert "Input should be greater than 0" in str(exc_info.value)


def test_amount_mismatch_is_rejected():
    """验证明细加总与总金额不一致时被拦截"""
    dirty = {
        "invoice_id": "INV-002",
        "total_amount": Decimal("100.00"),
        "items": [
            {"name": "打车费", "amount": Decimal("40.00")},
            {"name": "餐费", "amount": Decimal("50.00")},
        ],
    }
    with pytest.raises(ValueError) as exc_info:
        RawInvoiceInput.model_validate(dirty)
    assert "不一致" in str(exc_info.value)


def test_blocked_code_causes_serialization():
    """验证包含同步阻塞的 async 代码总耗时线性累加"""
    records = [
        {
            "invoice_id": f"INV-SEQ-{i}",
            "total_amount": Decimal("10.00"),
            "items": [{"name": "条目", "amount": Decimal("10.00")}],
        }
        for i in range(4)
    ]

    t0 = time.perf_counter()
    # 单项阻塞 0.05s，4 项串行总耗时应 >= 0.20s
    res = asyncio.run(process_invoices_broken_async(records, delay_per_item=0.05))
    elapsed = time.perf_counter() - t0

    assert len(res["succeeded"]) == 4
    assert elapsed >= 0.19, f"未能复现串行阻塞，耗时: {elapsed}s"


def test_controlled_async_limits_concurrency_and_time():
    """验证非阻塞调用在 Semaphore=2 的约束下，4 个任务分两批完成"""
    records = [
        {
            "invoice_id": f"INV-ASYNC-{i}",
            "total_amount": Decimal("10.00"),
            "items": [{"name": "条目", "amount": Decimal("10.00")}],
        }
        for i in range(4)
    ]

    async def _runner():
        async with httpx.AsyncClient() as client:
            t0 = time.perf_counter()
            # 单项延迟 0.05s，并发度为 2，4 个任务分两批完成，耗时在 0.10s - 0.16s 之间，显著小于串行的 0.20s
            res = await process_invoices_async(records, client=client, max_concurrency=2, delay_per_item=0.05)
            elapsed = time.perf_counter() - t0
            return res, elapsed

    res, elapsed = asyncio.run(_runner())
    assert len(res["succeeded"]) == 4
    assert elapsed < 0.18, f"受控异步并发超时，耗时: {elapsed}s"


def test_timeout_is_classified_correctly():
    """验证当外部服务延迟超过限制时，任务被准确标记为 OCR_TIMEOUT 而不是服务崩溃"""
    records = [
        {
            "invoice_id": "INV-TIMEOUT-01",
            "total_amount": Decimal("10.00"),
            "items": [{"name": "条目", "amount": Decimal("10.00")}],
        }
    ]

    async def _runner():
        async with httpx.AsyncClient() as client:
            # 单请求超时限制设为 0.02s，而外部延迟为 0.08s，必然超时
            return await process_invoices_async(
                records, client=client, max_concurrency=1, request_timeout=0.02, delay_per_item=0.08
            )

    res = asyncio.run(_runner())
    assert len(res["succeeded"]) == 0
    assert len(res["failed"]) == 1
    assert res["failed"][0]["error_type"] == "OCR_TIMEOUT"
