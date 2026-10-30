# V3-3 阶段 3 质量闭环实施验证 · 2026-10-30

本验证记录对应依据 `docs/v3/specs/L3.md` 与 `docs/v3/outline.md` 对阶段 3（L3.4、L3.6、L3.7）的重构实施与全量验证。

---

## 一、本次实施明细

| 编号 | 涉及章节 / 模块 | 分类 | 实现与整改说明 |
|---|---|---|---|
| **L3.4** | `chapters/part3-evals/3.3-llm-judge/` | 核心重构 | **LLM Judge 与校准**：<br>1. `llm_judge.py` 完全移除 LangChain 依赖，使用原生 OpenAI SDK（`common.get_openai_client()` / `common.chat_model_name()`）；<br>2. 实现基于 JSON Schema 的 Tool-as-Output 结构化评测打分契约（`submit_verdict`），兼容器具思考模式自动禁用（DeepSeek 等）；<br>3. 实现候选回答位置互换（Position Swap，正反序双轮调用），检测并缓解大模型对首位（Position A）的系统性偏好；<br>4. 实现一致率（Agreement Rate）与 Cohen's Kappa（$\kappa$）校准指标计算及混淆矩阵；<br>5. 默认完全离线确定性演练，`--live` 支持真实大模型接入；Gate 14/14 保持全绿。README 补充三级裁判梯队体系，引用 Anthropic 官方指南《Demystifying evals for AI agents》（2026-01-09，读取日期 2026-10-30），指向进阶章节 8.5。 |
| **L3.6** | `chapters/part3-evals/3.7-eval-regression-curve/`<br>`chapters/part3-evals/3.8-prompt-ab-judge/`<br>`chapters/part3-evals/3.10-eval-report-failures/` | 核心重构与扩展 | **回归曲线、A/B 评测与失败诊断**：<br>1. `3.7-eval-regression-curve/`: 追加 4 个纯函数（`pass_at_k`、`pass_all_k`、`empirical_pass_all`、`split_suites`），Gate 检查项扩展至 13 项（原有 8 项 + 新增 5 项）；`regression_curve.py` 改用原生调用与纯数据流处理，移除 LCEL 管道，默认离线确定性演练并输出回归告警与能力集/回归集拆分，`--live` 规范错误退出；<br>2. `3.8-prompt-ab-judge/`: `prompt_ab_judge.py` 改用原生 OpenAI SDK，对比 Strict 与 Helpful 两版 Prompt，支持 `--live` 与默认离线演练，Gate 5/5 保持全绿；<br>3. `3.10-eval-report-failures/`: `failure_diagnosis.py` 语言中性化，文件缺失抛出 `ValueError` 以对齐 Gate，新增导出 `summarize_layers` 函数。 |
| **L3.7** | `chapters/part3-evals/3.6-langsmith-eval/` | 平台演进 | **追踪与评测平台（OpenTelemetry 标准化）**：<br>1. 保留目录名 `3.6-langsmith-eval` 与平台示例 `langsmith_eval.py`；<br>2. 新建原生 OpenTelemetry 追踪实现 `otel_tracing_eval.py`，建立三层 Span 结构（`rag_pipeline` -> `rag_retrieval`、`assemble_context`、`chat_completion`），对齐 OpenTelemetry GenAI Semantic Conventions（`gen_ai.system`、`gen_ai.operation.name`、`gen_ai.usage.*` 等）；<br>3. 默认采用 `ConsoleSpanExporter` 离线输出控制台，零外部网络与凭证依赖；支持 `OTEL_EXPORTER_OTLP_ENDPOINT` 接入 OTLP 后端；默认开启敏感内容掩码（Privacy Redaction）；<br>4. 重写 `README.md`、`gate/CHECKLIST.md` 与 `workbook.md`，梳理 Langfuse、LangSmith、Phoenix 三大平台定位与隐私防线。 |
| **TEST** | `chapters/test_v3_lessons.py` | 自动化测试 | 追加 V3-3 自动化测试（涵盖 3.3 Cohen's Kappa 与解析、3.7 pass@k / pass^k / split_suites、3.8 评测指标、3.10 弱信号分流与统计、3.6 OTel 内存导出与属性断言），全量 34 项测试一次性通过。 |

---

## 二、真实组件与测试替身边界

| 模块 / 环节 | 实际运行的真实组件 | 测试替身（Mocks / 离线确定性逻辑） | 未验证 / 降级运行 |
|---|---|---|---|
| **LLM Judge 裁判** | `--live` 开启时真实通过 `common.get_openai_client()` 调用 OpenAI 兼容接口，并使用真实 Tool Calling | 默认离线模式基于规则提取器与确定性分数生成；Gate 测试使用 `judge_mock` 与合成样本集 | 未配置正式计费 API Key 运行完整百条大样本在线评测 |
| **回归曲线与指标** | `regression_curve.py` 真实执行百分位数 P50/P99 统计、pass@k 组合数精确计算与阈值报警 | 离线默认模式使用合成评测记录；Gate 检查通过注入模拟测试数据与异常指标检验 | 无 |
| **Prompt A/B 对比** | `--live` 模式下真实请求模型并度量输出字数、关键词与引用 | 默认离线模式使用固定对比知识库与两版 prompt 确定性输出 | 无 |
| **OpenTelemetry 追踪** | 真实加载 `opentelemetry-api` 与 `opentelemetry-sdk`，真实创建 Tracer、Span 并在内存与控制台完成序列化 | 离线模式使用 `ConsoleSpanExporter` / `InMemorySpanExporter`，不发起外部网络连接 | 外部 OTLP 后端（如 Langfuse / Phoenix Docker 实例）在本机离线环境下未配置连接（属可选验证项，已在 CHECKLIST 明确标注） |

---

## 三、Section 11 命令 1–10 逐项复跑验证结果

### 命令 1：Gate 默认骨架检查
运行各章 `gate/gate_check.py`，全部 4 个涉及 Gate 在骨架（starter）状态下均严格为 **0 通过（退出码 1）**：
- 3.3 `chapters/part3-evals/3.3-llm-judge/gate/gate_check.py`: **0/14 passed** (exit 1)
- 3.7 `chapters/part3-evals/3.7-eval-regression-curve/gate/gate_check.py`: **0/13 passed** (exit 1)
- 3.8 `chapters/part3-evals/3.8-prompt-ab-judge/gate/gate_check.py`: **0/5 passed** (exit 1)
- 3.10 `chapters/part3-evals/3.10-eval-report-failures/gate/gate_check.py`: **0/5 passed** (exit 1)

### 命令 2 & 3：Gate 临时参考解与确定性检查
1. 临时参考解检查（`.tmp/gate_solutions/v3/<章>.py`）：
   - 3.3: **14/14 passed** (exit 0)
   - 3.7: **13/13 passed** (exit 0)
   - 3.8: **5/5 passed** (exit 0)
   - 3.10: **5/5 passed** (exit 0)
2. 章节参考实现直接作为 `--module` 检查：
   - 3.3 (`llm_judge.py`): **14/14 passed** (exit 0)
   - 3.7 (`regression_curve.py`): **13/13 passed** (exit 0)
   - 3.8 (`prompt_ab_judge.py`): **5/5 passed** (exit 0)
   - 3.10 (`failure_diagnosis.py`): **5/5 passed** (exit 0)
3. 确定性检查：连续执行两次结果完全一致，退出码 0，无偶发失败。

### 命令 4：回归测试套件全量执行
- **课程工具与章节测试**：
  ```bash
  .venv\Scripts\python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
  ```
  实测输出：**68 passed**, 1 warning in 11.14s（退出码 0）。
- **Capstone 生产回归测试**：
  ```bash
  .venv\Scripts\python.exe -m pytest capstone/test_production.py -q
  ```
  实测输出：**34 passed**, 1 warning in 6.66s（退出码 0）。
- **小计**：测试套件 68 + 34 = **102 项全部通过**，退出码 0。

### 命令 5：全书 Markdown 链接校验
```bash
.venv\Scripts\python.exe tools/check_course_links.py
```
实测输出：扫描 366 个 Markdown 文件，**0 断链**（退出码 0）。

### 命令 6：Ruff 静态代码检查（目标版本 py311）
```bash
.venv\Scripts\ruff check --target-version py311 chapters/part3-evals/ common.py tools/ chapters/test_v3_lessons.py
```
实测输出：`All checks passed!`（退出码 0）。

### 命令 7：LangChain 边界检查
```bash
Get-ChildItem -Path chapters/part3-evals -Recurse -Filter *.py | Select-String -Pattern "^\s*(from|import)\s+(langchain|langgraph)"
```
实测输出：无任何输出（退出码 0，0 匹配）。除 `3.6-langsmith-eval/langsmith_eval.py` 中允许保留的 `from langsmith import Client, evaluate` 平台示例导入外，Part 3 原生实现与 Gate 脚本中完全零导入 `langchain*` / `langgraph*`。

### 命令 8：v2 标签映射检查
```bash
.venv\Scripts\python.exe tools/apply_v2_map.py --check
```
实测输出：`合计：111 份 README：inserted=0 updated=0 unchanged=111`（退出码 0）。

### 命令 9：v3 标签映射检查
```bash
.venv\Scripts\python.exe tools/apply_v3_map.py --check
```
实测输出：已有章节 `inserted=81`，本批次及已完成章节保持一致，待建章节 `待建=28`，符合课程推进预期。

### 命令 10：参考实现离线启动与 `--live` 失败场景
1. **离线默认启动（退出码 0）**：
   - `python chapters/part3-evals/3.3-llm-judge/llm_judge.py` -> exit 0，输出 Rubric 打分、Position Bias 消除演示与 Cohen's Kappa 校准报告；
   - `python chapters/part3-evals/3.6-langsmith-eval/otel_tracing_eval.py` -> exit 0，控制台输出格式化 OTel Spans，包含 `gen_ai.*` 属性与隐私掩码；
   - `python chapters/part3-evals/3.7-eval-regression-curve/regression_curve.py` -> exit 0，输出 Baseline/Candidate 告警、pass@k/pass^k 及回归集拆分；
   - `python chapters/part3-evals/3.8-prompt-ab-judge/prompt_ab_judge.py` -> exit 0，输出 Strict 与 Helpful 两版 Prompt 综合对比数据；
   - `python chapters/part3-evals/3.10-eval-report-failures/failure_diagnosis.py` -> exit 0，输出一级弱信号分流及失败根因分布。
2. **`--live` 缺少有效 API Key 时（退出码 1）**：
   - `3.3-llm-judge`: 优雅捕获 401 认证异常，输出清晰失败原因并以退出码 1 终止，无未捕获 trace 崩溃；
   - `3.6-langsmith-eval` (`otel_tracing_eval.py`): 真实将异常记录在 `chat_completion` Span 与 `rag_pipeline` Span（`status_code="ERROR"`, 记录 exception event），打印失败提示并以退出码 1 终止；
   - `3.7-eval-regression-curve`: 优雅捕获 401 认证异常，以退出码 1 终止；
   - `3.8-prompt-ab-judge`: 优雅捕获 401 认证异常，以退出码 1 终止。

---

## 四、细则偏离与工程决策说明

1. **3.6 目录命名保持与 OTel 标准升级**：
   - 细则与大纲要求：保留历史目录名 `chapters/part3-evals/3.6-langsmith-eval/`，避免破坏外部引用与现有链接；
   - 实现策略：保留 `langsmith_eval.py` 作为平台接入示范，主推新建的原生标准 `otel_tracing_eval.py`；
   - OpenTelemetry GenAI 约定状态标注：在 README 与代码中明确注明截至 2026-10-30，规范仍处于 Development / 演进状态，并附带官方文档链接。
2. **DeepSeek 思考模式与 Tool-Calling 兼容**：
   - 发现 DeepSeek 兼容接口在强制 `tool_choice={"type": "function", ...}` 且未禁用思考时会触发 `400 Thinking mode does not support this tool_choice`；
   - 在 `llm_judge.py` 中显式添加 `extra_body={"thinking": {"type": "disabled"}}` 并提供 `tool_choice="auto"` 自动回退保护，确保在各类兼容端点下稳健运行。
3. **临时参考解保留与清理**：
   - `.tmp/gate_solutions/v3/` 下的 `3.3.py`、`3.7.py`、`3.8.py`、`3.10.py` 作为评审证据在分支中保留，待复核确认通过合入 master 后统一清理。
