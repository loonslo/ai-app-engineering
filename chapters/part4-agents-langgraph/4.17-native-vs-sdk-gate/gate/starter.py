"""L4.8 原生版与SDK版 · 闭卷骨架。
只读README、本文件及指定SDK官方文档；不允许修改gate_check.py。
运行：python chapters/part4-agents-langgraph/4.17-native-vs-sdk-gate/gate/gate_check.py
"""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict


@dataclass(frozen=True)
class Final:
    text: str


@dataclass(frozen=True)
class Expected:
    final_contains: str | None
    tools_called: tuple[str, ...]
    forbidden_tools: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class Scenario:
    name: str
    user_prompt: str
    model_script: tuple[ToolCall | Final, ...]
    expected: Expected


def run_native(scenario: Scenario, tools: dict, *, max_steps: int) -> dict:
    """用gate的ScriptedChat驱动L4.2原生循环；每项脚本对应一次模型请求。
    tools是{name: callable}；callable.tool_spec是L4.3 ToolSpec，可带requires_approval=True。
    只读callable(**args)，写工具未审批不得执行；错误回传模型；max_steps<1抛ValueError。
    返回status(done/waiting_approval/failed)、final(str)、tools_called(list[str])、steps(int)、errors(list[str])。
    tools_called记录模型尝试调用（含未知、非法参数、待审），steps为实际模型请求数。
    Final('$tool')取最后工具结果（供gate验证输出不是编造）；脚本耗尽后重复末项。
    """
    raise NotImplementedError("实现原生运行适配器")


def run_pydantic_ai(scenario: Scenario, tools: dict, *, max_steps: int) -> dict:
    """同一script转为FunctionModel，真实运行Pydantic AI Agent，不能调用run_native冒充。
    错误、权限与返回结构同run_native；使用DeferredToolRequests阻止未审批写操作；
    UsageLimits限制请求数。可复用L4.3参数验证；未知工具让SDK处理，不注册虚假工具。
    """
    raise NotImplementedError("实现SDK运行适配器")


def evaluate(scenarios: list[Scenario], run_fn: Callable[[Scenario], dict]) -> dict:
    """逐场景调用run_fn一次；检查status、final_contains子串、tools_called有序子序列、
    forbidden_tools不出现；异常计为失败并继续。返回passed名称列表、failed[{name,reason}]、
    pass_rate(0–1，空输入0.0)、runs[{name,...运行结果}]，保留失败轨迹供比较。
    """
    raise NotImplementedError("实现同一套判分")


def compare(native_report: dict, sdk_report: dict) -> dict:
    """返回native_pass_rate、sdk_pass_rate、differences列表；按native runs顺序按name对齐。
    每项{name,steps_delta,tool_calls_delta}，差值均SDK减原生；缺失场景的差值为None。
    """
    raise NotImplementedError("实现指标比较")
