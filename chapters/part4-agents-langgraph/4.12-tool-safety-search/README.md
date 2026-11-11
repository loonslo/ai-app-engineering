# L4.10 扩展：搜索信任边界 · Gate（原 4.12）

[全书目录](../../README.md) · [上一章 L4.12](../4.20-sandbox-least-privilege/README.md) · [下一章 L4.14](../4.21-mcp-practice/README.md)

- **能力**：把外部搜索结果标记为不可信资料；检测常见提示词注入；防止标签提前闭合。
- **v3 路径**：L4.13 / 核心（Gate；Agent 安全）
- **前置**：4.10、4.11。
- **时间盒**：6 小时（1h 读 + 4h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `tool_safety_search.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.12-tool-safety-search/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

搜索结果是外部资料，不是指令。最常见的错误：

- 直接拼进 prompt，网页里的“忽略之前规则”被执行；
- 外部内容自带同名闭合标签，提前跳出隔离区；
- 只靠提示词“不要听网页的”，没有程序化检测；
- 检测只覆盖中文，英文注入漏掉；
- 非字符串输入直接崩。

这个 gate 用固定文本，验证标签隔离和注入特征检测。

## Agent 安全：把授权放在模型之外

提示注入是把资料中的文字伪装成系统指令、工具权限或审批决定。标签和特征检测能帮助模型辨别资料、帮助人排查，但攻击者能换写法、翻译或把指令分散在上下文里；“未命中”不代表安全。模型仍可能被诱导，因此最小权限必须由模型之外的程序、凭据和执行环境强制实施。

### OWASP Agentic Top 10 对照

[OWASP 发布说明](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/)于 2025-12 发布 Agentic Top 10，文档版本称为 2026；不要把发布日期与版本年份混为一谈（读取于 2026-10-31）。下表是课程映射，不表示这些练习能消除对应风险；L 编号是 v3 逻辑编号，链接指向保留的物理目录。

| 编号 / 官方风险名 | 课程覆盖点与仍需补的边界 |
|---|---|
| ASI01 Agent Goal Hijack（目标劫持） | 本章 L4.13：不可信资料、注入演示；[5.7 安全护栏](../../part5-production/5.7-security-guardrails/README.md)：继续做输入/输出安全，不声称消灭注入 |
| ASI02 Tool Misuse（工具滥用） | [L4.8 工具设计 / 4.18](../4.18-tool-design/README.md)：小工具与参数契约；本章程序白名单；真实业务仍需目的端授权 |
| ASI03 Identity & Privilege Abuse（身份与权限滥用） | [L4.12 沙箱 / 4.20](../4.20-sandbox-least-privilege/README.md)：短期最小权限凭据；[L4.14 MCP / 4.21](../4.21-mcp-practice/README.md)：scope；不是生产身份系统 |
| ASI04 Agentic Supply Chain Vulnerabilities（供应链漏洞） | L4.14 MCP：工具描述/结果不可信、服务接入取舍；仍需来源核验、版本锁定与供应链审查 |
| ASI05 Unexpected Code Execution（意外代码执行） | L4.12：路径、命令、网络和容器边界；Python 策略函数不能代替 OS 隔离 |
| ASI06 Memory & Context Poisoning（记忆与上下文投毒） | [L4.10 检查点 / 4.10](../4.10-checkpoint-context/README.md)：快照隔离；本章资料边界；深拷贝不等于内容可信 |
| ASI07 Insecure Inter-Agent Communication（不安全的 Agent 间通信） | [4.14 多 Agent](../4.14-supervisor-fanout/README.md)：分工/汇聚边界，L4.14 MCP：消息不等于授权；真实通信鉴权与完整性未由 gate 覆盖 |
| ASI08 Cascading Failures（级联失败） | [4.6 节点可靠性](../4.6-node-reliability/README.md)、[L4.11 执行面 / 4.19](../4.19-agent-execution-plane/README.md)：错误分类、阶段记录、预算和取消；仍需生产故障演练 |
| ASI09 Human-Agent Trust Exploitation（利用人对 Agent 的信任） | [L4.10 HITL / 4.11](../4.11-streaming-hitl/README.md)：从可信状态审批；本章网页“已通过审核”不能成为审批 |
| ASI10 Rogue Agents（失控 Agent） | L4.11 执行面和 [L4.17 异步综合 gate / 4.23](../4.23-async-agent-gate/README.md)：预算、取消、故障注入；这些是限制损害，不是对自主行为的完整证明 |

### LLM Top 10 的版本变化与证据边界

[OWASP LLM Top 10 2026 资源页](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/)确认 2026 版更新了排序与威胁覆盖；[官方发布新闻](https://genai.owasp.org/2026/09/01/owasp-genai-security-project-unveils-2026-top-10-for-llm-applications-new-agent-control-standard-and-sponsors-as-community-tops-30000-members/)所载项目参与者引语明确说 Excessive Agency（过度代理权）现列第三（均读取于 2026-10-31）。它关注的不只是“模型说错什么”，而是被诱导后能调用什么工具、接触什么数据、造成什么动作。

本次读取 PDF 下载入口返回 No Access；已读取的资源页/新闻没有列出提示注入的 2026 名次，因此这里不复述“2026 提示注入仍居第一”的未核实断言，也不拿 2025 的编号冒充 2026 排名。学习重点不依赖名次：不能靠提示与过滤根除攻击，要在模型外拒绝越权工具和参数、限制凭据与出网，并在高风险动作前核验真人审批。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `as_untrusted` | 删除伪造标签后，用 `<untrusted_search_results>` 包裹 |
| `detect_injection` | 按顺序返回命中的注入特征；无命中 [] |

关键口径：

- 先删除文本中所有 `<untrusted_search_results>` / `</...>`，再包裹。
- 输出开始/结束标签各一个。
- 至少检测：忽略之前/以上、ignore previous/all previous、system prompt/系统提示词、已通过审核。
- 非字符串 -> `ValueError`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 正常资料 | 被正确包裹 |
| 2 | 文本自带开/闭标签 | 伪造标签被清除 |
| 3 | 中文注入 | 命中“忽略之前/系统提示词” |
| 4 | 英文注入 | 命中 ignore previous |
| 5 | 正常搜索文本 | [] |
| 6 | 非字符串 | `ValueError` |

## 验收标准

`gate_check.py` 的 5 项全部 PASS：

- 包装、清理伪造标签、包装类型、注入检测、检测类型。

通过后，在 [workbook.md](workbook.md) 写：

1. 标签隔离能保证安全吗？它降低了什么风险？
2. 为什么真正的授权要靠工具白名单/参数校验/HITL？
3. 注入检测漏报/误报的代价是什么？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（5/5）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.12 tool_safety_search.py
# 显式调用真实模型，搜索仍用固定教学资料：
python tools/run_chapter.py 4.12 tool_safety_search.py --live
# 还要真实搜索时，另需可选 tavily-python 与 TAVILY_API_KEY：
python tools/run_chapter.py 4.12 tool_safety_search.py --live --live-search
```

默认原生 Python 路径不导入 LangChain / LangGraph，不创建模型客户端、不读取 `.env`、不联网，固定资料与脚本模型输出可复现。三段演示保持为：

1. 原生 Chat Completions 工具循环：记录工具调用、结果与答案，最多 4 轮；只允许 `web_search`，参数必须只有非空 `query`，结果先包装再回灌。不展示模型隐藏推理。
2. 搜索 → 总结 → SQLite 草稿快照 → 审批恢复：按 `thread_id` 保存待审状态，重新创建执行器后从同一 SQLite 文件恢复，演示代码显式提交 yes。这是**脚本化审批输入，不是真人审批**；拒绝路径用 `resume(thread_id, "no")`。临时目录在演示结束后删除；生产必须用受保护的持久目录。
3. 固定注入资料：打印命中特征、包装后的文本与总结，核对是否执行了网页伪指令。离线脚本答案是确定性流程替身，不能据此断言模型抗注入；真实模型需另做攻击集评测。

`--live` 才经 `common.get_openai_client()` / `common.chat_model_name()` 创建客户端，模型 ID 从公共配置读取，可能产生费用；DeepSeek 请求显式关闭思考，不强制 `tool_choice`。`--live-search` 必须同时给 `--live`，搜索错误不会静默回退成模拟成功。缺配置、缺依赖、网络或 SDK 错误都会给可读提示并退出 1，不打印 traceback。模式输出区分真实模型与固定资料；`example.com` 只是教学来源，不可当作真实引用证据。

接口依据：[OpenAI Function calling](https://developers.openai.com/api/docs/guides/function-calling) 的 Chat Completions 工具调用流程、[DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode) 的 `extra_body` 开关（读取于 2026-10-31）。这里仅支持所配置模型的 Chat Completions 工具接口；不能把“OpenAI 兼容客户端”当成所有模型都支持同一端点的保证。

对照时只回答：

1. 参考实现的 `as_untrusted` 怎么处理伪造标签？
2. 参考实现的提示词怎么说明标签内只是资料？
3. 标签隔离之外，参考实现还靠哪些程序化边界？

## 概念地图

- **外部资料**：证据，不是指令。
- **标签隔离**：明确边界，降低注入影响。
- **伪造标签**：先清理再包裹，防止提前闭合。
- **注入检测**：特征匹配，漏报/误报都要评估。
- **程序化授权**：工具白名单、参数校验、HITL。

## 边界

- gate 只测文本包装/检测，不调用模型。
- 通过 gate 不证明模型不会被注入；标签隔离只是辅助。
- 系统性防护见 5.7 和第 7 篇。
- SQLite 示例只保存完成的草稿和待审/完成状态，没有 worker 自动重启、审批鉴权、并发消费锁或外部副作用事务；这些属于 L4.11 执行面与真实系统的责任。
- 原生重写保留三段演示与被旧测试导入的 `as_untrusted` 名字/标签行为；七个历史 gate 未改，图/HITL 教学行为保留，4.3/4.6/4.10 仅做安全入口接线与同义 API 参数对齐。真实模型、Tavily、跨进程崩溃及生产权限未实测。
