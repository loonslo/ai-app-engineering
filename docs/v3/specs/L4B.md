# L4-B 状态、执行面与安全细则（V3-5）

阶段目标：在需要显式状态时才用状态图；理解检查点与持久执行的区别；把长任务做成异步、可恢复、受控的执行面；把沙箱与最小权限放在 harness 之外；对照 OWASP 做 Agent 安全；会用 MCP，也知道什么时候不用。

出口：异步专项 Agent：权限、审批、崩溃恢复、5 个故障注入、pass^3 报告。

---

## L4.9 状态图（LangGraph）· 增补

- **目录**：`chapters/part4-agents-langgraph/` 下的 `4.2-langgraph-basics`、`4.3-branch-loop`、`4.4-state-reducer`、`4.6-node-reliability`
- **课时**：8h
- **改动**：
  - 在 4.2 的 README 开头加一节“什么时候需要图”：流程有显式状态、分支、检查点恢复或人工介入时才用。引用雷达 Vol.34 把 LangGraph 从 Adopt 调到 Trial 的理由——更偏好用代码传递信息的简单 Agent，需要时才加图（注明读取日期）。
  - 精简四章 README 中重复的背景段落，每章只保留本章的新概念。
  - 注明 LangGraph 的锁定版本（`requirements.txt`），以及本机安装版本可能不同（2026-10-27 核对时为 1.2.10）。
- **不改**：四个 gate 与参考实现（允许使用 LangGraph）。

---

## L4.10 检查点、HITL 与持久执行 · 增补

- **目录**：`chapters/part4-agents-langgraph/4.10-checkpoint-context/`、`chapters/part4-agents-langgraph/4.11-streaming-hitl/`
- **课时**：7h
- **README 增补“检查点不等于持久执行”一节**（放在 4.10）：
  1. LangGraph 的几种 durability 模式，以及各自在进程崩溃时会丢失什么；以官方文档为准并注明读取日期。
  2. 检查点保存了数据，但谁来发现失败的运行并重启它？这正是持久执行引擎（Temporal、DBOS、Restate）解决的问题。引用雷达 Vol.34 的 Caution “Ignoring durability in agent workflows”。
  3. 有副作用的步骤必须带幂等键：从旧快照恢复可能让工具再执行一次。OpenAI Agents SDK 的人工审批文档明确写明，批准不保证工具只执行一次（注明读取日期）。
  4. 指向 L4.11：本课程用数据库步骤表实现可恢复的执行面。
- **workbook**：两章各加 2 道解释题（例如：“进程在工具执行后、快照写入前崩溃，恢复时会发生什么？”）。
- **不改**：两个 gate 与参考实现。

---

## L4.11 专项 Agent 执行面 · 新增 · gate

- **目录**：`chapters/part4-agents-langgraph/4.19-agent-execution-plane/`（新建）
- **课时**：8h（2h 读 + 4.5h 实现 + 1.5h 记录）
- **岗位任务 / 面试题型**：T3、T5 / F3
- **学完能做**：把长任务做成“提交即返回 task_id、后台分阶段执行、每步落盘、崩溃可续跑、副作用只执行一次、可审批可取消、有预算”的执行面。

### README 必讲

curriculum-v3.md 第 2.2 节的形态 B 规则逐条展开：

1. 异步化：提交即返回 task_id；状态从状态存储读取，不从队列读取。
2. 阶段化：外部状态机推进阶段，阶段内由 Agent 做事。
3. 断点与幂等。
4. 沙箱放在 harness 之外（详见 L4.12）。
5. 预算与取消。
6. 人工审批。
7. 缓存友好。
8. 评测。

另外说明三点：为什么只用 Celery 不够（它是队列，重试会整段重跑）；数据库步骤表、LangGraph、Temporal 三种做法各自的取舍；本章选数据库步骤表的原因。

### 闭卷接口（`gate/starter.py`）

```python
TERMINAL = {"succeeded", "failed", "cancelled", "budget_exceeded"}

@dataclass
class StepRecord:
    stage: str
    ok: bool
    output: str          # 输出摘要
    tokens: int
    duration_ms: int
    attempt: int
    error: str | None = None

@dataclass
class Budget:
    max_steps: int
    max_tokens: int
    max_wall_ms: int

@dataclass
class Task:
    id: str
    tenant_id: str
    payload: dict
    status: str          # "queued" | "running" | "waiting_approval" | 以及 TERMINAL 中的状态
    current_stage: int
    steps: list[StepRecord]
    budget: Budget
    approvals: dict[str, bool]
    cancel_requested: bool = False
    started_ms: int | None = None

@dataclass(frozen=True)
class StageOutput:
    output: str
    tokens: int

@dataclass(frozen=True)
class Stage:
    name: str
    fn: Callable[[Task], StageOutput]    # 可能抛 RetryableError 或其他异常
    side_effect: bool = False
    needs_approval: bool = False
    max_attempts: int = 2

class RetryableError(Exception): ...

def submit(store, tenant_id: str, payload: dict, idempotency_key: str, budget: Budget) -> str:
    """相同 (tenant_id, idempotency_key) 返回同一个 task_id；新任务状态为 queued。store 接口由 gate 提供：get、put、find_by_key。"""
def run_until_blocked(store, task_id: str, stages: list[Stage], *, clock, side_effect_log: dict[str, StageOutput]) -> Task:
    """从 current_stage 继续执行，直到任务进入终态或 waiting_approval：
    - 每个阶段完成后立刻追加 StepRecord 并 put 回 store；
    - side_effect 阶段使用幂等键 f"{task_id}:{stage.name}"：side_effect_log 中已有该键时直接复用结果，不再调用 fn；
    - needs_approval 阶段：approvals 中没有该阶段的决定时，状态置为 waiting_approval 并返回；决定为 False 时 failed；
    - 每个阶段开始前检查：cancel_requested 为真 → cancelled；步数、token、墙钟（clock() - started_ms）任一超出预算 → budget_exceeded；
    - fn 抛 RetryableError 时在 max_attempts 内重试；用尽或抛其他异常时，记录失败步骤并置 failed；
    - 全部阶段完成 → succeeded。"""
def approve(store, task_id: str, stage: str, decision: bool) -> Task: ...
def cancel(store, task_id: str) -> Task: ...
def deliver_result(task: Task, webhook_fn, delivered: set[str]) -> bool:
    """只有终态任务才投递；同一 task_id 只成功投递一次；webhook_fn 抛异常时返回 False，且不记为已投递。"""
```

### 检查项（总数 ≥14；gate 提供内存 store 与假时钟）

提交幂等；正常跑完全部阶段；阶段第一次抛异常、进程“崩溃”后续跑，从失败阶段继续；续跑时不重复执行已成功的副作用阶段；等待审批、批准后继续；拒绝后 failed；步数超预算；token 超预算；墙钟超预算；阶段之间取消生效；可重试错误在上限内成功；不可重试错误直接失败；每个阶段结束后 store 中都有对应的 StepRecord；webhook 重复调用只成功投递一次。

### 参考实现

`execution_plane.py`：一个“调研报告”任务，用 `sqlite3` 实现持久化的步骤表，演示模拟崩溃与续跑。

---

## L4.12 沙箱与最小权限 · 新增 · gate

- **目录**：`chapters/part4-agents-langgraph/4.20-sandbox-least-privilege/`（新建）
- **课时**：5h
- **岗位任务 / 面试题型**：T3、T5 / F3
- **学完能做**：为能执行代码或命令的 Agent 制定路径、命令、出网、凭据与容器策略，并识别“致命三要素”。

### README 必讲

1. 为什么沙箱要放在 harness 之外：DeepSeek Harness 的沙箱只覆盖文件系统（Wavect 2026-09 评审）；Pi 刻意不做权限确认。都注明来源与读取日期。
2. 容器隔离要点：非 root 用户、只读根文件系统、默认无网络或出网白名单、资源上限、只挂载工作目录、禁止 `--privileged`。
3. 凭据：按任务发放、临时、最小权限。
4. 路径与命令策略。
5. 致命三要素：私有数据 + 不可信内容 + 对外通信（Simon Willison 提出），以及怎样拆开。
6. 对应 OWASP Agentic Top 10 的 ASI05（意外代码执行）。

### 闭卷接口（`gate/starter.py`）

```python
class PolicyViolation(Exception):
    def __init__(self, kind: str, detail: str = ""): ...

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
    network: str          # "none" 或白名单网络名
    memory_mb: int
    cpus: float
    pids_limit: int

def resolve_in_workspace(path: str, workspace: str, realpath_fn=os.path.realpath) -> str:
    """规范化（经过 realpath_fn）后必须位于 workspace 内，否则抛 PolicyViolation("path_escape")。
    gate 通过注入 realpath_fn 模拟符号链接，不在文件系统上真的创建链接。"""
def check_egress(url: str, allow_hosts: frozenset[str]) -> Decision:
    """只允许 https；主机必须在白名单内，或是白名单主机的子域；IP 直连、localhost、file:// 一律拒绝。"""
def check_command(argv: list[str], policy: CommandPolicy) -> Decision:
    """程序不在 allowed_programs 中则拒绝；拒绝 sudo、chmod 777、对 / 或 ~ 的递归删除；
    curl / wget 的目标交给 check_egress 判断；参数中出现 ~/.ssh 或 .env 时拒绝。"""
def scope_credentials(required_scopes: frozenset[str], vault: list[Credential], now: int) -> list[Credential]:
    """只返回未过期、且 scopes 是 required_scopes 子集的凭据；不返回权限更大的凭据。"""
def container_args(spec: SandboxSpec) -> list[str]:
    """生成 docker run 参数：--network <spec.network>、--read-only、--user 非 root、--memory、--cpus、--pids-limit、
    只挂载 workspace（--mount type=bind,...）、--cap-drop ALL；任何情况下都不生成 --privileged。"""
def trifecta_risk(capabilities: set[str]) -> dict:
    """同时具备 private_data、untrusted_content、external_comm 时 risk="high"，并给出拆分建议；
    具备其中两项时为 "medium"；否则为 "low"。"""
```

### 检查项（总数 ≥12）

`..` 越界；绝对路径越界；模拟符号链接越界；工作目录内路径通过；http 被拒；子域规则；IP 直连被拒；不在白名单的程序；sudo 与递归删除；curl 访问非白名单主机；凭据范围筛选与过期剔除；容器参数完整且没有 `--privileged`；三要素风险分级。

### 参考实现

`sandbox_policy.py`：演示上述策略；本机有 Docker 时，`--docker` 用生成的参数真的启动一个受限容器（选做）。

---

## L4.13 Agent 安全 · 换实现 + 增补

- **目录**：`chapters/part4-agents-langgraph/4.12-tool-safety-search/`；文件 `tool_safety_search.py`
- **换实现**：改为原生实现。`chapters/test_new_lessons.py` 导入了本章，保持被测函数的名字与行为不变。
- **README 增补**：
  - OWASP Agentic Top 10（2025-12 发布）对照表：ASI01–ASI10 各自在本课程哪一章覆盖；
  - OWASP LLM Top 10 2026 版的变化：提示注入仍居第 1，Excessive Agency 升至第 3；
  - 结论：靠提示和过滤无法根除，必须在模型之外强制最小权限。
  - 以上注明来源与读取日期。
- **不改**：gate。

---

## L4.14 MCP 实战与取舍 · 新增 · gate

- **目录**：`chapters/part4-agents-langgraph/4.21-mcp-practice/`（新建）
- **课时**：5h
- **岗位任务 / 面试题型**：T3 / F3
- **学完能做**：把工具暴露为 MCP 工具、规整调用结果、按 scope 授权；能判断一个集成该用本地函数、CLI、Skill 还是 MCP。

### README 必讲

1. 角色：host、client、server；原语：tools、resources、prompts；传输：stdio、Streamable HTTP。
2. 2026-07-28 版规范的方向：无状态、`server/discover`、Tasks 与 MCP Apps 改为扩展、sampling / roots / logging / 动态客户端注册进入弃用期、鉴权向 OAuth 2.1 与 OIDC 看齐。说明这些细节出自 AAIF 按候选版写的文章，实施者须对照最终规范核实，并注明读取日期。
3. 治理：2025-12-09 捐给 Linux 基金会下的 AAIF。
4. 雷达 Vol.34 的 Caution “MCP by default”：MCP 的价值在结构化工具契约、OAuth 鉴权边界与受治理的多租户访问；其他情况先考虑更轻的方式。
5. 安全：工具描述与结果都是不可信输入；最小 scope。
6. 与旧章的关系：1.6 是入门旧章，10.1 深入鉴权与审批（选修）。

### 闭卷接口（`gate/starter.py`）

```python
@dataclass(frozen=True)
class Decision:            # 与 L4.12 同构；每章 starter 独立，在本章重新定义
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

def to_mcp_tool(name: str, description: str, params_schema: dict) -> dict:
    """返回 {"name", "description", "inputSchema"}；schema 的 type 必须为 object，否则抛 ValueError。"""
def from_mcp_result(result: dict) -> str:
    """拼接 content 中 type="text" 的项（用换行连接）；isError 为真时加前缀“工具错误：”；没有文本内容时返回“（无文本结果）”。"""
def authorize_call(tool_name: str, token_scopes: set[str], required_scopes: dict[str, set[str]]) -> Decision:
    """未知工具拒绝；缺少任一所需 scope 时拒绝，reason 列出缺少的 scope。"""
def choose_integration(needs: IntegrationNeeds) -> dict:
    """规则（按顺序判断）：
    needs_oauth_boundary、multi_tenant_governance、reused_by_multiple_clients 任一为真 → "mcp"；
    is_procedural_knowledge → "skill"；
    has_existing_cli 且 runs_locally_only → "cli"；
    其余 → "local_function"。
    返回 {"choice", "reasons"}，reasons 写明命中的条件。"""
def call_with_policy(session, tool_name: str, args: dict, token_scopes: set[str], required_scopes: dict[str, set[str]], timeout_s: float) -> str:
    """先授权，再调用 session.call_tool(name, args, timeout_s)，最后用 from_mcp_result 规整；
    授权失败返回“拒绝：<原因>”；session 抛 TimeoutError 时返回“工具超时：<name>”。session 由 gate 提供。"""
```

### 检查项（总数 ≥10）

工具描述转换；非 object schema 报错；文本拼接；`isError` 前缀；空结果；未知工具与缺少 scope；四个集成判断分支各至少一例；调用超时；授权失败时不调用 session。

### 参考实现

`mcp_practice.py`：若本机的 `mcp` SDK 支持，用进程内服务器暴露两个工具，再通过客户端会话调用，全程离线；接口以本机安装版本为准（2026-10-27 为 1.29.1），写明版本。不支持时打印提示。

---

## L4.15 复用现成 harness · 新增 · 清单（实操选做）

- **目录**：`chapters/part4-agents-langgraph/4.22-reuse-harness/`（新建）
- **课时**：2h（实操另计，选做）
- **岗位任务 / 面试题型**：T3、T7 / F3
- **README 必讲**：
  1. 候选及现状（注明来源与读取日期）：DeepSeek Harness（v0.1 开发者预览，2026-08-13）、Pi（TypeScript，0.x）、Claude Agent SDK、OpenAI Agents SDK 的沙箱 Agent、Pydantic AI Harness、LangChain Deep Agents。
  2. 什么时候复用、什么时候自己写：代码与脚本类任务适合复用；领域业务长链路更适合 L4.11 的执行面。
  3. 评估量表：隔离范围（文件、网络、进程）、权限与审批、版本稳定性、会话日志与可观测性、模型兼容、token 成本、失败处理。
- **CHECKLIST（实操时）**：
  - [ ] 使用一次性工作区，在容器或 VM 中运行；
  - [ ] 不放任何密钥；
  - [ ] 设置出网规则；
  - [ ] 锁定版本；
  - [ ] 只做一个可撤销的低风险任务；
  - [ ] 按量表打分，写进 workbook。

---

## L4.16 框架素养 · 改写 · 清单 + 练习

- **目录**：`chapters/part4-agents-langgraph/4.15-framework-landscape/`
- **课时**：3h
- **岗位任务 / 面试题型**：T3 / F3、F6
- **README 改写**：
  1. 用 2026 年的数据更新选型表：Stack Overflow 2026 编排框架使用率、雷达 Vol.34 的环位、Microsoft Agent Framework 1.0、OpenAI Agents SDK 仍为 0.x、Pydantic AI v2。均注明来源与读取日期。
  2. 原生概念与各框架 API 的对照：LangChain `create_agent` 与 middleware；LangGraph 的 StateGraph、checkpointer、interrupt；Deep Agents；OpenAI Agents SDK 的 Agent、Runner、handoff、guardrail、session；Pydantic AI 的 Agent、RunContext、deferred tools；Google ADK；Microsoft Agent Framework。
  3. 招聘现实：LangChain 在 AI/Agent 岗位中出现率约 23–35%。面试中怎么谈框架：讲需求与取舍，避免“什么都用 LangChain”。
- **练习**：新增 `create_agent_langchain.py`，用 LangChain `create_agent` 重写 L4.2 的订单工具循环；用 LangChain 自带的假聊天模型离线运行（类名以安装版本为准），并和原生版对比轨迹与代码行数。运行前需要安装 `langchain` 顶层包（2026-10-27 本机 `.venv` 缺失）。
- **CHECKLIST 更新**：对比矩阵至少包含原生、Pydantic AI、LangChain / LangGraph、OpenAI Agents SDK；写出选择、拒绝理由与退出成本。

---

## L4.17 Gate：异步专项 Agent · 新增 · gate + 产物

- **目录**：`chapters/part4-agents-langgraph/4.23-async-agent-gate/`（新建）
- **课时**：3h
- **岗位任务 / 面试题型**：T3、T4、T5 / F3、F4
- **学完能做**：组合 L4.5（Agent）、L4.11（执行面）、L4.12（沙箱策略）、L4.13（安全），完成一个异步专项 Agent，并用 pass^3 证明稳定性。

### 闭卷接口（`gate/starter.py`）

```python
def build_stages(agent_step, policy, tools) -> list:
    """返回 L4.11 的 Stage 列表，依次为：
    plan → gather（只读工具，调用前经 L4.12 的策略检查）→ draft → approve（needs_approval=True）→ publish（side_effect=True）。
    agent_step 是被注入的模型行为（gate 用脚本化替身）。"""
def run_e2e(store, task_id: str, stages: list, *, clock, side_effect_log: dict) -> "Task":
    """调用 L4.11 的 run_until_blocked；遇到 waiting_approval 时返回，由调用方批准后再次调用。"""
def run_trials(task_factory, k: int) -> dict:
    """同一任务独立运行 k 次，每次使用新的 store 与替身；返回 {"pass_at_1", "pass_all_k", "runs"}。"""
```

### gate 提供的故障场景（5 个）

1. gather 阶段工具超时 → 重试后成功；
2. draft 阶段崩溃 → 续跑，不重复执行 gather 的副作用；
3. 审批被拒 → failed，原因可读，未执行 publish；
4. 预算超出 → budget_exceeded；
5. gather 读到的恶意文档要求提前发布或调用禁止工具 → 被策略拦截并记录。

### 检查项（总数 ≥10）

正常路径成功；5 个故障场景各自的期望；publish 只执行一次；pass^3 统计正确；策略拦截有记录。

### 产物

离线 pass^3 报告，供 P4 使用。
