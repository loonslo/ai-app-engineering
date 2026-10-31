# L4.15 复用现成 harness：先划隔离边界，再借用循环

[全书目录](../../README.md) · [上一章 L4.14](../4.21-mcp-practice/README.md) · [下一章 L4.16](../4.15-framework-landscape/README.md)

- **目标**：判断何时复用现成 harness，并用可执行量表评估它的隔离、权限、成本与失败边界。
- **v3 路径**：L4.15 / 选做（清单验收；实操选做）
- **岗位任务 / 面试题型**：T3、T7 / F3。
- **前置**：L4.2 有界循环、L4.11 执行面、L4.12 沙箱与最小权限、L4.13 Agent 安全、L4.14 MCP。
- **环境**：阅读与选型不需要安装候选或密钥。2 小时（1h 阅读 + 1h 填量表）；实操另计，需一次性容器或 VM、可审查的固定版本与离线模型接入。默认不调用真实模型。

## 问题

Harness 是围绕模型循环的一组运行机制：工具、上下文管理、会话、计划、日志，有的还提供子 Agent 或沙箱适配。复用它可以省掉通用代码，但不能把它当成业务执行面或操作系统安全边界。

适合复用的判断：一次性代码修改、整理合成文件、运行小脚本，产物可审查、可撤销。领域业务长链路（订单退款、跨天审批、对外发布）先设计 L4.11 的提交、阶段、幂等、预算、取消与恢复，再决定阶段内是否借用 harness；不要把整条业务链藏进一个无法恢复的大提示里。

## 概念

### 候选与可核实状态

以下一手页面均读取于 **2026-10-31**。这是阅读清单，不是安全认证或性能排名；没有要求全部安装，也没有把上游滚动页面当作历史发布快照。

| 候选 | 本次读到的能力 / 状态 | 复用前必须核对 |
|---|---|---|
| DeepSeek Harness | [官方仓库](https://github.com/deepseek-ai/deepseek-harness) 仍注明 developer preview、可能发生兼容性破坏；[产品页](https://www.deepseek.com/en/harness/) 称 public preview，插件可组合模型、工具等 | [官方 SAFETY](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/SAFETY.md) 明确未经过安全审计，不能当唯一安全控制。细则所列“v0.1、2026-08-13”未从本次读到的一手发布记录核实，不作为当前版本或发布日期写入结论 |
| Pi | [官方说明](https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/README.md) 提供可扩展 harness、会话与 TypeScript SDK；[读取到的 main 包清单](https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/package.json) 是 1.4.0，不能继续把“0.x”当当前事实 | main 清单不是历史发布证据，实操还要选发布标签与镜像摘要。[安全说明](https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/docs/security.md) 说明工具以启动账户权限运行，不逐次确认；工作目录和项目 trust 都不等于沙箱 |
| Claude Agent SDK | [官方概览](https://platform.claude.com/docs/en/agent-sdk/overview) 提供 Claude Code 的工具循环、上下文、permissions、sessions、hooks；可用 Python / TypeScript 嵌入 | 权限模式、子进程、会话存放、认证条款与沙箱范围分别核对；不要把 SDK 与托管 Managed Agents 混为一谈 |
| OpenAI Agents SDK 的 sandbox agents | [官方概览](https://openai.github.io/openai-agents-python/) 有工作区、sandbox client、可恢复 sandbox session；[可核实 Python SDK 发布](https://github.com/openai/openai-agents-python/releases/tag/v0.24.0) 为 v0.24.0（2026-10-15），仍为 0.x | 选择哪种 sandbox client 才决定实际隔离；会话恢复不保证业务副作用只执行一次；不要混淆 `openai-agents` 与 `openai` |
| Pydantic AI Harness | [官方 Harness 文档](https://ai.pydantic.dev/harness/) 组合工作区、计划、上下文、记忆与子 Agent；特别说明 LocalWorkspace 不是沙箱 | 最新 Harness 文档不等于课程锁定的 Pydantic AI 2.31.1。单独环境核对兼容集，不为选做实验升级课程主环境，不把文件 root 误当 Shell 限制 |
| LangChain Deep Agents | [官方概览](https://docs.langchain.com/oss/python/deepagents/overview) 在 LangChain / LangGraph 上提供计划、虚拟文件系统、上下文与子 Agent；有自托管与托管路径 | 确认 backend 是内存、本地磁盘还是独立 sandbox；虚拟文件系统不是宿主文件、网络、进程隔离；托管服务还要核对数据流与费用 |

**稳定性有三层**：产品名、SDK 发布版本、实际插件/沙箱后端版本。只锁 SDK、不锁插件或容器镜像，不能复现安全边界。实操要记录 tag/commit、依赖锁文件、镜像 digest、后端与配置；没有可复核版本就停在文档评估。

### 为什么隔离放在 harness 之外

一个文件工具可能只允许 `/work`，但 Shell、插件或子进程仍可能访问整个容器；容器若挂载了宿主 HOME 或 Docker socket，又把宿主暴露出来。审批弹窗是交互机制，不是对抗恶意子进程的权限边界。让外层容器/VM、出网代理与凭据代理实施策略，而不是请求模型“不要越界”。

文件、网络、进程要分别检查；“有 sandbox”不是一项二元能力。模型兼容与 token 成本同样需要独立证据：接口能连通不代表工具调用、结构化输出、长上下文与费用都合适。

## 流程

1. **先筛任务**：只选一个可撤销、低风险的合成文件任务；写明允许的读写、输出和停止条件。业务长链路回到 L4.11。
2. **先做文档审查**：从候选表选一个，保存官方 URL、读取日期与版本，识别默认工具、插件、遥测与凭据来源。未知项写未知，不猜默认安全。
3. **建立外部隔离**：一次性容器或 VM，只挂载合成工作区；无真实密钥、HOME、SSH agent、云凭据、宿主环境透传或 Docker socket。非 root、只读根文件系统、CPU/内存/PID 上限、无 privileged、移除 capabilities。不能做到就不启动。
4. **控制网络**：默认无网络。安装与构建依赖是单独的准备阶段，完成后锁镜像；运行阶段不能通过 `npx latest` 临时下载。若离线替身在容器内，通过 loopback 接入；不为“让它能跑”开放任意出网。
5. **运行与取证**：按下面量表做正例、边界探针与可控失败。只记录实际工具调用、退出、策略拒绝和文件差异，不接受模型自称“已隔离”。
6. **决策与撤销**：量表填证据与分数，写复用/拒绝/暂缓理由、接入与退出成本。只导出审查后的产物与脱敏日志，停止并销毁实验容器/VM；宿主金丝雀不得改变。

## 练习

### A. 必做的纸面比较

选两个候选，把九维量表都填完。只读文档最多得到 1 分；没有来源或未验证为 0 分。即使总分不错，隔离未实测也不能写“可安全运行”。记录一个自写 L4.11 执行面更合适的任务与理由。

### B. 选做的无密钥隔离实操

任务仅为：在一次性 `/work` 内，把一份合成清单整理为 JSON，保留输入；人工检查字段、差异与输出位置。可以使用本地脚本化模型接入（候选必须明确支持）、本地离线模型或受控工具驱动，不发送真实用户文件。若候选强制云认证且没有无密钥离线路径，记录“未运行：缺少允许的离线路径”，不能偷偷注入真实密钥或改为联网。

**宿主准备**：在一次性目录放 `input.txt`（两行合成条目），在该目录之外另放 `outside-canary.txt`（仅含合成标记），记录两者散列。输入、输出、日志三者不要共用生产路径；金丝雀文件不挂载。

**容器启动约束示例（PowerShell）**：先由自己审查并构建包含所选 harness 与离线依赖的镜像，设置 `HARNESS_IMAGE` 为实际 `name@sha256:...`，设置 `HARNESS_WORKSPACE` 为合成目录的绝对路径。下面拒绝未锁定镜像；没有通用的 harness 启动命令，镜像 ENTRYPOINT 和离线接入参数须按所选版本官方说明配置并记录。

```powershell
if ($env:HARNESS_IMAGE -notmatch '@sha256:[0-9a-f]{64}$') { throw '先指定锁定 digest 的实验镜像' }
if (-not (Test-Path -LiteralPath $env:HARNESS_WORKSPACE -PathType Container)) { throw '先指定一次性合成工作区' }
docker run --rm --name l415-harness-lab --network none --read-only --user 1000:1000 `
  --cap-drop ALL --security-opt no-new-privileges --memory 512m --cpus 1 --pids-limit 64 `
  --tmpfs /tmp:rw,noexec,nosuid,size=64m `
  --mount "type=bind,source=$env:HARNESS_WORKSPACE,target=/work" --workdir /work `
  $env:HARNESS_IMAGE
```

这是限制示例，不是对所有候选的兼容承诺。若候选需要写 HOME，应放在容器内临时目录；不要挂载真实 HOME。若需要放宽限制，先记录原因和风险；无法维持最低边界则不运行。VM 路径也要记录等价的挂载、账户、出网和资源限制。外部超时/取消由宿主控制；超过预设时间应停止实验，不相信模型自行停机。

### 九维量表（本课程建议，不是行业认证）

评分：**0**＝未知、缺失或探针失败；**1**＝锁定版本文档和配置可定位，但未实测；**2**＝有文档、配置和本次正反例证据。不能用别人的测试结果替自己的 2 分。

| 维度 | 需要的配置证据 | 本次应做的低风险探针 / 期望 |
|---|---|---|
| 文件隔离 | 仅挂载 `/work`，无 HOME/socket；规范化和符号链接规则 | 正例读输入、写预期 JSON；请求读工作区外的宿主金丝雀、`..` 路径，必须拒绝或不可见；输入与外部散列不变 |
| 网络隔离 | 容器无网络或明确代理白名单、DNS 与回环规则 | 发起一次普通 HTTPS 到非允许域名（如 example.com），必须被运行环境阻断；有白名单时再记录允许目标正例，不用生产地址 |
| 进程隔离与资源 | 非 root、只读根、无 capabilities/privileged、PID/CPU/内存/墙钟限制 | 查看容器实际配置、身份与进程可见范围；向容器根目录做一次无害写入应失败；取消一个可终止的短等待任务并确认进程退出，不用 fork bomb 或耗尽宿主 |
| 权限与审批 | 最小工具集，默认拒绝危险写入；审批在 handler 前；禁止继承真实凭据 | 请求一次不允许的工作区外写入，handler 不执行；需要审批时拒绝一次并保留实际调用日志；没有内建审批则由外层禁用写工具，不伪称已实现审批 |
| 版本与供应链 | SDK、插件、依赖锁、镜像 digest、后端版本 | 在断网环境启动固定镜像；记录版本命令与锁文件，不允许隐式下载/自动升级；检查没有未审查插件加载 |
| 会话与可观测性 | 会话保存位置、保留/删除规则、外部遥测关闭 | 日志能还原工具名/参数摘要/结果/错误/停止；用合成敏感标记检查日志暴露，记录脱敏与删会话结果；不把真实秘密当测试数据 |
| 模型兼容 | 实际接入方式、工具消息格式、模型版本/配置 | 离线替身或本地模型跑一次工具调用和最终回答；记录不支持的参数与模式；不把本地兼容推断为所有云模型兼容 |
| token 与成本 | 请求/工具/子任务/token/墙钟上限，价格来源（若涉及） | 降低一个预算，确认外层有界停止；记录能观察到的请求/token。假模型无 usage 时写“不可测”，不能以 0 冒充真实费用 |
| 失败处理 | 工具异常、取消、会话重开、已发生写入的处理契约 | 给合成输入一个不存在的文件名，观察可读失败；取消后检查没有残留任务；若宣称恢复，再做重开证据，确认不重复覆盖已审查输出，否则标未验证 |

实操建议门槛：18 分中至少 14 分，且**文件、网络、进程、权限四项均为 2 分**；此外无真实密钥、版本锁定、任务可撤销三项必须满足。任何宿主越界、非白名单出网、未授权 handler 执行都立即停止，与总分无关。未完成实操只交纸面审查，不把其分数当部署许可。

## 产物与验收

在 [workbook](workbook.md) 保存候选对比、九维评分、来源、证据性质、选择/拒绝/暂缓理由、接入与退出成本。使用 [实操清单](gate/CHECKLIST.md)；本章没有可执行 gate 或预填通过报告。选做者额外提交脱敏命令/配置、版本锁、轨迹、差异、探针结果与销毁记录。

验收关注“什么能力由谁强制、证据在哪里”，不以一次漂亮回答或总分代替安全边界。无法完成离线、无密钥、外部隔离前提时，正确产物是带具体阻碍的“不运行”决定。

## 边界

本章未安装或运行全部候选，不验证真实模型、云后端、费用或生产安全。容器不是完整虚拟机；隔离效果还依赖宿主内核、运行时与配置。低风险探针不是渗透测试。量表不证明抵御所有提示注入，也不提供业务幂等、跨租户鉴权、持久执行或合规保证。DeepSeek 初始发布日期/版本与 Pi 0.x 的历史说法没有得到本次一手发布记录支持，已从事实结论删除，保留为复核边界。
