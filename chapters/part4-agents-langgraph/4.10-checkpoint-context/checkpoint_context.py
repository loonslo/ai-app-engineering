"""
章节 4.10 · 状态持久化（checkpoint）+ 上下文管理
==========================================================
两件让 Agent 能上真实场景的事：

1. 状态持久化（checkpoint/persistence）：前面的图每次 invoke 跑完 state 就没了，
   等于没记忆。LangGraph 的 checkpointer 每步自动存 state 快照，按 thread_id 隔离会话。
   - 多轮记忆：同一 thread_id 续聊自动带历史，不用手拼 messages；
   - 中断恢复：挂了/被打断后从上次 checkpoint 接着跑（章节 4.11 HITL 就靠它）；
   - 多用户隔离：不同 thread_id 各记各的。
   InMemorySaver 存内存（重启即丢）；生产换 SqliteSaver / PostgresSaver 落盘。

2. 上下文管理（Context Engineering）：对话越长 messages 越多，迟早超窗口、越来越贵。
   常见策略：只留最近 N 轮 + 把更早的压成一段摘要。关键是"该留的事实别在摘要里丢"。
==========================================================
"""

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
import argparse
import sys

LIVE = False


def get_llm(temperature: float = 0.0, **kwargs):
    """离线用可组合脚本模型；只有 --live 才读取公共模型配置。"""
    if LIVE:
        from common import get_llm as shared_llm
        return shared_llm(temperature=temperature, **kwargs)
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

    class OfflineModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return OfflineModel(responses=[
                AIMessage(content="", tool_calls=[{"name": "get_weather", "args": {"city": "北京"}, "id": "weather-1"}]),
                AIMessage(content="（离线脚本）北京本节晴，25℃"),
                AIMessage(content="", tool_calls=[{"name": "get_weather", "args": {"city": "上海"}, "id": "weather-2"}]),
                AIMessage(content="（离线脚本）上海本节晴，25℃"),
                AIMessage(content="（离线脚本）这是新会话，缺少此前讨论的天气上下文。"),
            ])

    return OfflineModel(responses=[
        AIMessage(content="（离线脚本）这里只演示消息裁剪/摘要接线，不验证模型是否记住事实。"),
    ])


llm = get_llm()  # 导入只创建离线脚本替身；main 的 --live 分支才替换为真实客户端。


# ============ 第一部分：checkpoint 持久化 + 多轮记忆 ============
@tool
def get_weather(city: str) -> str:
    """查询城市天气（演示假数据）。"""
    return f"{city}本节晴，25℃"


TOOLS = [get_weather]


def build_app():
    llm_with_tools = get_llm(temperature=0).bind_tools(TOOLS)

    def agent(state: MessagesState) -> dict:
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(TOOLS))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")
    # 关键：compile 时挂 checkpointer，图就有了"记忆"
    return g.compile(checkpointer=InMemorySaver())


def demo_memory():
    app = build_app()
    cfg = {"configurable": {"thread_id": "user-1"}}   # thread_id 标识一个会话
    print("第1轮：")
    r1 = app.invoke({"messages": [("user", "北京天气怎么样？")]}, cfg)
    print("  答：", r1["messages"][-1].content)
    print("第2轮（只说'那上海呢'，靠记忆理解在问天气）：")
    r2 = app.invoke({"messages": [("user", "那上海呢？")]}, cfg)
    print("  答：", r2["messages"][-1].content)
    print("换 thread_id（全新会话，无上面记忆）：")
    r3 = app.invoke({"messages": [("user", "那上海呢？")]},
                    {"configurable": {"thread_id": "user-2"}})
    print("  答：", r3["messages"][-1].content)


# ============ 第二部分：上下文管理（官方实现） ============
# 原理（手写版做的事）：切旧/新消息 → LLM 概括旧的 → 摘要+新消息拼回去。
# 生产直接用官方件，分两档：
#   2a. trim_messages     —— 不调 LLM，按 token 预算裁掉最旧的。快、免费、会丢信息。
#   2b. SummarizationNode —— 调 LLM 把旧消息压成摘要，带缓存不重复压。慢一点但保事实。
#       需要 pip install langmem
SAMPLE_HISTORY = [
    HumanMessage(content="我叫小王，在学 RAG"),
    AIMessage(content="好的小王，RAG 是检索增强生成"),
    HumanMessage(content="我之前是做测试的"),
    AIMessage(content="测试背景对 RAG 评测很有优势"),
    HumanMessage(content="那我现在叫什么名字？"),
]


def demo_trim():
    """2a. trim_messages：纯裁剪，无 LLM 调用。
    演示用 token_counter=len（按"条数"算），确定性强、必触发裁剪；
    真实场景换 count_tokens_approximately 按 token 预算算。
    """
    from langchain_core.messages import trim_messages

    trimmed = trim_messages(
        SAMPLE_HISTORY,
        strategy="last",           # 从最新往回保留
        max_tokens=3,              # token_counter=len 时，这里的单位就是"条"
        token_counter=len,         # 每条算 1，即"最多留 3 条"
        start_on="human",          # 裁完必须以 human 开头（OpenAI 系接口要求）
        include_system=True,       # SystemMessage 永远保留
    )
    print(f"  {len(SAMPLE_HISTORY)} 条 → 裁剪后 {len(trimmed)} 条：")
    for m in trimmed:
        print(f"    保留 {type(m).__name__}: {m.content[:20]}")
    ans = llm.invoke(trimmed).content
    print("  问'我叫什么'，模型答：", ans[:50], "← '小王'在被裁掉的第 1 条里，答不上")


def build_summary_app():
    """2b. SummarizationNode：挂在模型节点前，超阈值自动摘要。"""
    from typing import Any
    from langmem.short_term import SummarizationNode
    from langchain_core.messages.utils import count_tokens_approximately

    class State(MessagesState):
        context: dict[str, Any]        # SummarizationNode 的摘要缓存（避免每轮重复摘要）
        summarized_messages: list      # 压缩后"喂给 LLM 的视图"，不覆盖完整历史

    # 中文摘要 prompt：默认是英文的，且容易把"人名/身份"这类关键事实摘丢——显式要求保留。
    # 注意预算关系：max_tokens 要 ≥ max_summary_tokens + 近期消息所需空间，
    # 差值太小会触发 "Failed to trim messages..." 警告（塞不下近期消息，退回原始列表）。
    initial_prompt = ChatPromptTemplate.from_messages([
        ("placeholder", "{messages}"),
        ("user", "用中文概括以上对话。务必保留：人名、身份背景、关键事实和决定。"),
    ])
    existing_prompt = ChatPromptTemplate.from_messages([
        ("placeholder", "{messages}"),
        ("user", "已有摘要：{existing_summary}\n"
                 "结合新消息用中文更新摘要。务必保留：人名、身份背景、关键事实和决定。"),
    ])

    summarize = SummarizationNode(
        model=llm,
        token_counter=count_tokens_approximately,
        max_tokens=512,                     # 压缩后喂给模型的总预算（摘要 128 + 近期消息 384）
        max_tokens_before_summary=256,      # 历史超过这个数才触发摘要，否则原样通过
        max_summary_tokens=128,             # 摘要本身的预算
        initial_summary_prompt=initial_prompt,
        existing_summary_prompt=existing_prompt,
        output_messages_key="summarized_messages",  # 关键：写到单独的 key，messages 里仍是全量历史
    )

    def chat(state: State) -> dict:
        # 模型只看压缩视图；完整历史由 checkpointer 持久化，两者分离是官方设计
        return {"messages": [llm.invoke(state["summarized_messages"])]}

    g = StateGraph(State)
    g.add_node("summarize", summarize)
    g.add_node("chat", chat)
    g.add_edge(START, "summarize")
    g.add_edge("summarize", "chat")
    # 运行时若见 "Deserializing unregistered type ... RunningSummary" 提示：
    # 是 checkpoint 序列化 langmem 摘要缓存的兼容性提醒，不影响功能，可忽略。
    return g.compile(checkpointer=InMemorySaver())


def demo_context():
    print("--- 2a. trim_messages（裁剪：丢信息换速度） ---")
    demo_trim()

    print("--- 2b. SummarizationNode（摘要：保事实控 token） ---")
    try:
        app = build_summary_app()
    except ImportError:
        print("  未安装 langmem，先跑：pip install langmem")
        return
    cfg = {"configurable": {"thread_id": "ctx-demo"}}
    for q in ["我叫小王，在学 RAG", "我之前是做测试的",
              "测试背景做 AI 评估有什么优势？", "那我现在叫什么名字？"]:
        r = app.invoke({"messages": [HumanMessage(content=q)]}, cfg)
        fed = len(r.get("summarized_messages", []))
        print(f"  问：{q}")
        print(f"    全量历史 {len(r['messages'])} 条，实际喂模型 {fed} 条")
        print(f"    答：{r['messages'][-1].content[:50]}")
    # 检验点：最后一问历史已超阈值被摘要，但摘要里保住了"小王"


def run_demos() -> None:
    print("===== 1) checkpoint 持久化 + 多轮记忆 =====")
    demo_memory()
    print("\n===== 2) 上下文裁剪 + 摘要 =====")
    demo_context()


def main() -> int:
    global LIVE, llm
    parser = argparse.ArgumentParser(description="检查点与上下文历史演示；默认离线脚本模型")
    parser.add_argument("--live", action="store_true", help="显式调用真实模型")
    LIVE = parser.parse_args().live
    print("模式：真实模型" if LIVE else "模式：离线脚本模型（不评估摘要质量）")
    try:
        llm = get_llm(temperature=0)
        run_demos()
    except Exception as exc:
        print(f"运行失败（{type(exc).__name__}）：检查公共模型配置、依赖与网络；未生成成功结果。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ----------------------------------------------------------
# 小结：
# - checkpointer 按 thread_id 存每步 state 快照——多轮记忆 + 中断恢复都靠它，比 章节 1.4 手拼干净。
# - 上下文管理不用手写：裁剪用 trim_messages（免费丢信息），摘要用 langmem SummarizationNode
#   （花一次 LLM 调用保事实）。选型标准：历史里有"必须记住的事实"（名字/决定）就用摘要。
# - 官方设计的关键：完整历史(messages) 和 喂模型的视图(summarized_messages) 分离，
#   checkpointer 存全量，模型只看压缩版——审计/回放不丢数据。
# - 动手练习：把 InMemorySaver 换 SqliteSaver 落盘重启验证；
#   把 max_tokens_before_summary 调小到 64，看第 2 轮就触发摘要后"小王"还在不在。
# ----------------------------------------------------------
