"""L5.2 扩展 · 成本/缓存/路由 · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
cost_cache_routing.py。实现下面三组接口，然后运行：

    python chapters/part5-production/5.3-cost-cache-routing/gate/gate_check.py
"""

from __future__ import annotations


def cache_key(question: str) -> str:
    """归一化（去首尾空白、压缩空白、小写）后哈希；空问题 -> ValueError。"""
    raise NotImplementedError("实现缓存键")


class TTLCache:
    """带过期时间的缓存；clock 由调用方传入，便于测试。"""

    def __init__(self, ttl_seconds: float = 60):
        raise NotImplementedError("初始化缓存")

    def get(self, key: str, now: float) -> str | None:
        """命中且未过期返回值；过期/不存在返回 None（过期项应删除）。"""
        raise NotImplementedError("实现读取")

    def set(self, key: str, value: str, now: float) -> None:
        """写入并记录时间；ttl<=0 -> ValueError。"""
        raise NotImplementedError("实现写入")


def is_simple(question: str) -> bool:
    """短问题（<=12 字符）或含问候/闲聊提示词 -> True。"""
    raise NotImplementedError("实现难度判断")


def route(question: str) -> str:
    """简单 -> "cheap"，否则 "strong"；空问题 -> ValueError。"""
    raise NotImplementedError("实现路由")


def savings(simple_ratio: float, cheap_price: float, strong_price: float) -> float:
    """估算节省比例：simple_ratio * (1 - cheap/strong)。

    - 比例不在 [0,1] -> ValueError；
    - 价格 <=0 或 cheap>strong -> ValueError。
    """
    raise NotImplementedError("实现节省估算")


def cost_with_cache(input_tokens: int, cached_tokens: int, output_tokens: int, price: dict) -> float:
    """price = {"input", "cached_input", "output"}，单位为每百万 token；cached > input 时抛 ValueError。

    input_tokens 是总输入（含命中缓存的部分）：未命中部分按 input 计价，命中部分按 cached_input 计价。
    """
    raise NotImplementedError("实现带缓存的成本")


def schedule_batch(tasks: list[dict], now_utc_hour: int, offpeak_windows: list[tuple[int, int]]) -> list[dict]:
    """task = {"id", "urgent": bool}；urgent 任务立即执行（run_at_hour = now）；
    非 urgent 任务推迟到下一个低峰窗口的起点（窗口 [start, end) 可以跨零点，如 (22, 1)）；
    当前已处于低峰时立即执行。返回 [{"id", "run_at_hour"}]，顺序与输入一致。
    """
    raise NotImplementedError("实现低峰调度")
