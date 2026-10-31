"""J5 任务 C 的起点：空实现。把它复制成你自己的文件再实现。"""
from __future__ import annotations

from typing import Any, Callable


def run_agent(task: str, tools: dict[str, Callable[..., Any]], decide_fn: Callable[[str, list], dict], *,
              max_steps: int = 5, approve_fn: Callable[[str, dict], bool] | None = None,
              dangerous: frozenset[str] = frozenset()) -> dict:
    """接口约定见 briefs/c-tool-agent.md。"""
    raise NotImplementedError("实现 run_agent")
