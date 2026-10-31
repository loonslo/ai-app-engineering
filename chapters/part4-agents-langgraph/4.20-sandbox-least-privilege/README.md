# L4.12 沙箱与最小权限 · Gate

[全书目录](../../README.md) · [上一章 L4.11](../4.19-agent-execution-plane/README.md) · [下一章 L4.13](../4.12-tool-safety-search/README.md)

- **能力**：在模型之外限制路径、命令、出网与凭据，并生成受限容器配置。
- **v3 路径**：L4.12 / 核心（Gate；沙箱与权限）
- **岗位任务 / 面试题型**：T3、T5 / F3
- **前置**：L4.3 工具契约、L4.11 执行面。
- **时间盒**：5 小时（1.5h 读 + 2.5h 实现 + 1h 故障与记录）。
- **闭卷规则**：只读本页、`gate/starter.py` 和标准库官方文档；通过前不读 `sandbox_policy.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.20-sandbox-least-privilege/gate/gate_check.py
```

24 项全部 PASS 才算通过；报告写入 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。gate 只计算策略，不启动 Docker，不执行任何示例危险命令。

## 为什么做这个 gate

Agent 能提出动作，不意味着它应当拥有执行动作的全部权限。harness 是组织模型、工具、上下文和循环的宿主；沙箱是限制实际进程可访问资源的强制边界。把“请不要越界”放进 prompt，不能替代操作系统、容器、网络代理与凭据服务的限制。

[DeepSeek Harness 官方进程沙箱文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/sandbox.md) 明确：`SandboxMode` 只治理文件系统效果，不包括网络与进程可见性；还区分 full 与 partial enforcement。[Wavect 2026-09-02 评审](https://wavect.io/blog/deepseek-harness-enterprise-review/) 也指出这一边界，但它是第三方评审，不是我们的实测。官方 [SAFETY.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md) 要求不要把 harness 当作不可信负载的唯一安全控制。（以上读取于 2026-10-31。）

[Pi 官方主页](https://pi.dev/) 的 “No permission popups” 刻意不内置权限弹窗，而建议容器或扩展确认流程；[permission-gate 示例源码](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/examples/extensions/permission-gate.ts) 展示了应用层拦截。**确认是意图检查，不是隔离**：即使用户误批准，外部沙箱仍须拦住宿主文件、凭据与非授权出网。（读取于 2026-10-31；没有实际运行这两个 harness。）

## 概念

| 控制面 | 本章约束 | 不能误认为 |
|---|---|---|
| 路径 | 相对路径以任务 workspace 为根，realpath 后按路径组件判断 | 字符串前缀相同就安全，或检查后文件不会再变化 |
| 命令 | argv 程序白名单、危险参数拦截；不拼 shell 字符串 | 白名单里的解释器能安全执行任意代码 |
| 出网 | 默认断网；只允许 HTTPS 白名单域名与其子域 | URL 字符串检查已防住 DNS 重绑定与重定向 |
| 凭据 | 每任务短期发放、最小 scope、到期即剔除 | 读权限与管理员权限可互换 |
| 容器 | 非 root、只读根、资源上限、单一只读挂载、drop capabilities | 容器不存在内核/运行时漏洞 |

[Docker 运行文档](https://docs.docker.com/engine/containers/run/) 与 [CLI 参数参考](https://docs.docker.com/reference/cli/docker/container/run/) 说明这些选项的含义（读取于 2026-10-31）：

- `--user 65534:65534`：容器进程不以 root 运行。
- `--read-only`：根文件系统只读；本章工作目录也显式只读，不把仓库、HOME 或 Docker socket 挂进去。
- `--network none`：本章演示断网。命名网络只有被管理员配置了出口代理/防火墙才算白名单网络，名称本身不提供过滤。
- `--memory`、`--cpus`、`--pids-limit`：分别限制内存、CPU、进程数；不能把 0/-1 当作有效的有限资源上限。
- `--cap-drop ALL`、`no-new-privileges`：降低进程获得额外系统能力的机会；绝不生成 `--privileged`。
- `--pull never`：不隐式拉取镜像；固定 `/bin/echo` entrypoint、禁用 image healthcheck，只做可读消息演示。镜像仍必须由人预先审核，生产建议固定 digest。

凭据按任务与租户在外部 vault 发放；这里只筛选凭据**元数据**，不存储令牌值。要求是 `credential.scopes ⊆ required_scopes`，不是反过来。函数可以返回只覆盖部分需求的多个凭据，不能偷偷返回“大而全”的管理员凭据；是否覆盖任务所有需求由上游检查。

### 致命三要素

[Simon Willison 原文](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) 将 **私有数据 + 不可信内容 + 对外通信** 的组合称为 lethal trifecta（2025-06-16，读取于 2026-10-31）。例如：读客户邮件的 Agent 接到攻击者邮件，又能向任意地址发消息，便可能把客户信息发送出去。

拆开一个能力比再加一句“不要泄密”更可靠：不可信网页处理器没有私有凭据；私有查询器不出网；发送器只接脱敏、经审批的固定结构结果，目标不能由网页内容改写。本章 high/medium/low 是教学分级，不是原文定义的通用风险评分，也不是低风险安全保证。

[OWASP Agentic Top 10 官方说明](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/) 的 **ASI05 — Unexpected Code Execution（意外代码执行）** 对应本章：自然语言到命令的路径必须有模型之外的控制。凭据部分也涉及 ASI03，但本章不代替完整威胁建模。（读取于 2026-10-31。）

## 任务

实现 starter 的异常、五个冻结数据结构和六个策略函数；字段与完整输入边界见 docstring。

| 接口 | 输入 → 输出 / 失败行为 |
|---|---|
| `resolve_in_workspace` | 目标、workspace、可注入 realpath → 规范化绝对路径；越界抛 `PolicyViolation("path_escape")` |
| `check_egress` | URL、域名白名单 → `Decision(allowed, reason)`，不发请求 |
| `check_command` | argv、`CommandPolicy` → Decision，不运行命令 |
| `scope_credentials` | 所需 scopes、凭据列表、假时间 now → 保序、未到期、权限不超范围的列表 |
| `container_args` | `SandboxSpec` → `['docker', 'run', ..., image]`；不执行，无效配置抛 `container_spec` |
| `trifecta_risk` | 能力集合 → `{'risk', 'recommendations'}`，建议为稳定顺序的字符串列表 |

## 关键约定

1. 所有策略由可信执行面调用；模型无权修改白名单、workspace 或假时间。根目录本身合法，相似前缀目录不合法；gate 用注入函数模拟符号链接。
2. URL 按主机名匹配，`docs.example.com` 是子域，`notexample.com` 与 `example.com.evil.test` 不是。拒绝 IP、localhost、URL 用户信息、非 443 端口、反斜杠及格式异常；不访问 DNS。
3. 命令用 argv 而非 shell 字符串；程序名必须原样命中白名单。拒绝 sudo、su、通用 shell；拒绝 chmod 777/0777、对 `/` 或 `~` 递归删除、敏感路径参数。`curl`/`wget` 只支持一个裸 URL，所有选项都拒绝，避免配置文件、代理与重定向绕过。危险样例只作为字符串传给函数。
4. `expires_at == now` 已失效；scopes 空集合是合法子集，函数不修改 vault。
5. 容器只接受 `none` 或普通命名网络，拒绝 host/bridge/default；资源须正且有限；拒绝镜像选项注入和 workspace mount 分隔符。单一挂载、readonly、固定 entrypoint 的完整参数契约见 starter。
6. 只统计三个约定能力；未知能力不升级风险。`recommendations` 给具体拆分办法，不只是“注意安全”。

## 故障注入（必须亲手触发）

| # | 注入（只构造输入，不执行） | 期望 / 对应检查 |
|---|---|---|
| 1 | `..`、外部绝对路径、伪装同前缀、模拟链接到外部 | path_escape，01–05（04 是正常对照） |
| 2 | http/file、伪子域、IP/localhost、用户信息、端口/畸形 URL | 出网拒绝，06–10（07 是正常对照） |
| 3 | 未知程序、sudo/shell、rm 递归根目录/主目录、chmod777、凭据路径 | 命令拒绝，11–14 |
| 4 | curl 非白名单、下载器配置选项 | 不执行且拒绝，15；16 是安全对照 |
| 5 | 大权限凭据、恰好到期凭据 | 剔除并保序，17 |
| 6 | 容器缺约束、host 网络、无限资源、镜像/mount 注入 | 完整安全参数或 container_spec，18–20 |
| 7 | 三项/两项/单项/零项、附加未知能力 | high/medium/low 与拆分建议，21–24 |

## 验收标准

24 项：路径 5、出网 5、命令 6、凭据 1、容器 3、三要素 4。默认 starter 应 0/24、退出 1；实现后应 24/24、退出 0。可重复性是策略行为证据，不是容器安全审计。

## 提交物

实现后的 starter、24/24 `gate_report.json`、[workbook](workbook.md) 的预测、故障分析、解释题和边界记录。不要提交任何真实凭据，也不要运行危险字符串验证拦截。

## 通过后对照参考实现

```bash
python tools/run_chapter.py 4.20 sandbox_policy.py
# 选做：先人工确认 Docker 可用，且审核过的 Linux 镜像已缓存在本机
python tools/run_chapter.py 4.20 sandbox_policy.py --docker --image alpine:3.20
```

默认只打印策略与 Docker argv，不创建工作目录或启动进程。`--docker` 只挂载新建空临时目录，禁止网络/拉取，执行固定 echo；失败返回 1 和可读消息，无未捕获堆栈。可用 `--image` 指定已审核 digest；示例 tag 不代表供应链背书。没有模型调用或 `--live` 路径。

对照：① realpath 与 commonpath 分别解决什么问题？② 为什么 `check_command` 允许 cat 也不能替代文件隔离？③ 白名单域名解析到私网地址时，哪个外部边界负责拒绝？

## 概念地图

任务身份 → 最小凭据 → 路径/命令/URL 决策 → 外部沙箱强制执行 → 受控结果；三要素检查贯穿能力组合，而非只看单个工具。

## 边界

这是教学策略，不是通用 shell 解析器、SSRF 防护库或安全容器运行时。路径检查与打开之间仍有 TOCTOU（检查后被替换）风险；真实系统需原子化目录句柄/内核隔离。允许 Python 等解释器就必须假设它可绕过应用层命令规则，因此默认命令白名单不含它。URL 检查不处理 DNS 重绑定、解析到私网、服务端重定向、代理或继承环境；要由网络层默认拒绝并逐跳校验。只读挂载仍可能泄露文件，所以只挂载不含机密的一次性目录。命名网络、凭据签发/撤销、租户身份、Docker 权限、镜像漏洞、内核逃逸均未由本 gate 验证；选做 Docker 成功也不能证明这些边界安全。
