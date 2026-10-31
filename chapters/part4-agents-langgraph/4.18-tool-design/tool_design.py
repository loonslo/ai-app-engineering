"""L4.3：订单客服工具契约，默认离线；--live 才请求模型。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    params: dict
    permission: str
    max_result_chars: int = 2000


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    content: str
    error_kind: str | None
    from_cache: bool = False


def validate_tool_spec(spec: ToolSpec) -> list[str]:
    problems = []
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", spec.name):
        problems.append("name 必须是3–64位小写字母/数字/下划线，且字母开头")
    if not 20 <= len(spec.description) <= 1024:
        problems.append("description 长度须为20–1024")
    if spec.permission not in {"read", "write"}:
        problems.append("permission 须为read或write")
    props = spec.params.get("properties", {})
    required = spec.params.get("required", [])
    if spec.params.get("type") != "object":
        problems.append("params.type 须为object")
    for name, prop in props.items():
        if not prop.get("description"):
            problems.append(f"{name} 缺少description")
        if prop.get("type") not in {"string", "integer", "number", "boolean"}:
            problems.append(f"{name} 类型不支持")
    if any(name not in props for name in required):
        problems.append("required 引用了未声明参数")
    if spec.permission == "write" and (
        "idempotency_key" not in required or props.get("idempotency_key", {}).get("type") != "string"
    ):
        problems.append("write 必须有必填string idempotency_key")
    if type(spec.max_result_chars) is not int or spec.max_result_chars < 1:
        problems.append("max_result_chars 须为正整数")
    return problems


def validate_args(spec: ToolSpec, args: dict) -> list[str]:
    if not isinstance(args, dict):
        return ["参数须为object"]
    props = spec.params.get("properties", {})
    problems = [f"缺少必填参数 {key}" for key in spec.params.get("required", []) if key not in args]
    types = {"string": (str,), "integer": (int,), "number": (int, float), "boolean": (bool,)}
    for key, value in args.items():
        if key not in props:
            problems.append(f"未声明参数 {key}")
            continue
        prop = props[key]
        if type(value) not in types.get(prop.get("type"), ()):
            problems.append(f"{key} 类型须为 {prop.get('type')}")
        elif "enum" in prop and value not in prop["enum"]:
            problems.append(f"{key} 须取 {prop['enum']}")
    return problems


def format_tool_error(kind: str, detail: str, hint: str) -> str:
    return f"错误：{kind}；原因：{detail}；建议：{hint}"


def execute_tool(spec: ToolSpec, fn: Callable, args: dict, *, caller_permissions: set[str], idempotency_cache: dict[str, ToolResult]) -> ToolResult:
    problems = validate_args(spec, args)
    if problems:
        return ToolResult(False, format_tool_error("invalid_args", "、".join(problems), "按工具schema补齐或修正参数"), "invalid_args")
    if spec.permission not in caller_permissions:
        return ToolResult(False, format_tool_error("permission_denied", "缺少执行权限", "请有权限的用户确认后重试"), "permission_denied")
    key = args.get("idempotency_key")
    if spec.permission == "write" and key in idempotency_cache:
        return replace(idempotency_cache[key], from_cache=True)
    try:
        content = str(fn(**args))
    except Exception as exc:
        return ToolResult(False, format_tool_error("tool_error", str(exc), "核对业务条件后重试"), "tool_error")
    if len(content) > spec.max_result_chars:
        content = content[:spec.max_result_chars] + f"（已截断，共 {len(content)} 字，可用 page 参数翻页）"
    result = ToolResult(True, content, None)
    if spec.permission == "write":
        idempotency_cache[key] = result
    return result


def select_tools(task: str, specs: list[ToolSpec], limit: int) -> list[str]:
    def words(text: str) -> set[str]:
        return set(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text.lower()))
    query = words(task)
    ordered = sorted(specs, key=lambda spec: -len(query & words(spec.description)))
    return [spec.name for spec in ordered[:max(0, limit)]]


def order_tools(tenant_id: str = "shop_a") -> tuple[list[ToolSpec], dict, list]:
    """身份在宿主注入，不允许模型提交tenant_id。每次演示得到新订单、退款和缓存。"""
    orders = {"shop_a": {"A100": {"status": "shipped", "amount": 80}, "A101": {"status": "paid", "amount": 20}},
              "shop_b": {"B200": {"status": "paid", "amount": 90}}}
    refunds = []
    def get_order(order_id: str) -> str:
        if not re.fullmatch(r"[A-Z][0-9]{3}", order_id):
            raise ValueError("order_id 格式应为A100这样的字母加三位数字")
        order = orders.get(tenant_id, {}).get(order_id)
        return f"{order_id}: {order}" if order else "未找到订单"
    def list_orders(page: int = 1, status: str = "all") -> str:
        if page < 1:
            raise ValueError("page 从1开始")
        rows = [(key, value) for key, value in orders.get(tenant_id, {}).items() if status == "all" or value["status"] == status]
        start = (page - 1) * 1
        return json.dumps({"orders": rows[start:start + 1], "page": page, "next_page": page + 1 if start + 1 < len(rows) else None}, ensure_ascii=False)
    def create_refund_request(order_id: str, idempotency_key: str) -> str:
        if order_id not in orders.get(tenant_id, {}):
            raise ValueError("当前租户下未找到订单")
        if not idempotency_key.strip():
            raise ValueError("idempotency_key 不可为空")
        refunds.append({"order_id": order_id, "idempotency_key": idempotency_key})
        return "退款申请已创建（不是已退款）"
    order_arg = {"type": "string", "description": "订单编号，格式为A100这样的字母加三位数字"}
    specs = [
        ToolSpec("get_order", "查询当前租户的一笔订单状态与金额；不修改订单，也不查询其他租户。", {"type": "object", "properties": {"order_id": order_arg}, "required": ["order_id"]}, "read"),
        ToolSpec("list_orders", "分页列出当前租户订单，可按状态筛选；page从1开始，每页一条。", {"type": "object", "properties": {"page": {"type": "integer", "description": "页码，从1开始"}, "status": {"type": "string", "enum": ["all", "paid", "shipped"], "description": "只返回该状态的订单，all为全部"}}, "required": []}, "read"),
        ToolSpec("create_refund_request", "创建退款申请而非直接退款；需要用户确认与写权限，相同请求必须复用幂等键。", {"type": "object", "properties": {"order_id": order_arg, "idempotency_key": {"type": "string", "description": "本次退款申请的稳定唯一键，重试时保持不变"}}, "required": ["order_id", "idempotency_key"]}, "write"),
    ]
    return specs, {"get_order": get_order, "list_orders": list_orders, "create_refund_request": create_refund_request}, refunds


def demo(live: bool = False) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "4.5-react-agent"))
    from react_agent import ScriptedChat, ToolReply, make_live_chat, run_loop, tool_message
    specs, handlers, refunds = order_tools()
    caches = {spec.name: {} for spec in specs}
    def adapter(spec: ToolSpec) -> Callable:
        def call(**args):
            if spec.permission == "write":
                return ToolReply("退款申请需要用户确认", waiting_approval=True)
            result = execute_tool(spec, handlers[spec.name], args, caller_permissions={"read"}, idempotency_cache=caches[spec.name])
            return ToolReply(result.content, error=result.error_kind)
        return call
    schemas = [{"type": "function", "function": {"name": spec.name, "description": spec.description, "parameters": spec.params}} for spec in specs]
    chat = make_live_chat(schemas) if live else ScriptedChat([
        tool_message("get_order", {"order_id": "A100"}),
        tool_message("list_orders", {"page": 1, "status": "all"}),
        tool_message("create_refund_request", {"order_id": "A100", "idempotency_key": "refund-A100"}),
    ])
    result = run_loop("查询A100，列出订单，然后申请退款；写操作先等我确认。", chat, {spec.name: adapter(spec) for spec in specs}, max_steps=6)
    print("真实模型" if live else "离线脚本", json.dumps(result, ensure_ascii=False, default=str, indent=2))
    print("筛选：", select_tools("分页 订单 状态", specs, 2), "实际退款申请：", refunds)
    # 审批后的执行与重复重试，直接展示幂等契约，不自动替用户审批。
    write_spec = specs[-1]
    args = {"order_id": "A100", "idempotency_key": "confirmed-A100"}
    for _ in range(2):
        print("独立的已确认调用示例：", execute_tool(write_spec, handlers[write_spec.name], args, caller_permissions={"write"}, idempotency_cache=caches[write_spec.name]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    try:
        result = demo(args.live)
    except Exception as exc:
        print(f"运行失败：{type(exc).__name__}；请检查 common 的模型配置、密钥与服务连接。", file=sys.stderr)
        return 1
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
