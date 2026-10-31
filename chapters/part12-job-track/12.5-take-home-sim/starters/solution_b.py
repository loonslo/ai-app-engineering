"""J5 任务 B 的起点：空实现。把它复制成你自己的文件再实现。"""
from __future__ import annotations

from typing import Callable


def extract_ticket(text: str, chat_fn: Callable[[list[dict]], str], *, max_attempts: int = 2) -> dict:
    """接口约定见 briefs/b-extraction.md。"""
    raise NotImplementedError("实现 extract_ticket")


def evaluate(cases: list[dict], extract_fn: Callable[[str], dict]) -> dict:
    """接口约定见 briefs/b-extraction.md。"""
    raise NotImplementedError("实现 evaluate")
