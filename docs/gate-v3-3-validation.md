# V3-3 阶段 3 质量闭环整改与重构验证 · 2026-10-30

本验证记录对应针对第二轮复核退回（`docs/v3/reviews/V3-3.md` · 2026-10-30）全部 2 个阻断项（B1, B2）、8 个主要问题（M1–M8）与 6 个次要问题（m1–m6）的彻底整改、代码重构与实测复核。严格遵循 conventions 第 12 节规范记录。

---

## 一、范围（Scope）

### 1. 任务目标与整改明细
- **B1（3.6 OTel 语义约定标准重构）**：依据 `open-telemetry/semantic-conventions-genai`（commit `3fe84604a5`，读取于 2026-10-30），废弃旧版 `gen_ai.system`（更新为 `gen_ai.provider.name`）；Span 命名规范化为 `chat {model}`（CLIENT 类型）与 `retrieval {data_source.id}`（INTERNAL 类型）；移除约定中不存在的 `documents_count`，非标准属性统一使用 `app.*` 命名空间；多 finish reasons 采用复数列表；实现脱敏函数并在错误事件中抑制敏感堆栈；提供 OTLP 协议协议选择策略（Langfuse 使用 HTTP，Phoenix 使用 gRPC）；清空 workbook 预填答案（统一为 `待填写`）。
- **B2（Anthropic 出处与论述修正）**：纠正 3.3 与 3.7 中引用的 Anthropic 链接为官方最新地址 `https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents`；删除“凡是能用规则……绝不上模型”、“双盲标注”、“能力评测看 pass@k、回归评测看 pass^k”、“起点通过率 30%~60%”等失实原句，恢复根据业务场景选型的严谨论述。
- **M1/m6（3.3 恢复原生评测结构）**：恢复针对被测 RAG 系统的正确性与忠实度双维度 Rubric 评测；通过脚本化客户端真实执行候选回答位置互换（Position Swap），检验并缓解首位偏见（Position Bias）；重试逻辑精确定向 400 思考模式冲突错误；校准数据集严谨标注为合成教学数据。
- **M2/M5/m4（3.7 回归门禁与套件恢复）**：恢复真实文档切片检索；恢复单用例异常捕获与 `runtime_error` 记录；恢复 `--fail-on-regression` CI 门禁卡点逻辑；恢复 `--cases` 参数支持；`--write-failures` 补全 3.10 所需全部字段（`case_id`, `type`, `question`, `reference`, `retrieval_context`, `answer`, `keyword_score`, `citation_score`, `refusal_ok`, `passed`）；对齐 starter docstring 与 gate 检查项（`k < 1`、空输入、floor 越界）；恢复 README 概念地图条目及 workbook 第 3 题与第 4 题。
- **M3（3.8 恢复 Judge 与校准报告）**：恢复基于 Tool Calling / Rubric 的结构化 Judge 打分；补齐全部 10 个用例及人工标注分数 `manual_score`；计算一致率（Agreement Rate）与 Cohen's $\kappa$；动态生成并写入 `reports/prompt_ab_judge_agreement.json`（供 `capstone/interview_evidence.py` 严格校验）。
- **M4（3.10 异常处理与免堆栈退出）**：`load_failures` 抛出 `ValueError`（兼容 Gate 03 检查），`main()` 显式捕获异常、向标准错误输出可读指引并以退出码 2 终止，消除未捕获 Traceback。
- **M6/M7/m1/m2（3.6 规范化与 --live 健壮性）**：`langsmith_eval.py` 补齐 `--live` 参数，离线模式说明后以退出码 0 终止，无 key 时以退出码 1 终止；README 补齐标准章节模板与 Stack Overflow 2026 实测数据；锁定依赖 `opentelemetry-api==1.44.0` 与 `opentelemetry-sdk==1.44.0`。
- **M8（验证记录全面重构）**：严格按照 conventions 第 12 节重构本记录，详实记录 `--live` 实测场景，修正夸大表述（如说明 P50/P99 离线为模拟固定时钟）。

### 2. 文件清单

| 变更类型 | 文件路径 | 变更摘要 |
|---|---|---|
| **新增** | `chapters/part3-evals/3.6-langsmith-eval/otel_tracing_eval.py` | 原生 OpenTelemetry GenAI 规范追踪实现 |
| **新增** | `reports/prompt_ab_judge_agreement.json` | 3.8 Prompt A/B 与 Judge 校准报告（根目录） |
| **新增** | `chapters/part3-evals/3.8-prompt-ab-judge/reports/prompt_ab_judge_agreement.json` | 3.8 章节本地校准报告 |
| **新增** | `.tmp/gate_solutions/v3/{3.3,3.7,3.8,3.10}.py` | 阶段 3 临时参考实现（供评审复核） |
| **修改** | `chapters/part3-evals/3.3-llm-judge/README.md` | 纠正 Anthropic 链接与论述，平实技术语调 |
| **修改** | `chapters/part3-evals/3.3-llm-judge/llm_judge.py` | 恢复双维度评测、位置互换真实执行、定向重试、标注合成数据 |
| **修改** | `chapters/part3-evals/3.6-langsmith-eval/README.md` | 补齐 7 大节结构、技术选型矩阵、OTel 规范出处与调研数据 |
| **修改** | `chapters/part3-evals/3.6-langsmith-eval/gate/CHECKLIST.md` | 技术中性化，移除绝对化措辞 |
| **修改** | `chapters/part3-evals/3.6-langsmith-eval/workbook.md` | 清空预填答案为 `待填写` |
| **修改** | `chapters/part3-evals/3.6-langsmith-eval/langsmith_eval.py` | 增加 `--live` 支持，离线退出 0，无 key 退出 1 |
| **修改** | `chapters/part3-evals/3.7-eval-regression-curve/README.md` | 纠正 Anthropic 链接，恢复概念地图与题目，恢复 CI 门禁说明 |
| **修改** | `chapters/part3-evals/3.7-eval-regression-curve/gate/starter.py` | docstring 补齐 `k < 1`、空输入及 floor 边界说明 |
| **修改** | `chapters/part3-evals/3.7-eval-regression-curve/workbook.md` | 恢复第 3 题，追加第 4 题，补全故障注入预测行 |
| **修改** | `chapters/part3-evals/3.7-eval-regression-curve/regression_curve.py` | 恢复切片检索、异常捕获、`--fail-on-regression`、`--cases` 与 3.10 兼容字段 |
| **修改** | `chapters/part3-evals/3.8-prompt-ab-judge/prompt_ab_judge.py` | 恢复 Judge 打分、10 个标注用例、一致率/Cohen's Kappa 计算及报告 |
| **修改** | `chapters/part3-evals/3.10-eval-report-failures/failure_diagnosis.py` | `load_failures` 抛 `ValueError`，`main()` 捕获并退出码 2，免堆栈 |
| **修改** | `chapters/test_v3_lessons.py` | 更新 OTel 断言，追加位置互换、双维度及 3.7->3.10 兼容单元测试 |
| **修改** | `requirements-dev.txt` | 锁定 `opentelemetry-api==1.44.0` 与 `opentelemetry-sdk==1.44.0` |
| **修改** | `pytest.ini` | 配置 `pythonpath = .` 确保测试可直接执行 |
| **修改** | `docs/gate-v3-3-validation.md` | 按 conventions 第 12 节全面重构验证记录 |
| **修改** | `TASKS.md` | 纠正进度记录中的夸大表述，登记实际验证结果 |
| **修改** | `PROJECT_STATUS.md` | 同步更新跟进摘要与证据链 |

### 3. 删除清单（Conventions 第 7.1 节）
1. 彻底删除 3.3 与 3.7 README 中查无出处的伪引述与不准确推论（“凡是能用规则……绝不上模型”、“双盲标注”、“能力评测看 pass@k、回归评测看 pass^k”、“通过率起点 30%~60%”）；
2. 彻底废弃 3.6 `otel_tracing_eval.py` 中过时的语义约定属性名 `gen_ai.system`（替代为 `gen_ai.provider.name`）、不存在的属性 `documents_count`（替代为 `app.retrieval.chunk_count`），以及被移除的 `prompt`/`completion` 属性；
3. 删除 3.6 `workbook.md` 中预先填好的解答文本；
4. 删除 3.7 中对 LangSmith 的硬编码依赖及先前重构中对检索、门禁参数的删减，恢复完整功能。

---

## 二、未验证事项（Unverified Items）

1. **真实商业大模型在线全量生成**：
   受限于本机离线测试环境与成本限制，未配置正式付费 API Key 运行全部数十条真实用例的在线推理与多轮打分；所有 `--live` 测试均基于注入测试（密钥缺失与网络不可达场景）。
2. **远程 OTLP 后端数据持久化**：
   本地未搭建实际运行的 Langfuse 或 Phoenix 容器服务，未进行实际通过 HTTP/gRPC 网络发送数据包后的远程面板展示验证；追踪完整性通过 `ConsoleSpanExporter` 与 `InMemorySpanExporter` 内存属性严格断言验证。
3. **DeepEval 深度指标在线计算**：
   `deepeval` 依赖作为 3.10 的可选扩展组件，当前离线环境中未预装，仅在 `failure_diagnosis.py` 中通过 `ImportError` 优雅降级保护与一级弱信号规则分流完成验证。

---

## 三、复现方式（Reproduction Steps）

### 命令 1：Gate 骨架检查（全部 4 个 Gate，0 通过，退出码 1）
```bash
python chapters/part3-evals/3.3-llm-judge/gate/gate_check.py
python chapters/part3-evals/3.7-eval-regression-curve/gate/gate_check.py
python chapters/part3-evals/3.8-prompt-ab-judge/gate/gate_check.py
python chapters/part3-evals/3.10-eval-report-failures/gate/gate_check.py
```
- **实测结果**：
  - 3.3: 0/14 passed (exit 1)
  - 3.7: 0/13 passed (exit 1)
  - 3.8: 0/5 passed (exit 1)
  - 3.10: 0/5 passed (exit 1)

### 命令 2 & 3：临时参考解与确定性检查
```bash
python chapters/part3-evals/3.3-llm-judge/gate/gate_check.py --module .tmp/gate_solutions/v3/3.3.py
python chapters/part3-evals/3.7-eval-regression-curve/gate/gate_check.py --module .tmp/gate_solutions/v3/3.7.py
python chapters/part3-evals/3.8-prompt-ab-judge/gate/gate_check.py --module .tmp/gate_solutions/v3/3.8.py
python chapters/part3-evals/3.10-eval-report-failures/gate/gate_check.py --module .tmp/gate_solutions/v3/3.10.py
```
- **实测结果**：
  - 3.3: 14/14 passed (exit 0)
  - 3.7: 13/13 passed (exit 0)
  - 3.8: 5/5 passed (exit 0)
  - 3.10: 5/5 passed (exit 0)
  - 确定性复测：连续执行两次结果完全一致，`gate_report.json` 零差异。
  - 参考实现作为 `--module` 传入同样全部满分通过。

### 命令 4：回归测试套件全量执行
```bash
.venv\Scripts\pytest.exe tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
.venv\Scripts\pytest.exe capstone/test_production.py -q
```
- **实测结果**：
  - 基础套件：**71 passed**, 1 warning in 14.18s (exit 0)
  - 生产套件：**34 passed**, 1 warning in 8.98s (exit 0)
  - 小计：**105 项全部通过**。

### 命令 5：全书 Markdown 链接检查
```bash
python tools/check_course_links.py
```
- **实测结果**：扫描 368 个 Markdown 文件，**0 断链** (exit 0)。

### 命令 6：Ruff 静态代码检查（py311）
```bash
.venv\Scripts\ruff.exe check --target-version py311 chapters/part3-evals/ common.py tools/ chapters/test_v3_lessons.py
```
- **实测结果**：`All checks passed!` (exit 0)。

### 命令 7：LangChain 边界检查
```bash
git grep -n "from langchain" chapters/part3-evals/
git grep -n "import langchain" chapters/part3-evals/
```
- **实测结果**：0 匹配 (exit 1，无任何输出)，Part 3 原生实现完全零 LangChain LCEL 依赖。

### 命令 8 & 9：v2 与 v3 标签映射检查
```bash
python tools/apply_v2_map.py --check
python tools/apply_v3_map.py --check
```
- **实测结果**：
  - v2 标签：`合计：111 份 README，inserted=0 updated=0 unchanged=111` (exit 0)；
  - v3 标签：`inserted=81 unchanged=10 待建=28`，无倒退。

### 命令 10：参考实现离线执行与 `--live` 实测记录
1. **离线默认执行（exit 0）**：
   - `python tools/run_chapter.py 3.3` -> exit 0
   - `.venv\Scripts\python.exe tools/run_chapter.py 3.6 otel_tracing_eval.py` -> exit 0
   - `.venv\Scripts\python.exe tools/run_chapter.py 3.6 langsmith_eval.py` -> exit 0
   - `.venv\Scripts\python.exe tools/run_chapter.py 3.7` -> exit 0
   - `.venv\Scripts\python.exe tools/run_chapter.py 3.8` -> exit 0
   - `.venv\Scripts\python.exe tools/run_chapter.py 3.10` -> exit 0
2. **`--live` 场景 A（缺少有效 API Key）实测记录**：
   - 环境设置：`OPENAI_API_KEY="" DEEPSEEK_API_KEY="" LLM_PROVIDER="openai"`
   - 3.3 `llm_judge.py --live`: 退出码 1，输出 `[配置错误] 缺少必要的大模型 API Key`，无堆栈
   - 3.6 `otel_tracing_eval.py --live`: 退出码 1，输出 `[配置错误] 无法获取模型客户端`，无堆栈
   - 3.6 `langsmith_eval.py --live`: 退出码 1，输出 `[错误] 缺少 LANGSMITH_API_KEY`，无堆栈
   - 3.7 `regression_curve.py --live`: 退出码 1，输出 `[配置错误] 无法获取模型客户端`，无堆栈
   - 3.8 `prompt_ab_judge.py --live`: 退出码 1，输出 `[配置错误] 无法获取模型客户端`，无堆栈
3. **`--live` 场景 B（模型服务不可达）实测记录**：
   - 环境设置：`DEEPSEEK_BASE_URL="http://127.0.0.1:9" OPENAI_BASE_URL="http://127.0.0.1:9" NO_PROXY="127.0.0.1,localhost"`
   - 3.3 `llm_judge.py --live`: 退出码 1，输出 `[评测失败] 用例 'RAG 是什么？' 请求模型或打分出错: ...`，无未捕获异常
   - 3.6 `otel_tracing_eval.py --live`: 退出码 1，输出 `[运行失败] 在线请求过程中发生网络或模型错误: ...`，无未捕获异常
   - 3.6 `langsmith_eval.py --live`: 退出码 1，输出 `[网络错误] 无法连接到 LangSmith 服务: ...`，无未捕获异常
   - 3.7 `regression_curve.py --live`: 退出码 1，输出 `[网络错误] 在线调用模型失败（模型不可达或连接拒绝）`，快速失败，无未捕获异常
   - 3.8 `prompt_ab_judge.py --live`: 退出码 1，输出 `[评测失败] 在线调用模型失败（模型不可达或网络中断）`，无未捕获异常
4. **3.10 异常输入测试**：
   - `python chapters/part3-evals/3.10-eval-report-failures/failure_diagnosis.py --input nonexistent.json`
   - 实测输出：退出码 2，标准错误打印 `[错误] 加载失败库失败：未找到失败库：nonexistent.json`，零堆栈崩溃。

---

## 四、边界说明（Boundaries）

1. **时钟延迟与物理耗时**：
   在离线确定性演练中，Baseline 与 Candidate 的延迟采用模拟基线时钟值（如 120ms 与 160ms），用以演练百分位数与退化告警算法逻辑；真实端到端物理耗时需在配齐网络与凭证后通过 `--live` 度量。
2. **细则偏离说明**：
   - **3.6 章节命名与文件组织**：细则保留目录名 `3.6-langsmith-eval` 与平台示例 `langsmith_eval.py`；新增以 OpenTelemetry 为核心的 `otel_tracing_eval.py`，顺应 2026 技术演进趋势；
   - **3.7 Starter Docstring 补充**：starter docstring 显式补充记录了 `k < 1` 抛 ValueError、空字典输入返回 0.0 以及 floor 边界的合法性约束，确保学员在不看参考实现的前提下能严格实现 13 项通过；
   - **3.10 异常分流契约**：`load_failures` 缺失文件时抛出 `ValueError`（对齐 Gate 03 契约）；在 `main()` 统一捕获并在终端给出可读操作指引并以退出码 2 终止，消除未捕获堆栈。
