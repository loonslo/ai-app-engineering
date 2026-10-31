"""
章节 4.3 · LangGraph 入门（下）：分支与循环 + 对比手写循环
==========================================================
章节 4.2 搭了最小【线性图】，但那和 LCEL 没区别。图真正的价值本节才登场：
【一】分支与循环：conditional_edges 按 state 决定下一步走哪条边；
    把条件边指回前面的节点就形成循环，用 recursion_limit 防死循环。
【二】对比手写循环：用 LangGraph 重写 章节 1.5/章节 2.5 的手写 while 工具循环，
    看清"框架到底替我做了什么"（这层封装叫 harness）。

一句话：分支/循环/状态，才是"要用图而不是 LCEL"的理由。

衔接：章节 4.2 是线性图基础；本文件加分支/循环；章节 4.4 讲 state 合并(reducer)；
      章节 4.5 加工具调用做成 ReAct Agent；章节 4.14 升级到多 Agent（Supervisor）。
==========================================================
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langchain_core.tools import tool
import argparse
import sys

LIVE = False


def get_llm(temperature: float = 0.0, **kwargs):
    """离线用脚本模型；真实模型只由 --live 经公共工厂启用。"""
    if LIVE:
        from common import get_llm as shared_llm
        return shared_llm(temperature=temperature, **kwargs)
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage

    class OfflineModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    return OfflineModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "add", "args": {"a": 18, "b": 24}, "id": "add-1"}]),
        AIMessage(content="（离线脚本）18 + 24 = 42"),
        AIMessage(content="", tool_calls=[{"name": "add", "args": {"a": 42, "b": 100}, "id": "add-2"}]),
        AIMessage(content="（离线脚本）42 + 100 = 142"),
    ])


# ============================================================
# 【一】分支与循环：conditional_edges + recursion_limit
# ============================================================
class LoopState(TypedDict):
    quality: int   # 当前质量分
    rounds: int    # 已打磨轮数


def improve(state: LoopState) -> dict:
    """每轮质量 +1，轮数 +1。"""
    q, r = state["quality"] + 1, state["rounds"] + 1
    print(f"  [improve] 第{r}轮，质量 {q}")
    return {"quality": q, "rounds": r}


def route(state: LoopState) -> str:
    """条件函数：返回的字符串决定走哪条边。"""
    return "good_enough" if state["quality"] >= 5 else "keep_going"


def build_loop():
    g = StateGraph(LoopState)
    g.add_node("improve", improve)
    g.add_edge(START, "improve")
    g.add_conditional_edges("improve", route, {
        "keep_going": "improve",   # 不达标 → 回到自己，形成循环
        "good_enough": END,        # 达标 → 结束
    })
    return g.compile()


# ============================================================
# 【二】对比手写循环：LangGraph 重写工具调用 + 对比表
# ============================================================
@tool
def add(a: int, b: int) -> int:
    """计算 a + b。"""
    return a + b


TOOLS = [add]


def build_agent():
    llm = get_llm(temperature=0).bind_tools(TOOLS)

    def agent(state: MessagesState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(TOOLS))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)   # 有 tool_calls 就去 tools，否则结束
    g.add_edge("tools", "agent")                        # 工具结果回灌，循环
    return g.compile(checkpointer=InMemorySaver())       # 挂 checkpointer = 多轮记忆


COMPARISON = """
| 关注点            | 手写循环（章节 1.5/章节 2.5）          | LangGraph（本文件）              |
|------------------|----------------------------------|----------------------------------|
| 判断要不要调工具  | 自己解析 tool_calls + if 判断     | tools_condition 内置             |
| 执行工具+回灌结果 | 自己拼 ToolMessage 塞回 messages  | ToolNode 自动                    |
| 循环控制          | 自己 while + 自己防死循环         | 图的边 + recursion_limit         |
| 多轮记忆          | 自己维护 messages 列表            | checkpointer 按 thread_id 自动   |
| 中断/恢复/HITL    | 几乎没法做                        | interrupt + checkpointer 内置    |
结论：框架替我包掉的 = 工具解析、循环、记忆、中断恢复——这层就是 harness。
"""


def run_demos() -> None:
    print("===== 【一】分支与循环 + 防死循环 =====")
    loop = build_loop()
    print("正常循环到达标：", loop.invoke({"quality": 0, "rounds": 0}))
    try:
        # 从 0 分到 5 分要 5 轮，但只允许 4 步 → 触发上限保护
        loop.invoke({"quality": 0, "rounds": 0}, {"recursion_limit": 4})
    except GraphRecursionError as e:
        print(f"  已被 recursion_limit 拦截（防死循环生效）：{type(e).__name__}")

    print("\n===== 【二】LangGraph 工具 Agent（带记忆）+ 对比 =====")
    app = build_agent()
    cfg = {"configurable": {"thread_id": "t1"}}
    r1 = app.invoke({"messages": [("user", "帮我算 18 加 24")]}, cfg)
    print("第1轮：", r1["messages"][-1].content)
    r2 = app.invoke({"messages": [("user", "再加 100 呢")]}, cfg)   # 靠记忆理解"再加"
    print("第2轮（带记忆）：", r2["messages"][-1].content)
    print(COMPARISON)


def main() -> int:
    global LIVE
    parser = argparse.ArgumentParser(description="状态循环与工具循环；默认离线脚本模型")
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
# - conditional_edges：用路由函数按 state 决定下一跳，是分支/循环的核心；
#   循环 = 把条件边指回前面的节点，靠退出条件停下。
# - recursion_limit：步数安全阀，超了抛 GraphRecursionError。生产 Agent 必配。
# - 对比手写循环：框架替你包掉工具解析、循环、记忆、中断恢复——这就是 harness 层。
# - 承接 章节 4.2：线性图无所谓用不用图；分支/循环/状态才是"必须用图"的理由。
# - 路由目前用字符串返回；生产里更稳的做法是结构化输出路由（见 章节 4.7）。
# ----------------------------------------------------------
