"""章节 1.5 · 工具调用协议（原生实现）

知识点：
1. 用 JSON Schema 声明工具能力契约（tools 与 tool_choice）
2. 原生解析 tool_calls（支持并行调用、未知工具拦截与参数解析防御）
3. 执行工具并按协议以 role="tool" + tool_call_id 回传执行结果
4. 工具执行失败作为工具观察结果回灌给模型，而不是崩溃抛出
5. 最大循环步数（max_steps）截断防死循环

运行方式：
    python chapters/part1-foundations/1.5-tool-calling/tool_calling.py
"""

from __future__ import annotations

import copy
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 导入共享配置与客户端工厂
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from common import chat_model_name, get_openai_client
except ImportError:
    chat_model_name = None  # type: ignore
    get_openai_client = None  # type: ignore


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, type]
    handler: Callable[[dict[str, Any]], str]


class ToolError(ValueError):
    """工具调用不合法。"""


def _safe_calc(expression: str) -> str:
    """安全的简单数学表达式计算。"""
    allowed_chars = set("0123456789+-*/(). ")
    if not all(c in allowed_chars for c in expression):
        raise ValueError("包含非法计算字符")
    # 仅允许在完全受限的命名空间计算
    result = eval(expression, {"__builtins__": None}, {})  # noqa: S307
    return str(result)


def build_tools() -> dict[str, ToolSpec]:
    """返回标准内置工具字典。"""
    return {
        "get_weather": ToolSpec(
            name="get_weather",
            description="查询指定城市当天的实时天气",
            parameters={"city": str},
            handler=lambda args: f"{args['city']} 晴 22℃，湿度 45%",
        ),
        "calculate": ToolSpec(
            name="calculate",
            description="计算数学算式表达式的值",
            parameters={"expression": str},
            handler=lambda args: _safe_calc(args["expression"]),
        ),
    }


def dispatch_tool(
    tools: dict[str, ToolSpec],
    name: str,
    args: object,
) -> dict[str, Any]:
    """执行一次工具分发与防护。

    返回 {"ok": bool, "result": str, "error": str | None}
    - 未知工具 -> error="unknown_tool"
    - args 非字典或参数不合法 -> error="invalid_args"
    - handler 抛出异常 -> error="tool_error"
    - handler 返回非 str -> error="invalid_tool_output"
    """
    if name not in tools:
        return {"ok": False, "result": "", "error": "unknown_tool"}

    if not isinstance(args, dict):
        return {"ok": False, "result": "", "error": "invalid_args"}

    spec = tools[name]
    for param_name, param_type in spec.parameters.items():
        if param_name not in args:
            return {"ok": False, "result": "", "error": "invalid_args"}
        val = args[param_name]
        if param_type is int and isinstance(val, bool):
            return {"ok": False, "result": "", "error": "invalid_args"}
        if not isinstance(val, param_type):
            return {"ok": False, "result": "", "error": "invalid_args"}

    try:
        raw_output = spec.handler(args)
    except Exception:
        return {"ok": False, "result": "", "error": "tool_error"}

    if not isinstance(raw_output, str):
        return {"ok": False, "result": "", "error": "invalid_tool_output"}

    return {"ok": True, "result": raw_output, "error": None}


def run_tool_loop(
    messages: list[dict[str, Any]],
    llm_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    tools: dict[str, ToolSpec] | None = None,
    max_steps: int = 3,
) -> dict[str, Any]:
    """执行“模型请求工具 -> 程序执行 -> 结果喂回”的闭环循环。"""
    if max_steps < 1:
        raise ValueError("max_steps 必须大于等于 1")

    if tools is None:
        tools = build_tools()

    history = copy.deepcopy(messages)
    trace: list[dict[str, Any]] = []

    for _ in range(max_steps):
        try:
            resp = llm_fn(history)
        except Exception as exc:
            return {
                "answer": f"模型调用失败: {exc}",
                "trace": trace,
                "stopped_reason": "model_error",
            }

        tool_calls = resp.get("tool_calls", [])
        content = resp.get("content", "")

        # 如果没有工具调用，说明给出了最终回答
        if not tool_calls:
            return {"answer": content, "trace": trace, "stopped_reason": "final"}

        # 追加模型的中间思考或工具请求消息
        history.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
        })

        # 依次处理工具调用（支持并行调用）
        for call_item in tool_calls:
            call_id = call_item.get("id", "")
            tool_name = call_item.get("name", "")
            tool_args = call_item.get("args", {})

            dispatch_res = dispatch_tool(tools, tool_name, tool_args)
            trace.append({
                "tool": tool_name,
                "args": tool_args,
                "ok": dispatch_res["ok"],
                "result": dispatch_res["result"],
                "error": dispatch_res["error"],
            })

            # 把执行结果作为 role="tool" 的消息回传给模型（失败时不崩，把错误信息回传）
            tool_feedback = (
                dispatch_res["result"]
                if dispatch_res["ok"]
                else f"工具执行失败: {dispatch_res['error']}"
            )
            history.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": tool_feedback,
            })

    return {"answer": "", "trace": trace, "stopped_reason": "max_steps"}


def demonstrate_native_tools() -> None:
    print("=== 原生工具调用协议演示 ===")
    tools = build_tools()

    # 1. 离线分发测试
    print("--- 1. 离线工具分发防御测试 ---")
    calc_ok = dispatch_tool(tools, "calculate", {"expression": "128 * 4"})
    print(f"合法调用 calculate: {calc_ok}")

    unknown_res = dispatch_tool(tools, "non_existent_tool", {})
    print(f"未知工具拦截: {unknown_res}")

    bad_args_res = dispatch_tool(tools, "get_weather", {"city": 123})
    print(f"参数类型错误拦截: {bad_args_res}")

    # 2. 真实模型端到端工具闭环
    if get_openai_client is None or chat_model_name is None:
        print("\n[提示] 缺少 common 模块，跳过真实模型工具调用演示。")
        return

    try:
        client = get_openai_client()
    except Exception as exc:
        print(f"\n[提示] 未能初始化客户端（{exc}）。演示跳过真实网络请求。")
        return

    model = chat_model_name()
    print(f"\n--- 2. 真实模型端到端工具闭环（模型: {model}）---")

    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询指定城市当天的实时天气",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string", "description": "城市名称，如北京、上海"}},
                    "required": ["city"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "计算数学表达式的值",
                "parameters": {
                    "type": "object",
                    "properties": {"expression": {"type": "string", "description": "算式，如 24 * 7"}},
                    "required": ["expression"],
                },
            },
        },
    ]

    def raw_llm_fn(hist: list[dict[str, Any]]) -> dict[str, Any]:
        resp = client.chat.completions.create(
            model=model,
            messages=hist,  # type: ignore
            tools=openai_tools,
            temperature=0.0,
        )
        msg = resp.choices[0].message
        tc_list = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    parsed_args = json.loads(tc.function.arguments)
                except Exception:
                    parsed_args = {}
                tc_list.append({"id": tc.id, "name": tc.function.name, "args": parsed_args})
        return {"content": msg.content or "", "tool_calls": tc_list}

    user_query = "请帮我查一下北京今天的天气，并算一下 15 乘以 24 等于多少？"
    print(f"用户提问: {user_query}")

    initial_messages = [
        {"role": "system", "content": "你是一个工具调用助手，遇到事实或计算问题应积极调用工具。"},
        {"role": "user", "content": user_query},
    ]

    loop_res = run_tool_loop(initial_messages, raw_llm_fn, tools=tools, max_steps=5)
    print(f"最终回答: {loop_res['answer']}")
    print("调用轨迹 (Trace):")
    for step in loop_res["trace"]:
        print(f"  - 工具: {step['tool']}, 入参: {step['args']}, 结果: {step['result']}, 成功: {step['ok']}")


if __name__ == "__main__":
    demonstrate_native_tools()
