"""4.7：把 submit_decision 当输出通道，枚举校验后再进入业务分支。"""
from __future__ import annotations

import argparse
import json
from collections.abc import Callable

ROUTES = {"research", "writing", "review", "finish"}
INTENTS = {"knowledge", "data_query", "chitchat"}


def parse_field(text: str, field: str, allowed: set[str]) -> str:
    if not isinstance(text, str):
        raise ValueError("输出必须是 JSON 字符串")
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError("输出不是合法 JSON") from exc
    value = data.get(field) if isinstance(data, dict) else None
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{field} 必须属于 {sorted(allowed)}")
    return value


def parse_route(text: str, allowed: set[str]) -> str:
    return parse_field(text, "next", allowed)


def route_next(state: dict) -> str:
    if state.get("done"):
        return "end"
    value = state.get("_next")
    if not isinstance(value, str) or value not in {"research", "writing", "review"}:
        raise ValueError("非法路由")
    return value


def parse_intent(text: str) -> str:
    return parse_field(text, "category", INTENTS)


def choose_enum(prompt: str, field: str, allowed: set[str], chat_fn: Callable) -> str:
    """工具不执行业务；参数就是输出。即使有 enum，应用侧仍须校验。"""
    schema = {"type": "function", "function": {
        "name": "submit_decision", "description": "提交一个路由选择，不执行任何业务操作",
        "parameters": {"type": "object", "properties": {
            field: {"type": "string", "enum": sorted(allowed)},
        }, "required": [field], "additionalProperties": False},
    }}
    response = chat_fn([
        {"role": "system", "content": "只调用 submit_decision 提交分类，不输出自由文本。"},
        {"role": "user", "content": prompt},
    ], schema)
    calls = response.get("tool_calls") or []
    if len(calls) != 1 or calls[0].get("function", {}).get("name") != "submit_decision":
        raise ValueError("必须且只能提交一次 submit_decision")
    return parse_field(calls[0]["function"].get("arguments"), field, allowed)


def make_live_chat() -> Callable:
    from common import LLM_PROVIDER, chat_model_name, get_openai_client

    client = get_openai_client(timeout=20, max_retries=0)
    model = chat_model_name()
    extra = {"extra_body": {"thinking": {"type": "disabled"}}} if LLM_PROVIDER == "deepseek" else {}

    def chat(messages: list[dict], schema: dict) -> dict:
        response = client.chat.completions.create(
            model=model, messages=messages, tools=[schema],
            tool_choice={"type": "function", "function": {"name": "submit_decision"}},
            temperature=0, **extra,
        )
        return response.choices[0].message.model_dump(exclude_none=True)

    return chat


class ScriptedRouting:
    """离线也走工具参数解析，而非绕过 choose_enum。"""

    def __init__(self, decisions: list[str]) -> None:
        self.decisions = iter(decisions)

    def __call__(self, messages: list[dict], schema: dict) -> dict:
        field = schema["function"]["parameters"]["required"][0]
        return {"tool_calls": [{"function": {
            "name": "submit_decision", "arguments": json.dumps({field: next(self.decisions)}),
        }}]}


def run_supervisor(task: str, chat_fn: Callable, *, max_steps: int = 8) -> dict:
    if max_steps < 1:
        raise ValueError("max_steps 必须 >= 1")
    state = {"task": task, "step_log": [], "done": False, "_next": ""}
    for _ in range(max_steps):
        selected = choose_enum(f"任务：{task}；已完成：{state['step_log']}", "next", ROUTES, chat_fn)
        state.update(_next=selected, done=selected == "finish")
        state["step_log"].append(f"supervisor→{selected}")
        print("  [supervisor]", selected)
        if route_next(state) == "end":
            return state
        # 本章只演示分流，专家节点不生成真实文章。
        state["step_log"].append(f"{selected} 完成（路由教学节点）")
    raise ValueError("主管超过 max_steps，未提交 finish")


def run_intent_router(question: str, chat_fn: Callable) -> dict:
    category = choose_enum(question, "category", INTENTS, chat_fn)
    branches = {"knowledge": "[RAG 路由教学节点] ",
                "data_query": "[Text2SQL 路由教学节点] ", "chitchat": "[普通对话教学节点] "}
    return {"question": question, "category": category, "answer": branches[category] + question}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    try:
        live = make_live_chat() if args.live else None
        print("[live] 真实模型选择路由，专家为教学节点" if args.live else "[offline] 脚本化工具输出")
        print("===== 一：枚举主管 research→writing→review→finish =====")
        state = run_supervisor("写一篇 Python 装饰器短文", live or ScriptedRouting([
            "research", "writing", "review", "finish",
        ]))
        print("流程轨迹：", state["step_log"])
        print("\n===== 二：知识 / 数据 / 闲聊意图分流 =====")
        chat = live or ScriptedRouting(["knowledge", "data_query", "chitchat"])
        for question in ["RAG 的原理是什么？", "示例科技 2025Q2 利润多少？", "在吗，聊聊天"]:
            print(run_intent_router(question, chat))
    except Exception as exc:
        print(f"路由失败：{type(exc).__name__}；请检查输出枚举、common 配置或服务连接。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
