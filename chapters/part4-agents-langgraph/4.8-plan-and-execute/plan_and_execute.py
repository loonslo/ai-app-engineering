"""4.8：显式 JSON 计划、逐步执行、保存失败游标后恢复。默认离线。"""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from pathlib import Path

PLANNING_PARADIGMS = {
    "ReAct": "决定→调用工具→观察结果→再决定。路径不确定时按观察推进；必须给循环设预算。",
    "Plan-and-Execute": "先写出计划，再逐步执行；适合检查步骤和保留恢复点，但计划本身仍可能错。",
    "Reflexion": "根据执行反馈记录反思，再尝试；需要外部成功信号，不能把自我评价当验证。",
    "ReWOO": "先列出取证和依赖关系，再执行工具，最后汇总；依赖前序结果的步骤仍要等待。",
    "Tree of Thoughts": "搜索多个候选路径，并评估、回溯；需要额外的搜索与评估预算。",
}
MULTI_AGENT_FRAMEWORKS = {
    "LangGraph": "状态图、检查点和人工介入；后续 4.10/4.11 展开。",
    "AutoGen": "多 Agent 对话协作的框架；本章不实现。",
    "CrewAI": "角色与任务组织的框架；本章不实现。",
    "A2A": "Agent 间通信协议，不是本章的执行循环；本章不实现。",
}


def supervisor_sketch() -> str:
    return "任务→supervisor→research / writer / sql→supervisor→完成；原生多 Agent 示例见 4.14。"


def parse_plan(text: str, min_steps: int = 2, max_steps: int = 4) -> list[str]:
    """旧 gate 的文本计划解析；原生模型路径改用 parse_json_plan。"""
    if not isinstance(text, str):
        raise ValueError("计划必须是字符串")
    steps = []
    for line in text.splitlines():
        step = re.sub(r"^\s*(?:\d+[.)]\s*|[-•]\s*)", "", line).strip()
        if step and step not in steps:
            steps.append(step)
    if not min_steps <= len(steps) <= max_steps:
        raise ValueError("计划步数越界")
    return steps


def parse_json_plan(text: str) -> list[str]:
    """只接受 {\"steps\": [非空字符串, ...]}，2–4 步且不重复。"""
    data = json.loads(text)
    steps = data.get("steps") if isinstance(data, dict) else None
    if (not isinstance(steps, list) or not 2 <= len(steps) <= 4
            or any(not isinstance(step, str) or not step.strip() for step in steps)):
        raise ValueError("JSON 计划必须含 2–4 个非空字符串步骤")
    steps = [step.strip() for step in steps]
    if len(set(steps)) != len(steps):
        raise ValueError("JSON 计划不能重复步骤")
    return steps


def new_state(task: str, plan: list[str]) -> dict:
    if not task.strip():
        raise ValueError("任务不能为空")
    return {"task": task, "plan": plan, "results": [], "cursor": 0, "error": None}


def execute_remaining(state: dict, execute_fn: Callable[[str, str], str], *, max_steps: int = 10) -> dict:
    """成功才推进 cursor。失败保留旧结果，恢复时只重试当前失败步骤。"""
    if max_steps < 1:
        raise ValueError("max_steps 必须 >= 1")
    state["error"] = None
    while state["cursor"] < min(len(state["plan"]), max_steps):
        step = state["plan"][state["cursor"]]
        try:
            output = execute_fn(state["task"], step)
            if not isinstance(output, str) or not output.strip():
                raise ValueError("执行结果必须是非空字符串")
        except Exception:
            state["error"] = "execute_error"
            return state
        state["results"].append(output)
        state["cursor"] += 1
        print(f"执行第 {state['cursor']} 步：{step}\n  → {output}")
    if state["cursor"] < len(state["plan"]):
        state["error"] = "plan_too_long"
    return state


def run_plan(task: str, plan_fn: Callable, execute_fn: Callable, max_steps: int = 10) -> dict:
    """保留旧 gate 的规划/执行错误码；参考流程另外暴露恢复函数。"""
    if max_steps < 1:
        raise ValueError("max_steps 必须 >= 1")
    state = new_state(task, [])
    try:
        state["plan"] = plan_fn(task)
    except Exception:
        state["error"] = "plan_error"
        return state
    return execute_remaining(state, execute_fn, max_steps=max_steps)


def load_state(text: str) -> dict:
    """恢复自己保存的检查点；结果数必须与成功游标一致。"""
    state = json.loads(text)
    if not isinstance(state, dict) or not isinstance(state.get("task"), str) or not state["task"].strip():
        raise ValueError("检查点缺少 task")
    parse_json_plan(json.dumps({"steps": state.get("plan")}, ensure_ascii=False))
    cursor, results = state.get("cursor"), state.get("results")
    if (type(cursor) is not int or not 0 <= cursor <= len(state["plan"])
            or not isinstance(results, list) or len(results) != cursor
            or any(not isinstance(item, str) or not item.strip() for item in results)):
        raise ValueError("检查点 cursor 与 results 不一致")
    return state


def make_live_functions() -> tuple[Callable, Callable]:
    from common import LLM_PROVIDER, chat_model_name, get_openai_client

    client = get_openai_client(timeout=20, max_retries=0)
    model = chat_model_name()
    extra = {"extra_body": {"thinking": {"type": "disabled"}}} if LLM_PROVIDER == "deepseek" else {}

    def complete(prompt: str, *, json_mode: bool = False) -> str:
        options = {"response_format": {"type": "json_object"}} if json_mode else {}
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            temperature=0, **options, **extra,
        )
        return response.choices[0].message.content or ""

    def plan(task: str) -> list[str]:
        return parse_json_plan(complete(
            '把任务拆成2–4个可执行步骤，只返回JSON：{"steps":["步骤一","步骤二"]}。任务：' + task,
            json_mode=True,
        ))

    def execute(task: str, step: str) -> str:
        return complete(f"围绕总任务「{task}」，完成这一步并简要给出结果：{step}")

    return plan, execute


OFFLINE_STEPS = ["整理 RAG 的定义", "列出检索与生成流程", "编写科普短文提纲"]
OFFLINE_RESULTS = {
    OFFLINE_STEPS[0]: "RAG 先检索外部资料，再用资料辅助生成答案。",
    OFFLINE_STEPS[1]: "问题→检索→选取上下文→生成→核对引用。",
    OFFLINE_STEPS[2]: "提纲：为什么需要外部资料；检索与生成怎样配合；引用和权限边界。",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--checkpoint", type=Path, help="把本次状态保存到指定 JSON 文件")
    parser.add_argument("--resume", type=Path, help="从检查点失败步骤继续，不重新规划")
    args = parser.parse_args()
    try:
        print("===== 一：规划范式 =====")
        for name, detail in PLANNING_PARADIGMS.items():
            print(f"[{name}] {detail}")
        print("\n===== 多 Agent 框架与协议速查 =====")
        for name, detail in MULTI_AGENT_FRAMEWORKS.items():
            print(f"[{name}] {detail}")
        print(supervisor_sketch())
        print("\n===== 二：显式计划→逐步执行 =====")
        print("[live] 真实模型" if args.live else "[offline] 脚本化计划与合成结果")
        if args.live:
            plan_fn, execute_fn = make_live_functions()
        else:
            def plan_fn(task: str) -> list[str]:
                return parse_json_plan(json.dumps({"steps": OFFLINE_STEPS}, ensure_ascii=False))

            def execute_fn(task: str, step: str) -> str:
                return OFFLINE_RESULTS[step]
        if args.resume:
            state = load_state(args.resume.read_text(encoding="utf-8"))
        else:
            state = new_state("为一篇介绍 RAG 的科普短文做准备", [])
            try:
                state["plan"] = plan_fn(state["task"])
            except Exception:
                state["error"] = "plan_error"
        print("显式 JSON 计划：", json.dumps(state["plan"], ensure_ascii=False))
        if state["error"] != "plan_error":
            if not args.live and not args.resume:
                def injected_failure(task: str, step: str) -> str:
                    if step == OFFLINE_STEPS[1]:
                        raise RuntimeError("教学故障：第二步失败")
                    return execute_fn(task, step)

                execute_remaining(state, injected_failure)
                print("失败检查点：", json.dumps(state, ensure_ascii=False))
                state = load_state(json.dumps(state, ensure_ascii=False))
                print("恢复：从第二步继续，不重做第一步。")
            execute_remaining(state, execute_fn)
        if args.checkpoint:
            args.checkpoint.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print("最终状态：", state)
        return 1 if state["error"] else 0
    except Exception as exc:
        print(f"规划执行失败：{type(exc).__name__}；请检查 JSON 检查点、common 配置或服务连接。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
