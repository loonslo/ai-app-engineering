# V3-3 阶段 3 质量闭环复核整改验证 · 2026-10-31

## 后续补查：报告写入边界（2026-10-31）

在已有未提交整改上继续自检，未代替 Claude 复核，也未合并或启动 V3-4。

- 先运行 `.venv/Scripts/python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py capstone/test_production.py -q`：原有 108 项通过。
- 新增写入函数测试后，运行 `.venv/Scripts/python.exe -m pytest chapters/test_v3_lessons.py -k 'writer_protects or cli_report_boundary' -q --basetemp=.tmp/pytest-ab-boundary`：3 failed、5 passed，复现直接调用 `write_ab_report(..., root_evidence=True)` 可以绕过 CLI，覆盖根目录证据。复现只操作 pytest 临时目录中的替身文件。
- 最小修复：写入前校验 `mode=live`、非空模型 ID、Strict/Helpful 两版均有可用裁判结果；不满足时抛 `ValueError`，任何报告文件都尚未写入。保留现有 CLI 行为，不改 gate。
- 新增 8 个参数化测试：3 个直接写入拒绝场景；5 个 CLI 场景（离线、离线要求更新、模拟在线成功、全部裁判降级、部分降级）。验证原文件内容和纳秒修改时间保持不变，或模拟在线结果按预期写出；部分降级的条目从一致率样本数中排除。
- 修复后重跑同一完整 pytest 命令：116 passed、1 warning（Chroma 的 `asyncio.iscoroutinefunction` 弃用提示）。在线成功测试使用脚本化假生成器和假裁判，不调用真实模型，不读真实凭据，不更新仓库实际证据。
- `.venv/Scripts/python.exe -m ruff check --target-version py311 chapters/part3-evals common.py tools chapters/test_v3_lessons.py`：通过。
- `.venv/Scripts/python.exe tools/check_course_links.py`：368 个 Markdown、0 断链。`apply_v2_map.py --check`：111 unchanged；`apply_v3_map.py --check`：inserted=81、updated=0、unchanged=10、待建=28，退出 1 是 V3-10 前的预期状态。
- 在 Python 3.14.4 下，通过 `subprocess.run` 再执行下文第三节所列的四个 gate 命令：骨架退出 1，临时参考解退出 0、连跑两次输出一致，本章实现作为 `--module` 也均退出 0。六个参考入口离线执行均退出 0，无 Traceback；实际根报告字节内容和纳秒修改时间均保持不变。
- 通过子进程分别执行 3.3、3.6 两个入口、3.7、3.8 的 `--live`：统一设 `LLM_PROVIDER=openai`、`OPENAI_BASE_URL=http://127.0.0.1:9/v1`、`NO_PROXY=127.0.0.1,localhost`，关闭 LangSmith tracing；缺密钥场景令 `OPENAI_API_KEY` 为空，不可达场景使用假占位值。10 次运行均退出 1，无 Traceback 或 `exception.stacktrace`，未连接真实模型或远端追踪平台。
- `git diff --check` 通过；项目内自行核对 `PROJECT_STATUS.md` 的字段唯一性、必填项、未加引号日期、允许状态、非空字符串和 39 条 evidence 路径，均通过。未使用跨项目日常同步工具。

本次只修改 3.8 参考实现、3.8 README、`chapters/test_v3_lessons.py` 和项目任务/验证/状态文档。未改审核者结论，未修改 capstone 或冻结的旗舰快照。真实模型成功路径、远端 OTLP 和原报告恢复仍未验证。

本记录对应 `docs/v3/reviews/V3-3.md` 复核一节（2026-10-31）退回的 2 个阻断项（N1、B1-r）、4 个主要问题（M1-r、M9、M6-r、M8-r）与 5 个次要问题（b2-r、m2-r、m5-r、m7、m8）。只记录本轮实际执行过的命令与结果；未运行的真实模型、远端后端与原件恢复列入“未验证”。

---

## 一、范围（Scope）

### 1. 整改内容

- **N1（3.8 judge 结果与证据文件）**：
  - 默认离线运行只写 `chapters/part3-evals/3.8-prompt-ab-judge/reports/`，不再写仓库根目录；只有 `--live --update-evidence` 才更新根目录证据，报告记录 `mode`、模型 ID、生成时间与 judge 来源；
  - live 裁判改为复用 3.3 的 `run_native_judge_eval`（`extra_body.thinking.type=disabled`，只在思考模式冲突的 400 时降级）；调用失败不再静默改用规则，而是标记 `degraded=True` / `source="rule"`，汇总时排除出一致率；
  - 删除 `ab_048` 的按题特判，改掉该用例会触发拒答特征词的措辞；
  - 人工标签补充 2 条 `manual_score=2` 的负向用例（ab_056、ab_057）；只有一类标签时 `cohen_kappa` 返回 `null` 并说明“不可计算”；
  - 结论句按 L3 出口阈值（一致率 ≥ 80%）由数值得出，不再写死“稳定可信”；
  - `reports/README.md` 说明原文件已被覆盖、原件丢失、内容不能作为证据；`capstone/interview_evidence.py` 从证据中移除该文件。
- **B1-r（3.6 检索 span 与消息正文）**：
  - 检索 span 的 kind 改为 `CLIENT`，README 按 `gen-ai-spans.md` 写明“Span kind SHOULD be `CLIENT`”；
  - `--capture-content` 时 `gen_ai.input.messages` / `gen_ai.output.messages` 按 role + parts 的 JSON schema 序列化后写入；
  - `resolve_provider_name()` 按注册表映射：`azure` → `azure.ai.openai`、`bedrock` → `aws.bedrock`；兼容网关无法判断厂商时用 `custom`，不冒用 `openai`。
- **M1-r（3.3、3.7 被测 RAG）**：
  - 3.3 的离线与 live 都改用 2.6 的 `build_retriever` / `build_rag_chain`；live 读取 `chapters/shared-data/eval_set_full.json`（没有时读 `eval_set.json`），逐题评分并输出正确性、忠实度平均分；文件缺失时给出可读提示并以 1 退出；
  - 3.7 的检索改用 2.6 的 `build_retriever` / `format_context`，不再使用本章自写的关键词段落匹配。
- **M9（3.6 stacktrace）**：根 span 与推理 span 以 `record_exception=False` 创建，异常路径只手动写 `error.type` 与清洗后的状态描述；实际跑一次 `--live` 失败场景，输出中没有 `exception.stacktrace`。
- **M6-r（3.6 README）**：补“Agent 与工具调用”小节（`invoke_agent`、`execute_tool`、`gen_ai.agent.name`、`gen_ai.tool.name`、`gen_ai.tool.call.id` 等，附规范链接）；Stack Overflow 一条补链接与读取日期，并把 2,277 说明为回答该题的人数，而不是“使用 AI 工具的专业开发者”。
- **M8-r（本记录）**：文件清单把根 `reports/prompt_ab_judge_agreement.json` 记为“覆盖”而非“新增”；检索 span 记为 CLIENT；删除“恢复真实文档切片检索”这类不准确表述；补齐细则偏离；B2 一行按 3.7 README 的实际改法重写。
- **次要问题**：b2-r 把 pass@k / pass^k 的对应关系标为本章判断；m2-r 统一 `[REDACTED_BY_DEFAULT]` 占位符并在代码中补 `app.privacy.placeholder`；m5-r 去掉“严禁”“有效避免误判 A 为绝对优胜”；m7 补 DeepSeek 文档链接与错误原文说明，补位置互换的倒序胜出与平局测试；m8 在 3.7 失败记录中写入 `mode`，3.10 README 提醒离线失败库加 `--mode offline`。

### 2. 文件清单

| 变更类型 | 文件 | 摘要 |
|---|---|---|
| 修改 | `chapters/part3-evals/3.3-llm-judge/llm_judge.py` | 复用 2.6 检索与 RAG 链；live 读共享评测集并汇总平均分 |
| 修改 | `chapters/part3-evals/3.3-llm-judge/README.md` | 补在线评测与被测系统说明、DeepSeek 文档链接与错误原文说明 |
| 修改 | `chapters/part3-evals/3.6-langsmith-eval/otel_tracing_eval.py` | 检索 span CLIENT；消息 JSON schema；provider 映射；`record_exception=False`；占位符统一 |
| 修改 | `chapters/part3-evals/3.6-langsmith-eval/README.md` | 检索 kind、Agent/工具调用属性、Stack Overflow 出处与样本、隐私说明 |
| 修改 | `chapters/part3-evals/3.6-langsmith-eval/gate/CHECKLIST.md` | 去掉“严禁”措辞 |
| 修改 | `chapters/part3-evals/3.7-eval-regression-curve/regression_curve.py` | 复用 2.6 检索；失败记录加 `mode` |
| 修改 | `chapters/part3-evals/3.7-eval-regression-curve/README.md` | pass@k / pass^k 标为本章判断；补失败库 `mode` 与 3.10 `--mode` 说明 |
| 修改 | `chapters/part3-evals/3.8-prompt-ab-judge/prompt_ab_judge.py` | 报告写入规则、复用 3.3 裁判、降级标记、κ 不可计算、负向用例、阈值结论 |
| 修改 | `chapters/part3-evals/3.8-prompt-ab-judge/README.md` | 补运行模式与报告写入规则 |
| 修改 | `chapters/part3-evals/3.10-eval-report-failures/README.md` | 提醒 3.7 离线失败库用 `--mode offline` |
| 修改 | `chapters/test_v3_lessons.py` | 补 OTel 属性/消息 schema、provider 映射、位置互换倒序与平局、3.8 κ 与降级测试 |
| 修改 | `reports/README.md` | 说明根报告被覆盖后的离线遗留文件已删除（原件仍丢失）、默认不写根目录 |
| 修改 | `capstone/interview_evidence.py` | 证据中移除 `reports/prompt_ab_judge_agreement.json` |
| 修改 | `docs/gate-v3-3-validation.md` | 本记录 |
| 修改 | `TASKS.md`、`PROJECT_STATUS.md` | 同步本轮整改进度与证据 |
| **删除** | `reports/prompt_ab_judge_agreement.json` | 2026-10-30 23:20 被 3.8 离线替身结果覆盖后的遗留文件已删除（原件仍丢失）；原件含原始 LangSmith 数据集与实验名称，`git` 与 `.tmp` 中均无原件 |
| 生成（忽略） | `chapters/part3-evals/3.8-prompt-ab-judge/reports/prompt_ab_judge_agreement.json` | 本轮离线运行生成，`mode=offline`，仅作教学演示 |
| 生成（忽略） | `chapters/shared-data/failures.json` | 3.7 `--write-failures` 生成的失败库，含 `mode` 字段 |
| 生成（忽略） | `chapters/part3-evals/3.10-eval-report-failures/reports/failure_diagnosis.json` | 3.10 诊断输出 |

没有新增纳入版本控制的文件。

### 3. 删除清单

1. 删除 3.8 中 `ab_048` 的按题特判（`if case.get("id") == "ab_048"`）。
2. 删除 3.8 自带的 `JUDGE_TOOL`，改用 3.3 的裁判工具契约。
3. 删除 3.3 的 `retrieve_context_offline()` 与 3.7 的 `retrieve_chunks()` 两套自写关键词检索。
4. 删除 3.8 默认写仓库根目录 `reports/` 的行为，改为 `--live --update-evidence` 显式触发。
5. 删除 3.8 写死的“表明当前裁判标准稳定可信”结论句。
6. 删除 3.6 的 `redacted_for_privacy` 占位写法，统一为 `[REDACTED_BY_DEFAULT]`。

---

## 二、未验证事项

1. **真实模型在线评测**：本轮没有调用真实 DeepSeek/OpenAI 模型。3.3、3.7、3.8 的 live 成功路径未跑；只验证了缺密钥、模型不可达两种失败场景，以及用假客户端模拟 DeepSeek 400 的 3.8 降级路径。
2. **远端 OTLP 后端**：没有搭建 Langfuse / Phoenix，未验证真实网络发送后的平台 UI；Span 属性通过 `ConsoleSpanExporter` 与 `InMemorySpanExporter` 断言。
3. **DeepEval 二级复核**：当前环境未安装 `deepeval`，3.10 的维度分路径未执行。
4. **原证据恢复**：`reports/prompt_ab_judge_agreement.json` 被覆盖后的离线遗留文件已删除（原件仍丢失），且已从 capstone 证据中移除。`git` 历史中另有一份 2026-06-23 的旧离线报告（提交 `76f2ff5`，52 例、`mode=offline`），schema 与丢失的 LangSmith 原件不同，未拿它冒充原件。
5. **3.3 live 平均分**：共享评测集读取到 17 条，但真实评分未执行，因此没有真实平均分。

---

## 三、复现方式（实际执行）

环境：Windows，`.venv\Scripts\python.exe`（Python 3.14.4），工作目录为仓库根目录。未设置真实模型密钥进行在线调用；模型不可达场景使用 `DEEPSEEK_BASE_URL=http://127.0.0.1:9` 与 `NO_PROXY=127.0.0.1,localhost`。

### 1. 四个 gate

```bash
python chapters/part3-evals/3.3-llm-judge/gate/gate_check.py
python chapters/part3-evals/3.7-eval-regression-curve/gate/gate_check.py
python chapters/part3-evals/3.8-prompt-ab-judge/gate/gate_check.py
python chapters/part3-evals/3.10-eval-report-failures/gate/gate_check.py
```

结果：骨架 0/14、0/13、0/5、0/5，均以 1 退出。

```bash
python chapters/part3-evals/3.3-llm-judge/gate/gate_check.py --module .tmp/gate_solutions/v3/3.3.py
python chapters/part3-evals/3.7-eval-regression-curve/gate/gate_check.py --module .tmp/gate_solutions/v3/3.7.py
python chapters/part3-evals/3.8-prompt-ab-judge/gate/gate_check.py --module .tmp/gate_solutions/v3/3.8.py
python chapters/part3-evals/3.10-eval-report-failures/gate/gate_check.py --module .tmp/gate_solutions/v3/3.10.py
```

结果：14/14、13/13、5/5、5/5，均以 0 退出。把本章实现文件本身作为 `--module` 传入，结果相同。

### 2. 测试

```bash
.venv\Scripts\pytest.exe tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
.venv\Scripts\pytest.exe capstone/test_production.py -q
```

结果：`74 passed`（1 warning）；`34 passed`（1 warning）。合计 108 项通过。

### 3. 静态检查

```bash
.venv\Scripts\ruff.exe check --target-version py311 chapters/part3-evals/ common.py tools/ chapters/test_v3_lessons.py
python tools/check_course_links.py
python tools/apply_v2_map.py --check
python tools/apply_v3_map.py --check
git grep -n "from langchain" chapters/part3-evals/
git grep -n "import langchain" chapters/part3-evals/
```

结果：ruff `All checks passed!`；368 个 Markdown、断链 0；v2 `111 unchanged`；v3 `inserted=81 unchanged=10 待建=28`；part3 无 LangChain 导入；`langsmith` 只出现在 3.6。

### 4. 参考实现离线运行

```bash
python tools/run_chapter.py 3.3
python tools/run_chapter.py 3.6 otel_tracing_eval.py
python tools/run_chapter.py 3.6 langsmith_eval.py
python tools/run_chapter.py 3.7
python tools/run_chapter.py 3.8
python tools/run_chapter.py 3.10
```

结果：全部以 0 退出，无未捕获堆栈。3.3 离线检索来自 2.6 的 `retriever`（`[来源：test_doc.txt]` 上下文）；3.7 离线检索同样来自 2.6。

### 5. `--live` 失败场景

缺密钥（`LLM_PROVIDER=openai`、`OPENAI_API_KEY` 为空）：

```bash
python tools/run_chapter.py 3.3 --live
python tools/run_chapter.py 3.6 otel_tracing_eval.py --live
python tools/run_chapter.py 3.6 langsmith_eval.py --live
python tools/run_chapter.py 3.7 --live
python tools/run_chapter.py 3.8 --live
```

结果：均以 1 退出，输出可读的缺密钥提示，无 Traceback。

模型不可达（`DEEPSEEK_BASE_URL=http://127.0.0.1:9`）：

```bash
python tools/run_chapter.py 3.3 --live
python tools/run_chapter.py 3.6 otel_tracing_eval.py --live
python tools/run_chapter.py 3.7 --live
python tools/run_chapter.py 3.8 --live
```

结果：均以 1 退出，无未捕获堆栈。3.3 在失败前已读取 17 条共享评测集用例；3.7 读取 10 条。3.6 的控制台 Span 输出中检索与推理 span 为 `SpanKind.CLIENT`，根 span 与上下文拼装为 `SpanKind.INTERNAL`；`error.type=APIConnectionError`，没有 `exception.stacktrace` 事件。

### 6. 3.8 报告与降级

```bash
python tools/run_chapter.py 3.8
python tools/run_chapter.py 3.8 --update-evidence
```

结果：当时默认离线运行前后，仓库根目录 `reports/prompt_ab_judge_agreement.json` 的修改时间未变化（2026-10-30 23:20:56；该离线遗留文件现已删除，原件仍丢失）；章节本地报告 `mode=offline`，`judge_human_agreement.*.available=false`，结论为“离线模式使用确定性规则打分……不能作为 LLM Judge 校准证据”。`--update-evidence` 不带 `--live` 时以 2 退出，提示“离线结果不会覆盖仓库证据文件”。

用假客户端模拟 DeepSeek 思考模式对强制 `tool_choice` 返回 400：`judge_answer` 返回 `source="rule"`、`degraded=True`、`error="Fake400: Thinking mode does not support this tool_choice"`，并在 stderr 明确提示“不计入 LLM Judge 一致率”。该行为有单元测试覆盖。

### 7. 3.7 → 3.10 失败库

```bash
python tools/run_chapter.py 3.7 --write-failures
python tools/run_chapter.py 3.7 --fail-on-regression
python tools/run_chapter.py 3.10 --mode offline
python chapters/part3-evals/3.10-eval-report-failures/failure_diagnosis.py --input nonexistent_xyz.json
```

结果：失败库含 `mode` 字段，3.10 以 `--mode offline` 读取 2 条失败并完成一级分流；`--fail-on-regression` 在退化时以 1 退出；3.10 缺文件时以 2 退出并给出可读提示。

---

## 四、边界（Boundaries）

1. **离线延迟是固定值**：3.7 离线 Baseline/Candidate 的 120ms/160ms 是模拟时钟，只用于演示分位数与告警算法；真实物理耗时需 `--live`。
2. **3.8 离线报告不是证据**：它只用于教学演示，`mode=offline`、`available=false`，不能当作 LLM Judge 校准结果。根目录 `reports/prompt_ab_judge_agreement.json` 被覆盖后的离线遗留文件已删除（原件仍丢失）。
3. **3.6 检索 span 用 CLIENT 是规范建议**：`gen-ai-spans.md` 写的是 “Span kind SHOULD be `CLIENT`”；本章检索在进程内执行，仍按规范记为 CLIENT，没有另写偏离说明。若未来改为明确的进程内检索实现，可以再评估是否登记偏离。
4. **provider 映射**：`azure` 与 `bedrock` 按注册表写 `azure.ai.openai`、`aws.bedrock`；`openai_compatible` 只有从 base URL 能判断厂商时才写具体值，否则写 `custom`，不冒用 `openai`。
5. **3.7 失败库与 3.10 推断**：3.7 现在离线也会写入真实 `retrieval_context`，3.10 仍按该字段推断 live；用离线失败库时必须显式加 `--mode offline`。3.10 的代码按细则要求不再改动，只在 README 提醒。
6. **3.10 的代码改动属于上一轮**：`load_failures` 抛 `ValueError`、`main()` 捕获后以 2 退出、`summarize_layers` 与 deepeval 容错，都是上一轮已登记的细则偏离，本轮未再改代码。

---

## 五、细则偏离

1. **3.7 starter docstring**：补充 `k < 1`、空字典、`regression_floor` 越界的约束（上一轮）。
2. **3.10 异常处理与诊断函数**：`load_failures` 缺文件抛 `ValueError`；`main()` 捕获并以 2 退出；新增 `summarize_layers` 与 deepeval 可选导入容错（上一轮）。
3. **3.8 报告与用例**：新增 `--update-evidence`、`mode`/`model`/`generated_at`/`judge` 字段，用例从 10 条增加到 12 条（补 2 条人工不合格的负向样本）；这是为了满足 N1 的证据边界与 κ 可计算要求。
4. **3.6 新增 `otel_tracing_eval.py`**：保留目录名与 `langsmith_eval.py` 平台示例，新增以 OpenTelemetry 为核心的实现（上一轮）。
5. **3.3、3.7 复用 2.6**：这是对 M1-r 的整改，不是偏离；2.6 的 `build_retriever` / `build_rag_chain` 本来就是为下游保留的入口。

---

## 六、逐条对应

| 问题 | 本轮处理 | 证据 |
|---|---|---|
| N1 | 默认不写根报告；`--live --update-evidence` 才更新；复用 3.3 裁判；降级标记并排除；删 `ab_048` 特判；补负向用例；κ 不可计算；结论按 80% 阈值；证据移除 | 3.8 代码、3.8 README、`reports/README.md`、`capstone/interview_evidence.py`、单元测试 |
| B1-r | 检索 span CLIENT；消息 JSON schema；provider 注册表映射 | 3.6 代码、README、OTel 测试 |
| M1-r | 3.3、3.7 改用 2.6 检索/生成；3.3 live 读共享评测集并汇总平均分 | 3.3/3.7 代码与 README；离线/失败运行输出 |
| M9 | `record_exception=False`，手动 `error.type`；失败运行无 stacktrace | 3.6 代码；`--live` 不可达输出 |
| M6-r | 补 Agent/工具调用属性；Stack Overflow 链接、读取日期与样本说明 | 3.6 README |
| M8-r | 本记录按实际改写；根报告记“覆盖”；检索 span 记 CLIENT；补偏离 | 本文件 |
| b2-r | pass@k/pass^k 的对应标为本章判断，补原文选择依据 | 3.7 README |
| m2-r | 占位符统一为 `[REDACTED_BY_DEFAULT]`；补 `app.privacy.placeholder` | 3.6 代码、README、workbook、测试 |
| m5-r | 去掉“严禁”“有效避免误判 A 为绝对优胜” | CHECKLIST、3.3 离线输出 |
| m7 | DeepSeek 文档链接与错误原文说明；补倒序胜出、平局测试 | 3.3 README、测试 |
| m8 | 3.7 失败记录加 `mode`；3.10 README 提醒 `--mode offline` | 3.7 代码、3.10 README |

---

## 七、合入前仍需

- 审核者复核 N1、B1-r、M1-r、M9、M6-r、M8-r 与 5 个次要问题；
- 真实模型在线跑一次 3.3、3.7、3.8 的成功路径（本轮未调用真实模型）；
- 用户 2026-10-31 决定不再恢复 LangSmith 原报告；保持“离线遗留文件已删除（原件仍丢失）”的状态，不作为证据引用。

---

## 八、后续补查：DeepSeek live 成功路径（2026-10-31）

用本机 `.env` 的 `DEEPSEEK_API_KEY`、模型 `deepseek-flash`，在仓库根目录实际执行 `python tools/run_chapter.py 3.3 --live`、`3.7 --live`、`3.8 --live`（均不加 `--update-evidence`），三条命令退出码 0。

| 章节 | 观测 |
|---|---|
| 3.3 | 共享评测集 17 条；平均正确性 5.00/5，平均忠实度 5.00/5。全部满分，不能据此判断裁判是否过松，需另配负例校准。 |
| 3.7 | 抽前 10 条。Baseline 通过率 100%；Candidate 通过率 10%、引用分 10%，触发 2 条回归告警。这是候选 Prompt 的真实退化，按设计应报警。 |
| 3.8 | 12 条全部由 LLM 裁判计入，无降级。Strict 一致率 83.3%（κ 0.5714），Helpful 一致率 100%（κ 1.0000）；两版都不低于 80% 出口线。Strict 在多题只答“信息不足，无法回答。”，综合通过率 41.7%。 |

边界：单次运行，无重复；3.8 未加 `--update-evidence`，根目录 `reports/` 未写入，也没有恢复原 LangSmith 报告；第 7 节中“真实模型在线跑一次”一项已完成，其余未变。第 2 节第 1、5 项的“未执行”表述以本节为准。
