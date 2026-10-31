"""完全离线的闭卷验收；默认starter必须零通过。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(path: Path):
    sys.path.insert(0, str(HERE.parent))
    spec = importlib.util.spec_from_file_location("candidate", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate"] = module
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class Gate:
    def __init__(self) -> None:
        self.rows = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, module_path: Path, gate_name: str) -> int:
        passed = sum(row["ok"] for row in self.rows)
        for row in self.rows:
            print(f"[{'PASS' if row['ok'] else 'FAIL'}] {row['name']} {row['error']}")
        print(f"{passed}/{len(self.rows)} passed")
        report = {"gate": gate_name, "module": str(module_path), "passed": passed, "total": len(self.rows), "ok": passed == len(self.rows), "checks": self.rows}
        (HERE / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    path = Path(parser.parse_args().module).resolve()
    core = load_module(path)
    gate = Gate()
    schema = {"type": "object", "properties": {"order_id": {"type": "string", "description": "订单编号"}, "page": {"type": "integer", "description": "页码"}, "status": {"type": "string", "enum": ["paid", "shipped"], "description": "订单状态"}}, "required": ["order_id"]}
    def spec(**kwargs):
        values = {"name": "get_order", "description": "查询订单状态与金额，仅查询当前租户订单，不执行修改。", "params": schema, "permission": "read"}
        values.update(kwargs)
        return core.ToolSpec(**values)
    def bad_spec(**kwargs):
        expect(bool(core.validate_tool_spec(spec(**kwargs))), "期望返回工具契约问题，实际未报告")
    gate.check("01 合法工具契约", lambda: expect(core.validate_tool_spec(spec()) == [], "合法契约应无问题"))
    gate.check("02 名称不合规", lambda: bad_spec(name="Get-Order"))
    gate.check("03 描述过短", lambda: bad_spec(description="查订单"))
    gate.check("04 参数缺描述", lambda: bad_spec(params={"type": "object", "properties": {"order_id": {"type": "string"}}, "required": []}))
    gate.check("05 写工具缺幂等键", lambda: bad_spec(permission="write"))
    gate.check("06 必填缺失", lambda: expect(bool(core.validate_args(spec(), {})), "缺order_id应报错"))
    gate.check("07 类型错误含bool整数边界", lambda: expect(bool(core.validate_args(spec(), {"order_id": "A100", "page": True})), "bool不应算integer"))
    gate.check("08 enum外取值", lambda: expect(bool(core.validate_args(spec(), {"order_id": "A100", "status": "lost"})), "未知状态应报错"))
    gate.check("09 多余字段", lambda: expect(bool(core.validate_args(spec(), {"order_id": "A100", "tenant_id": "other"})), "多余字段应报错"))
    def permission():
        calls = []
        result = core.execute_tool(spec(), lambda **args: calls.append(args), {"order_id": "A100"}, caller_permissions=set(), idempotency_cache={})
        expect(not result.ok and result.error_kind == "permission_denied" and not calls, f"期望权限拒绝且不执行，实际{result}")
    gate.check("10 权限不足不执行", permission)
    def cached():
        write = spec(permission="write", params={"type": "object", "properties": {"idempotency_key": {"type": "string", "description": "稳定请求键"}}, "required": ["idempotency_key"]})
        cache, calls = {}, []
        def handler(**args):
            calls.append(args)
            return "已创建"
        a = core.execute_tool(write, handler, {"idempotency_key": "k1"}, caller_permissions={"write"}, idempotency_cache=cache)
        denied = core.execute_tool(write, handler, {"idempotency_key": "k1"}, caller_permissions=set(), idempotency_cache=cache)
        b = core.execute_tool(write, handler, {"idempotency_key": "k1"}, caller_permissions={"write"}, idempotency_cache=cache)
        expect(a.ok and not a.from_cache and b.ok and b.from_cache and len(calls) == 1 and denied.error_kind == "permission_denied", "期望只执行一次，缓存不可绕过权限")
    gate.check("11 幂等重复与权限顺序", cached)
    def broken():
        def handler(**args):
            raise ValueError("订单已关闭")
        result = core.execute_tool(spec(), handler, {"order_id": "A100"}, caller_permissions={"read"}, idempotency_cache={})
        expect(result.error_kind == "tool_error" and not result.ok and "建议：" in result.content, f"期望可读tool_error，实际{result}")
    gate.check("12 工具异常转上下文", broken)
    def truncated():
        result = core.execute_tool(spec(max_result_chars=4), lambda **args: "abcdefghij", {"order_id": "A100"}, caller_permissions={"read"}, idempotency_cache={})
        expect(result.content == "abcd（已截断，共 10 字，可用 page 参数翻页）", f"截断内容不符：{result.content}")
    gate.check("13 截断与翻页提示", truncated)
    def selection():
        specs = [spec(name="first_tool", description="shipping order"), spec(name="second_tool", description="refund order"), spec(name="third_tool", description="refund order")]
        expect(core.select_tools("refund order", specs, 2) == ["second_tool", "third_tool"], "期望按重合词排序，同分稳定且最多2个")
        expect(core.select_tools("refund", specs, 0) == [], "limit0应为空")
    gate.check("14 工具筛选排序上限", selection)
    gate.check("15 可读错误固定格式", lambda: expect(core.format_tool_error("invalid_args", "缺编号", "补编号") == "错误：invalid_args；原因：缺编号；建议：补编号", "错误格式不符"))
    def invalid_before_permissions():
        calls = []
        result = core.execute_tool(spec(), lambda **args: calls.append(args), {}, caller_permissions=set(), idempotency_cache={})
        expect(result.error_kind == "invalid_args" and not calls, "参数错误应先于权限拒绝")
        expect(core.validate_args(spec(), {"order_id": "A100", "page": 1, "status": "paid"}) == [], "合法参数应通过")
    gate.check("16 参数校验先于权限且合法参数可用", invalid_before_permissions)
    return gate.report(path, "L4.3-tool-design")


if __name__ == "__main__":
    raise SystemExit(main())
