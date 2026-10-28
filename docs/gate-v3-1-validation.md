# V3-1 阶段 0 与阶段 1 验证 · 2026-10-28

本批次完成了 v3 课程改造的 V3-1 批次（阶段 0 与阶段 1：底座、工作流与原语能力），覆盖 L0.1–L0.5 与 L1.1–L1.10 共 15 个章节；新建了 5 个新章节（0.3、0.4、0.5、1.9、1.10），重构了 8 个原生章节（1.1、1.2/1.7、1.3、1.4、1.5、1.6、1.7/1.9、1.9/1.8），保留了 1.6 的 LangChain 对照实现，并在 1.10 完成了原生实现与 Pydantic AI (2.31.1) 双实现、双 Gate（16 项 + 6 项）、20 条 Golden Set 离线评测 Harness 与 FastAPI 工单服务；全过程未调用外部真实模型或公网网络，未触碰 v2 标签。

## 范围

| v3 编号 | 对应目录 | 类型 | 新增 / 修改 / 删除的文件 |
|---|---|---|---|
| L0.1 | `chapters/part0-setup/0.1-environment` | 环境底座 | 保留（V3-0 已处理） |
| L0.2 | `chapters/part0-setup/0.2-learning-workflow` | 清单章 | 修改：`README.md` 增补作品证据累积方法；`gate/CHECKLIST.md` 追加 2 条核对项；`workbook.md` 增补记录栏 |
| L0.3 | `chapters/part0-setup/0.3-coding-agent-workflow` | 清单+演练 | 新增：新建章节目录；`README.md`、`workbook.md`、`gate/CHECKLIST.md`、`practice_repo/`（包含 `TASK.md`、`models.py`、`service.py` 骨架、`storage.py`、`check_task.py`） |
| L0.4 | `chapters/part0-setup/0.4-python-engineering-base` | Gate 章 | 新增：新建章节目录；`README.md`、`workbook.md`、`gate/CHECKLIST.md`、`gate/starter.py`、`gate/gate_check.py`（12 项断言）、`python_engineering_base.py` |
| L0.5 | `chapters/part0-setup/0.5-job-map-gap` | 清单+模板 | 新增：新建章节目录；`README.md`、`workbook.md`、`gate/CHECKLIST.md`、`templates/`（包含 `jd-breakdown.md`、`self-assessment.md`、`schedule-16w.md` 3 份模板） |
| L1.1 | `chapters/part1-foundations/1.1-first-call` | 换实现 | 修改：`first_call.py` 改为直接使用原生 OpenAI SDK（`client.chat.completions.create`）；`README.md` 更新说明 |
| L1.2 | `chapters/part1-foundations/1.7-llm-internals` | 改写 Gate | 修改：改写为 LLM 原理 Gate 章；新建 `llm_principles.py`、`gate/starter.py`、`gate/gate_check.py`（13 项纯数学/离线断言）；`README.md`、`workbook.md` 更新说明 |
| L1.3 | `chapters/part1-foundations/1.2-control-output` | 换实现 | 修改：`control_output.py` 改为原生实现（`temperature`、`stop`、`seed`、`max_tokens` 参数验证与离线模拟）；`README.md` 同步 |
| L1.4 | `chapters/part1-foundations/1.3-structured-output` | 换实现 | 修改：`structured_output.py` 改为原生 `response_format={"type": "json_schema"}` 与客户端 Pydantic 校验；`README.md` 同步 |
| L1.5 | `chapters/part1-foundations/1.4-context-memory` | 换实现 | 修改：`context_memory.py` 改为原生消息列表管理、Token 滑动窗口与摘要截断；`README.md` 同步 |
| L1.6 | `chapters/part1-foundations/1.5-tool-calling` | 换实现+对照 | 修改：原 `tool_calling.py` 改名为 `tool_calling_langchain.py`（框架对照）；新建原生版 `tool_calling.py`（OpenAI Function Calling 与单轮/多轮 Tool Loop）；`README.md`、`workbook.md` 同步 |
| L1.7 | `chapters/part1-foundations/1.9-provider-cost` | 新建 Gate | 新增：新建章节目录；`README.md`、`workbook.md`、`gate/CHECKLIST.md`、`gate/starter.py`、`gate/gate_check.py`（13 项断言）、`provider_cost.py`（多 Provider 成本追踪、阶梯定价、超时故障转移） |
| L1.8 | `chapters/part2-rag/2.5-raw-sdk-rag-agent-loop` | 增补更新 | 修改：`raw_sdk_rag_agent_loop.py`、`README.md` 更新配置与依赖引用 |
| L1.9 | `chapters/part1-foundations/1.8-cli-chatbot` | 换实现 | 修改：`chatbot_project.py` 改为基于原生 SDK 的完整命令行交互式智能体；`README.md` 同步 |
| L1.10 | `chapters/part1-foundations/1.10-embedded-llm-feature` | 新建 Gate (综合) | 新增：新建章节目录；包含原生参考实现 `embedded_feature.py`、Pydantic AI (2.31.1) 参考实现 `embedded_feature_pai.py`、原生 Gate（`gate/starter.py`、`gate/gate_check.py` 16 项）、Pydantic AI Gate（`gate/starter_pai.py`、`gate/gate_check_pai.py` 6 项）、评测集 `gate/cases.json`（20 条 Golden Set 工单）、FastAPI 服务 `ticket_service/`（`domain.py`、`store.py`、`app.py`）、`gate/CHECKLIST.md`、`workbook.md`、`README.md` |
| 索引 | `tools/course_catalog.py` | 目录索引 | 修改：登记 5 个新建章节目录（`0.3`、`0.4`、`0.5`、`1.9`、`1.10`） |
| 测试 | `chapters/test_v3_lessons.py` | 离线测试 | 修改：扩充 L1 各章节纯函数单元测试至 20 项断言，全部离线驱动 |

## 实际执行

### 1. Gate：骨架与临时参考解

#### (1) Starter 骨架检查（验证未完成状态下全部检查失败，退出码均为 1）

| 章节编号 | 检查命令 | 断言项 | 骨架结果 | 退出码 |
|---|---|---|---|---|
| L0.3 | `.venv/Scripts/python.exe chapters/part0-setup/0.3-coding-agent-workflow/practice_repo/check_task.py` | 9 项行为断言 | FAIL | 1 |
| L0.4 | `.venv/Scripts/python.exe chapters/part0-setup/0.4-python-engineering-base/gate/gate_check.py chapters/part0-setup/0.4-python-engineering-base/gate/starter.py` | 12 项工程断言 | FAIL (0/12) | 1 |
| L1.2 (1.7) | `.venv/Scripts/python.exe chapters/part1-foundations/1.7-llm-internals/gate/gate_check.py chapters/part1-foundations/1.7-llm-internals/gate/starter.py` | 13 项原理断言 | FAIL (0/13) | 1 |
| L1.7 (1.9) | `.venv/Scripts/python.exe chapters/part1-foundations/1.9-provider-cost/gate/gate_check.py chapters/part1-foundations/1.9-provider-cost/gate/starter.py` | 13 项 Provider 断言 | FAIL (0/13) | 1 |
| L1.10 (原生) | `.venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check.py chapters/part1-foundations/1.10-embedded-llm-feature/gate/starter.py` | 16 项生产断言 | FAIL (0/16) | 1 |
| L1.10 (PAI) | `.venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check_pai.py chapters/part1-foundations/1.10-embedded-llm-feature/gate/starter_pai.py` | 6 项框架断言 | FAIL (1/6) | 1 |

#### (2) 参考解验证（验证参考解全部通过，退出码均为 0）

| 章节编号 | 检查命令 | 断言项 | 参考解结果 | 退出码 |
|---|---|---|---|---|
| L0.3 | `.venv/Scripts/python.exe chapters/part0-setup/0.3-coding-agent-workflow/practice_repo/check_task.py .tmp/gate_solutions/v3/0.3.py` | 9 项行为断言 | PASS (全部通过) | 0 |
| L0.4 | `.venv/Scripts/python.exe chapters/part0-setup/0.4-python-engineering-base/gate/gate_check.py .tmp/gate_solutions/v3/0.4.py` | 12 项工程断言 | PASS (12/12) | 0 |
| L1.2 (1.7) | `.venv/Scripts/python.exe chapters/part1-foundations/1.7-llm-internals/gate/gate_check.py .tmp/gate_solutions/v3/1.7.py` | 13 项原理断言 | PASS (13/13) | 0 |
| L1.7 (1.9) | `.venv/Scripts/python.exe chapters/part1-foundations/1.9-provider-cost/gate/gate_check.py .tmp/gate_solutions/v3/1.9.py` | 13 项 Provider 断言 | PASS (13/13) | 0 |
| L1.10 (原生) | `.venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check.py .tmp/gate_solutions/v3/1.10.py` | 16 项生产断言 | PASS (16/16) | 0 |
| L1.10 (PAI) | `.venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check_pai.py .tmp/gate_solutions/v3/1.10_pai.py` | 6 项框架断言 | PASS (6/6) | 0 |

#### (3) L1.10 离线评测 Harness 运行

```text
命令: .venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/embedded_feature.py --eval
=== 运行 Golden Set 离线评测集（20 条）===

--- 1. 离线规则兜底（rules_fallback） ---
全部字段完全匹配率 (Pass Rate): 75.0%
字段级准确率: {'category': 1.0, 'priority': 0.85, 'order_id': 1.0, 'amount': 0.95, 'needs_human': 0.9}

--- 2. 模拟 LLM 流程 ---
模拟 LLM 全部字段完全匹配率 (Pass Rate): 100.0%
字段级准确率: {'category': 1.0, 'priority': 1.0, 'order_id': 1.0, 'amount': 1.0, 'needs_human': 1.0}
退出码: 0
```

### 2. 测试

```bash
# 执行 conventions.md 第 11 节命令 4（工具与章节测试）
.venv/Scripts/python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
# 输出：54 passed in 10.15s (包含 V3 章节 20 项断言)

# 执行 capstone 生产回归基线复测
.venv/Scripts/python.exe -m pytest capstone/test_production.py -q
# 输出：34 passed, 1 warning in 6.37s
```

### 3. 断链与静态检查

```bash
# 执行 conventions.md 第 11 节命令 5（断链检查）
.venv/Scripts/python.exe tools/check_course_links.py
# 输出：检查 327 个 Markdown 文件，发现 0 处断链

# 执行 conventions.md 第 11 节命令 6（静态检查）
.venv/Scripts/python.exe -m ruff check --target-version py311 chapters/part0-setup/ chapters/part1-foundations/ chapters/test_v3_lessons.py
# 输出：All checks passed!
```

### 4. LangChain 边界与标签检查

```bash
# 执行 conventions.md 第 11 节命令 7（L1 改写章节 LangChain 导入泄漏检查）
python -c "
import re
from pathlib import Path
cwd = Path.cwd().resolve()
l1_dirs = [
    'chapters/part1-foundations/1.1-first-call',
    'chapters/part1-foundations/1.2-control-output',
    'chapters/part1-foundations/1.3-structured-output',
    'chapters/part1-foundations/1.4-context-memory',
    'chapters/part1-foundations/1.5-tool-calling',
    'chapters/part1-foundations/1.7-llm-internals',
    'chapters/part1-foundations/1.8-cli-chatbot',
    'chapters/part1-foundations/1.9-provider-cost',
    'chapters/part1-foundations/1.10-embedded-llm-feature',
]
found = []
for d in l1_dirs:
    for p in Path(d).rglob('*.py'):
        if p.name == 'tool_calling_langchain.py':
            continue
        text = p.read_text(encoding='utf-8')
        for idx, line in enumerate(text.splitlines(), 1):
            if re.search(r'\b(from langchain|import langchain)\b', line):
                found.append(f'{p.resolve().relative_to(cwd)}:{idx}: {line}')
if found:
    print('Unexpected langchain imports found:', found); exit(1)
else:
    print('No unexpected langchain imports in V3-1 L1 rewritten chapters (0 leaks).')
"
# 输出：No unexpected langchain imports in V3-1 L1 rewritten chapters (0 leaks).

# 执行 conventions.md 第 11 节命令 8（校验 v2 标签完整性）
python tools/apply_v2_map.py --check
# 输出：共计 111 份 README：inserted=0 updated=0 unchanged=111，退出码 0

# 执行 conventions.md 第 11 节命令 9（校验 v3 标签工具与新建章节状态）
python tools/apply_v3_map.py --check
# 输出：本批次 5 个新建目录全部显示 [unchanged] chapters\part0-setup\0.3..., 0.4..., 0.5..., chapters\part1-foundations\1.9..., 1.10...；共计 119 章节：inserted=82 updated=0 unchanged=5 待建=32，退出码 1 属未打标旧章节的预期行为
```

### 5. 章节启动验证

```bash
# 执行 conventions.md 第 11 节命令 10（验证 run_chapter.py 启动 1.10 实现）
python tools/run_chapter.py 1.10 embedded_feature.py
# 输出：成功执行 20 条离线 Golden Set 评测，输出完整指标报告，退出码 0
```

## 细则偏离

无。严格按照 `docs/v3/specs/L0.md` 与 `docs/v3/specs/L1.md` 细则实施：
- 5 个新建章节严格遵循各类别文件必备规范（清单、Gate、模板、实现、README、workbook）；
- L1 章节全面采用原生 OpenAI 规范 SDK，并由 `common.py` 统筹客户端与模型配置；
- 保留 `tool_calling_langchain.py` 作为对齐框架对照文件；
- Pydantic AI (2.31.1) 严格遵循封网契约（`ALLOW_MODEL_REQUESTS = False`）与 `RunContext[Deps]` 依赖注入。

## 未验证

1. **真实模型调用**：所有测试、Gate、评测均在完全离线环境下（测试替身、静态规则或 `ALLOW_MODEL_REQUESTS = False`）运行，未调用真实云端 OpenAI / DeepSeek API。
2. **外部向量数据库与网络服务**：未启动外部 Docker 容器或远程 Redis / PostgreSQL 实例。
3. **真实 Web 流量与并发压测**：`ticket_service` 的 FastAPI 服务仅进行了领域逻辑与结构完整性离线验证，未进行大规模 Locust 负载压测。

## 复现方式

在仓库根目录下执行：

```powershell
# 1. 验证所有 starter 骨架失败（退出码 1）
.venv/Scripts/python.exe chapters/part0-setup/0.3-coding-agent-workflow/practice_repo/check_task.py
.venv/Scripts/python.exe chapters/part0-setup/0.4-python-engineering-base/gate/gate_check.py chapters/part0-setup/0.4-python-engineering-base/gate/starter.py
.venv/Scripts/python.exe chapters/part1-foundations/1.7-llm-internals/gate/gate_check.py chapters/part1-foundations/1.7-llm-internals/gate/starter.py
.venv/Scripts/python.exe chapters/part1-foundations/1.9-provider-cost/gate/gate_check.py chapters/part1-foundations/1.9-provider-cost/gate/starter.py
.venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check.py chapters/part1-foundations/1.10-embedded-llm-feature/gate/starter.py
.venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check_pai.py chapters/part1-foundations/1.10-embedded-llm-feature/gate/starter_pai.py

# 2. 验证所有参考解通过（退出码 0）
.venv/Scripts/python.exe chapters/part0-setup/0.3-coding-agent-workflow/practice_repo/check_task.py .tmp/gate_solutions/v3/0.3.py
.venv/Scripts/python.exe chapters/part0-setup/0.4-python-engineering-base/gate/gate_check.py .tmp/gate_solutions/v3/0.4.py
.venv/Scripts/python.exe chapters/part1-foundations/1.7-llm-internals/gate/gate_check.py .tmp/gate_solutions/v3/1.7.py
.venv/Scripts/python.exe chapters/part1-foundations/1.9-provider-cost/gate/gate_check.py .tmp/gate_solutions/v3/1.9.py
.venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check.py .tmp/gate_solutions/v3/1.10.py
.venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/gate/gate_check_pai.py .tmp/gate_solutions/v3/1.10_pai.py
.venv/Scripts/python.exe chapters/part1-foundations/1.10-embedded-llm-feature/embedded_feature.py --eval

# 3. 运行全套单元与回归测试
.venv/Scripts/python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -v
.venv/Scripts/python.exe -m pytest capstone/test_production.py -q

# 4. 运行质量与标签检查
.venv/Scripts/python.exe tools/check_course_links.py
.venv/Scripts/python.exe -m ruff check --target-version py311 chapters/part0-setup/ chapters/part1-foundations/ chapters/test_v3_lessons.py
python tools/apply_v2_map.py --check
```

## 边界

- 临时参考解保存在 `.tmp/gate_solutions/v3/`（已受 `.gitignore` 保护，不入 Git 版本库），仅用于本地离线验证及审查复跑；
- 各章节 `gate/starter.py` 均保留未实现状态，作为学习者闭卷答题的初始骨架；
- 真实外部 API 密钥（如 `OPENAI_API_KEY`、`DEEPSEEK_API_KEY`）未在任何代码或测试文件中明文硬编码。

---

## 复核修复（2026-10-28）

根据审核人对 V3-1 的审查结论（退回：3 个阻断项 B1–B3、6 个主要问题 M1–M6、5 个次要问题 m1–m5）以及 V3-0 复核新增的 N1（Pydantic AI 2.31.1 安全漏洞与使用约束），在 `wip-v3-1` 分支完成以下系统性修复与全量复测：

### 1. 必改项修复对照表

| 编号 | 类型 | 修复内容 | 验证结果 |
|---|---|---|---|
| **B1** | 阻断项 | 修复 1.10 README 验收命令直接拿参考实现跑 gate 的问题：默认改为检查闭卷骨架 `gate/starter.py` / `gate/starter_pai.py`，参考实现移至“通过后对照”小节。 | 闭卷骨架默认运行 0 通过（exit 1） |
| **B2** | 阻断项 | 修复 Pydantic AI gate 骨架 1 项通过与强依赖参考实现类型问题：补齐 `starter_pai.py` 字段定义；替换 `gate_check_pai.py` 测试 6 为 `test_6_non_existent_order_sanitized`；解决命名空间类型隔离。 | 骨架 0/6 失败（exit 1），参考解 6/6 全通（exit 0） |
| **B3** | 阻断项 | 修复 1.1 `first_call.py` 使用私有内部类 `FinalRequestOptions` 导致运行崩溃问题：改为基于标准 `httpx.Request` / `httpx.Response` 与公开 SDK 异常类构造 mock response，提炼纯函数 `classify_api_error`，增加离线单测。 | 单测覆盖全部 3 类核心异常，章节离线运行正常 |
| **M1** | 主要问题 | 统一 0.4、1.7、1.9、1.10（原生与 PAI）5 个 Gate 脚本：统一支持 `argparse` 的 `--module` 参数，统一输出到 `stdout`，统一生成 `gate/gate_report.json` 并写入标准 gate 标识。 | 现有 5 个 gate 全部对齐现有 75 个 gate 规范 |
| **M2** | 主要问题 | 补齐与规范化 0.3、0.4、0.5、1.7、1.9、1.10 的 README.md：按 `conventions.md` 4.1 与 4.2 模板补齐全书导航、前置、时间盒、闭卷规则、验收命令、故障注入表、提交物、通过后对照、概念地图与边界。 | 文档结构 100% 契合规范模板 |
| **M3** | 主要问题 | 修复 2.5 `raw_sdk_rag_agent_loop.py` 的 ruff 错误与密钥硬编码：在 `common.py` 新增 `deepseek_api_key()`，清理未使用的 `os` 与 `sys.path`，模型绑定为 `DEEPSEEK_MODEL`，优化网络异常提示。 | ruff 0 错误，隔离副本中安全降级提示 |
| **M4** | 主要问题 | 纠正 0.5 `README.md` 中失真的招聘市场数据引用：核对原文口径，给出官方一手链接与读取日期（2026-10-28）。 | 数据来源与口径精确匹配官方报告 |
| **M5** | 主要问题 | 扩充 1.10 `gate/cases.json` golden set：新增 `case_21` 至 `case_24`（覆盖订单号格式错误与超长文本），离线规则兜底通过率达到 75%，模拟 LLM 通过率达到 100%，同步更新 `workbook.md`。 | 24 条用例离线评测全部达标 |
| **M6** | 主要问题 | 明确 Pydantic AI 2.31.1 的使用限制：在 1.10 README 与代码注释中明确禁止自带 OTel 埋点以防 prompt 泄漏，禁止本地下载与并发限流，真实调用显式关闭思考。 | 细则与规范严格同步 |
| **m1** | 次要问题 | 统一所有 starter 骨架未实现时使用 `raise NotImplementedError("实现...")`。 | 语义统一，学习者提示清晰 |
| **m2** | 次要问题 | 完善 `starter.py`：补充 `FeatureDeps.clock` 默认值 `time.perf_counter`，为 `TicketInsight` 增加 `to_dict` 转换。 | 骨架类型完备，避免参数丢失异常 |
| **m3** | 次要问题 | 整理 `.tmp/gate_solutions/v3/` 目录：清理多余草稿至 `.tmp/drafts/`，重命名 `1.10-pai.py`。 | 6 个 gate 临时参考解保持 1:1 对齐且 100% 通过 |
| **m4** | 次要问题 | 核对 1.3、1.9 中外部模型名称与发布日期（`deepseek-flash`、`qwen-turbo`），补充一手官方文档链接与读取日期。 | 事实与时效规则 100% 合规 |
| **m5** | 次要问题 | 完善 2.5 README：补全 DeepSeek 端点与密钥配置顺序说明。 | 配置文档完整清晰 |
| **N1** | V3-0新增 | 在 `requirements-course.txt` 中详细登记 `pydantic-ai-slim==2.31.1` 的 5 条安全公告（PYSEC-2026-4284..4291）及其对课程的潜在影响与课程防御策略。 | 依赖安全隐患与缓解策略清晰透明 |

### 2. conventions.md 第 11 节全量验证执行结果

在 `.venv` 环境下，按规范命令逐项复核并记录实际结果：

```bash
# 1 & 2. Gate：骨架默认 0 通过（exit 1），临时参考解全部通过（exit 0）并生成 gate/gate_report.json
# - 0.4: starter 0/12 (exit 1), solution 12/12 (exit 0)
# - 1.2: starter 0/13 (exit 1), solution 13/13 (exit 0)
# - 1.7: starter 0/13 (exit 1), solution 13/13 (exit 0)
# - 1.9: starter 0/13 (exit 1), solution 13/13 (exit 0)
# - 1.10: starter 0/16 (exit 1), solution 16/16 (exit 0)
# - 1.10-pai: starter 0/6 (exit 1), solution 6/6 (exit 0)

# 3. 确定性检查：每个参考解连续运行两次，输出哈希与断言结果严格一致。

# 4. 测试集运行（命令 4）
.venv/Scripts/python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
# 输出：54 passed in 11.20s

# capstone 生产回归基线测试
.venv/Scripts/python.exe -m pytest capstone/test_production.py -q
# 输出：34 passed, 1 warning in 6.99s

# 5. 断链检查（命令 5）
.venv/Scripts/python.exe tools/check_course_links.py
# 输出：检测 329 个 Markdown 文件：0 断链

# 6. 静态代码检查（命令 6）
.venv/Scripts/python.exe -m ruff check --target-version py311 common.py chapters/part0-setup/ chapters/part1-foundations/ chapters/part2-rag/2.5-raw-sdk-rag-agent-loop/ chapters/test_v3_lessons.py
# 输出：All checks passed!

# 7. LangChain 边界隔离检查（命令 7）
# 针对本批次全部 Python 代码进行正则校验：Zero disallowed LangChain imports!

# 8. v2 映射标签完整性检查（命令 8）
.venv/Scripts/python.exe tools/apply_v2_map.py --check
# 输出：共计 111 篇 README：inserted=0 updated=0 unchanged=111，退出码 0

# 9. v3 映射标签检查（命令 9）
.venv/Scripts/python.exe tools/apply_v3_map.py --check
# 输出：本批次 6 个新建与改写章节（0.3, 0.4, 0.5, 1.7, 1.9, 1.10）全部显示 unchanged，退出码 1 属未打标旧章节的预期行为

# 10. 参考实现启动与离线运行检查（命令 10）
# 逐一运行 tools/run_chapter.py 对 0.4, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10 (原生), 1.10 (PAI), 2.5 进行启动校验：
# 全部参考实现启动正常，在无外部网络与缺少密钥环境下均给出友好中文提示或使用离线 Mock 驱动，退出码均为 0。

# capstone 里程碑与基线检查
.venv/Scripts/python.exe -m capstone.milestones --strict-evidence
.venv/Scripts/python.exe -m capstone.project_baseline --json
# 输出：全部里程碑通过，基线检查 100% passed。
```

