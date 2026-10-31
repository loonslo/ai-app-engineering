"""L4.14：工具契约与最小 scope；默认运行实际 MCP SDK 的进程内会话，不联网。"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
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
    def call_tool(self, name: str, args: dict, timeout_s: float) -> dict: ...


def to_mcp_tool(name: str, description: str, params_schema: dict) -> dict:
    """只做协议形状转换；复制 schema，避免调用方后续修改影响契约。"""
    if params_schema.get("type") != "object":
        raise ValueError("MCP inputSchema.type 必须为 object")
    return {"name": name, "description": description, "inputSchema": copy.deepcopy(params_schema)}


def from_mcp_result(result: dict) -> str:
    """只提取文本；规整不代表信任内容，也不能把它当作系统指令。"""
    texts = [item["text"] for item in result.get("content", []) if item.get("type") == "text"]
    content = "\n".join(texts) if texts else "（无文本结果）"
    return ("工具错误：" if result.get("isError", False) else "") + content


def authorize_call(
    tool_name: str, token_scopes: set[str], required_scopes: dict[str, set[str]],
) -> Decision:
    """未知工具默认拒绝；missing 排序保证报告稳定。身份与scope由可信宿主提供。"""
    if tool_name not in required_scopes:
        return Decision(False, f"未知工具：{tool_name}")
    missing = required_scopes[tool_name] - token_scopes
    if missing:
        return Decision(False, "缺少 scope：" + ", ".join(sorted(missing)))
    return Decision(True, "已具备全部所需 scope")


def choose_integration(needs: IntegrationNeeds) -> dict:
    """依规格顺序选择，不把 MCP 用作默认包装。"""
    mcp_conditions = [
        name for name in ("needs_oauth_boundary", "multi_tenant_governance", "reused_by_multiple_clients")
        if getattr(needs, name)
    ]
    if mcp_conditions:
        return {"choice": "mcp", "reasons": mcp_conditions}
    if needs.is_procedural_knowledge:
        return {"choice": "skill", "reasons": ["is_procedural_knowledge"]}
    if needs.has_existing_cli and needs.runs_locally_only:
        return {"choice": "cli", "reasons": ["has_existing_cli", "runs_locally_only"]}
    return {"choice": "local_function", "reasons": ["无需跨客户端、OAuth边界或多租户治理，且未命中Skill/本地CLI条件"]}


def call_with_policy(
    session: PolicySession, tool_name: str, args: dict, token_scopes: set[str],
    required_scopes: dict[str, set[str]], timeout_s: float,
) -> str:
    """授权必须先于执行；超时只报告，不自动重试可能具有副作用的工具。"""
    decision = authorize_call(tool_name, token_scopes, required_scopes)
    if not decision.allowed:
        return f"拒绝：{decision.reason}"
    try:
        result = session.call_tool(tool_name, args, timeout_s)
    except TimeoutError:
        return f"工具超时：{tool_name}"
    return from_mcp_result(result)


async def sdk_demo() -> dict:
    """返回实际 SDK 工具、契约与三次策略调用结果，便于离线回归直接 await。"""
    # SDK 依赖仅在参考演示导入；闭卷函数及 gate 不依赖 SDK。
    import anyio
    from mcp.server.fastmcp import FastMCP
    from mcp.shared.memory import create_connected_server_and_client_session

    server = FastMCP("offline-order-tools")

    @server.tool()
    def add(a: int, b: int) -> str:
        """两个整数相加；无文件、网络或数据库副作用。"""
        return str(a + b)

    @server.tool()
    def order_status(order_id: str) -> str:
        """只查询合成订单状态，不访问真实客户数据。"""
        orders = {"A100": "已发货", "A101": "待支付"}
        if order_id not in orders:
            raise ValueError("合成订单不存在")
        return orders[order_id]

    async with create_connected_server_and_client_session(server) as session:
        listing = await session.list_tools()
        report = {
            "tools": [item.name for item in listing.tools],
            "contracts": [
                to_mcp_tool(item.name, item.description or "", item.inputSchema)
                for item in listing.tools
            ],
            "calls": [],
        }

        class SDKSessionAdapter:
            """从 AnyIO 工作线程回到会话事件循环；不是伪造的 SDK 结果。"""
            async def _call(self, name: str, args: dict, timeout_s: float) -> dict:
                with anyio.fail_after(timeout_s):
                    result = await session.call_tool(name, args)
                return result.model_dump(by_alias=True, mode="json")

            def call_tool(self, name: str, args: dict, timeout_s: float) -> dict:
                return anyio.from_thread.run(self._call, name, args, timeout_s)

        adapter = SDKSessionAdapter()
        required = {"add": {"math:read"}, "order_status": {"orders:read"}}
        examples = [
            ("add", {"a": 2, "b": 3}, {"math:read"}),
            ("order_status", {"order_id": "A100"}, {"orders:read"}),
            ("order_status", {"order_id": "A100"}, set()),
        ]
        for name, arguments, scopes in examples:
            # 不在当前事件循环中阻塞等自己；所有 SDK I/O 仍由原会话事件循环管理。
            result = await anyio.to_thread.run_sync(
                lambda: call_with_policy(adapter, name, arguments, scopes, required, 2.0)
            )
            report["calls"].append({"name": name, "content": result})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        print(f"MCP SDK {version('mcp')}；进程内内存传输；不调用模型、不开端口。")
        report = asyncio.run(sdk_demo())
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (ImportError, PackageNotFoundError):
        print("当前环境缺少 MCP SDK 或进程内会话 API；请使用课程锁定环境（源码核对版本 1.29.1）。")
        return 1
    except Exception as exc:
        print(f"MCP 离线演示未完成：{type(exc).__name__}；请核对 SDK 版本与会话配置。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
