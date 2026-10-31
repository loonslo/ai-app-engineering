"""
章节 5.3 · 成本优化：缓存 + model routing + 低峰调度（原生 openai SDK）
==========================================================
LLM 调用按 token 收费，规模一上来成本很可观。常用的几招：
1. 缓存：同一个问题问过就别再调模型，直接返回上次结果（省钱又快）
2. model routing：简单问题用便宜小模型，复杂问题才用贵的大模型
3. 提示词缓存的计价：命中缓存的输入 token 比未命中便宜很多，成本公式要把它算进去
4. 低峰调度：不着急的批处理任务推迟到低价时段

本节用最朴素的实现把原理讲透；生产里缓存可换 Redis、routing 可上分类模型。

前置：5.2；工程版路由需要本地 embedding 模型
运行：python tools/run_chapter.py 5.3           （离线：假模型函数 + 本地 embedding，不花钱）
      python tools/run_chapter.py 5.3 --live    （调用真实模型，会产生少量费用）
输出：缓存命中前后的对比、规则版与 embedding 分类器版的路由结果、带缓存的成本与调度示例
==========================================================
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections.abc import Callable
from typing import Any

import numpy as np

ChatFn = Callable[[str, str], str]  # (模型档位 "cheap"/"strong", 问题) -> 回答


# ---------- 1. 缓存：问题 → 答案。简单用 dict，键用归一化后问题的 hash ----------
def cache_key(question: str) -> str:
    normalized = " ".join(question.split()).lower()
    if not normalized:
        raise ValueError("问题不能为空")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


_CACHE: dict[str, str] = {}


def ask_with_cache(question: str, chat: ChatFn) -> str:
    k = cache_key(question)
    if k in _CACHE:
        print("  [cache] 命中，直接返回（没调模型）")
        return _CACHE[k]
    print("  [cache] 未命中，调用模型")
    _CACHE[k] = chat("strong", question)
    return _CACHE[k]


# ---------- 2. model routing：按问题难度选模型 ----------
def is_simple(question: str) -> bool:
    """粗略判断：短、且像闲聊/问候的，算简单。生产可换成一个小分类模型。"""
    q = question.strip()
    simple_hint = any(w in q for w in ["你好", "谢谢", "再见", "几点", "是谁"])
    return len(q) <= 12 or simple_hint


def route(question: str) -> str:
    if not question.strip():
        raise ValueError("问题不能为空")
    return "cheap" if is_simple(question) else "strong"


def ask_with_routing(question: str, chat: ChatFn) -> str:
    tier = route(question)
    print(f"  [routing] {'简单问题 → 便宜模型' if tier == 'cheap' else '复杂问题 → 强模型'}")
    return chat(tier, question)


def savings(simple_ratio: float, cheap_price: float, strong_price: float) -> float:
    """节省比例 ≈ 简单问题占比 ×（1 - 便宜/强模型价差）。"""
    if not 0 <= simple_ratio <= 1 or cheap_price <= 0 or strong_price <= 0 or cheap_price > strong_price:
        raise ValueError("比例须在 [0,1]，价格须为正且 cheap ≤ strong")
    return simple_ratio * (1 - cheap_price / strong_price)


# ---------- 3. 带缓存命中的成本 ----------
def cost_with_cache(input_tokens: int, cached_tokens: int, output_tokens: int, price: dict) -> float:
    """price = {"input", "cached_input", "output"}，单位：每百万 token。

    input_tokens 是总输入（含命中缓存的部分）；未命中部分按 input 计价，命中部分按 cached_input 计价。
    """
    if cached_tokens > input_tokens:
        raise ValueError("命中缓存的 token 不能多于总输入 token")
    missed = input_tokens - cached_tokens
    return (missed * price["input"] + cached_tokens * price["cached_input"] + output_tokens * price["output"]) / 1_000_000


# ---------- 4. 低峰调度 ----------
def _in_window(hour: int, window: tuple[int, int]) -> bool:
    start, end = window
    return start <= hour < end if start < end else hour >= start or hour < end  # 窗口可以跨零点


def schedule_batch(tasks: list[dict], now_utc_hour: int, offpeak_windows: list[tuple[int, int]]) -> list[dict]:
    """urgent 任务立即执行；非 urgent 推迟到下一个低峰窗口的起点；当前已在低峰则立即执行。

    返回 [{"id", "run_at_hour"}]，顺序与输入一致。
    """
    if any(_in_window(now_utc_hour, w) for w in offpeak_windows):
        next_start = now_utc_hour
    else:
        # 距离现在最近的下一个窗口起点（按 24 小时环计算）
        next_start = min((w[0] for w in offpeak_windows), key=lambda s: (s - now_utc_hour) % 24) if offpeak_windows else now_utc_hour
    return [{"id": t["id"], "run_at_hour": now_utc_hour if t.get("urgent") else next_start} for t in tasks]


# ---------- 5. 工程版 routing：离线定标 → 在线分类 → 抽样监控 ----------
# 上面 is_simple() 的关键词规则只是冷启动。生产里的完整闭环是：
#   A. 离线（一次性 token 成本）：便宜模型跑历史问题 + judge 打分 → 产出"简单/复杂"标注
#      "难度"的定义 = 便宜模型能不能答对（实测），不靠拍脑袋
#   B. 在线（每次请求）：embedding 质心分类器做路由，本地推理 0 token、毫秒级
#   C. 监控（抽样 1~5%）：线上用 judge 复核路由质量，发现漂移就回炉重标
JUDGE_PROMPT = """你是评审员。判断下面的"回答"是否正确、完整地回答了"问题"。
只输出一个字：是 或 否。
问题：{q}
回答：{a}"""


def offline_label(questions: list[str], chat: ChatFn, out_path: str = "routing_labels.json") -> list[tuple[str, bool]]:
    """离线一次性：便宜模型作答 → judge 判对错。judge 说"是"= 便宜模型够用 = 简单。"""
    labeled = []
    for q in questions:
        ans = chat("cheap", q)
        verdict = chat("strong", JUDGE_PROMPT.format(q=q, a=ans))
        labeled.append((q, verdict.strip().startswith("是")))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(labeled, f, ensure_ascii=False, indent=2)
    return labeled


# 演示用种子标注（真实场景由 offline_label 从历史日志产出）
SEED_LABELED = [
    ("你好，在吗", True),
    ("谢谢你的帮助", True),
    ("现在几点了", True),
    ("RAG 是什么的缩写", True),
    ("帮我把这句话翻译成英文：今天天气不错", True),
    ("详细对比 RAG 和微调在成本、时效、数据安全上的取舍", False),
    ("设计一个支持多租户的企业知识库权限方案", False),
    ("我的向量检索召回率很低，帮我分析可能的原因并给出排查步骤", False),
    ("写一个带重试和熔断的 LLM 调用封装，要求可配置", False),
    ("解释检查点机制并说明如何实现人工审批", False),
    ("如何为 Agent 的工具调用轨迹设计自动化评估指标", False),
]


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


class EmbeddingRouter:
    """把两类标注问题各求一个质心向量；线上问题算 embedding 后看离谁近。
    用的是本地 embedding 模型，不调 API——这就是"判定本身不花钱"的关键。"""

    def __init__(self, labeled: list[tuple[str, bool]]):
        from common import embed_texts

        self._embed = embed_texts  # 已归一化，余弦相似度 = 点积
        self.c_simple = np.mean(self._embed([q for q, ok in labeled if ok]), axis=0)
        self.c_hard = np.mean(self._embed([q for q, ok in labeled if not ok]), axis=0)

    def is_simple(self, question: str) -> bool:
        v = np.array(self._embed([question])[0])
        return _cos(v, self.c_simple) > _cos(v, self.c_hard)


AUDIT_RATE = 0.05           # 抽 5% 请求用 judge 复核，成本可控
AUDIT_LOG: list[dict] = []  # 生产里落库/上报，配合 5.1 落库的 token / 成本记录看漂移


def ask_production(question: str, router: EmbeddingRouter, chat: ChatFn, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    simple = router.is_simple(question)
    print(f"  [prod-routing] {'简单→便宜模型' if simple else '复杂→强模型'}：{question[:20]}")
    ans = chat("cheap" if simple else "strong", question)
    if simple and rng.random() < AUDIT_RATE:  # 只审便宜模型的答案，强模型默认可信
        verdict = chat("strong", JUDGE_PROMPT.format(q=question, a=ans))
        AUDIT_LOG.append({"q": question, "pass": verdict.strip().startswith("是")})
        print("  [audit] 本条被抽检，judge 结果：", verdict.strip()[:5])
    return ans


# ---------- 模型函数：离线假模型 / 真实原生客户端 ----------
def offline_chat(tier: str, question: str) -> str:
    """脚本化回答：只用来演示控制流，不代表任何模型的真实表现。"""
    return f"（离线{'便宜' if tier == 'cheap' else '强'}模型的回答：{question[:10]}…）"


def live_chat() -> ChatFn:
    import common

    client = common.get_openai_client(timeout=30.0, max_retries=2)
    model = common.chat_model_name()  # 演示用同一个模型充当两档；真实场景把 cheap 换成小模型的 ID

    def chat(tier: str, question: str) -> str:
        resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": question}])
        return resp.choices[0].message.content or ""

    return chat


def main() -> int:
    parser = argparse.ArgumentParser(description="5.3 成本：缓存、路由、低峰调度")
    parser.add_argument("--live", action="store_true", help="调用真实模型")
    args = parser.parse_args()
    try:
        chat: ChatFn = live_chat() if args.live else offline_chat
        if args.live:
            print("[live 真实模型]")
        else:
            print("[离线演示] 模型回答为脚本化假回答，只演示缓存/路由/计价流程\n")

        print("===== 缓存：同一问题问两次 =====")
        q = "用一句话解释 RAG"
        print("答1：", ask_with_cache(q, chat)[:50])
        print("答2：", ask_with_cache(q, chat)[:50])  # 第二次应命中缓存

        print("\n===== routing（规则版）：简单 vs 复杂 =====")
        print("答：", ask_with_routing("你好", chat)[:50])
        print("答：", ask_with_routing("详细对比 RAG 和微调在成本与时效上的取舍", chat)[:50])

        print("\n===== routing（工程版）：embedding 分类器路由决策（本地，0 token）=====")
        router = EmbeddingRouter(SEED_LABELED)  # 生产里 labeled 来自 offline_label()
        for text in ["帮我翻译：机器学习", "如何设计 RAG 系统的灰度发布和回滚方案"]:
            print(f"  {text[:22]} → {'便宜模型' if router.is_simple(text) else '强模型'}")
        print("答：", ask_production("RAG 是什么意思", router, chat, random.Random(1))[:50])

        print("\n===== 带缓存命中的成本（单价为占位示例，请换成你的模型当前价格）=====")
        price: dict[str, Any] = {"input": 0.30, "cached_input": 0.006, "output": 1.20}
        no_cache = cost_with_cache(10_000, 0, 500, price)
        with_cache = cost_with_cache(10_000, 8_000, 500, price)
        print(f"  1 万输入 + 500 输出：无缓存 ${no_cache:.6f}，80% 命中缓存 ${with_cache:.6f}")

        print("\n===== 低峰调度（UTC，窗口 [10,18) 与跨零点的 [22,1)）=====")
        tasks = [{"id": "urgent-report", "urgent": True}, {"id": "nightly-eval", "urgent": False}]
        print("  现在 08 点：", schedule_batch(tasks, 8, [(10, 18), (22, 1)]))
        print("  现在 23 点（已在低峰）：", schedule_batch(tasks, 23, [(10, 18), (22, 1)]))
    except Exception as exc:  # 只给类型和提示，SDK 异常正文可能含 URL
        print(f"运行失败（{type(exc).__name__}）：检查模型配置、密钥、本地 embedding 模型与网络。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ----------------------------------------------------------
# 小结：
# - 缓存：重复问题直接返回，省 token 也降延迟；键用归一化后的 hash，值存答案。
# - model routing：简单走便宜模型、复杂走强模型，按需分流控成本。
# - 提示词缓存计价：命中部分按更低的单价算，公式要拆成"未命中 + 命中 + 输出"三段。
# - 低峰调度：只有不着急、可以延后的批处理任务才适合推迟；面向用户的请求不能等。
# - 算账决定取舍：省钱幅度 ≈ 简单问题占比 ×（1 - 便宜/强模型价差）。
#   两个数都从日志和离线评估里量出来，不靠感觉。
#
# 动手练习：
# 1. 给缓存加"过期时间"（gate 的 TTLCache），超过 N 秒的旧答案视为失效。
# 2. 用评测集跑一次 offline_label()，看便宜模型真实通过率，再算 routing 能省多少钱。
# ----------------------------------------------------------
