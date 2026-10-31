# 任务 C：带安全约束与测试的工具调用 Agent

- **限时**：4 小时（计时开始后不要看参考实现；超时就在时限点提交当时的版本，并在自评里写明未完成项）
- **离线检查器**：见下方“接口约定”；检查器用假模型运行固定用例，**通过检查器只说明接口与基本行为正确，不代表质量好**。

## 需求

实现 `run_agent`：一个**有界**的工具调用循环。每一步由 `decide_fn` 决定“调用某个工具”还是“给出最终回答”。

1. 步数有上限（`max_steps`），超过就停止，状态为 `max_steps`；
2. 只能调用 `tools` 里存在的工具；未知工具、参数不是字典，都不执行，记入 trace，继续下一步；
3. **危险工具**（`dangerous` 里列出的名字）只有在 `approve_fn(name, args)` 返回 `True` 时才执行；没有 `approve_fn` 或返回别的值，就不执行，在 trace 里标记 `blocked`；
4. 工具执行抛异常时，记入 trace（只记异常类名），让下一步的 `decide_fn` 能看到，继续；
5. `decide_fn` 抛异常时返回 `status="error"`，不要把异常抛给调用方；
6. 非危险工具不触发审批。

## 提供的数据

没有外部数据。检查器用脚本化的 `decide_fn` 与假工具（查订单、删除订单、会抛异常的工具）。

## 接口约定（供离线检查器调用）

```python
def run_agent(task: str, tools: dict, decide_fn, *, max_steps: int = 5, approve_fn=None, dangerous=frozenset()) -> dict:
    """decide_fn(task, trace) -> {"tool": 名字, "args": 字典} 或 {"final": 文本}；trace 是此前各步记录的列表。
    返回 {"status": "done" | "max_steps" | "error", "final": str | None, "trace": list[dict]}。
    trace 的每项是 {"tool", "args"}，再加 "result"（成功）、"error"（失败，只记异常类名或 unknown_tool / bad_args）、
    "blocked": True（危险工具未获批准）三者之一。"""
```

运行检查器：

```bash
python chapters/part12-job-track/12.5-take-home-sim/checkers/check_c.py --module path/to/solution_c.py
```

起点文件：`starters/solution_c.py`（空实现）。

## 交付物

- 你的实现文件；
- 一个 **README**：做了什么、怎么运行、安全约束的取舍、已知限制；
- 你自己补的**测试**（至少 3 条，覆盖检查器没有覆盖的情形，例如“危险工具连续被拒绝后模型改用别的办法”）；
- 自评表。

## 评分表（自评用，见 `../templates/self-review.md`）

| 维度 | 看什么 |
|---|---|
| 可运行 | 检查器 7 项全部通过 |
| 安全约束 | 步数上限、审批、未知工具、参数校验 |
| 测试 | 你自己补的用例质量 |
| 可观察性 | trace 是否足以排查一次失败 |
| README | 写明取舍与限制，诚实 |
