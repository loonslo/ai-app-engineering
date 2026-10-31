"""L4.12：只检查计算结果；不执行命令、联网或创建符号链接。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
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
        report = {"gate": "L4.12-sandbox-least-privilege", "module": str(path), "passed": passed,
                  "total": len(self.rows), "ok": passed == len(self.rows), "checks": self.rows}
        (HERE / "gate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    path = Path(parser.parse_args().module).resolve()
    core = load_module(path)
    gate = Gate()
    root = os.path.abspath(os.path.join("virtual", "workspace"))
    outside = os.path.abspath(os.path.join("virtual", "outside", "secret.txt"))
    hosts = frozenset({"example.com"})

    def violation(fn, kind="path_escape"):
        try:
            fn()
        except core.PolicyViolation as exc:
            expect(exc.kind == kind, f"期望 {kind}，实际 {exc.kind}")
        else:
            raise AssertionError(f"期望抛出 PolicyViolation({kind})，实际未拒绝")

    def egress(url, allowed):
        decision = core.check_egress(url, hosts)
        expect(decision.allowed is allowed and bool(decision.reason), f"期望 allowed={allowed} 且有原因，实际 {decision}")

    programs = frozenset({"cat", "rm", "sudo", "chmod", "curl", "wget", "bash"})

    def command(argv, allowed):
        decision = core.check_command(argv, core.CommandPolicy(programs, hosts))
        expect(decision.allowed is allowed and bool(decision.reason), f"期望 allowed={allowed}，实际 {decision}")

    gate.check("01 点点路径越界", lambda: violation(lambda: core.resolve_in_workspace("../outside/secret.txt", root)))
    gate.check("02 绝对路径越界", lambda: violation(lambda: core.resolve_in_workspace(outside, root)))

    def symlink():
        link = os.path.join(root, "link", "secret.txt")
        calls = []

        def realpath(value):
            calls.append(value)
            return outside if value == link else os.path.abspath(value)

        violation(lambda: core.resolve_in_workspace("link/secret.txt", root, realpath))
        expect(root in calls and link in calls, "期望根目录与目标都经过注入的 realpath")

    gate.check("03 模拟符号链接越界", symlink)
    gate.check("04 内部路径与根目录通过", lambda: expect(
        core.resolve_in_workspace("docs/../report.txt", root) == os.path.join(root, "report.txt")
        and core.resolve_in_workspace(".", root) == root, "期望规范化到工作目录内"))
    gate.check("05 相似字符串前缀不能越界", lambda: violation(lambda: core.resolve_in_workspace(root + "-other/file.txt", root)))
    gate.check("06 HTTP与file被拒", lambda: [egress(url, False) for url in ["http://example.com", "file:///etc/passwd"]])
    gate.check("07 白名单与合法子域", lambda: [egress(url, True) for url in ["https://example.com/a", "https://DOCS.Example.com./a"]])
    gate.check("08 伪子域与恶意后缀被拒", lambda: [egress(url, False) for url in ["https://notexample.com", "https://example.com.evil.test"]])
    gate.check("09 IPv4 IPv6 localhost被拒", lambda: [egress(url, False) for url in ["https://127.0.0.1", "https://[::1]", "https://localhost", "https://a.localhost"]])
    gate.check("10 用户信息端口及畸形URL被拒", lambda: [egress(url, False) for url in ["https://user@example.com", "https://example.com:8080", "https://[bad", "https://example.com\\@evil.test"]])
    gate.check("11 非白名单程序与空命令", lambda: [command(argv, False) for argv in [["python", "-c", "print(1)"], []]])
    gate.check("12 sudo与通用shell即使列入白名单仍拒", lambda: [command(argv, False) for argv in [["sudo", "cat", "report.txt"], ["bash", "-c", "echo hi"]]])
    gate.check("13 递归删除根目录主目录被拒", lambda: [command(argv, False) for argv in [["rm", "-rf", "/"], ["rm", "--recursive", "~/"], ["rm", "-Rf", "/tmp/../"]]])
    gate.check("14 chmod777与凭据路径被拒", lambda: [command(argv, False) for argv in [["chmod", "0777", "report.txt"], ["cat", "~/.ssh/id_ed25519"], ["cat", "settings/.env.production"]]])
    gate.check("15 curl非白名单与选项绕过被拒", lambda: [command(argv, False) for argv in [["curl", "https://evil.test"], ["curl", "--config", "settings"], ["wget", "--input-file=urls.txt"]]])
    gate.check("16 安全命令与白名单下载目标", lambda: [command(argv, True) for argv in [["cat", "report.txt"], ["curl", "https://docs.example.com"], ["wget", "https://example.com"]]])

    def credentials():
        vault = [core.Credential("read", frozenset({"read"}), 101),
                 core.Credential("admin", frozenset({"read", "write"}), 101),
                 core.Credential("expired", frozenset({"read"}), 100),
                 core.Credential("empty", frozenset(), 102)]
        result = core.scope_credentials(frozenset({"read"}), vault, 100)
        expect([item.name for item in result] == ["read", "empty"], f"期望最小scope且未到期，实际 {result}")
        expect(len(vault) == 4, "不得改变 vault")

    gate.check("17 凭据子集与到期边界", credentials)

    def spec(**changes):
        values = dict(image="reviewed:local", workspace=root, network="none", memory_mb=128, cpus=0.5, pids_limit=32)
        values.update(changes)
        return core.SandboxSpec(**values)

    def container():
        args = core.container_args(spec())
        expected = {"--network": "none", "--user": "65534:65534", "--memory": "128m",
                    "--cpus": "0.5", "--pids-limit": "32", "--cap-drop": "ALL",
                    "--pull": "never", "--security-opt": "no-new-privileges", "--entrypoint": "/bin/echo"}
        expect(args[:2] == ["docker", "run"] and args[-1] == "reviewed:local", f"期望 docker run 与镜像，实际 {args}")
        for key, value in expected.items():
            expect(key in args and args[args.index(key) + 1] == value, f"期望 {key} {value}，实际 {args}")
        expect(all(flag in args for flag in ["--read-only", "--rm", "--no-healthcheck"]), "缺少只读/清理/禁止健康检查")
        expect(args.count("--mount") == 1 and args[args.index("--mount") + 1] == f"type=bind,source={root},target=/workspace,readonly", "只能只读挂载工作目录")
        expect(not any(flag in args for flag in ["--privileged", "--volume", "-v", "--env-file", "--pid"]), "存在权限扩张参数")

    gate.check("18 容器完整约束与唯一挂载", container)
    gate.check("19 拒绝宿主网络与无限资源", lambda: [violation(lambda changes=changes: core.container_args(spec(**changes)), "container_spec") for changes in [{"network": "host"}, {"memory_mb": 0}, {"cpus": float("inf")}, {"pids_limit": -1}]])
    gate.check("20 拒绝镜像与mount参数注入", lambda: [violation(lambda changes=changes: core.container_args(spec(**changes)), "container_spec") for changes in [{"image": "--privileged"}, {"workspace": root + ",target=/host"}]])

    def risk(capabilities, expected):
        original = set(capabilities)
        result = core.trifecta_risk(capabilities)
        expect(result["risk"] == expected, f"期望 {expected}，实际 {result}")
        expect(isinstance(result["recommendations"], list) and (not original or bool(result["recommendations"])), "应有拆分建议列表")
        expect(original == capabilities, "不得改变能力集合")

    gate.check("21 三要素高风险与拆分建议", lambda: risk({"private_data", "untrusted_content", "external_comm"}, "high"))
    gate.check("22 两要素中风险", lambda: risk({"private_data", "untrusted_content"}, "medium"))
    gate.check("23 单要素与空集合低风险", lambda: [risk(value, "low") for value in [{"private_data"}, set()]])
    gate.check("24 未知能力不改变风险", lambda: expect(core.trifecta_risk({"private_data", "untrusted_content", "other"})["risk"] == "medium", "未知能力不得算第三项"))
    return gate.report(path)


if __name__ == "__main__":
    raise SystemExit(main())
