# invoice_batch.py
import asyncio
import time
from typing import Any
import httpx
from pydantic import ValidationError
from course.lesson_01.invoice_models import RawInvoiceInput


def mock_sync_ocr_verify(invoice_id: str, delay_seconds: float = 0.1) -> dict[str, Any]:
    time.sleep(delay_seconds)
    return {"invoice_id": invoice_id, "ocr_status": "VERIFIED"}


def process_invoices_sync(
    raw_records: list[dict[str, Any]],
    delay_per_item: float = 0.1
) -> dict[str, list[Any]]:
    succeeded = []
    failed = []

    for raw in raw_records:
        try:
            validated = RawInvoiceInput.model_validate(raw)
            ocr_res = mock_sync_ocr_verify(validated.invoice_id, delay_per_item)
            succeeded.append({
                "invoice_id": validated.invoice_id,
                "amount": validated.total_amount,
                "ocr_status": ocr_res["ocr_status"],
            })
        except ValidationError as err:
            failed.append({
                "raw_id": raw.get("invoice_id", "UNKNOWN"),
                "error_type": "VALIDATION_ERROR",
                "detail": err.errors()[0]["msg"],
            })

    return {"succeeded": succeeded, "failed": failed}


async def mock_blocked_async_ocr(invoice_id: str, delay_seconds: float = 0.1) -> dict[str, Any]:
    time.sleep(delay_seconds)
    return {"invoice_id": invoice_id, "ocr_status": "VERIFIED"}


async def process_invoices_broken_async(
    raw_records: list[dict[str, Any]],
    delay_per_item: float = 0.1
) -> dict[str, list[Any]]:
    async def _handle_one(raw: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        try:
            validated = RawInvoiceInput.model_validate(raw)
            ocr_res = await mock_blocked_async_ocr(validated.invoice_id, delay_per_item)
            return True, {
                "invoice_id": validated.invoice_id,
                "amount": validated.total_amount,
                "ocr_status": ocr_res["ocr_status"],
            }
        except ValidationError as err:
            return False, {
                "raw_id": raw.get("invoice_id", "UNKNOWN"),
                "error_type": "VALIDATION_ERROR",
                "detail": err.errors()[0]["msg"],
            }

    tasks = [_handle_one(raw) for raw in raw_records]
    results = await asyncio.gather(*tasks)

    succeeded = [item for is_ok, item in results if is_ok]
    failed = [item for is_ok, item in results if not is_ok]
    return {"succeeded": succeeded, "failed": failed}


async def mock_network_ocr_call(
    client: httpx.AsyncClient,
    invoice_id: str,
    delay_seconds: float = 0.05
) -> dict[str, Any]:
    await asyncio.sleep(delay_seconds)
    return {"invoice_id": invoice_id, "ocr_status": "VERIFIED"}


async def process_invoices_async(
    raw_records: list[dict[str, Any]],
    client: httpx.AsyncClient | None = None,
    max_concurrency: int = 2,
    request_timeout: float = 1.0,
    delay_per_item: float = 0.05,
) -> dict[str, list[Any]]:
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _handle_single(
        target_client: httpx.AsyncClient,
        raw: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        try:
            validated = RawInvoiceInput.model_validate(raw)
        except ValidationError as err:
            return False, {
                "raw_id": raw.get("invoice_id", "UNKNOWN"),
                "error_type": "VALIDATION_ERROR",
                "detail": err.errors()[0]["msg"],
            }

        async with semaphore:
            try:
                ocr_resp = await asyncio.wait_for(
                    mock_network_ocr_call(target_client, validated.invoice_id, delay_per_item),
                    timeout=request_timeout
                )
                return True, {
                    "invoice_id": validated.invoice_id,
                    "amount": validated.total_amount,
                    "ocr_status": ocr_resp["ocr_status"],
                }
            except asyncio.TimeoutError:
                return False, {
                    "raw_id": validated.invoice_id,
                    "error_type": "OCR_TIMEOUT",
                    "detail": f"外部调用超过时限 ({request_timeout}s)",
                }
            except Exception as exc:
                return False, {
                    "raw_id": validated.invoice_id,
                    "error_type": "OCR_ERROR",
                    "detail": str(exc),
                }

    async def _execute_with_client(active_client: httpx.AsyncClient) -> dict[str, list[Any]]:
        tasks = [_handle_single(active_client, record) for record in raw_records]
        results = await asyncio.gather(*tasks)
        succeeded = [res for is_ok, res in results if is_ok]
        failed = [res for is_ok, res in results if not is_ok]
        return {"succeeded": succeeded, "failed": failed}

    if client is not None:
        return await _execute_with_client(client)

    async with httpx.AsyncClient(timeout=httpx.Timeout(request_timeout)) as managed_client:
        return await _execute_with_client(managed_client)
