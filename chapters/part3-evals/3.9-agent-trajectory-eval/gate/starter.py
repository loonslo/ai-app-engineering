"""L4.7 Agent 轨迹评测 · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
trajectory_eval.py。不允许修改 gate_check.py。实现下面五个函数，然后运行：

    python chapters/part3-evals/3.9-agent-trajectory-eval/gate/gate_check.py
"""

from __future__ import annotations


def extract_tool_names(trajectory: list[dict]) -> list[str]:
    """提取 role="ai" 步骤里的 tool_calls[].name，保持顺序。"""
    raise NotImplementedError("实现工具提取")


def evaluate_trajectory(case: dict, trajectory: list[dict]) -> dict:
    """评测一条轨迹。

    返回至少含：called_tools/expected_ok/forbidden_ok/completed/step_count/
    max_steps_exceeded/tool_call_count/min_calls_met/keyword_score/passed。
    规则：
    - expected_tools 全部出现才算 expected_ok；
    - forbidden_tools 一个都不出现才算 forbidden_ok；
    - 有 role="final" 才算 completed；
    - step_count 只数 role="ai"；tool_call_count 只数有 tool_calls 的 ai 步；
    - step_count > max_steps（缺省 inf）算超限；
    - min_calls_met = tool_call_count >= min_tool_calls（缺省 0）；
    - keyword_score 是 final 内容命中 keywords 的比例，无 keywords 记 1.0；
    - passed 要求 expected/forbidden/completed/未超限/最少调用全满足。
    """
    raise NotImplementedError("实现轨迹评测")


def summarize_trajectories(results: list[dict]) -> dict:
    """汇总通过率、期望工具、禁用工具、完成率；空列表全 0。"""
    raise NotImplementedError("实现轨迹汇总")


def grade_run(outcome_ok: bool, trajectory: list[dict], *, forbidden_tools: set[str], max_steps: int, partial_checks: dict[str, bool]) -> dict:
    """返回 {"score": 0–1保留两位小数, "violations": [违规名]}。

    trajectory 结构沿用上方：仅 role="ai" 算一步；提取其 tool_calls[].name。
    子项通过数/总数给部分分，空 partial_checks 记1；超 max_steps 扣0.2，
    加入 "max_steps"；outcome_ok=False 或调用禁止工具时 score=0，
    后者加入 "forbidden_tool"（先禁用、后超步）；最低0，最高1。
    不要求固定的工具步骤顺序。
    """
    raise NotImplementedError("实现结果优先判分")


def consistency_report(runs: dict[str, list[dict]], k: int) -> dict:
    """runs 为任务到独立试验 grade_run 结果的映射，k<1抛 ValueError。

    返回 {"tasks": {任务: {"pass@1": 0.0或1.0, "pass^k": 0.0或1.0}},
          "overall": {"pass@1": 任务等权均值, "pass^k": 任务等权均值}}。
    pass@1 看该题首次 score==1；pass^k 看前k次是否全部 score==1。
    无试验的任务两项0；不足k次 pass^k 为0；空runs的总体两项0。
    这里是有限样本的经验指标，不是概率估计公式。
    """
    raise NotImplementedError("实现独立试验稳定性汇总")
