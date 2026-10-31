"""L4.12：模型之外的策略；默认只生成参数，--docker 才运行固定低风险命令。"""
from __future__ import annotations

import argparse
import ipaddress
import json
import math
import os
import posixpath
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit


class PolicyViolation(Exception):
    def __init__(self, kind: str, detail: str = "") -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}" if detail else kind)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class CommandPolicy:
    allowed_programs: frozenset[str]
    allow_hosts: frozenset[str]


@dataclass(frozen=True)
class Credential:
    name: str
    scopes: frozenset[str]
    expires_at: int


@dataclass(frozen=True)
class SandboxSpec:
    image: str
    workspace: str
    network: str
    memory_mb: int
    cpus: float
    pids_limit: int


def resolve_in_workspace(
    path: str, workspace: str, realpath_fn: Callable[[str], str] = os.path.realpath,
) -> str:
    """相对路径以 workspace 为基准；解析真实路径后用路径组件而非字符串前缀比较。"""
    root = os.path.abspath(realpath_fn(workspace))
    candidate = os.path.abspath(path if os.path.isabs(path) else os.path.join(root, path))
    resolved = os.path.abspath(realpath_fn(candidate))
    try:
        inside = os.path.normcase(os.path.commonpath([root, resolved])) == os.path.normcase(root)
    except ValueError:
        inside = False
    if not inside:
        raise PolicyViolation("path_escape", "路径不在任务工作目录内")
    return resolved


def check_egress(url: str, allow_hosts: frozenset[str]) -> Decision:
    """只做离线 URL 策略，不解析 DNS、不发起请求、不跟随重定向。"""
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        return Decision(False, "URL 格式无效")
    if parsed.scheme != "https" or not host or "\\" in url or any(c.isspace() for c in url):
        return Decision(False, "仅允许有效的 HTTPS URL")
    if parsed.username is not None or parsed.password is not None or port not in (None, 443):
        return Decision(False, "不允许 URL 凭据或非 HTTPS 默认端口")
    if host == "localhost" or host.endswith(".localhost"):
        return Decision(False, "禁止 localhost")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return Decision(False, "禁止 IP 直连")
    # 单标签、纯数字和旧式 IP 拼写也不应通过域名白名单。
    labels = host.split(".")
    if len(labels) < 2 or not any(c.isalpha() for c in labels[-1]) or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels
    ):
        return Decision(False, "仅允许 DNS 域名")
    for allowed in sorted(allow_hosts):
        domain = allowed.lower().rstrip(".")
        if domain and (host == domain or host.endswith("." + domain)):
            return Decision(True, "主机命中白名单或其子域")
    return Decision(False, "主机不在出网白名单中")


def check_command(argv: list[str], policy: CommandPolicy) -> Decision:
    """仅检查 argv，不运行程序；不要把结果转换为 shell=True 的字符串执行。"""
    if not argv:
        return Decision(False, "命令为空")
    program = argv[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
    if program in {"sudo", "su", "sh", "bash", "cmd", "cmd.exe", "powershell", "pwsh"}:
        return Decision(False, "禁止提权或通用 shell")
    if argv[0] not in policy.allowed_programs:
        return Decision(False, "程序不在白名单中")
    normalized = [arg.replace("\\", "/").lower() for arg in argv[1:]]
    if any("~/.ssh" in arg or ".env" in arg for arg in normalized):
        return Decision(False, "禁止访问凭据路径")
    if program == "chmod" and any(re.fullmatch(r"0*777", arg) for arg in normalized):
        return Decision(False, "禁止 chmod 777")
    if program == "rm":
        options = [arg for arg in normalized if arg.startswith("-")]
        recursive = any(arg == "--recursive" or (not arg.startswith("--") and "r" in arg) for arg in options)
        targets = [arg for arg in normalized if not arg.startswith("-")]
        if recursive and any(posixpath.normpath(arg) in {"/", "~"} for arg in targets):
            return Decision(False, "禁止递归删除根目录或主目录")
    if program in {"curl", "wget"}:
        # 不实现完整 CLI 语法：只接受裸 URL，杜绝配置、代理、重定向等参数绕开检查。
        if len(argv) != 2 or argv[1].startswith("-"):
            return Decision(False, "下载器只接受一个裸 HTTPS URL，不接受选项")
        return check_egress(argv[1], policy.allow_hosts)
    return Decision(True, "命令通过当前策略；不代表任意程序内部行为安全")


def scope_credentials(
    required_scopes: frozenset[str], vault: list[Credential], now: int,
) -> list[Credential]:
    """保持 vault 原顺序；到期时刻即失效，拒绝权限超集，不复制或输出凭据值。"""
    return [item for item in vault if item.expires_at > now and item.scopes <= required_scopes]


def container_args(spec: SandboxSpec) -> list[str]:
    """返回包含 docker/run 和 image 的 argv，不启动容器；命令由可信宿主另行追加。"""
    if not spec.image or spec.image.startswith("-") or any(c.isspace() for c in spec.image):
        raise PolicyViolation("container_spec", "镜像名无效")
    if (
        spec.memory_mb <= 0 or not math.isfinite(spec.cpus) or spec.cpus <= 0
        or spec.pids_limit <= 0
    ):
        raise PolicyViolation("container_spec", "资源上限必须为正数")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", spec.network) or spec.network in {"host", "bridge", "default"}:
        raise PolicyViolation("container_spec", "只接受 none 或管理员配置的白名单网络名")
    workspace = os.path.realpath(spec.workspace)
    if any(c in workspace for c in ',\n\r"'):
        raise PolicyViolation("container_spec", "工作目录不能包含 mount 分隔符")
    if os.path.dirname(workspace) == workspace:
        raise PolicyViolation("container_spec", "禁止把宿主根目录作为工作目录")
    return [
        "docker", "run", "--rm", "--pull", "never", "--network", spec.network,
        "--read-only", "--user", "65534:65534", "--memory", f"{spec.memory_mb}m",
        "--cpus", str(spec.cpus), "--pids-limit", str(spec.pids_limit),
        "--mount", f"type=bind,source={workspace},target=/workspace,readonly",
        "--workdir", "/workspace", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--no-healthcheck", "--entrypoint", "/bin/echo", spec.image,
    ]


def trifecta_risk(capabilities: set[str]) -> dict:
    """只统计三个约定能力；recommendations 是中文字符串列表，不是授权决定。"""
    present = capabilities & {"private_data", "untrusted_content", "external_comm"}
    risk = "high" if len(present) == 3 else "medium" if len(present) == 2 else "low"
    suggestions = {
        "private_data": "私有数据交给独立只读任务，只输出脱敏摘要",
        "untrusted_content": "不可信内容只作数据，隔离到没有私有凭据的任务",
        "external_comm": "移除直接出网能力，由独立审批发送器发送固定目标结果",
    }
    return {"risk": risk, "recommendations": [suggestions[key] for key in sorted(present)]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", action="store_true", help="显式启动本地已缓存镜像；无拉取、无网络")
    parser.add_argument("--image", default="alpine:3.20", help="预先人工审核并缓存的 Linux 镜像，建议用 digest")
    args = parser.parse_args()
    try:
        print("离线策略：", check_egress("https://docs.example.com/guide", frozenset({"example.com"})))
        workspace = os.path.abspath("sandbox-workspace")
        print("目录内路径：", resolve_in_workspace("report.txt", workspace))
        policy = CommandPolicy(frozenset({"cat", "curl"}), frozenset({"example.com"}))
        print("命令决策（不执行）：", check_command(["cat", "report.txt"], policy))
        vault = [
            Credential("task-read", frozenset({"read"}), 101),
            Credential("too-broad", frozenset({"read", "write"}), 101),
            Credential("expired", frozenset({"read"}), 100),
        ]
        print("假时间100下的凭据名称：", [
            item.name for item in scope_credentials(frozenset({"read"}), vault, 100)
        ])
        print("风险：", json.dumps(trifecta_risk({"private_data", "untrusted_content", "external_comm"}), ensure_ascii=False))
        if not args.docker:
            spec = SandboxSpec(args.image, os.path.abspath("sandbox-workspace"), "none", 128, 0.5, 32)
            print("仅生成，不执行：", json.dumps(container_args(spec) + ["sandbox demo"], ensure_ascii=False))
            return 0
        # 只挂载新建空目录，绝不把项目、HOME、密钥或 Docker socket 放进去。
        with tempfile.TemporaryDirectory(prefix="agent-sandbox-") as workspace:
            spec = SandboxSpec(args.image, workspace, "none", 128, 0.5, 32)
            result = subprocess.run(
                container_args(spec) + ["sandbox demo"], shell=False,
                capture_output=True, text=True, timeout=20, check=False,
            )
            if result.returncode:
                print("容器未完成：请确认 Docker 可用、Linux 镜像已人工审核并缓存；不会自动拉取。")
                return 1
            print("显式 Docker 演示：", result.stdout.strip())
            return 0
    except (OSError, ValueError, PolicyViolation, subprocess.SubprocessError) as exc:
        print(f"无法完成沙箱演示：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
