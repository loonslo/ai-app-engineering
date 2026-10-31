"""4.5：显式打印 messages、step、finished；天气查询与错误修复只执行一次。"""
from __future__ import annotations

import argparse

from react_agent import ScriptedChat, make_live_chat, run_loop, tool_message

_WEATHER_DB = {"北京": "晴，25℃", "上海": "多云，28℃", "广州": "雷阵雨，30℃", "深圳": "阴，29℃"}


def get_weather(city: str) -> str:
    """固定教学数据，不代表当前天气。"""
    return f"{city}：{_WEATHER_DB.get(city, '暂无数据')}（固定教学数据）"


SCHEMAS = [{"type": "function", "function": {
    "name": "get_weather", "description": "查询固定教学天气，非实时天气",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                   "required": ["city"], "additionalProperties": False},
}}]


def run_agent(question: str, chat_fn) -> dict:
    """复用同一循环；从返回的消息打印增量，不再 invoke 第二遍。"""
    print(f"\n===== 问题：{question} =====")
    result = run_loop(question, chat_fn, {"get_weather": get_weather},
                      max_steps=5, max_tool_calls=4, tool_schemas=SCHEMAS)
    step = []
    for message in result["messages"]:
        role = message["role"]
        if role in {"assistant", "tool"}:
            step.append("agent" if role == "assistant" else "tools")
        print(f"  追加 [{role}]：{message}")
    print("--- 最终 state ---")
    print({"finished": result["status"] == "done", "step": step,
           "message_count": len(result["messages"]), "stopped_reason": result["stopped_reason"]})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    try:
        live = make_live_chat(SCHEMAS) if args.live else None
        print("[live] 真实模型；天气仍为固定数据" if args.live else "[offline] 脚本化模型与固定天气")
        scenarios = [
            ("北京现在适合穿短袖吗？", [tool_message("get_weather", {"city": "北京"}),
                                        {"role": "assistant", "content": "教学天气25℃，可考虑短袖。"}]),
            ("北京和上海，哪个更热？", [tool_message("get_weather", {"city": "北京"}, "bj"),
                                         tool_message("get_weather", {"city": "上海"}, "sh"),
                                         {"role": "assistant", "content": "固定数据里上海28℃，比北京25℃热。"}]),
        ]
        for question, script in scenarios:
            if run_agent(question, live or ScriptedChat(script))["status"] != "done":
                return 1
        if not args.live:
            run_agent("错误参数后修正", ScriptedChat([
                tool_message("get_weather", {"city": 123}, "bad"),
                tool_message("get_weather", {"city": "北京"}, "fixed"),
                {"role": "assistant", "content": "已修正参数并取得北京教学天气。"},
            ]))
            print("\n===== 重复动作：工具预算先耗尽 =====")
            bounded = run_loop("反复查询", ScriptedChat([
                tool_message("get_weather", {"city": "北京"}, str(i)) for i in range(4)
            ]), {"get_weather": get_weather}, max_steps=5, max_tool_calls=2, tool_schemas=SCHEMAS)
            print({key: bounded[key] for key in ("status", "steps", "tools_called", "stopped_reason")})
    except Exception as exc:
        print(f"真实调用失败：{type(exc).__name__}；请检查 common 密钥、模型配置与服务连接。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
