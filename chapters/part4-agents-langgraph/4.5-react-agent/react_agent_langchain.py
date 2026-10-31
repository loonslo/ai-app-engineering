"""4.5 的框架对照：保留手搭 agent↔tools 图与现成 Agent 两组演示。

默认仅提示入口；显式 --live 才调用模型。先完成原生版，再读 4.15 框架素养。
"""

from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain.agents import create_agent
import argparse


def get_llm(temperature: float = 0.0, **kwargs):
    """对照版也复用 common 配置，并关闭 DeepSeek 思考。"""
    from common import LLM_PROVIDER, get_llm as common_llm

    if LLM_PROVIDER == "deepseek":
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    return common_llm(temperature=temperature, **kwargs)


# ---------- 工具 ----------
@tool
def add(a: int, b: int) -> int:
    """计算两个整数相加。"""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """计算两个整数相乘。"""
    return a * b


@tool
def get_weather(city: str) -> str:
    """查询某城市天气（演示用，返回假数据）。"""
    return f"{city}本节晴，26℃"


TOOLS = [add, multiply, get_weather]


# ============================================================
# 第一部分：手搭 agent↔tools 循环
# ============================================================
def build_handmade():
    llm = get_llm(temperature=0)
    llm_with_tools = llm.bind_tools(TOOLS)   # 告诉模型有哪些工具可用

    def agent(state: MessagesState) -> dict:
        # 把目前所有消息发给模型，模型可能直接答、也可能要求调用工具
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(TOOLS))     # 现成节点：执行模型要求的工具
    g.add_edge(START, "agent")
    # tools_condition：模型要调工具→去"tools"，否则→END
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")             # 工具结果带回 agent，再想一轮
    return g.compile()


# ============================================================
# 第二部分：create_agent 现成版
# ============================================================
def build_prebuilt():
    # 对照框架封装的循环与上面的手搭图。
    return create_agent(
        get_llm(temperature=0),
        tools=TOOLS,
        system_prompt="你是一个会用工具的助手。需要计算或查询时调用合适的工具，最后用中文回答。",
    )


def demo() -> None:
    print("===== 手搭 ReAct Agent =====")
    app = build_handmade()
    for q in ["12 加 30 等于多少？", "北京天气怎么样？"]:
        print(f"\n问：{q}")
        result = app.invoke({"messages": [("user", q)]})
        print("答：", result["messages"][-1].content)

    print("\n===== create_agent 现成版（连续两步）=====")
    agent = build_prebuilt()
    # 故意问需要连续两步的题，观察 ReAct 的"想→做→再想"
    q = "先算 3 乘 4，再把结果加 10，等于多少？"
    print(f"问：{q}\n")
    result = agent.invoke({"messages": [("user", q)]})

    # 打印完整轨迹：能看到模型怎么一步步推理 + 调工具
    for m in result["messages"]:
        role = type(m).__name__
        tc = getattr(m, "tool_calls", None)
        if tc:
            print(f"[{role}] 调用工具：{[(c['name'], c['args']) for c in tc]}")
        elif m.content:
            print(f"[{role}] {m.content}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        print("框架对照未调用模型。离线主教程：react_agent.py；真实对照加 --live。")
        return 0
    try:
        demo()
    except Exception as exc:
        print(f"真实框架演示失败：{type(exc).__name__}；请检查 common 模型配置与服务连接。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
