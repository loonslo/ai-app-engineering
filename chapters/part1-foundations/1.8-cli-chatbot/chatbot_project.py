"""章节 1.8 · 综合小项目：命令行助手（原生实现）

结合 L1 前序章节所学：
- 1.1 原生消息协议与一次调用往返
- 1.3 结构化提取与防御性校验（复用 1.3）
- 1.4 多轮会话内存隔离与上下文预算裁剪
- 1.5 工具调用协议与多步回灌（复用 1.5）

运行方式：
    python chapters/part1-foundations/1.8-cli-chatbot/chatbot_project.py
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

# 导入根目录 common
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 复用 1.3 结构化输出与 1.5 工具调用的模块（不复制代码）
_CH13_DIR = Path(__file__).resolve().parent.parent / "1.3-structured-output"
_CH15_DIR = Path(__file__).resolve().parent.parent / "1.5-tool-calling"
if str(_CH13_DIR) not in sys.path:
    sys.path.insert(0, str(_CH13_DIR))
if str(_CH15_DIR) not in sys.path:
    sys.path.insert(0, str(_CH15_DIR))

try:
    import structured_output as so_mod
except ImportError:
    so_mod = None  # type: ignore

try:
    import tool_calling as tc_mod
except ImportError:
    tc_mod = None  # type: ignore

try:
    from common import chat_model_name, get_openai_client
except ImportError:
    chat_model_name = None  # type: ignore
    get_openai_client = None  # type: ignore

SYSTEM_PROMPT = "你是一个命令行助手，用简洁中文回答。"


class CLIError(ValueError):
    """CLI 参数或输入不合法。"""


def run_cli(
    inputs: Iterable[str],
    chat_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    tools: dict[str, Callable[[dict[str, Any]], str]] | None = None,
    max_turns: int = 20,
) -> dict[str, Any]:
    """执行脚本化或交互式的 CLI 循环。

    chat_fn(messages) 返回：
        {"content": str, "tool_calls": [{"id": str, "name": str, "args": dict}]}

    返回字典包含：
    - outputs: list[str]（每轮模型回答或系统提示）
    - trace: list[dict]（每轮 turn/input/output/tools 轨迹）
    - exit_code: int（0 正常退出，1 模型或工具异常，2 达到 max_turns）
    - history: list[dict]（最终保存的消息历史）
    """
    if max_turns < 1:
        raise CLIError(f"max_turns={max_turns} 必须大于等于 1")

    history: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    outputs: list[str] = []
    trace: list[dict[str, Any]] = []
    turn_count = 0

    for user_input in inputs:
        clean_text = user_input.strip()
        if not clean_text:
            continue

        if clean_text.lower() == "quit":
            return {
                "outputs": outputs,
                "trace": trace,
                "exit_code": 0,
                "history": history,
            }

        if clean_text.lower() == "clear":
            history = [{"role": "system", "content": SYSTEM_PROMPT}]
            outputs.append("记忆已清除")
            continue

        turn_count += 1
        if turn_count > max_turns:
            outputs.append("达到最大轮数限制，会话已自动终止")
            return {
                "outputs": outputs,
                "trace": trace,
                "exit_code": 2,
                "history": history,
            }

        history.append({"role": "user", "content": clean_text})
        turn_tools_used: list[dict[str, Any]] = []

        # 内部工具闭环处理（最多 5 步）
        while True:
            try:
                resp = chat_fn(history)
            except Exception as exc:
                outputs.append(f"模型调用发生异常: {exc}")
                return {
                    "outputs": outputs,
                    "trace": trace,
                    "exit_code": 1,
                    "history": history,
                }

            tool_calls = resp.get("tool_calls", [])
            content = resp.get("content", "")

            if not tool_calls:
                history.append({"role": "assistant", "content": content})
                outputs.append(content)
                trace.append({
                    "turn": turn_count,
                    "input": clean_text,
                    "output": content,
                    "tools": turn_tools_used,
                })
                break

            # 记录工具请求消息
            history.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
            })

            # 遍历并执行所有工具调用
            has_error = False
            for tc in tool_calls:
                call_id = tc.get("id", "")
                t_name = tc.get("name", "")
                t_args = tc.get("args", {})

                if tools is None or t_name not in tools:
                    outputs.append(f"调用了未知工具: {t_name}")
                    return {
                        "outputs": outputs,
                        "trace": trace,
                        "exit_code": 1,
                        "history": history,
                    }

                try:
                    tool_result_str = tools[t_name](t_args)
                except Exception as exc:
                    outputs.append(f"工具执行异常: {exc}")
                    return {
                        "outputs": outputs,
                        "trace": trace,
                        "exit_code": 1,
                        "history": history,
                    }

                turn_tools_used.append({"tool": t_name, "args": t_args, "result": tool_result_str})
                history.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_result_str,
                })

            if has_error:
                break

    return {
        "outputs": outputs,
        "trace": trace,
        "exit_code": 0,
        "history": history,
    }


def main_interactive() -> None:
    print("=== 1.8 CLI 智能助手（原生驱动）===")
    print("输入 'clear' 清空上下文记忆，输入 'quit' 退出。")

    if get_openai_client is None or chat_model_name is None:
        print("[提示] 缺少 common 模块，退出交互。")
        return

    try:
        client = get_openai_client()
    except Exception as exc:
        print(f"[提示] 未能初始化客户端（{exc}）。请先配置 API Key。")
        return

    model = chat_model_name()

    # 复用 1.5 章节定义的工具体系
    native_tools = tc_mod.build_tools() if tc_mod else {}
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": {
                    "type": "object",
                    "properties": {k: {"type": "string"} for k in spec.parameters},
                    "required": list(spec.parameters.keys()),
                },
            },
        }
        for spec in native_tools.values()
    ]

    tool_handlers = {
        name: (lambda spec=spec: (lambda args: spec.handler(args)))()
        for name, spec in native_tools.items()
    }

    def real_chat_fn(hist: list[dict[str, Any]]) -> dict[str, Any]:
        resp = client.chat.completions.create(
            model=model,
            messages=hist,  # type: ignore
            tools=openai_tools if openai_tools else None,
            temperature=0.0,
        )
        msg = resp.choices[0].message
        tc_list = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    p_args = json.loads(tc.function.arguments)
                except Exception:
                    p_args = {}
                tc_list.append({"id": tc.id, "name": tc.function.name, "args": p_args})
        return {"content": msg.content or "", "tool_calls": tc_list}

    def input_generator():
        while True:
            try:
                line = input("\nUser > ")
                yield line
                if line.strip().lower() == "quit":
                    break
            except (EOFError, KeyboardInterrupt):
                yield "quit"
                break

    res = run_cli(input_generator(), real_chat_fn, tools=tool_handlers, max_turns=10)
    print(f"\n会话结束（退出码: {res['exit_code']}，保存轮数: {len(res['history'])}）")


if __name__ == "__main__":
    # 若在非交互终端中运行，执行基本断言自测
    if not sys.stdin.isatty():
        def fake_chat(messages):
            return {"content": "自测通过", "tool_calls": []}
        r = run_cli(["测试"], fake_chat, max_turns=5)
        print(f"自测完成: {r['outputs']}")
    else:
        main_interactive()
