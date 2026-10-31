"""L4.17：阶段内注入 Agent，阶段外强制权限、预算与审批。"""
from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "4.19-agent-execution-plane"))
sys.path.insert(0, str(HERE.parent / "4.20-sandbox-least-privilege"))

from execution_plane import (  # noqa: E402
    Budget, RetryableError, SQLiteEffects, SQLiteStore, Stage, StageOutput, Task,
    approve, run_until_blocked, submit,
)
from sandbox_policy import check_command  # noqa: E402


def build_stages(agent_step, policy, tools) -> list[Stage]:
    """policy含read_tools、command_policy、tool_commands与audit；详见starter。"""
    def reject(stage, reason):
        policy["audit"].append({"stage": stage, "allowed": False, "reason": reason})
        raise PermissionError(reason)

    def model_stage(name):
        def execute(task):
            result = agent_step(name, task)
            if not isinstance(result, StageOutput):
                reject(name, "模型输出只能是阶段摘要，不能调用工具或提前发布")
            return result
        return execute

    def gather(task):
        request = agent_step("gather", task)
        name = request.get("tool", "")
        if name not in policy["read_tools"] or name not in tools:
            reject("gather", f"禁止工具：{name}")
        argv = policy["tool_commands"].get(name, [])
        decision = check_command(argv, policy["command_policy"])
        policy["audit"].append({"stage": "gather", "tool": name, "allowed": decision.allowed,
                                "reason": decision.reason})
        if not decision.allowed:
            raise PermissionError(decision.reason)
        try:
            text = tools[name](**request.get("args", {}))
        except TimeoutError as exc:
            raise RetryableError("只读资料工具超时") from exc
        # 包装是数据边界提示，不是授权；真正授权发生在上方的模型外策略。
        return StageOutput("<untrusted_document>" + html.escape(str(text)) + "</untrusted_document>", 0)

    def publish(task):
        # 不给模型publish函数；由可信阶段推进器在审批后单独调用。
        output = tools["publish"](task)
        return output if isinstance(output, StageOutput) else StageOutput(str(output), 0)

    return [Stage("plan", model_stage("plan")), Stage("gather", gather),
            Stage("draft", model_stage("draft")),
            Stage("approve", lambda task: StageOutput("人工已批准", 0), needs_approval=True),
            Stage("publish", publish, side_effect=True)]


def run_e2e(store, task_id: str, stages: list, *, clock, side_effect_log: dict) -> Task:
    return run_until_blocked(store, task_id, stages, clock=clock, side_effect_log=side_effect_log)


def run_trials(task_factory, k: int) -> dict:
    if k < 1:
        raise ValueError("k 必须至少为1")
    runs = []
    for index in range(k):
        task = task_factory()
        passed = task.status == "succeeded"
        runs.append({"run": index + 1, "status": task.status, "passed": passed})
    return {"pass_at_1": sum(run["passed"] for run in runs) / k,
            "pass_all_k": float(all(run["passed"] for run in runs)), "runs": runs}


def demo_agent_step():
    """复用 L4.5 的 SDK 层：FunctionModel 替代模型，结构化输出校验仍真实执行。"""
    from pydantic import BaseModel
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelResponse, ToolCallPart, UserPromptPart
    from pydantic_ai.models.function import FunctionModel

    class Decision(BaseModel):
        output: str
        tokens: int
        tool: str = ""

    def respond(messages, info):
        prompt = next(part.content for part in messages[-1].parts if isinstance(part, UserPromptPart))
        stage, _, context = prompt.partition("\n")
        if stage == "gather":
            decision = Decision(output="", tokens=0, tool="read_notes")
        else:
            decision = Decision(output=("报告依据：" + context) if stage == "draft" else "计划：读取固定资料并形成报告",
                                tokens=8 if stage == "draft" else 4)
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, decision.model_dump())])

    agent = Agent(FunctionModel(respond), output_type=Decision)
    agent.instrument = False

    def step(stage, task):
        context = "\n".join(record.output for record in task.steps if record.stage == "gather" and record.ok)
        decision = agent.run_sync(stage + "\n" + context).output
        if stage == "gather":
            return {"tool": decision.tool, "args": {}}
        return StageOutput(decision.output, decision.tokens)

    return step


def demo_trial() -> Task:
    from sandbox_policy import CommandPolicy

    with tempfile.TemporaryDirectory(prefix="async-agent-") as directory:
        store = SQLiteStore(Path(directory) / "tasks.sqlite")
        task_id = submit(store, "t1", {"topic": "异步调研"}, "demo", Budget(12, 100, 1000))
        policy = {"read_tools": frozenset({"read_notes"}),
                  "command_policy": CommandPolicy(frozenset({"reader"}), frozenset()),
                  "tool_commands": {"read_notes": ["reader", "notes.txt"]}, "audit": []}

        agent_step = demo_agent_step()

        published = []
        tools = {"read_notes": lambda: "步骤落盘、可信审批与业务幂等键",
                 "publish": lambda task: published.append(task.id) or "已写本地演示账本"}
        stages, effects = build_stages(agent_step, policy, tools), SQLiteEffects(store)
        task = run_e2e(store, task_id, stages, clock=lambda: 0, side_effect_log=effects)
        if task.status == "waiting_approval":
            approve(store, task_id, "approve", True)
            task = run_e2e(store, task_id, stages, clock=lambda: 0, side_effect_log=effects)
        store.close()
        return task


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=HERE / "reports" / "offline_pass3.json")
    args = parser.parse_args()
    report = {"mode": "offline-scripted", "k": 3, "evidence_scope": "执行面与策略规则，不代表真实模型稳定性",
              **run_trials(demo_trial, 3)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("离线报告：", args.report)
    return 0 if report["pass_all_k"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
