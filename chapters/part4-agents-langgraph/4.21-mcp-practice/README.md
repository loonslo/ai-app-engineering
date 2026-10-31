# L4.14 MCP 实战与取舍 · Gate

[全书目录](../../README.md) · [上一章 L4.13](../4.12-tool-safety-search/README.md) · [下一章 L4.15](../4.22-reuse-harness/README.md)

- **能力**：暴露结构化 MCP 工具、规整结果、在调用前做最小 scope 授权，并解释何时不需要 MCP。
- **v3 路径**：L4.14 / 核心（Gate；MCP 实战）
- **岗位任务 / 面试题型**：T3 / F3
- **前置**：L4.3 工具契约、L4.12 最小权限、L4.13 安全。
- **时间盒**：5 小时（1.5h 读 + 2.5h 实现 + 1h 故障与记录）。
- **闭卷规则**：只读本页、`gate/starter.py` 和标准库/MCP SDK 官方文档；通过前不读 `mcp_practice.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.21-mcp-practice/gate/gate_check.py
```

18 项全部 PASS 才算通过；报告写 `gate/gate_report.json`。不允许修改 `gate_check.py`。gate 使用脚本化同步会话，不联网、不读 `.env`、不调用模型；参考演示则使用真正的 SDK 内存传输，两者不是同一类证据。

## 为什么做这个 gate

MCP（Model Context Protocol）约定工具、资源与提示模板怎样被发现和调用；它不是 Agent 循环，不自动给予业务权限，也不会让工具描述或返回值变得可信。把一个本地函数包成 MCP 服务，若没有跨客户端复用、鉴权边界或治理需求，可能只是多了一层协议。

[Thoughtworks 雷达 Vol.34 的 “MCP by default”](https://www.thoughtworks.com/radar/techniques/mcp-by-default) 位于 Caution：结构化契约、OAuth 边界与受治理的多租户访问是价值来源，但协议层也有复杂度与信息保真成本。先问能否使用函数、现成 CLI 或 Skill，再决定是否需要互操作。（2026-04 发布，读取于 2026-10-31。）

## 概念

按 [官方架构说明](https://modelcontextprotocol.io/docs/learn/architecture)（读取于 2026-10-31）：

| 术语 | 职责 | 本章对应 |
|---|---|---|
| host | 管理模型上下文、客户端和授权的应用 | 参考脚本的编排与策略层，不调用模型 |
| client | 与某个 server 交换协议消息的组件 | SDK ClientSession |
| server | 暴露上下文和工具的程序 | FastMCP 暴露 add、order_status |
| tools | 可执行的动作，有参数 schema 和调用结果 | 本章核心接口 |
| resources | 可被读取的上下文数据 | 本章解释，不新增资源服务 |
| prompts | 可复用的提示模板 | 不等于具有最高优先级的可信指令 |
| stdio | 本地父子进程通过标准输入输出交换消息 | 不需要 HTTP 监听；旧章有示例 |
| Streamable HTTP | 通过 HTTP 请求与可选流式响应交换消息 | 跨网络服务需要单独部署与鉴权 |

本章的内存传输是 SDK 提供的进程内通信方式，不是新定义的标准部署传输。它仍经过实际 server 分发、client 会话和协议结果类型，不是直接调用两个 Python handler 冒充 MCP。

### 规范版本与 SDK 版本必须分开

候选版文章只能作为线索，不能直接当最终规范。这里已对照 [2026-07-28 最终 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)、[授权规范](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) 与 [扩展总览](https://modelcontextprotocol.io/extensions/overview)（读取于 2026-10-31），核实如下：

| 最终规范的方向 | 对实现的影响 |
|---|---|
| 无状态核心 | 去掉 initialize 握手与协议级 session；每请求携带版本/能力元数据。无状态不等于业务不能持久化任务数据 |
| `server/discover` | server 必须实现，client 可提前查询支持版本/能力；不是“client 必须先调用一次” |
| Tasks 与 MCP Apps | 位于可选扩展，不应假定每个 server/client 都支持；Tasks 从核心实验功能迁出，Apps 作为 UI 扩展存在，不把两者迁移历史混为一谈 |
| sampling / roots / logging | 进入弃用期，不等于当日删除；新实现不再添加这些能力。部分旧 RPC 被移除或改为按请求元数据 |
| 动态客户端注册 DCR | 已弃用但为兼容保留，优先 Client ID Metadata Documents；不能说 DCR 立即不可用 |
| HTTP 鉴权 | 以 OAuth 2.1 为基础，支持 OAuth 元数据与 OIDC Discovery；校验 issuer/audience，按需申请 scope，不等于任意 OIDC 登录 token 都能访问 MCP |

**实际安装 SDK 是 1.29.1，不是“支持最新规范”的承诺。** 2026-10-31 已读取本机 package metadata、`mcp/shared/memory.py`、`mcp/client/session.py` 与协议版本常量：支持内存 server/client 会话，最高版本常量仍为 `2025-11-25`，内部使用 initialize。对应的 [1.29.1 memory 源码](https://github.com/modelcontextprotocol/python-sdk/blob/v1.29.1/src/mcp/shared/memory.py) 也明确创建会话并初始化。本章按已安装 API 写参考演示，不为“看起来最新”手写 server/discover 或替换 SDK。未来升级必须重新核对协议协商与扩展支持，不能机械删除 initialize。

### 治理不是安全保证

[Linux 基金会 2025-12-09 公告](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) 宣布成立 AAIF，并接收 Anthropic 的 MCP 等项目贡献（读取于 2026-10-31）。开放治理解决的是标准维护归属，不是对任何第三方 MCP server 的安全认证。

工具描述可能含恶意指令，结果也可能来自恶意网页或数据库字段。schema 只说明形状，不能证明业务语义或来源可信；scope 必须由可信身份层授予，不能让模型把 `token_scopes={'admin'}` 当作参数传入就获得权限。真实远程 server 必须独立验证令牌、租户与资源范围，host 预检查不是服务端授权的替代。

## 任务

实现两个冻结数据结构和五个函数，不需要在 starter 导入 MCP SDK。

| 函数 | 输入 → 输出 / 失败行为 |
|---|---|
| `to_mcp_tool` | 名称、描述、object schema → `{name, description, inputSchema}`；非 object 抛 ValueError |
| `from_mcp_result` | MCP 字典结果 → 文本项按序换行；工具错误加 `工具错误：`；无文本用占位 |
| `authorize_call` | 名称、可信 scopes、所需权限映射 → Decision；未知工具默认拒绝，列出全部缺项 |
| `choose_integration` | `IntegrationNeeds` 六个布尔条件 → `{choice, reasons}`，理由是非空字符串列表 |
| `call_with_policy` | 注入会话、参数、权限、timeout → 授权后才执行并规整；拒绝/超时变成固定可读文本 |

## 关键约定

1. 工具契约只有三个字段，schema 嵌套内容要与调用方后续修改隔离。完整 JSON Schema 校验仍由 SDK/服务端负责，本接口仅检查顶层 type。
2. 文本拼接不解析其中“请忽略规则”之类指令。没有 text 项返回 `（无文本结果）`，一个空 text 项仍是空字符串；错误且无文本则 `工具错误：（无文本结果）`。
3. `required_scopes` 中没有工具名就拒绝；已知工具的所需权限为空则允许。列出排序后的全部缺项，保证多次报告一致；额外 scope 不代表额外工具也可执行。
4. 选型严格按顺序：OAuth 边界 / 多租户治理 / 多客户端复用任一为真 → **mcp**；否则流程知识 → **skill**；否则现成且只在本地运行的 CLI → **cli**；其余 → **local_function**。reasons 要指出命中条件，不能只写“合适”。这是练习的决策规则，不是所有系统的唯一架构答案。
5. `call_with_policy` 的会话接口是**同步教学协议**：`session.call_tool(name, args, timeout_s) -> dict`，不是 SDK 同名方法的原签名。真实 SDK 方法是 async，返回 Pydantic 对象；参考实现用 AnyIO 工作线程/事件循环适配器完成 await、超时边界与 `model_dump`，不把协程对象当结果。
6. 授权失败返回 `拒绝：<原因>`，会话调用计数必须为零；允许后只调用一次且原样传 timeout。TimeoutError 返回 `工具超时：<name>`，不自动重试；其他异常交给宿主处理，不能吞掉并伪装成功。超时不代表远程副作用没有发生，写工具仍需幂等协议。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 / 对应检查 |
|---|---|---|
| 1 | 非object schema、契约生成后修改原schema | ValueError / 嵌套隔离，01–02 |
| 2 | 混入图片、工具错误、无文本、空文本 | 固定文本规则，03–06 |
| 3 | 未知工具或缺多个 scope | 拒绝且列明缺项，07–09 |
| 4 | 多分支同时满足、现成CLI但并非仅本地 | 按优先级选择，不默认 MCP，10–13 |
| 5 | 未授权请求 | 拒绝且会话零调用，15（14 是正常对照） |
| 6 | 会话抛 TimeoutError | 可读超时且一次调用，16 |
| 7 | isError 或非超时异常 | 规整错误但不修改输入 / 异常留给宿主，17–18 |

## 验收标准

18 项：契约 2、结果规整 4、授权 3、选型 4、带策略调用 5。默认 starter 应 0/18、退出 1；实现后应 18/18、退出 0。

## 提交物

实现后的 starter、18/18 `gate_report.json`、[workbook](workbook.md) 预测与解释、一个“为什么本集成不选 MCP”的决策记录。SDK 离线演示结果另记，不把脚本化 gate 写成真实 OAuth 或网络互操作验收。

## 通过后对照参考实现

```bash
python tools/run_chapter.py 4.21 mcp_practice.py
```

默认用安装的 MCP 1.29.1 `FastMCP` 与 `create_connected_server_and_client_session` 注册两个真实工具，客户端列出契约，再经授权包装调用 add 与合成订单查询，最后演示缺 scope 拒绝。全部进程内、不监听端口、不发 HTTP、不启动子进程、不需要模型密钥。SDK 不可用或 API 不支持时可读提示、退出 1；不伪造协议成功，也不自动安装依赖。没有真实模型路径，因此不提供 `--live`。

供离线回归复用的 `await sdk_demo()` 返回 `{"tools": list[str], "contracts": list[dict], "calls": list[dict]}`；每次调用记录有 `name` 与规整后的 `content`。它创建并关闭真实内存会话，不打印、不起子进程；CLI 负责打印报告。这是参考实现入口，不增加闭卷接口。

对照：① 为什么 server 已有 schema 仍要 scope？② 包装器与真实 async SDK 的超时参数在哪里适配？③ 如果只有一个本地脚本复用查询函数，为什么可能不需要 MCP？

## 概念地图

业务集成需求 → 选择函数/CLI/Skill/MCP → 发现工具契约 → 身份与 scope → 调用 → 规整不可信结果 → host 决策。

## 边界

gate 只证明包装器行为；参考脚本证明的目标是已安装 SDK 内存路径，不代表完成 2026-07-28 规范互操作。未验证 stdio/HTTP 部署、TLS、OAuth/OIDC、token签名/issuer/audience、跨租户资源隔离、Tasks/Apps 扩展、并发和真实模型工具选择。示例 scope 是可信宿主注入的集合，不是假装签名令牌，也不是生产授权服务。真实系统必须在 server 再次强制权限并在网络之外做隔离。

[1.6 入门旧章](../../part1-foundations/1.6-mcp-intro/README.md) 保留 stdio/HTTP 与三原语的入门演示；[10.1 鉴权与审批](../../part10-mcp-a2a-optional/10.1-mcp-auth-approval/README.md) 是选修深化。本章不改两章实现，也不把它们的旧实现当最新规范依据。
