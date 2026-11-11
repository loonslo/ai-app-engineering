# v3 编写规范

实施者在每个批次开工前通读本文件。优先级：仓库根目录 `AGENTS.md` > 本文件 > 各批次细则。细则对某一章另有规定时，以细则为准。

## 1. 先读再改

- 改旧章节前，先读该章的 README、workbook、`gate/` 和参考实现，保留原有教学意图与验收项编号。
- 新章节先读同一阶段相邻章节，沿用它们的写法与命名。
- 不确定的接口（SDK 版本、参数名）先查官方文档或本机已安装版本，不凭记忆写。

## 2. 目录与编号

- **不改任何现有目录名。** 交叉链接与工具都依赖目录名。
- 新章节目录按 [outline.md](outline.md) 第 4 节创建，格式为 `chapters/part<N>-<篇名>/<章节号>-<英文短名>/`。
- 章节号在全仓库唯一。`tools/run_chapter.py` 按目录名中第一个 `-` 之前的部分匹配章节号。
- 篇 11、篇 12 是新篇：`chapters/part11-project-sprint/`、`chapters/part12-job-track/`，各自需要一个篇首 `README.md`。
- **谁建目录，谁登记**：在 `tools/course_catalog.py` 的 `CHAPTERS` 中按编号顺序加入新目录。
- `chapters/README.md` 与根目录 `README.md` 由 V3-10 统一更新，内容批次不要改。

## 3. 每类章节的必备文件

| 类型 | 必备文件 |
|---|---|
| gate 章 | `README.md`、`workbook.md`、`gate/starter.py`、`gate/gate_check.py`、参考实现 `<英文短名>.py`；需要固定数据时另加 `gate/cases.json` |
| 清单章 | `README.md`、`workbook.md`、`gate/CHECKLIST.md` |
| 项目章（P）与就业章（J） | `README.md`、`gate/CHECKLIST.md`、`templates/` 下的模板；有演练代码时另加测试 |
| 换实现（旧章） | 只改参考实现和 README 中与实现相关的段落；gate 不动，除非细则要求追加检查项 |

## 4. README 模板

### 4.1 gate 章

```markdown
# L1.10 嵌入式 LLM 功能 · Gate

[全书目录](../../README.md) · [上一章 L1.9](../1.8-cli-chatbot/README.md) · [下一章 L2.1](../../part2-rag/2.12-context-engineering/README.md)

- **能力**：一句话写学完能做什么。
- **v3 路径**：L1.10 / 核心（Gate；嵌入式功能）
- **岗位任务 / 面试题型**：T1、T4 / F4、F5
- **前置**：L1.4、L1.6、L1.7。
- **时间盒**：6 小时（2h 读 + 3h 实现 + 1h 故障与记录）。
- **闭卷规则**：只读本页、`gate/starter.py` 和标准库或指定 SDK 的官方文档；通过 gate 之前不要打开参考实现。
- **验收命令**：

（代码块：python chapters/…/gate/gate_check.py）

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 来绕过检查。

## 为什么做这个 gate
## 概念            （新概念较多时才写；否则并入“为什么”）
## 任务            （函数 / 行为表）
## 关键约定        （返回结构、错误码、枚举值）
## 故障注入（必须亲手触发）  （编号表：注入 / 期望）
## 验收标准        （检查项数量与分组）
## 提交物
## 通过后对照参考实现  （运行命令 + 3 个对照问题）
## 概念地图
## 边界            （没验证什么、简化了什么、真实系统还差什么）
```

- 上一章 / 下一章按 v3 顺序链接。
- “v3 路径”一行与 `docs/course-v3-map.json` 中的条目一致。
- 新章节不写 `v2 路径` 行。

### 4.2 清单章

头部字段用：**目标**、**v3 路径**、**岗位任务 / 面试题型**、**前置**、**环境**（需要什么外部条件）。正文依次为：`问题`、`概念`、`流程`、`练习`、`产物与验收`、`边界`。

### 4.3 换实现的旧章

- 保留原标题、导航、`v2 路径` 行和全部 gate 段落。
- 只改写提到 LangChain 实现的句子、参考实现的运行说明，以及“通过后对照”中涉及实现细节的问题。
- 规格要求“保留框架对照”的章节，在“通过后对照”之后加一个 `## 框架对照` 小节，说明同一行为在 LangChain 里怎么写。

### 4.4 项目章与就业章

头部字段用：**目标**、**v3 路径**、**岗位任务 / 面试题型**、**节奏**（第几周、每周几小时）、**前置**。正文依次为：`为什么`、`步骤`、`模板`、`产物与验收`、`常见失败`、`边界`。

## 5. workbook 模板

gate 章沿用现有格式：闭卷记录、实现前预测（表格）、Gate 结果、解释题、通过后对照、未验证边界。清单章写：执行记录、证据（代码块模板）、未验证边界。所有待填项写“待填写”，不要预填答案。

## 6. gate 规范

### 6.1 `gate/starter.py`

- 文件头 docstring 写：v3 编号、闭卷规则、运行命令、“不允许修改 gate_check.py”。
- 只保留接口：类型标注齐全；用 `@dataclass(frozen=True)` 定义数据结构；函数体为 `raise NotImplementedError("实现……")`。
- 每个函数的 docstring 写清输入、输出、错误行为与边界条件，学习者只看 docstring 就能实现。
- 不导入真实 SDK 客户端；需要模型时，以参数形式注入可调用对象（如 `chat_fn`）。

### 6.2 `gate/gate_check.py`

- 结构沿用现有 gate：`argparse` 的 `--module` 参数（默认同目录 `starter.py`）、`load_module`、`Gate` 类、`expect` 断言、PASS / FAIL 打印，以及写出 `gate/gate_report.json`。
- 报告的 `gate` 字段用 `"<v3 编号>-<英文短名>"`，如 `"L1.10-embedded-feature"`。
- 全部离线：模型、工具、时钟、网络、存储都用脚本化替身注入。需要时间时注入假时钟，不调用 `time.sleep`。
- 确定性：同一实现连跑两次，结果完全一致；有随机数时固定种子。
- 检查项数量不少于细则规定；README 故障注入表中的每一条至少对应一个检查项，检查名能看出对应关系。
- 失败信息说明“期望什么、实际是什么”，不暴露参考答案。
- 默认骨架必须 0 通过、退出码 1；临时参考解必须全部通过、退出码 0。
- 兼容 Python 3.11（CI 版本）：不用 3.12 及以上才有的语法，如 `type` 语句、PEP 695 泛型、跨引号嵌套的 f-string。

### 6.3 临时参考解

- 路径：`.tmp/gate_solutions/v3/<章节号>.py`（`.tmp/` 已被 `.gitignore` 忽略）。一章有多个 gate 时加后缀，如 `1.10-pai.py`。
- 只用于证明 gate 可通过，不入库；审核通过后由审核者通知删除。

### 6.4 给已有 gate 追加检查项

- 原有检查项的名字与顺序不变，新项追加在末尾。
- README 的验收标准、故障注入表和 workbook 的计数同步更新。
- 原有临时参考解需要补齐新接口；验证记录写明“原 N 项 + 新增 M 项”。

## 7. LangChain 使用边界

只有下列位置允许导入 `langchain*` 或 `langgraph*` 包：

| 位置 | 原因 |
|---|---|
| 4.2、4.3、4.4、4.6、4.10、4.11 | L4.9、L4.10 的 LangGraph 状态图、检查点与人工介入 |
| 4.15 | L4.16 框架素养的对照练习 |
| 1.6、4.9、4.13、5.6、6.2 | 选修章，本轮不改 |
| `chapters/part8-*`、`part9-*`、`part10-*` | 选修累积项目，本轮不改 |
| 文件名含 `langchain` 或 `langgraph` 的脚本 | 换实现时保留的框架对照版 |
| `chapters/test_new_lessons.py` | 旧测试，按需同步修改 |
| `capstone/` | V3-9 之前保持现状 |

`langsmith` 只允许出现在 3.6 的平台示例中。批次完成后，下面的命令应无输出：

```bash
grep -rlE "^\s*(from|import) (langchain|langgraph)" chapters --include=*.py \
  | grep -vE "/(1\.6|4\.2|4\.3|4\.4|4\.6|4\.9|4\.10|4\.11|4\.13|4\.15|5\.6|6\.2)-[^/]+/" \
  | grep -vE "(langchain|langgraph)[^/]*\.py$" \
  | grep -vE "^chapters/part(8|9|10)-" \
  | grep -v "^chapters/test_new_lessons.py$"
```

只检查本批次范围时，在第一行后加 `| grep "<本批次目录>"`。

### 7.1 换实现时怎么处理旧脚本

- 默认：原文件名改写为原生实现，旧 LangChain 版本删除；在验证记录里列出删除清单（git 可恢复）。
- 细则标注“保留框架对照”的：先把旧文件改名为 `<原名>_langchain.py`（或 `_langgraph.py`），再在原文件名下写原生版。README 的命令要写明脚本名，因为章节目录里会有两个脚本。
- 参考实现被 `chapters/test_new_lessons.py` 导入时，保持被测函数的名字和行为不变；必须改动时同步修改测试，并在验证记录里说明。

## 8. 原生调用约定

- 模型调用统一用 V3-0 新增的 `common.get_openai_client()` 和 `common.chat_model_name()`；不在章节里读取密钥或拼 base_url。
- 基线接口是 Chat Completions（DeepSeek、Ollama、vLLM 与多数网关都兼容）。Responses API 只出现在对比段落，并写明只适用于支持它的厂商。
- **结构化输出**：先用“工具即输出”或 JSON 模式加 Pydantic 校验；严格 JSON Schema 只在厂商明确支持时使用。Pydantic AI 文档称 DeepSeek 的 Chat Completions 端点不接受严格 JSON Schema，相关章节要写明这一点，并注明读取日期。
- **DeepSeek V4 默认开启思考**，思考模式下不接受强制 `tool_choice`。需要稳定的工具调用或结构化输出时，按官方文档关闭思考，并在 README 中说明。
- **模型 ID 只从环境变量取**，不写死 `deepseek-chat` 之类的旧别名；V3-0 负责核对当前可用的 ID。
- **真实模型调用只出现在参考实现里**：通过 `--live` 参数或环境变量显式开启；缺少密钥时打印可读提示并退出，不抛堆栈；输出中标明哪些结果来自真实模型。
- **embedding 与 reranker** 统一用 V3-0 新增的 `common.get_sentence_embedder()`、`common.embed_texts()`、`common.get_cross_encoder()`。
- **复用前序章节**：后续章节的参考实现优先导入前序章节参考实现中的函数（`tools/run_chapter.py` 已把篇 0–6 的章节目录加入导入路径），不复制粘贴；只有需要演示差异时才重写。

## 9. Pydantic AI 约定

- 依赖为 `pydantic-ai-slim[openai]`，版本由 V3-0 锁定在 `requirements-course.txt`；README 写明“本章基于 Pydantic AI x.y.z”。
- gate 中用 `TestModel` 或 `FunctionModel`，并在 gate_check 开头设置 `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False`。
- 真实调用走 `DeepSeekProvider`（或通用的 OpenAI 兼容 provider），模型名取自 `common.chat_model_name()`。
- Pydantic AI 发版频繁。接口以锁定版本的官方文档为准，引用文档时写读取日期。
- **当前锁定版本为 2.53.0**（`requirements-course.txt`、`requirements-dev.txt`）。2026-11-02 核对的 PyPI 2.53.0 元数据没有列出 2.31.1 的五条安全公告；本条对 2.31.1 的公告与 `openai<3` 兼容限制是历史记录，不再适用于当前锁定集。
  - 课程仍统一使用 L5.6 的 `opentelemetry-sdk` 明确选择并脱敏导出的字段；这属于项目追踪策略，不是对当前 Pydantic AI 埋点的漏洞结论。
  - `web_fetch_tool`、`FileUrl` 和 `ConcurrencyLimitedModel` 是否适合特定场景，按当前官方文档与实际边界逐项评估；不是当前课程的统一禁用清单。
  - DeepSeek 思考模式、结构化输出与工具调用兼容性按所用模型和端点验证，不沿用 2.31.1 的 provider 限制推断。
  - 章节 API 以当前锁定版本与离线/在线验证结果为准；升级后仍需复核依赖解析与回归，不因 PyPI 无公告列表而宣称全面安全。

## 10. 依赖与版本

- 不新增依赖，除非细则列出。本轮允许新增的只有：`pydantic-ai-slim[openai]`、`opentelemetry-sdk`（V3-0 锁定版本）。
- 新依赖锁定在 `requirements-course.txt`，写明用于哪些章节。
- CI 运行的测试（`tools/`、`chapters/test_new_lessons.py`、`chapters/test_v3_lessons.py`）只能导入 `requirements-dev.txt` 已锁定的包。
- SKILL.md、YAML frontmatter 之类的简单格式用标准库解析，不依赖传递安装的 PyYAML。

## 11. 验证命令

在仓库根目录、`.venv` 环境下运行；Windows 终端输出中文时先设 `PYTHONUTF8=1`。

```bash
# 1. gate：默认骨架应 0 通过（退出码 1）
python chapters/<篇>/<章>/gate/gate_check.py
# 2. gate：临时参考解应全部通过（退出码 0）
python chapters/<篇>/<章>/gate/gate_check.py --module .tmp/gate_solutions/v3/<章节号>.py
# 3. 确定性：命令 2 连跑两次，输出一致
# 4. 测试（pytest.ini 已设置 --basetemp）
python -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
# 5. 断链
python tools/check_course_links.py
# 6. 静态检查，按 CI 的 Python 版本
python -m ruff check --target-version py311 <本批次改动的目录与文件>
# 7. LangChain 边界：第 7 节的 grep 命令应无输出
# 8. v3 标签未被改动（2026-11-08 起 v2 路线已移除，只保留 v3 路径标签）
python tools/apply_v3_map.py --check
# 9. 参考实现能启动；无密钥时给出可读提示
python tools/run_chapter.py <章节号> [脚本名]
```

`chapters/test_v3_lessons.py` 由 V3-0 创建；在那之前，命令 4 去掉这个文件。

## 12. 验证记录模板

文件名为 `docs/gate-v3-<批次号>-validation.md`，结构见 `docs/gate-v3-10-validation.md`：

```markdown
# V3-x <批次名> 验证 · YYYY-MM-DD

一句话写本批次改了什么、没改什么。

## 范围
| v3 编号 | 目录 | 类型 | 新增 / 修改 / 删除的文件 |

## 实际执行
### 1. Gate：骨架与临时参考解（表：命令 / 结果）
### 2. 测试
### 3. 断链与静态检查
### 4. LangChain 边界与标签检查

## 细则偏离
## 未验证
## 复现方式
## 边界
```

只写实际运行过的命令与结果；没运行的写进“未验证”。

## 13. TASKS 与 PROJECT_STATUS

- 按 `AGENTS.md` 契约执行：先在 `TASKS.md` 的 Done 区加一条（日期、范围、结果、未验证项、证据路径），再更新 `PROJECT_STATUS.md`（`progress`、`next`、`evidence`，正文追加一段）。
- `evidence` 只填现存的项目内相对路径，新增本批次的验证记录。
- 措辞区分“离线 gate 通过”“真实模型运行”“已部署”；不写“已验收”“已学完”。

## 14. 文风

- 第一句直接写这章 / 这个函数做什么；不写“接下来我们将”“值得一提的是”这类套话。
- 能用一句话说清的不写一段，但概念要让初学者看懂：第一次出现的术语给一句解释。
- 接口、返回值、错误码用表格；行为契约写“输入 → 输出 / 失败时怎样”。
- 中文标点，技术术语保留英文原文；不用表情符号和营销词。
- 代码注释写“为什么”和行为契约，不复述代码。

## 15. 事实与时效

- 版本、价格、弃用、市场数据等会变的事实，必须给出官方文档或一手数据链接，并写读取日期，如“（Pydantic AI 文档，读取于 2026-11-02）”。
- 优先引用官方文档与一手数据。按用户要求，不引用中文社区类来源。
- 没有实测的结论写“未实测”；推测写“判断”，不写成事实。

## 16. 禁止事项

- 重命名任何现有目录。
- 为了通过而修改 `gate_check.py` 的判定逻辑，或删减原有检查项。
- 提交临时参考解，或把答案写进 README、workbook。
- 在测试或 gate 中调用真实模型、联网、读取 `.env`。
- 修改 `flagship-project/`（已冻结）；在 V3-9 之外修改 `capstone/`。
- 修改或删除任何 `v2 路径` 行（V3-10 也只新增 v3 行，不改 v2 行）。
- 在代码、文档或日志中写入密钥、令牌或真实个人数据。
- 删除现有章节目录；顺手格式化与本批次无关的文件。
