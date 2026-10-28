# L2.9 静态上下文与 Skills · Gate（2.13）

[全书目录](../../README.md) · [上一章 2.10](../2.10-chroma-persist/README.md) · [下一章 2.14](../2.14-memory-compaction/README.md)

- **能力**：读懂并编写 `AGENTS.md` 与 `SKILL.md`；实现渐进披露的 Skill 加载；发现说明文件里的指令膨胀与疑似硬编码密钥。
- **v3 路径**：L2.9 / 核心（Gate；静态上下文与 Skills）
- **前置**：2.12（上下文工程总论）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 审计分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `skills_loader.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.13-static-context-skills/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许修改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

在当今 Agentic Coding 与自主微智能体开发中，静态上下文（说明文件、System Prompt、Skills）构成了 Agent 推理的宪法级底座：

1. **项目级静态说明**：`AGENTS.md`（面向通用编码 Agent）、`CLAUDE.md` 等文件为智能体明确规定了仓库代码边界、禁止修改目录（如本项目的旗舰快照与日常 vault 边界）、构建命令与验证契约。
2. **开放标准 Agent Skills**：2025-12-18 发布的 [agentskills.io](https://agentskills.io) 开放标准（*规范读取核对日期：2026-10-28*）定义了文件夹级的可复用技能单元：每个 Skill 包含带有 YAML frontmatter（声明 `name` 与 `description`）的 `SKILL.md`，以及可选的 `scripts/` 与 `references/`。
3. **渐进披露（Progressive Disclosure）**：若在智能体初始化时将所有 Skill 的完整操作指南与脚本代码全量灌入 System Prompt，将引发灾难性的**指令膨胀（Instruction Bloat）**——大量无关 token 抢占注意力窗口，首 Token 延迟飙升，且互相冲突的规则极易被模型选择性忽略。渐进披露要求启动阶段仅在上下文注入 `name` 和 `description` 索引列表；仅当任务命中时才按需读取完整 `body` 与参考文档，通常可降低 60%~80% 的前缀 Token 损耗。
4. **安全与供应链风险**：Thoughtworks 技术雷达 Vol.34 指出，恶意代码注入与不受控执行的风险已从 MCP 协议进一步延伸至 Agent Skills。说明文件中可能潜藏过期的硬编码密钥（如 `sk-`、`AKIA`），或诱导 Agent 运行非安全沙箱脚本的提示词注入。

这个 gate 验证一个合规、安全、轻量且具备渐进披露能力的 Agent Skills 加载与巡检引擎。

## 任务

实现 `gate/starter.py` 的数据结构与五个函数：

| 函数 / 接口 | 你要交付的行为 |
|---|---|
| `parse_skill_md` | 解析 `SKILL.md`：严格以 `---` 起止 frontmatter；单行解析 `key: value`（不依赖 PyYAML）；校验 name 与 description 约束；分离正文 body |
| `build_index` | 构造摘要索引行 `"- <name>: <description>"`；超预算截断并追加 `"（另有 N 个 Skill 未列出）"`；索引绝不能包含正文 body |
| `select_skills` | 计算任务描述与 Skill 描述的分词交集重合度；按重合数降序初筛返回前 `limit` 个 name；无重合返回 `[]` |
| `load_skill` | 渐进加载：首次加载返回 body 并记入 `loaded`；重复加载返回 `""`；未知技能抛 `SkillNotFound` |
| `lint_instructions` | 静态安全质量巡检：行数超限报 `"too_long"`；重复非空行报 `"duplicate_line:<行号>"`；疑似硬编码密钥报 `"secret_like:<行号>"` |

关键口径（依据 agentskills.io 2026-10-28 规范）：
- `name`：必填，1~64 字符，仅限小写字母、数字和连字符 `-`，且必须以字母或数字开头。
- `description`：必填，1~1024 字符的非空描述文本。
- 格式错误均必须抛出 `SkillFormatError`，说明具体原因。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 | 对应检查项 |
|---|---|---|---|
| 1 | 有效的 `pdf-reader` Skill | 成功提取 name、description 与 body，不含分界符 | 01 |
| 2 | 缺少 `---` 起始/闭合 frontmatter | 抛出 `SkillFormatError` | 02 |
| 3 | frontmatter 缺少 `name` 字段 | 抛出 `SkillFormatError` | 03 |
| 4 | `name` 含大写或非法字符 | 抛出 `SkillFormatError` | 04 |
| 5 | 构建索引包含正文 body | 断言失败，索引严禁泄露正文 | 05 |
| 6 | 索引超出预算 | 截断并追加 `"（另有 N 个 Skill 未列出）"` 提示 | 06 |
| 7 | 多关键词重合与单关键词重合 | 按重合数排序，高重合优先返回 | 07 |
| 8 | 任务与所有技能零词汇重合 | 返回空列表 `[]` | 08 |
| 9 | 第二次加载相同 Skill | 返回空串 `""` 防止上下文重复膨胀 | 09 |
| 10 | 请求不存在的 Skill | 抛出 `SkillNotFound` | 10 |
| 11 | 说明文件含超长行数、重复规则行、`sk-` 疑似密钥 | 分别命中 `too_long`、`duplicate_line`、`secret_like` | 11 |

## 验收标准

`gate_check.py` 的 11 项全部 PASS：

1. 合法 SKILL.md 解析
2. 缺少 frontmatter
3. 缺少 name 字段
4. 字段不符合约束
5. 索引仅含 name 与 description
6. 超预算截断提示
7. 选择初筛排序与截断
8. 无重合词返回空列表
9. 首次加载与重复加载防重
10. 未知技能抛 SkillNotFound
11. 指令文件三重 Lint 告警

通过后，在 [workbook.md](workbook.md) 中记录并回答三个深入问题。

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（11/11）。
- workbook 里的失败注入与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 2.13
```

对照时只回答：

1. 参考实现演示了全量加载与渐进披露的 Token 对比；渐进加载节约了多少比例的静态上下文开销？
2. 为什么 agentskills.io 规范严禁 Skill name 使用大写或下划线？这与模型工具调用函数命名有何关系？
3. `lint_instructions` 中对疑似密钥的正则拦截在 CI/CD 流程中应处于哪一阶段？

## 概念地图

- **AGENTS.md**：项目级上帝视角指导文件，规定工程红线、运行契约与目录边界。
- **Agent Skill**：功能内聚的独立文件夹，以 `SKILL.md` 为统一接口定义。
- **渐进披露**：启动仅暴露 Metadata Index，按需单次拉取 Body，杜绝指令膨胀。
- **指令巡检（Linting）**：防注入、防密钥泄露、防冗余行干扰模型注意力。

## 边界

- 本章解析器采用 Python 标准库实现，确保轻量与零第三方重型依赖。
- 复杂场景下的语义 Embedding 初筛可结合 L2.2 检索函数，但在轻量场景下分词交集已具备极高的性价比与确定性。
