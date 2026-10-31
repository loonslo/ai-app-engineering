"""4.5：从 4.3 的 decide→run_tool→decide 读懂原生 agent→tools→agent。"""
from __future__ import annotations

from typing import TypedDict


class ReactState(TypedDict):
    todo: list[str]
    history: list[str]


def agent(state: ReactState) -> str:
    """用待办数量代替模型决策；不调用模型。"""
    print(f"  [agent] 剩余待办：{state['todo']}")
    return "call_tool" if state["todo"] else "end"


def tools(state: ReactState) -> None:
    current = state["todo"].pop(0)
    result = f"工具执行结果<{current}>"
    state["history"].append(result)
    print(f"  [tools] 执行：{current} → {result}")


def run_react(todo: list[str], *, max_steps: int = 6) -> dict:
    """每轮决定后最多执行一个待办；耗尽预算时保留未完成项。"""
    if max_steps < 1:
        raise ValueError("max_steps 必须 >= 1")
    state: ReactState = {"todo": list(todo), "history": []}
    for _ in range(max_steps):
        if agent(state) == "end":
            return {**state, "stopped_reason": "done"}
        tools(state)
    return {**state, "stopped_reason": "done" if not state["todo"] else "max_steps"}


if __name__ == "__main__":
    print("===== 从 4.3 改出 ReAct（无 SDK、无密钥）=====")
    print("4.3: decide→run_tool→decide；4.5: agent→tools→agent")
    print("最终 state：", run_react(["步骤A", "步骤B", "步骤C"]))
    print("真实版把 todo 判断换成模型 tool_calls，把 history 换成 messages；见 react_agent.py。")
