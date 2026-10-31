"""五种 workflow 与自主循环：离线脚本化模型，只观察控制权与停止条件。"""

from __future__ import annotations

from collections import Counter
from typing import Callable


def fixed_workflow(a: int, b: int) -> int:
    """固定路径：校验，再相加；bool 不是本练习允许的整数。"""
    if type(a) is not int or type(b) is not int:
        raise ValueError("输入必须是整数")
    return a + b


def prompt_chain(text: str, steps: list[Callable[[str], str]]) -> str:
    """提示链：上一阶段的输出就是下一阶段的输入。"""
    for step in steps:
        text = step(text)
    return text


def route(query: str, classify_fn: Callable, routes: dict[str, Callable], default: str) -> tuple[str, str]:
    if default not in routes:
        raise ValueError("默认路由不存在")
    try:
        label = classify_fn(query)
    except Exception:
        label = default
    if label not in routes:
        label = default
    return label, routes[label](query)


def parallel_vote(workers: list[Callable[[], str]], min_success: int) -> dict:
    """本章顺序模拟并行分支；4.14 再观察真正并行与上下文隔离。"""
    answers, failures = [], []
    for index, worker in enumerate(workers):
        try:
            answers.append(worker())
        except Exception as exc:
            failures.append({"worker": index, "error": str(exc)})
    counts = Counter(answers)
    majority = max(answers, key=counts.get) if answers else None
    return {"ok": len(answers) >= min_success, "answers": answers, "failures": failures, "majority": majority}


def orchestrator_workers(task: str, plan_fn: Callable, worker_fn: Callable) -> list[dict]:
    """任务由编排者按输入拆分，而非预先固定分支数；合并时保留子任务。"""
    return [{"task": part, "result": worker_fn(part)} for part in plan_fn(task)]


def evaluator_optimizer(generate_fn: Callable, evaluate_fn: Callable, *, max_rounds: int) -> dict:
    if max_rounds < 1:
        raise ValueError("max_rounds 必须大于 0")
    feedback, history = None, []
    for round_number in range(1, max_rounds + 1):
        draft = generate_fn(feedback)
        passed, feedback = evaluate_fn(draft)
        history.append({"draft": draft, "passed": passed, "feedback": feedback})
        if passed:
            break
    return {"passed": passed, "rounds": round_number, "draft": draft, "history": history}


def scripted_planner(state: dict) -> dict:
    return {"action": "finish" if state["observations"] else "add", "a": 2, "b": 3}


def initial_state() -> dict:
    return {"question": "计算2加3", "steps": 0, "observations": [],
            "decision": {"action": "finish", "a": 0, "b": 0}, "status": "running", "error": ""}


def run_agent(state: dict, planner: Callable | None = None, *, max_steps: int = 2) -> dict:
    """自主循环：规划器看观察决定下一步；代码掌握白名单、预算和失败出口。"""
    if max_steps < 1:
        raise ValueError("max_steps 必须大于 0")
    planner = planner or scripted_planner
    state = {**state, "observations": list(state["observations"])}
    while state["status"] == "running":
        try:
            choice = planner(state)
        except (ValueError, TimeoutError) as exc:
            state.update(status="failed", error=str(exc))
            break
        state["decision"] = choice
        if choice.get("action") == "finish":
            state["status"] = "done"
        elif choice.get("action") != "add":
            state.update(status="failed", error="工具不在白名单")
        elif state["steps"] >= max_steps:
            state.update(status="failed", error="工具步数预算耗尽")
        else:
            state["steps"] += 1
            try:
                value = fixed_workflow(choice.get("a"), choice.get("b"))
            except ValueError as exc:
                state.update(status="failed", error=str(exc))
            else:
                state["observations"].append(value)
    return state


def main() -> int:
    print("[offline] 脚本化模型，不衡量真实模型能力")
    print("固定工作流：", fixed_workflow(2, 3))
    print("提示链：", prompt_chain("订单", [lambda x: x + "摘要", lambda x: x + "已审核"]))
    print("路由：", route("订单", lambda _: "orders", {"orders": lambda x: x + "查询"}, "orders"))
    print("并行投票：", parallel_vote([lambda: "通过", lambda: "通过", lambda: "复核"], 2))
    print("编排者-执行者：", orchestrator_workers("订单与物流", lambda _: ["订单", "物流"], lambda x: x + "完成"))
    print("评估者-优化者：", evaluator_optimizer(
        lambda feedback: "初稿" if feedback is None else "含证据的稿件",
        lambda draft: ("证据" in draft, "补证据"), max_rounds=2))
    for name, planner in (("正常循环", None), ("预算耗尽", lambda _: {"action": "add", "a": 2, "b": 3})):
        result = run_agent(initial_state(), planner)
        print(name, result["status"], result["observations"], result["error"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
