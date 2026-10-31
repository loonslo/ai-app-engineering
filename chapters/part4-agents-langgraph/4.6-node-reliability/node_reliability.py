"""
章节 4.6 · 节点容错与重试：出错怎么办（生产第一课）
==========================================================
章节 4.5 的 Agent 能跑，但所有工具都"一定成功"。真实世界不是这样：
搜索超时、SQL 连不上、LLM 限流 429、工具抛异常……
默认情况下，节点里一抛异常 → 整张图崩掉 → 用户拿到 500。这在生产是事故。

四道防线，从轻到重：
【一】节点级 try/except + fallback：捕获异常，返回一个"降级但可用"的结果，图继续走。
【二】RetryPolicy：瞬时错误（网络抖动/限流）自动重试几次，避免一次失败就放弃。
【三】ToolNode 工具报错不崩：让工具异常作为 ToolMessage 回喂给模型，模型自己换个法子。
【四】超时护栏：给慢节点设上限，别让一个卡死的工具拖垮整条请求。

核心原则：区分【可重试的瞬时错误】和【不可重试的确定错误】——
限流/超时值得重试；参数错了/无权限，重试一百次也没用，应快速失败并降级。

衔接：章节 4.5 给了能跑的 ReAct；这里让它"跑得稳"；章节 4.9 让它"出错查得到"。
==========================================================
"""

import random
import time
from typing import TypedDict
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
import argparse
import sys

LIVE = False


def get_llm(temperature: float = 0.0, **kwargs):
    """只由 --live 使用公共模型工厂；离线脚本保留除零工具演示。"""
    if LIVE:
        from common import get_llm as shared_llm
        return shared_llm(temperature=temperature, **kwargs)
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage

    class OfflineModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    return OfflineModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "divide", "args": {"a": 10, "b": 0}, "id": "divide-1"}]),
        AIMessage(content="（离线脚本）工具返回除零错误，不能给出合法数值。"),
    ])


# ============================================================
# 【一】节点级 try/except + fallback：出错不崩，降级继续
# ============================================================
class State(TypedDict):
    query: str
    result: str


def flaky_fetch(query: str) -> str:
    """模拟一个不稳定的外部调用：一半概率抛异常。"""
    if random.random() < 0.5:
        raise ConnectionError("模拟：外部服务超时")
    return f"「{query}」的真实数据"


def robust_node(state: State) -> dict:
    """生产写法：把可能失败的调用包在 try 里，失败给降级结果，图照样往下走。"""
    try:
        data = flaky_fetch(state["query"])
        return {"result": data}
    except Exception as e:
        # 关键：不 re-raise。记下原因（章节 4.9 会把它结构化落盘），返回可用的降级值
        print(f"  [robust_node] 调用失败降级：{e}")
        return {"result": f"（降级）暂时取不到「{state['query']}」的数据，请稍后重试"}


def build_fallback():
    g = StateGraph(State)
    g.add_node("fetch", robust_node)
    g.add_edge(START, "fetch")
    g.add_edge("fetch", END)
    return g.compile()


# ============================================================
# 【二】RetryPolicy：瞬时错误自动重试（框架帮你重，不用手写 for）
# ============================================================
_attempt = {"n": 0}


def sometimes_fails(state: State) -> dict:
    """模拟前两次抛错、第三次成功——演示重试把瞬时错误磨平。"""
    _attempt["n"] += 1
    if _attempt["n"] < 3:
        print(f"  [retry_node] 第 {_attempt['n']} 次：抛错")
        raise TimeoutError("模拟瞬时超时")
    print(f"  [retry_node] 第 {_attempt['n']} 次：成功")
    return {"result": "重试后拿到结果"}


def build_retry():
    """按锁定版本的 API 给节点配置同一重试策略。"""
    from langgraph.types import RetryPolicy
    g = StateGraph(State)
    # 最多重试 3 次；retry_on 指定"哪些异常才重试"——只重瞬时错误
    g.add_node("work", sometimes_fails,
               retry_policy=RetryPolicy(max_attempts=3, retry_on=(TimeoutError, ConnectionError)))
    g.add_edge(START, "work")
    g.add_edge("work", END)
    return g.compile()


# ============================================================
# 【三】ToolNode 工具报错不崩：异常回喂模型，让它自救
# ============================================================
@tool
def divide(a: int, b: int) -> float:
    """两数相除。"""
    return a / b   # b=0 会抛 ZeroDivisionError


def build_tool_safe():
    llm = get_llm(temperature=0).bind_tools([divide])

    def agent(state: MessagesState) -> dict:
        try:
            return {"messages": [llm.invoke(state["messages"])]}
        except Exception as exc:
            # 工具错误仍回灌；模型不可用不能伪装成演示成功。
            raise RuntimeError(f"模型调用失败（{type(exc).__name__}），请检查公共配置或网络") from None

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    # handle_tool_errors=True：工具抛异常时，把错误信息包成 ToolMessage 回喂模型，
    # 而不是让整图崩。模型看到"报错了"可以换参数或改口。
    g.add_node("tools", ToolNode([divide], handle_tool_errors=True))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")
    return g.compile()


# ============================================================
# 【四】超时护栏：给慢调用设上限（工具内自控，最稳）
# ============================================================
def with_timeout(fn, seconds: float, on_timeout):
    """极简超时封装：真实项目用 httpx/requests 的 timeout 参数或 asyncio.wait_for。
    这里演示"超时就走降级"的思路。"""
    start = time.time()
    result = fn()
    if time.time() - start > seconds:
        return on_timeout
    return result


def run_demos() -> None:
    random.seed(0)   # 固定随机，输出可复现

    print("===== 【一】try/except + fallback：失败降级不崩 =====")
    for i in range(3):
        out = build_fallback().invoke({"query": "北京天气", "result": ""})
        print(f"  第{i+1}次 →", out["result"])

    print("\n===== 【二】RetryPolicy：前两次失败、自动重试到成功 =====")
    _attempt["n"] = 0
    out = build_retry().invoke({"query": "x", "result": ""})
    print("  最终 →", out["result"])

    print("\n===== 【三】ToolNode handle_tool_errors：除零不崩，回喂模型自救 =====")
    app = build_tool_safe()
    res = app.invoke({"messages": [("user", "帮我算 10 除以 0")]})
    print("  最终答复 →", res["messages"][-1].content)

    print("\n===== 【四】超时护栏：快调用拿到真实结果，慢调用触发降级 =====")
    # 模拟快速服务：0.2s 返回
    fast_result = with_timeout(
        fn=lambda: (time.sleep(0.2), "真实数据")[1],
        seconds=0.5,
        on_timeout="（降级）请求超时，返回缓存数据"
    )
    print(f"  快速调用 → {fast_result}")

    # 模拟慢服务：1.5s 返回，超过 0.5s 阈值 → 触发降级
    slow_result = with_timeout(
        fn=lambda: (time.sleep(1.5), "真实数据")[1],
        seconds=0.5,
        on_timeout="（降级）请求超时，返回缓存数据"
    )
    print(f"  慢速调用 → {slow_result}")


def main() -> int:
    global LIVE
    parser = argparse.ArgumentParser(description="节点可靠性历史演示；默认离线脚本模型")
    parser.add_argument("--live", action="store_true", help="显式调用真实模型")
    LIVE = parser.parse_args().live
    print("模式：真实模型" if LIVE else "模式：离线脚本模型")
    try:
        run_demos()
    except Exception as exc:
        print(f"运行失败（{type(exc).__name__}）：检查公共模型配置、依赖与网络；未生成成功结果。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ----------------------------------------------------------
# 小结：
# - 默认节点一抛异常，整图崩。生产必须给每层加防线。
# - try/except+fallback：捕获→返回降级值→图继续（用户至少拿到可用回复）。
# - RetryPolicy(max_attempts, retry_on)：瞬时错误自动重试；只重"值得重的"异常。
# - ToolNode(handle_tool_errors=True)：工具报错包成 ToolMessage 回喂模型，不崩。
# - 超时护栏：慢调用设上限，别让一个卡死的工具拖垮整条请求。
# - 判断心法：可重试(限流/超时/抖动) vs 不可重试(参数错/无权限)——后者快速失败别硬重。
#
# 动手练习：把 章节 4.12 的 web_search 加上 RetryPolicy(重试 2 次) + 超时降级到内置假数据，
#          让搜索 Agent 在断网时也能优雅返回而不是报 500。
# ----------------------------------------------------------
