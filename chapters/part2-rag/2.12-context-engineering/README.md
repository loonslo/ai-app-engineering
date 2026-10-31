# 2.12 上下文工程总论 · Gate

[全书目录](../../README.md) · [上一章 L1.10](../../part1-foundations/1.10-embedded-llm-feature/README.md) · [下一章 L2.2（2.1）](../2.1-load-split/README.md)

- **能力**：按 Token 预算确定性组装上下文段落；保证静态前缀稳定以最大化 Prompt Caching 命中；识别破坏缓存的时间戳与单段体积超限；掌握上下文工程的六大失败模式与防御策略。
- **v3 路径**：L2.1 / 核心（Gate；上下文工程）
- **岗位任务 / 面试题型**：T2、T3 / F3
- **前置**：已完成 [L1.10 嵌入式 LLM 功能与 Eval Harness](../../part1-foundations/1.10-embedded-llm-feature/README.md)
- **时间盒**：4 小时（1.5h 读 + 2h 实现 + 0.5h 记录）
- **闭卷规则**：只读本页、`gate/starter.py` 和 Python 标准库文档；**通过 gate 之前不要打开参考实现**。
- **验收命令**：

```bash
python chapters/part2-rag/2.12-context-engineering/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 来绕过检查。

---

## 为什么做这个 gate

在生产级 LLM 应用开发中，初学者往往把上下文窗口视为“无底洞”，将所有资料、历史、工具说明和临时变量一股脑拼入 Prompt。然而：
1. **真实成本与延迟**：每次调用的计费与时延与输入 Token 长度呈正比；
2. **注意力稀释（Lost in the Middle）**：模型注意力随上下文长度增长而衰减，过长的无关背景会显著降低对关键业务规则的遵循度；
3. **缓存击穿资损**：若在静态 Prompt 前缀中夹杂动态时间戳、随机数或易变变量，会导致底层前缀缓存（Prompt Caching）100% 击穿，造成高达数倍的算力与资金浪费。

本 gate 要求你脱离第三方框架，用纯 Python 实现确定性的上下文装配与审查引擎：严格遵循“静态前置、Required 保证、优先级丢弃、去重告警、易失审查”。

---

## 概念

### 1. 上下文的六大组成部分
一个生产级 Agent 或 RAG 请求的上下文通常由以下部分装配而成：
- **系统指令（System Instructions）**：智能体人设、不可违反的系统级安全红线；
- **知识与事实（Knowledge / Facts）**：从知识库或检索系统召回的片段；
- **工具定义（Tool Schemas）**：可用外部工具的名称、参数契约与说明；
- **长期记忆（Long-term Memory）**：用户画像、跨会话偏好事实；
- **对话历史（Conversation History）**：当前会话最近的多轮输入与输出；
- **输出格式约束（Format Constraints）**：JSON Schema、枚举或业务 DTO 契约。

### 2. Token 预算与注意力经济
上下文中的每一个字符都在消耗 Token 算力、推理延迟和模型有限的自注意力。生产系统的上下文工程核心就是“在固定预算下选择最高信息密度的片段”。

### 3. 静态与动态：Prompt Caching 的黄金法则
所有主流大模型服务商（Anthropic、DeepSeek、OpenAI）的 Prompt Caching 机制均要求**前缀完全一致**：
- **静态内容必须在前**：固定人设、静态业务政策、未修改的工具说明必须作为头部前缀；
- **动态内容严格后置**：易变的时间戳、用户提问、动态历史只能追加在末尾。
> [!NOTE]
> 行业数据：根据 Datadog 发布的报告《State of AI Engineering》（https://www.datadoghq.com/state-of-ai-engineering/ ，读取于 2026-10-28）：在企业级生产调用中，**System Prompt 平均占输入 Token 的 69%**，然而在所有具备缓存潜力的调用中，**仅有约 28% 真正命中了前缀缓存**。导致未能命中的主要原因正是“静态前缀中夹杂动态易变变量”。

### 4. 解决上下文膨胀的四种技术手段
- **渐进披露（Progressive Disclosure）**：初始仅暴露元数据（如 Skill 名称与描述），模型确认需要时再动态加载正文；
- **按需检索（On-demand Retrieval）**：非全局注入，只在遇到具体问题时通过向量或关键字索引局部召回；
- **上下文压缩（Compaction）**：长会话多轮压缩摘要，剔除冗余沟通，保留核心事实；
- **子 Agent 隔离（Sub-agent Isolation）**：将复杂子任务委托给拥有独立精简上下文的子智能体。

### 5. 指令膨胀（Instruction Bloat）与雷达评级
> [!IMPORTANT]
> 架构趋势：在 Thoughtworks 技术雷达 Vol.34（https://www.thoughtworks.com/radar ，读取于 2026-10-28）中：
> - **Agent instruction bloat（智能体指令膨胀）** 被列入 **Caution（警惕）**：盲目堆砌成千上万行 Prompt 会导致指令互相冲突、模型遵循率大幅下跌；
> - **Context engineering（上下文工程）** 被列入 **Adopt（采纳）**：提倡系统化治理上下文结构、预算分配与缓存生命周期。

### 6. 常见上下文工程三大失败模式
- **上下文污染（Context Poisoning）**：恶意的用户输入注入了伪造的系统级规则；
- **注意力分散（Distraction）**：无关检索召回片段淹没了核心指令；
- **指令冲突（Instruction Conflict）**：通用 Prompt 与特定业务规则说法相左，模型产生逻辑摇摆。

---

## 任务与关键约定

在 `gate/starter.py` 中实现下列核心组件与函数：

| 函数 / 类型 | 你要交付的行为 |
|---|---|
| `count_tokens` | 确定性字符近似计量：`math.ceil(len(text) / 3.5)`，空串为 0 |
| `assemble_context` | 装配上下文：去重并产生 warning；校验 required 段落不超预算；非 required 按 priority 降序放入；输出先 static 后 dynamic；计算 static 前缀 SHA256 哈希 |
| `lint_context` | 静态审查：检查 static 中是否混入日期时间，检查单段是否超过 50% 预算 |

关键约定：
1. **去重规则**：同一 name 重复出现或同一 text 重复出现，仅保留首次出现的段落；后续重复项记入 warnings：`duplicate:<name>`。
2. **熔断规则**：若所有 `required=True` 段落的 Token 之和已超过 budget，立即抛出 `ContextBudgetError`。
3. **前缀哈希**：`static_prefix_hash` 为纳入的所有 static 段落拼接正文的 SHA-256 十六进制摘要；若无 static 段落则为空字符串 `""`。
4. **拼接格式**：各段落正文之间使用双换行 `\n\n` 拼接，不添加多余前后空格。

---

## 故障注入自测表

| 故障注入场景 | 预期系统行为 | 验证断言 |
|---|---|---|
| static 段落中意外硬编码了当前日期时间 | Lint 审查命中并告警 | `volatile_in_static:<name>` 出现于 warnings |
| 单个段落内容极其庞大，耗尽了超 50% 的预算 | Lint 审查命中并告警 | `oversized:<name>` 出现于 warnings |
| required=True 的必须条款本身即超出 budget | 立即抛出 ContextBudgetError 熔断 | 抛出 `ContextBudgetError` |
| 列表中存在同名或相同文本的段落 | 仅保留首次出现，后续段落丢弃 | 仅保留 1 条且产生 `duplicate:<name>` warning |
| 预算不足容纳全部非 required 段落 | 低 priority 段落被丢弃，高 priority 获得保留 | 低优段落进入 `dropped`，高优进入 `included` |
| 仅修改动态提问内容，系统静态规则未变 | 前缀缓存哈希必须完全一致 | `res1.static_prefix_hash == res2.static_prefix_hash` |

---

## 验收标准

1. `gate/starter.py` 闭卷实现并通过全部 11 项断言检查（退出码 0）；
2. 骨架默认状态下必须 0 项通过，退出码 1；
3. `gate/gate_report.json` 写入标准结果，标识为 `"L2.1-context-engineering"`；
4. 完成 [workbook.md](workbook.md) 中的设计思考记录。

---

## 提交物

- `gate/starter.py`（完成实现的闭卷代码）
- `gate/gate_report.json`（11/11 全部通过报告）
- [workbook.md](workbook.md) 中记录上下文装配分析

---

## 通过后对照参考实现

通过 gate 之前不要阅读参考解。通过后运行参考实现进行对照：

```bash
python chapters/part2-rag/2.12-context-engineering/context_engineering.py
```

若配置了模型 API 密钥，可加 `--live` 参数测试两次连续相同前缀请求下的真实缓存命中情况：
```bash
python chapters/part2-rag/2.12-context-engineering/context_engineering.py --live
```

对照思考以下问题：
1. 参考实现如何通过稳定排序保证相同 priority 段落输入顺序的一致性？你的实现做到了确定性吗？
2. 为什么计算 `static_prefix_hash` 时必须仅针对纳入的 static 段落进行拼接？
3. 对比 Datadog 报告中 28% 的缓存命中率，你的系统在架构上如何从根源防御时间戳泄露？

---

## 概念地图

- **前缀确定性**：static 段落严格前置；
- **预算硬约束**：优先丢弃低优，保证 required 段落完整交付；
- **缓存健康度**：Lint 拦截动态时间戳污染；
- **信息密度**：单段体积预警，拒绝巨型臃肿文档直接灌入。

---

## 边界

- **Token 计数模型**：本章 `count_tokens` 为离线纯数学确定性近似计数（CJK 字符 = 1，西文非空词片段 = 1），真实生产中根据所选模型使用对应的 Tokenizer（如 `tiktoken`、`tokenizers`）；
- **缓存实现机制**：Prompt Caching 由大模型服务商服务端管理（服务端通常要求静态前缀达到最小长度，如 1024 Token 才会开启前缀索引）；
- **动态切分粒度**：对于超大段落，本章通过 Lint 告警，生产环境可结合后续 L2.2 文本切分器与 L2.10 压缩器进行动态分片或摘要。
