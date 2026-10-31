"""
章节 4.14 · 多 Agent：Supervisor 主管模式 + Fan-out 并行
==========================================================
单 Agent（章节 4.5 ReAct、章节 4.8 Plan-and-Execute）一个人扛所有活，遇到
"既要查资料、又要写、还要审"的复合任务就吃力。多 Agent 把任务拆给专家，
由一个"主管（Supervisor）"协调——

【一】Supervisor 模式：supervisor 节点按当前进度决定下一步交给哪个专家
    （research / writing / review），专家干完回到 supervisor，直到 FINISH。
    本质还是"条件边 + 循环"，但每个节点是另一个 Agent。带 max_steps 护栏防死循环。

【二】Fan-out 并行：一个节点同时分叉到多个分支并行执行，再汇聚（fan-in）合并。
    适合"从不同角度各查一块、最后汇总"的场景，比串行省时间。

【三】agent-as-tool：主流工具（Claude Code / Cursor / OpenAI Agents SDK）的做法
    ——子 Agent 不是图上的节点，而是主 Agent 工具列表里的一个 tool。
    核心差别不是"分工"，是"省 context"：子 Agent 独立上下文，
    只收一段任务描述、只回一段结果摘要，主 Agent 看不到它的中间过程。

注意：专家 Agent 都走真实 LLM。Supervisor 本身不调用 LLM，按固定流水线
（research → writing → review）确定性推进：简单可靠、不额外消耗 token。
生产里可以让 LLM 决定路由（做法见 4.7），但必须配硬约束防止死循环。
==========================================================
"""

import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from common import get_llm

# 保留图版演示；只在 main 的 --live 分支初始化模型。
llm = None


# ============================================================
# 【一】Supervisor 多 Agent
# ============================================================
def research_agent(state: MessagesState) -> dict:
    """研究 Agent：负责信息收集。"""
    system = SystemMessage(content="你是一个专业的研究员，负责收集和整理信息。请简洁地总结关键信息。")
    response = llm.invoke([system] + state["messages"])
    return {"messages": [response]}


def writing_agent(state: MessagesState) -> dict:
    """写作 Agent：负责内容创作。"""
    system = SystemMessage(content="你是一个专业的写作者，负责根据已有信息撰写内容。请保持内容清晰流畅。")
    response = llm.invoke([system] + state["messages"])
    return {"messages": [response]}


def review_agent(state: MessagesState) -> dict:
    """审校 Agent：负责质量控制。"""
    system = SystemMessage(content="你是一个专业的编辑，负责审核和改进内容质量。请指出问题并给出改进建议。")
    response = llm.invoke([system] + state["messages"])
    return {"messages": [response]}


# 固定流水线：research → writing → review → FINISH。
# 为什么不让 LLM 决定下一步？共享全量消息历史时，LLM 会在 writing/review 之间反复横跳、
# 迟迟不输出 FINISH，直接撞穿 recursion_limit（本文件最初的报错就是这么来的）。
# 生产里想让 LLM 路由是可以的，但必须配"阶段已完成"这类硬约束防止死循环；
# 演示阶段用确定性推进最可靠、也不额外烧 token。
PIPELINE = ["research", "writing", "review"]


class SupervisorState(MessagesState):
    stage: str   # 记录刚跑完的阶段，供 supervisor 确定性推进，保证一定收敛


def supervisor_node(state: SupervisorState) -> dict:
    """主管：按固定流水线推进到下一个阶段（不调 LLM，确定性、可复现）。"""
    stage = state.get("stage", "")
    if stage == "":
        nxt = PIPELINE[0]                       # 首次 → 第一个阶段
    else:
        i = PIPELINE.index(stage)
        nxt = PIPELINE[i + 1] if i + 1 < len(PIPELINE) else "FINISH"
    return {"stage": nxt}


def route_by_supervisor(state: SupervisorState) -> str:
    """根据主管给出的下一阶段路由；FINISH → 结束。"""
    stage = state["stage"]
    return stage if stage in PIPELINE else END


def build_supervisor():
    g = StateGraph(SupervisorState)
    # supervisor 是"调度器"（只推进 stage、不调 LLM）；下面三个才是干活的专家 Agent。
    # 注意：add_node 第一个参数是"图里的节点名"，第二个才是"执行函数"，两者可以不同名。
    g.add_node("supervisor", supervisor_node)
    g.add_node("research", research_agent)
    g.add_node("writing", writing_agent)
    g.add_node("review", review_agent)

    g.add_edge(START, "supervisor")
    # route_by_supervisor 直接返回"目标节点名"（research/writing/review）或 END，
    # 所以不用再传映射字典——省掉那份 {"research": "research"} 式的冗余、也不易看花。
    g.add_conditional_edges("supervisor", route_by_supervisor)
    # 每个专家干完都回到 supervisor，由它决定下一步 / 结束（这里的循环变量是"节点名"，不是 Agent 对象）。
    for node_name in PIPELINE:
        g.add_edge(node_name, "supervisor")
    return g.compile(checkpointer=InMemorySaver())


# ============================================================
# 【二】Fan-out 并行 + Fan-in 汇聚
# ============================================================
class FanState(TypedDict):
    topic: str
    # 并发写：b1/b2/b3 在同一 step 都写 angles，必须给 reducer（operator.add）
    # 合并；否则框架抛 InvalidUpdateError（原理与正解见 章节 4.4）。
    angles: Annotated[list[str], operator.add]
    summary: str


def _collect(angle: str):
    """模拟一个分支：针对某个角度搜集要点（这里用规则模拟，避免并发打 LLM）。"""
    samples = {
        "定义": "概念定义：用一句话说清它是什么。",
        "优缺点": "优点可控、缺点需规划；适合生产。",
        "例子": "例子：用它搭一个带人工审批的搜索 Agent。",
    }
    return samples.get(angle, f"关于「{angle}」的要点。")


def fan_branch(state: FanState, angle: str) -> dict:
    """带固定参数的分支节点工厂（每个角度一个并行分支）。"""
    point = _collect(angle)
    print(f"  [branch] 角度「{angle}」→ {point}")
    # 只返回自己这一条，交给 reducer 合并——不要手拼 state["angles"]+[...]，
    # 并发下会丢更新，且无 reducer 时框架直接报错（章节 4.4 详解）。
    return {"angles": [point]}


def merge_node(state: FanState) -> dict:
    """汇聚：把各分支要点合并成一段总结。"""
    summary = "；".join(state["angles"])
    return {"summary": summary}


def build_fanout():
    g = StateGraph(FanState)
    # 三个分支节点，各负责一个角度。用 lambda 是为了把"角度"这个固定参数提前绑进去，
    # 因为节点函数只接收 state 一个入参，没法在建图时直接传 angle 进去。
    g.add_node("b1", lambda s: fan_branch(s, "定义"))
    g.add_node("b2", lambda s: fan_branch(s, "优缺点"))
    g.add_node("b3", lambda s: fan_branch(s, "例子"))
    g.add_node("merge", merge_node)      # 汇聚节点：等三个分支都跑完再合并

    # fan-out：START 同时连向 b1/b2/b3，三条边在同一 super-step 并行触发。
    g.add_edge(START, "b1")
    g.add_edge(START, "b2")
    g.add_edge(START, "b3")

    # fan-in：三个分支都连向 merge。LangGraph 会等所有前驱都跑完才执行 merge（barrier 同步），
    # 所以不会各触发一次；三条 angles 靠 FanState 里的 reducer（operator.add）自动合并，不会互相覆盖。
    g.add_edge("b1", "merge")
    g.add_edge("b2", "merge")
    g.add_edge("b3", "merge")

    g.add_edge("merge", END)
    return g.compile()


# ============================================================
# 【三】agent-as-tool：主流工具（Claude Code / Cursor / OpenAI Agents SDK）的做法
#     ——子 Agent 不是图上的节点，而是主 Agent 工具列表里的一个 tool。
#     核心差别不是"分工"，是"省 context"：子 Agent 独立上下文，
#     只收一段任务描述、只回一段结果摘要，主 Agent 看不到它的中间过程。
# ============================================================


def _sub_agent(role_prompt: str, task: str) -> str:
    """跑一个独立上下文的子 Agent：入参只有 task，返回只有结论。"""
    resp = llm.invoke([SystemMessage(content=role_prompt), HumanMessage(content=task)])
    return resp.content


@tool
def researcher(task: str) -> str:
    """当需要收集/整理某个主题的资料时调用。task 是给研究员的一句话任务描述。"""
    return _sub_agent("你是研究员，收集并用要点形式简洁总结关键信息，不超过 150 字。", task)


@tool
def writer(task: str) -> str:
    """当资料已备齐、需要成文时调用。task 里应包含要写什么以及可用的素材。"""
    return _sub_agent("你是写作者，根据给定素材写出清晰流畅的短文。", task)


@tool
def reviewer(task: str) -> str:
    """当初稿完成、需要审校时调用。task 里应包含待审内容。"""
    return _sub_agent("你是编辑，指出问题并给出可执行的改进建议，不超过 150 字。", task)


def run_delegating_agent(user_task: str, max_steps: int = 6):
    """普通 ReAct 循环 + 动态委派：调不调、调几个、调几次都由 LLM 现场决定。

    对比【一】的图版本：
      - 没有一条边是预先画好的，路由 = LLM 的 tool_call
      - 一轮可返回多个 tool_call → 天然 fan-out，不用 reducer
      - 子 Agent 的中间过程不进主上下文，只回填一条摘要
    """
    tools = {t.name: t for t in [researcher, writer, reviewer]}
    agent = llm.bind_tools(list(tools.values()))
    msgs = [
        SystemMessage(content="你是任务主管。可把子任务委派给 researcher/writer/reviewer 工具，完成后直接给出最终成果。"),
        HumanMessage(content=user_task),
    ]
    for _ in range(max_steps):          # max_steps = 这里的循环护栏
        ai = agent.invoke(msgs)
        msgs.append(ai)
        if not ai.tool_calls:
            return ai.content
        for call in ai.tool_calls:      # 同一轮多个 tool_call → 并行委派的位置
            print(f"  [委派] {call['name']} ← {str(call['args'])[:60]}")
            out = tools[call["name"]].invoke(call["args"])
            msgs.append(ToolMessage(content=out, tool_call_id=call["id"]))
    return "达到 max_steps 护栏，未收敛。"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="历史 LangGraph 对照；学完 L4.9 后阅读")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        print("LangGraph 历史对照版需要 --live；离线主教材请运行 supervisor_native.py。")
        return 0
    global llm
    try:
        llm = get_llm(temperature=0, timeout=15, max_retries=0,
                      extra_body={"thinking": {"type": "disabled"}})
        print("[live] 一、Supervisor 固定流水线")
        sup = build_supervisor()
        cfg = {"configurable": {"thread_id": "sup-1"}, "recursion_limit": 12}
        result = sup.invoke(
            {"messages": [HumanMessage(content="请帮我写一篇关于 Python 装饰器的简短介绍文章")]}, cfg)
        for message in result["messages"][-4:]:
            print(f"  [{type(message).__name__}] {str(message.content)[:80]}")
        print("二、Fan-out/Fan-in")
        out = build_fanout().invoke({"topic": "LangGraph", "angles": [], "summary": ""})
        print("汇聚后的总结：", out["summary"])
        print("三、agent-as-tool 动态委派")
        print(run_delegating_agent("请帮我写一篇关于 Python 装饰器的简短介绍文章"))
    except Exception as exc:
        print(f"对照版运行失败：{type(exc).__name__}；请检查模型配置、连接与步数预算。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ----------------------------------------------------------
# 小结：
# - Supervisor 模式：一个 supervisor 节点按进度把活分给 research/writing/review 等专家，
#   专家干完回到 supervisor，直到 FINISH。本质 = 条件边 + 循环，只是节点换成了 Agent。
# - 生产里路由可由 LLM 自己决定（更灵活，见 4.7），本文件用固定流水线做演示（确定性、可复现、省 token）。
# - 必须给多 Agent 循环加护栏（recursion_limit / max_steps），否则可能停不下来。
# - Fan-out：一个节点分叉到多个并行执行；Fan-in：多分支汇聚到一个合并。适合"多角度看、再汇总"。
# - 并发分支写同一字段（angles）必须用 reducer（Annotated[list, operator.add]），
#   否则 InvalidUpdateError；这正是 章节 4.4 的用武之地。
# - 与前面章节 的关系：章节 4.5 是单 Agent ReAct；章节 4.8 是先规划再执行；章节 4.14 是多 Agent 协作——
#   复杂任务从"一个人干"升级到"一个团队干"。
#
# ========== 编排（orchestration）vs 委派（delegation）==========
# 本文件【一】【二】写的是"编排"，主流工具（Claude Code / Cursor / OpenAI Agents SDK）做的是"委派"。
# 相同：都是"一个协调者 + 多个专家"、都要循环护栏、都有 fan-out 并行。
#
# 三个关键差别：
# 1) 路由方式
#    图版本：条件边预先画死，路径是静态的。
#    主流做法：子 Agent 即工具（agent-as-tool）。主 Agent 就是普通 ReAct 循环，
#    "调用研究员"只是工具列表里的一个 tool——调不调、调几个、调几次由 LLM 在循环里现场决定。
# 2) 状态隔离（多 Agent 真正的价值）
#    图版本：MessagesState 共享，所有专家看同一份消息历史，很快爆 context。
#    主流做法：子 Agent 独立上下文，只接收一段任务描述、只返回一段结果摘要。
#    多 Agent 的价值不是"分工"，是"省 context"。
# 3) fan-out
#    图版本：显式画三条边 + reducer 合并。
#    主流做法：LLM 一轮返回多个 tool_call，runtime 并行执行、结果一起回填，
#    reducer 问题在框架层就解决了。
#
# 什么时候仍该用图：流程确定、必须按序、要能中断续跑、要审计每一步——工单处理、合规审批。
#   图的价值是可控性和可观测性，不是灵活性。
# 什么时候别用图：任务开放、步骤不可预知（写代码、做研究），图会一直跑偏或卡死，
#   ReAct + 动态委派更合适。
# 一句话：选哪个看流程确定性。两者并存，不是谁淘汰谁。
#
# 动手练习：
# 1) 把 Supervisor 的路由从"关键词"换成"让 LLM 输出 JSON 决定下一步"，看会不会更灵活但更易跑偏。
# 2) 跑一遍【三】，对比它和【一】的差别：主上下文里塞了多少东西、路径是谁决定的。
# ----------------------------------------------------------
