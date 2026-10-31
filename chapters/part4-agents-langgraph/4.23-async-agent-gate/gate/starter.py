"""L4.17 异步专项 Agent · 闭卷骨架。
只读README、本文件、L4.11/L4.12公开接口与标准库文档；不允许修改gate_check.py。
运行：python chapters/part4-agents-langgraph/4.23-async-agent-gate/gate/gate_check.py
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from execution_plane import Task


def build_stages(agent_step, policy, tools) -> list:
    """返回L4.11 Stage列表，名称顺序plan/gather/draft/approve/publish。
    plan与draft调用agent_step(stage_name,task)，只接受L4.11 StageOutput；其他值（如工具请求）
    记录policy['audit']中allowed=False、stage、reason，并抛PermissionError，阻止越阶段执行。
    gather调用agent_step('gather',task)，得到{'tool':str,'args':dict}；只允许policy['read_tools']
    中且tools存在的工具，然后对policy['tool_commands'][name]（缺省[]）调用L4.12 check_command，
    每次决策追加audit记录（stage/tool/allowed/reason）。拒绝抛PermissionError且不能调用工具。
    允许后调用tools[name](**args)，TimeoutError转L4.11 RetryableError；输出用html.escape转义后
    包装为<untrusted_document>...</untrusted_document>，返回StageOutput(text,0)。
    工具由可信应用提供，read_tools中的handler必须只读、绑定固定资料；command映射是可信元数据，
    不是让模型选择真实shell命令。此协议不接受模型提供新的可执行程序。
    approve阶段needs_approval=True，返回StageOutput('人工已批准',0)，不由模型生成批准。
    publish阶段side_effect=True，只调用tools['publish'](task)；返回StageOutput直接复用，其他值转str并令tokens=0。
    policy是dict：read_tools frozenset、command_policy L4.12 CommandPolicy、tool_commands dict、audit list。
    正常阶段max_attempts=2；gather本身只读，不标为副作用，但成功游标确保续跑不重复。
    """
    raise NotImplementedError("实现受控阶段组合")


def run_e2e(store, task_id: str, stages: list, *, clock, side_effect_log: dict) -> "Task":
    """调用L4.11 run_until_blocked；waiting_approval直接返回，不能自动批准。
    进程退出模拟BaseException应传播，调用方重开状态存储后再次调用。
    """
    raise NotImplementedError("实现端到端推进")


def run_trials(task_factory, k: int) -> dict:
    """k<1抛ValueError。每次调用无参数task_factory()获得一个L4.11 Task，工厂必须新建store/替身。
    返回{'pass_at_1':成功次数/k,'pass_all_k':全部成功时1.0否则0.0,
    'runs':[{'run':从1开始的序号,'status':task.status,'passed':status=='succeeded'},...]}。
    这里pass_at_1为独立单次试验的经验成功率；pass_all_k是一组k次全部成功的指示值，非概率估计p**k。
    """
    raise NotImplementedError("实现独立重复统计")
