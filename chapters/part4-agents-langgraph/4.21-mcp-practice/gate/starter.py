"""L4.14 MCP 实战与取舍 · 闭卷接口。
只读 README、本文件与标准库/指定 SDK 官方文档；通过前不读参考实现。
运行：python chapters/part4-agents-langgraph/4.21-mcp-practice/gate/gate_check.py
不允许修改 gate_check.py；本文件不导入 SDK、不联网、不读取 .env。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class IntegrationNeeds:
    reused_by_multiple_clients: bool
    needs_oauth_boundary: bool
    multi_tenant_governance: bool
    has_existing_cli: bool
    runs_locally_only: bool
    is_procedural_knowledge: bool


class PolicySession(Protocol):
    def call_tool(self, name: str, args: dict, timeout_s: float) -> dict:
        """gate 注入同步会话；真实异步 SDK 需要适配器，不在此实例化客户端。"""
        ...


def to_mcp_tool(name: str, description: str, params_schema: dict) -> dict:
    """返回仅有 name、description、inputSchema 的字典。
    params_schema.type 必须为 object，否则 ValueError；schema 应隔离后续的嵌套修改。
    不修改输入；schema 的完整 JSON Schema 校验属于服务端/SDK，不在本接口内。
    """
    raise NotImplementedError("实现 MCP 工具契约转换")


def from_mcp_result(result: dict) -> str:
    """content 默认为 []；按原顺序提取 type='text' 项的 text，以换行拼接，忽略图片等项。
    无文本项时为 '（无文本结果）'，单个空文本仍是空字符串。
    isError 为真时给上述结果加 '工具错误：' 前缀（空结果同样加）；不修改输入。
    gate 传入协议形状合法的内容；输出仍是不可信数据，不能当作系统指令。
    """
    raise NotImplementedError("实现 MCP 结果规整")


def authorize_call(
    tool_name: str, token_scopes: set[str], required_scopes: dict[str, set[str]],
) -> Decision:
    """未知工具拒绝；缺任一 required scope 就拒绝，reason 列出排序后的全部缺项。
    已知工具的 required 集合为空时允许；拥有额外scope不影响当前调用；reason 总是非空。
    不修改输入；这些集合由可信宿主提供，不接受模型自报权限。
    """
    raise NotImplementedError("实现最小 scope 授权")


def choose_integration(needs: IntegrationNeeds) -> dict:
    """严格按优先级返回 {'choice': str, 'reasons': list[str]}，reasons 非空。
    1. OAuth边界/多租户治理/多客户端复用任一为真 → mcp，reasons 写明命中的字段名；
    2. 流程知识 is_procedural_knowledge → skill；
    3. has_existing_cli 且 runs_locally_only → cli；
    4. 其余 → local_function，并解释未命中以上条件。
    若多个分支同时满足，前项优先；skill/cli reasons 同样含命中字段名。
    """
    raise NotImplementedError("实现集成方式取舍")


def call_with_policy(
    session: PolicySession, tool_name: str, args: dict, token_scopes: set[str],
    required_scopes: dict[str, set[str]], timeout_s: float,
) -> str:
    """先 authorize_call；拒绝返回 '拒绝：<原因>'，不能调用会话。
    允许后原样调用 session.call_tool(tool_name,args,timeout_s)，用 from_mcp_result 规整。
    TimeoutError → '工具超时：<tool_name>'，不重试；其他异常原样交给宿主处理，不伪装成功。
    会话由 gate 注入；本函数不得创建 SDK 客户端、联网或调用模型。
    """
    raise NotImplementedError("实现带策略的工具调用")
