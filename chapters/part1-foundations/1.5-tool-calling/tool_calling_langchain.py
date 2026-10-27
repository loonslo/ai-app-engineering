"""
章节 1.5 · 工具调用（Tool Calling）
==========================================================
模型只会"说"，不会"做"：它算不准大数，也查不到实时天气。工具调用让模型在需要时
请求调用你写的函数，拿到真实结果后再回答。这是后面 Agent 的基础。

知识点：
1. @tool：把普通函数变成模型可调用的工具，docstring 是给模型看的说明书
2. llm.bind_tools()：把工具清单绑给模型
3. 两轮流程：模型决定调哪个工具 → 程序执行 → 结果喂回 → 模型给最终回答
4. 判断模型是否要调工具，看 tool_calls，不看 content

前置：1.1
运行：python tools/run_chapter.py 1.5（调用真实模型，会产生少量费用）
输出：模型请求的工具调用、工具执行结果，以及最终回答
==========================================================
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


# @tool 把函数注册成"工具"。
# 注意：docstring 不是写给人看的，是写给模型看的——模型靠它判断"这个工具干嘛、啥时候用"。
# docstring 写得越清楚，模型选工具越准。这是 tool 最关键的部分。
@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气，输入城市名称，例如 '北京'"""
    data = {"北京": "晴天 25°C", "上海": "多云 22°C", "广州": "小雨 28°C"}
    return data.get(city, f"{city}暂无数据")


@tool
def calculate(expression: str) -> str:
    """计算数学表达式，输入合法的 Python 数学表达式，例如 '99 * 88'"""
    try:
        # 教学示例为了简短直接用 eval，它会执行任意代码，真实项目不能这样写。
        # 1.8 限制了 eval 的可用名字；来自不可信输入的表达式应改用 ast 白名单解析，见 5.7。
        return str(eval(expression))
    except Exception:
        return "计算失败，请检查表达式"


# 把工具清单绑给模型。绑完后模型在回答时，可以选择"我要调用某个工具"。
llm_with_tools = llm.bind_tools([get_weather, calculate])


# ---------- 工具调用的完整两轮流程 ----------
messages = [HumanMessage("北京天气怎么样？再帮我算 99 * 88")]

# 第一轮：模型不直接回答，而是返回"我要调用哪些工具、参数是什么"（tool_calls）
response = llm_with_tools.invoke(messages)
print("模型请求的工具调用：", response.tool_calls)
messages.append(response)   # 把模型这一步也加进对话历史

# 由程序真正执行工具，再把结果用 ToolMessage 追加回去。
# tool_call_id 用来告诉模型：这条结果对应它的哪一次请求。
tools_map = {"get_weather": get_weather, "calculate": calculate}
for call in response.tool_calls:
    result = tools_map[call["name"]].invoke(call["args"])
    print(f"执行 {call['name']}({call['args']}) → {result}")
    messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

# 第二轮：模型看到工具返回的真实结果，给出最终回答
final = llm_with_tools.invoke(messages)
print("最终回答：", final.content)


# ----------------------------------------------------------
# 小结：
# - @tool 的 docstring 是模型选工具的依据，务必写清楚"干嘛、参数是什么"
# - 流程是两轮：模型给 tool_calls → 你执行 → 喂回结果 → 模型给最终答
# - 判断模型是否要调工具：看 response.tool_calls 是否为空，
#   不要看 response.content（有的模型调工具时 content 也会有内容）
#
# 安全提醒（重要）：真实项目里绝不要把"删除/转账/发邮件"这类危险操作
#   直接做成工具让模型自由调用，必须加人工确认。后面 Agent 阶段会专门讲。
# ----------------------------------------------------------
