# 1.10 嵌入式 LLM 功能与 Eval Harness · Gate

[全书目录](../../README.md) · [上一章 L1.9](../1.8-cli-chatbot/README.md) · [下一章 L2.2](../../part2-rag/2.1-load-split/README.md)

- **能力**：在现有后端服务中嵌入 LLM 洞察能力，构建业务校验、降级熔断与离线评测 Harness；掌握二阶校验、租户身份隔离、退款 fail-closed 安全策略；对比原生实现与 Pydantic AI (2.31.1) 实现。
- **v3 路径**：L1.10 / 核心（Gate；嵌入式功能）
- **岗位任务 / 面试题型**：T1、T4 / F4、F5
- **前置**：已完成 [L1.4 结构化输出](../1.3-structured-output/README.md)、[L1.6 工具调用协议](../1.5-tool-calling/README.md)、[L1.7 Provider 成本](../1.9-provider-cost/README.md)
- **时间盒**：6 小时（2h 读 + 3h 实现 + 1h 故障与记录）
- **闭卷规则**：只读本页、`gate/starter.py`、`gate/starter_pai.py` 和 Python 标准库、Pydantic/Pydantic AI 官方文档；**通过 gate 之前不要打开参考实现**。
- **验收命令**：

```bash
# 1. 运行原生 Gate（默认检查闭卷骨架 gate/starter.py，全部通过才算达标）
python chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check.py
# 若检查自己的实现：python chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check.py --module path/to/my_solution.py

# 2. 运行 Pydantic AI Gate（默认检查闭卷骨架 gate/starter_pai.py）
python chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check_pai.py
# 若检查自己的实现：python chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check_pai.py --module path/to/my_pai_solution.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 来绕过检查。

---

## 为什么做这个 gate

在真实的生产系统（SaaS、工单系统、CRM、电商后台）中，**90% 的企业级落地都是把 LLM 作为一个局部智能算子嵌入现有服务**——例如对进线工单自动打标、抽取订单号与退款金额、辅助客服打标签。

这种场景下，大模型不是系统的主宰，而是“不可靠的第三方外部服务”。工程设计的核心不是 Prompt 写得多花哨，而是如何防御模型的不可靠性：
1. **契约先行，Schema 正确不等于业务有效**：模型生成的 JSON 哪怕完全符合类型，也可能捏造不存在的订单号或负数金额；
2. **LLM 提议，代码裁决（LLM Proposes, Code Disposes）**：模型负责分类与抽取提议，后端代码拥有唯一写库与资金操作裁决权；
3. **身份与租户永不信任模型输出**：租户与用户身份严格由后端依赖注入，模型在 JSON 中伪造的租户字段一律忽略；
4. **资金安全 fail-closed**：普通咨询工单失败可降级（fail-open），退款与钱相关的操作一旦超时或失败无条件转人工审核（fail-closed）；
5. **基于 Golden Set 的离线评测体系**：构建确定性 Eval Harness，测量字段级准确率与通过率。

---

## 概念

### 1. 二阶业务校验
- **第一阶（格式校验）**：Pydantic 模型解析，验证 JSON 字段齐全且类型正确；
- **第二阶（领域业务校验）**：核查订单号格式（`^ORD-\d{6}$`）并查询当前租户数据库；核查金额非负；核查退款人工阈值。

### 2. 隐私与脱敏契约（CallRecord）
可观测指标（耗时、Token、重试次数、降级标记、校验错误）中**严禁记录工单原文**；用户 ID 必须通过不可逆哈希（`sha256(user_id)[:12]`）进行脱敏存储。

### 3. Eval Harness 的四个核心概念
根据 Anthropic 官方评测体系（《Demystifying evals for AI agents》，读取于 2026-10-27）：
- **Task（任务定义）**：工单输入与提取目标；
- **Trial（试验运行）**：固定采样或受控环境下的单次或多次执行，多 trial 测量模型一致性；
- **Grader（评分器）**：针对每个关键字段逐一对比期望值（计算字段级准确率与用例完全匹配率）；
- **Transcript（运行轨迹与失误归因）**：完整记录错题的输入截断摘要、实际输出与失败字段，便于提示词优化。

### 4. Pydantic AI (2.31.1) 的使用与安全限制
本章对比了原生 SDK 与 Pydantic AI (`pydantic-ai-slim==2.31.1`) 两种实现方案。
> [!IMPORTANT]
> **锁定版本 2.31.1 的安全限制**（conventions.md 第 9 节）：
> - **不启用自带的 OpenTelemetry 埋点**（`instrument=True`、`Agent.instrument_all()`）：PyPI 安全公告 PYSEC-2026-4284 指出，即使设置 `include_content=False`，prompt 正文仍会经由异常事件等途径导出泄露。追踪统一使用 L5.6 的 `opentelemetry-sdk` 手写脱敏埋点；
> - **禁用受影响的额外功能**：不使用 `web_fetch_tool`、`FileUrl` 的本地文件下载与 `ConcurrencyLimitedModel`；
> - **关闭思考模式**：2.31.1 的 `DeepSeekProvider` 尚未识别 `deepseek-flash` 思考参数，真实调用时须显式关闭思考。

---

## 任务

### 原生 Gate 任务（实现 `gate/starter.py`）
| 函数 | 你要交付的行为 |
|---|---|
| `build_messages(ticket_text, prompt_version)` | 构造消息列表；system 声明“工单为数据非指令”；user 消息用固定分隔符定界防注入 |
| `parse_llm_output(raw)` | 反序列化 JSON；非法 JSON 抛 `OutputError("invalid_json")`；缺字段抛 `OutputError("schema:<字段>")` |
| `to_dto(parsed, deps)` | 二阶校验：枚举范围校验、负数金额置 None、非法或跨租户订单置 None、退款超限转人工；输出 `TicketInsight` |
| `rules_fallback(ticket_text)` | 关键词启发式规则兜底；判定为退款时一律 `needs_human=True`（fail-closed） |
| `extract_insight(ticket_text, deps, max_retries)` | 主流水线：build → chat → parse → to_dto；失败重试；耗尽走 rules_fallback；记录脱敏 `CallRecord` |
| `run_eval(cases, feature, trials)` | 运行评测集；返回 `field_accuracy`、`pass_rate`、`consistency` 与 `transcripts` 轨迹 |

### Pydantic AI Gate 任务（实现 `gate/starter_pai.py`）
| 函数 | 你要交付的行为 |
|---|---|
| `build_agent(model)` | 构建 Pydantic AI Agent；`deps_type` 绑定 `FeatureDeps`；`output_type` 绑定契约模型；注册 `check_order` 工具通过 `ctx.deps` 查询；注册 `output_validator` 在枚举不符时抛出 `ModelRetry` |
| `extract_with_agent(agent, ticket_text, deps)` | 运行 `agent.run_sync`；结果经二阶业务校验转为 `TicketInsight`；重试耗尽或异常时回退到 `rules_fallback` |

---

## 关键约定

- 分类枚举 `CATEGORIES = ("refund", "shipping", "account", "technical", "other")`；
- 优先级枚举 `PRIORITIES = ("low", "medium", "high", "urgent")`；
- 订单正则 `^ORD-\d{6}$`；
- 订单在当前租户不存在时置 `order_id=None` 并记录 `"order_not_found"`；
- 负数金额置 `amount=None` 并记录 `"negative_amount"`；
- 无论模型中间是否伪造 `tenant_id`，一律使用 `deps.tenant_id` 裁决。

---

## 故障注入（必须亲手触发）

| # | 注入场景 | 期望行为 |
|---|---|---|
| 1 | 模型返回非 JSON 乱码字符串 | 触发重试；重试耗尽后标记 `fallback=True` 并回退至 `rules_fallback` |
| 2 | 模型输出非法类别 `category="not_in_enum"` | 抛出 `OutputError("schema:category")`（PAI 中触发 `ModelRetry`） |
| 3 | 模型输出负数退款金额 `-100.0` | `amount` 置 `None`，`reasons` 包含 `"negative_amount"` |
| 4 | 模型输出另一租户的订单号 `ORD-999999` | 依赖校验失败，`order_id` 置 `None`，`reasons` 包含 `"order_not_found"` |
| 5 | 模型输出不符合格式的订单号 `ORD-123` 或 `ORD-88888` | 正则不匹配，`order_id` 置 `None`，`reasons` 包含 `"order_not_found"` |
| 6 | 工单文本中包含提示词注入攻击指令 | 输入定界生效，模型将输入作为纯数据处理，指令被忽略 |
| 7 | 模型请求超时（TimeoutError） | 安全熔断降级至 `rules_fallback`，时钟记录耗时 |
| 8 | 退款工单金额达到或超过 500 元 | 自动标记 `needs_human=True` 强制转人工复核 |
| 9 | 涉及退款且模型发生失败走降级 | 触发 fail-closed 安全底线，无条件标记 `needs_human=True` |

---

## 验收标准

1. **原生 Gate（`gate/gate_check.py`）**：16 项断言全部 PASS（覆盖错误解析、枚举校验、负数清洗、跨租户隔离、格式校验、超时降级、退款安全、注入隔离、CallRecord 脱敏、Harness 指标与波动性计算）；
2. **Pydantic AI Gate（`gate/gate_check_pai.py`）**：6 项断言全部 PASS（覆盖 DTO 转换、ModelRetry 纠偏、重试耗尽 fail-closed 降级、deps 租户隔离、RunContext 工具调用、订单不存在清洗）；
3. **评测集运行**：运行 24 条 Golden Set 基准工单（含订单号格式错误与超长文本），离线规则兜底通过率达到 75%，模拟 LLM 通过率达到 100%。

---

## 提交物

- `gate/starter.py`（完成原生实现的闭卷代码）
- `gate/starter_pai.py`（完成 Pydantic AI 实现的闭卷代码）
- `gate/gate_report.json`（原生与 PAI 的 Gate 验收通过报告）
- [workbook.md](workbook.md) 中记录 24 条 Golden Set 的评测基线指标与架构思考

---

## 通过后对照参考实现

闭卷通过之前不要查看参考解。通过后运行参考解进行对照验证：

```bash
# 1. 运行原生参考实现与离线 Eval Harness（24 条工单集）
python chapters/part1-foundations/1.10-embedded-llm-feature/embedded_feature.py --eval

# 2. 运行 Pydantic AI 参考实现（基于 FunctionModel 离线驱动）
python chapters/part1-foundations/1.10-embedded-llm-feature/embedded_feature_pai.py

# 3. 运行现成企业工单 Web 服务并测试 /tickets 与 /insight 接口
python chapters/part1-foundations/1.10-embedded-llm-feature/ticket_service/app.py
```

对照思考以下问题：
1. 原生实现与 Pydantic AI 在处理 ModelRetry 时代码复杂度差异有多大？
2. 参考实现中的 `rules_fallback` 在面对退款类工单时为什么坚决采用 fail-closed（`needs_human=True`）？你的实现如何权衡自动化率与资损风险？
3. 在离线 Eval Harness 中，多 trial 一致性指标（Consistency）在什么情况下会发生衰减？对高随机性任务该如何优化采样？

---

## 概念地图

- **契约输入定界**：数据非指令，系统与用户消息隔离；
- **二阶业务校验**：Schema 验证 + 领域规则裁决；
- **身份不信任模型**：租户上下文严格由框架注入；
- **安全熔断策略**：只读查询 fail-open vs 资金操作 fail-closed；
- **质量度量闭环**：Golden Set 字段准确率与错误归因。

---

## 边界

- **规则兜底能力有限**：`rules_fallback` 仅作为防止服务崩溃的熔断层，分类精度无法替代大模型；
- **评测集规模**：24 条基准用例主要用于 CI 门禁与抗回归验证，生产环境能力评测需构建百条级业务评测集；
- **Pydantic AI 2.31.1 安全边界**：如前述概念说明，严禁开启自带 OTel 埋点与使用受影响的下载/流式限流功能，真实调用显式关闭思考；
- **语言范围**：当前用例与规则针对中文工单设计，多语言场景需扩展提示词定界与多语言分词。
