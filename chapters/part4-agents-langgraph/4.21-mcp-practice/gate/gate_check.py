"""L4.14：脚本化会话验证协议边界与取舍，不导入真实客户端或联网。"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    if spec is None or spec.loader is None:
        raise ValueError("无法加载候选模块")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate"] = module
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class Gate:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, path: Path) -> int:
        passed = sum(row["ok"] for row in self.rows)
        for row in self.rows:
            print(f"[{'PASS' if row['ok'] else 'FAIL'}] {row['name']} {row['error']}")
        print(f"{passed}/{len(self.rows)} passed")
        report = {"gate": "L4.14-mcp-practice", "module": str(path), "passed": passed,
                  "total": len(self.rows), "ok": passed == len(self.rows), "checks": self.rows}
        (HERE / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if report["ok"] else 1


class ScriptedSession:
    def __init__(self, result: dict | None = None, error: Exception | None = None) -> None:
        self.result = result if result is not None else {"content": [{"type": "text", "text": "已发货"}]}
        self.error = error
        self.calls: list[tuple] = []

    def call_tool(self, name: str, args: dict, timeout_s: float) -> dict:
        self.calls.append((name, args, timeout_s))
        if self.error is not None:
            raise self.error
        return self.result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    path = Path(parser.parse_args().module).resolve()
    core = load_module(path)
    gate = Gate()
    required = {"order_status": {"orders:read", "tenant:current"}, "public": set()}

    def contract():
        schema = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
        result = core.to_mcp_tool("order_status", "查询合成订单", schema)
        expect(result == {"name": "order_status", "description": "查询合成订单", "inputSchema": schema}, f"期望协议三字段，实际 {result}")
        schema["properties"]["id"]["type"] = "integer"
        expect(result["inputSchema"]["properties"]["id"]["type"] == "string", "嵌套 schema 应隔离调用方后续修改")

    gate.check("01 工具契约转换与嵌套隔离", contract)

    def invalid_schema():
        for schema in [{"type": "array"}, {"properties": {}}]:
            try:
                core.to_mcp_tool("bad", "错误契约", schema)
            except ValueError:
                continue
            raise AssertionError(f"期望非object schema抛ValueError，实际接受 {schema}")

    gate.check("02 非object schema报错", invalid_schema)
    gate.check("03 多文本拼接忽略非文本", lambda: expect(core.from_mcp_result({"content": [
        {"type": "text", "text": "第一段"}, {"type": "image", "data": "synthetic", "mimeType": "image/png"},
        {"type": "text", "text": "第二段"}]}) == "第一段\n第二段", "期望按原顺序换行拼接文本"))
    gate.check("04 工具错误前缀", lambda: expect(core.from_mcp_result({"isError": True, "content": [{"type": "text", "text": "缺编号"}]}) == "工具错误：缺编号", "期望工具错误中文前缀"))
    gate.check("05 无文本与错误空结果", lambda: expect(core.from_mcp_result({}) == "（无文本结果）" and core.from_mcp_result({"isError": True, "content": []}) == "工具错误：（无文本结果）", "期望无文本占位及错误前缀"))
    gate.check("06 空文本不等于没有文本项", lambda: expect(core.from_mcp_result({"content": [{"type": "text", "text": ""}]}) == "", "单个空文本应保留空字符串"))
    gate.check("07 未知工具默认拒绝", lambda: expect(not core.authorize_call("hidden", {"admin"}, required).allowed, "未知工具即使有admin仍应拒绝"))

    def missing():
        decision = core.authorize_call("order_status", set(), required)
        expect(not decision.allowed and "orders:read" in decision.reason and "tenant:current" in decision.reason, f"期望列出所有缺项，实际 {decision}")
        expect(decision.reason.index("orders:read") < decision.reason.index("tenant:current"), "缺项原因应排序稳定")

    gate.check("08 缺少scope拒绝并列全部缺项", missing)
    gate.check("09 具备全部scope与公开工具", lambda: expect(core.authorize_call("order_status", {"orders:read", "tenant:current", "extra"}, required).allowed and core.authorize_call("public", set(), required).allowed, "全部所需权限/空所需权限应允许"))

    def choose(expected, **values):
        fields = dict(reused_by_multiple_clients=False, needs_oauth_boundary=False,
                      multi_tenant_governance=False, has_existing_cli=False,
                      runs_locally_only=False, is_procedural_knowledge=False)
        fields.update(values)
        result = core.choose_integration(core.IntegrationNeeds(**fields))
        expect(result["choice"] == expected and isinstance(result["reasons"], list) and bool(result["reasons"]), f"期望 {expected} 与非空理由列表，实际 {result}")
        return result

    def mcp():
        for field in ["reused_by_multiple_clients", "needs_oauth_boundary", "multi_tenant_governance"]:
            result = choose("mcp", **{field: True})
            expect(field in " ".join(result["reasons"]), f"理由应指出命中 {field}")
        choose("mcp", needs_oauth_boundary=True, is_procedural_knowledge=True, has_existing_cli=True, runs_locally_only=True)

    gate.check("10 MCP三个触发条件与优先级", mcp)
    gate.check("11 Skill优先于CLI", lambda: choose("skill", is_procedural_knowledge=True, has_existing_cli=True, runs_locally_only=True))
    gate.check("12 现成且本地CLI", lambda: choose("cli", has_existing_cli=True, runs_locally_only=True))
    gate.check("13 本地函数与非本地CLI边界", lambda: [choose("local_function"), choose("local_function", has_existing_cli=True, runs_locally_only=False)])

    def successful_call():
        session = ScriptedSession()
        arguments = {"order_id": "A100"}
        result = core.call_with_policy(session, "order_status", arguments, {"orders:read", "tenant:current"}, required, 0.25)
        expect(result == "已发货" and session.calls == [("order_status", arguments, 0.25)], f"期望原样传参/超时且只调用一次，实际 {result}/{session.calls}")

    gate.check("14 授权后调用传参并规整", successful_call)

    def denied_call():
        session = ScriptedSession()
        for name in ["order_status", "unknown"]:
            result = core.call_with_policy(session, name, {}, set(), required, 1.0)
            expect(result.startswith("拒绝：") and len(result) > 3, f"期望可读拒绝，实际 {result}")
        expect(session.calls == [], "授权失败不得调用session")

    gate.check("15 拒绝时不调用会话", denied_call)

    def timeout():
        session = ScriptedSession(error=TimeoutError("scripted"))
        result = core.call_with_policy(session, "public", {}, set(), required, 0.01)
        expect(result == "工具超时：public" and len(session.calls) == 1, f"期望可读超时且不重试，实际 {result}")

    gate.check("16 调用超时且不自动重试", timeout)

    def tool_error():
        payload = {"isError": True, "content": [{"type": "text", "text": "订单不存在"}]}
        snapshot = copy.deepcopy(payload)
        result = core.call_with_policy(ScriptedSession(payload), "public", {}, set(), required, 1.0)
        expect(result == "工具错误：订单不存在" and payload == snapshot, "错误结果必须规整且不能修改原始数据")

    gate.check("17 会话工具错误与输入不变", tool_error)

    def unexpected_error():
        session = ScriptedSession(error=RuntimeError("scripted failure"))
        try:
            core.call_with_policy(session, "public", {}, set(), required, 1.0)
        except RuntimeError:
            expect(len(session.calls) == 1, "非超时异常不重试")
        else:
            raise AssertionError("非超时异常不得伪装成成功或超时")

    gate.check("18 非超时异常保留宿主处理", unexpected_error)
    return gate.report(path)


if __name__ == "__main__":
    raise SystemExit(main())
