# V3-4 L4-A Agent 控制流验证 · 2026-10-31

完成 L4.1–L4.8；这是教程实现与离线规则验证，不代表本人已学完或生产验收。默认演示使用脚本化模型；真实模型只由显式 `--live` 开启。

## 范围与改动文件

以下路径均相对仓库根目录。未改根 README、chapters/README、flagship-project、capstone、待跟进，也未提交 git。

| 细则 | 目录 | 修改文件 | 新增文件 |
|---|---|---|---|
| L4.1 | `chapters/part4-agents-langgraph/4.1-agent-patterns/` | `README.md`、`workbook.md`、`agent_patterns.py`、`gate/starter.py`、`gate/gate_check.py` | — |
| L4.2 | `chapters/part4-agents-langgraph/4.5-react-agent/` | `README.md`、`react_agent.py`、`react_loop.py`、`react_reliability.py` | `react_agent_langchain.py`（原实现迁入） |
| L4.3 | `chapters/part4-agents-langgraph/4.18-tool-design/` | — | `README.md`、`workbook.md`、`tool_design.py`、`gate/starter.py`、`gate/gate_check.py` |
| L4.4 | `chapters/part4-agents-langgraph/4.7-structured-routing/` | `README.md`、`structured_routing.py` | — |
| L4.4 | `chapters/part4-agents-langgraph/4.8-plan-and-execute/` | `README.md`、`plan_and_execute.py` | — |
| L4.5 | `chapters/part4-agents-langgraph/4.16-pydantic-ai-agent/` | — | `README.md`、`workbook.md`、`pydantic_ai_agent.py`、`gate/starter.py`、`gate/gate_check.py` |
| L4.6 | `chapters/part4-agents-langgraph/4.14-supervisor-fanout/` | `README.md`、`workbook.md`、`langgraph_supervisor.py` | `supervisor_native.py` |
| L4.7 | `chapters/part3-evals/3.9-agent-trajectory-eval/` | `README.md`、`workbook.md`、`trajectory_eval.py`、`gate/starter.py`、`gate/gate_check.py` | — |
| L4.8 | `chapters/part4-agents-langgraph/4.17-native-vs-sdk-gate/` | — | `README.md`、`workbook.md`、`native_vs_sdk_gate.py`、`gate/starter.py`、`gate/gate_check.py`、`gate/scenarios.py` |
| 集成 | 根目录与共享入口 | `requirements-course.txt`、`requirements-dev.txt`、`tools/course_catalog.py`、`chapters/test_new_lessons.py`、`chapters/test_v3_lessons.py`、`TASKS.md`、`PROJECT_STATUS.md` | 本记录 |

没有删除文件。删除/替换的旧实现：4.1 的 LangGraph 构图与暂停参数改为原生 `run_agent`；4.5 的原框架实现迁到对照文件；4.5 另两个脚本、4.7、4.8 的框架调用改为原生调用。4.14 的图版保留，只把模型初始化移入 `--live`、复用 common 工厂并集中异常提示。原固定流水线、并行、委派等演示保留。

9 个 gate 运行时生成的 `gate/gate_report.json` 是忽略的运行产物，不是独立模型质量证据。临时参考解全部保留在 `.tmp/gate_solutions/v3/`，不入库。

## 实际执行

环境：Windows，`.venv/Scripts/python.exe`，实际 `--version` 为 Python 3.14.4；子进程设 `PYTHONUTF8=1`。下文 `python` 均指该解释器；ruff 实际用 `.venv/Scripts/ruff.exe`。

### 1. 逐章 gate、全量复跑与确定性

每章完成后先运行骨架、再运行对应临时参考解；集成后又统一执行下列每行的三个命令：

1. `python <gate_check.py>`；
2. `python <gate_check.py> --module .tmp/gate_solutions/v3/<章号>.py`；
3. 与命令 2 完全相同，再运行一次，并逐字比较 stdout、stderr 与退出码。

| 章号 | 实际 gate_check.py 路径 | 骨架（exit 1） | 临时解（两次均 exit 0） | 两次输出 |
|---|---|---|---|---|
| 4.1 | `chapters/part4-agents-langgraph/4.1-agent-patterns/gate/gate_check.py` | 0/14 | 14/14 | 一致 |
| 4.5 | `chapters/part4-agents-langgraph/4.5-react-agent/gate/gate_check.py` | 0/14 | 14/14 | 一致 |
| 4.18 | `chapters/part4-agents-langgraph/4.18-tool-design/gate/gate_check.py` | 0/16 | 16/16 | 一致 |
| 4.7 | `chapters/part4-agents-langgraph/4.7-structured-routing/gate/gate_check.py` | 0/4 | 4/4 | 一致 |
| 4.8 | `chapters/part4-agents-langgraph/4.8-plan-and-execute/gate/gate_check.py` | 0/6 | 6/6 | 一致 |
| 4.16 | `chapters/part4-agents-langgraph/4.16-pydantic-ai-agent/gate/gate_check.py` | 0/15 | 15/15 | 一致 |
| 4.14 | `chapters/part4-agents-langgraph/4.14-supervisor-fanout/gate/gate_check.py` | 0/5 | 5/5 | 一致 |
| 3.9 | `chapters/part3-evals/3.9-agent-trajectory-eval/gate/gate_check.py` | 0/11 | 11/11 | 一致 |
| 4.17 | `chapters/part4-agents-langgraph/4.17-native-vs-sdk-gate/gate/gate_check.py` | 0/21 | 21/21 | 一致 |

合计参考解 106/106。4.1 保留原 8 项名称、顺序和行为断言，追加 6 项；3.9 保留原 7 项，追加 4 项。4.5、4.7、4.8、4.14 的 gate 未改。

实施期间 4.16 首次参考解曾因当前 SDK 不接受构造参数 `instrument=` 失败；改用 `agent.instrument=False` 后全过，最终复跑结果如表。4.17 增强变异体后再跑仍为 21/21；变异体实际绕过审批调用退款 handler，评测将其判失败。8 个固定场景同时运行原生循环与真实 Pydantic AI `FunctionModel`，不是拿预填报告作比较。

### 2. pytest 与 tools 测试

```text
.venv/Scripts/python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
```

实际：`91 passed, 1 warning in 12.90s`，exit 0。warning 来自 Chroma 的 `asyncio.iscoroutinefunction` 弃用提示。命令包含 tools 全部测试，未另算一遍。

4.1 的两项 Agent 回归从 `build_graph().invoke(...)` 迁为原生 `run_agent(...)`：正常工具循环、重复动作预算终止、未知工具与非法参数仍被覆盖。原暂停恢复测试改测 4.11 已有的离线 HITL 图，断言恢复不重复执行 prepare，未删除检查点教学测试。新增 9 项 V3-4 离线回归覆盖五模式、真并行与资料隔离、结果评分、原生错误/预算/审批、枚举路由、计划失败恢复、SDK 历史与审批、工具幂等及两实现同场景。

### 3. 断链与静态检查

```text
.venv/Scripts/python.exe tools/check_course_links.py
```

首次执行：374 个 Markdown、0 断链，exit 0（当时尚未创建本记录）；记录与状态文件写入后，原命令再跑：375 个 Markdown、0 断链，exit 0。

```text
.venv/Scripts/ruff.exe check --target-version py311 chapters/part4-agents-langgraph/4.1-agent-patterns chapters/part4-agents-langgraph/4.5-react-agent chapters/part4-agents-langgraph/4.7-structured-routing chapters/part4-agents-langgraph/4.8-plan-and-execute chapters/part4-agents-langgraph/4.14-supervisor-fanout chapters/part4-agents-langgraph/4.16-pydantic-ai-agent chapters/part4-agents-langgraph/4.17-native-vs-sdk-gate chapters/part4-agents-langgraph/4.18-tool-design chapters/part3-evals/3.9-agent-trajectory-eval chapters/test_new_lessons.py chapters/test_v3_lessons.py tools/course_catalog.py
```

首次发现历史对照版 `langgraph_supervisor.py` 两个 E402；将两条导入移至顶部后，原命令复跑 `All checks passed!`，exit 0。没有运行格式化器。

### 4. LangChain 边界与标签

用仓库搜索工具执行 `^\s*(from|import) (langchain|langgraph)`：范围为表中 9 个章节目录，排除文件名含 `langchain` 或 `langgraph` 的保留对照版。实际 `No matches found`。没有把其他尚未改造批次纳入零泄漏结论。

```text
.venv/Scripts/python.exe tools/apply_v2_map.py --check
.venv/Scripts/python.exe tools/apply_v3_map.py --check
```

实际：v2 `111 unchanged`，exit 0；v3 `inserted=81 updated=0 unchanged=13 待建=25`，exit 1。本批次新建 4.16、4.17、4.18 全部 unchanged；余下 inserted 都是旧章节，待建属于后续批次，符合 V3-10 前约定。

### 5. 参考入口离线启动

每行实际执行 `python tools/run_chapter.py <章号> <脚本名>`：

| 章号 | 脚本名 | 结果 |
|---|---|---|
| 4.1 | `agent_patterns.py` | exit 0，无 Traceback |
| 4.5 | `react_agent.py` | exit 0，无 Traceback |
| 4.5 | `react_loop.py` | exit 0，无 Traceback；纯离线待办循环 |
| 4.5 | `react_reliability.py` | exit 0，无 Traceback |
| 4.5 | `react_agent_langchain.py` | exit 0，只提示需 --live，不请求模型 |
| 4.7 | `structured_routing.py` | exit 0，无 Traceback |
| 4.8 | `plan_and_execute.py` | exit 0，无 Traceback |
| 4.14 | `supervisor_native.py` | exit 0，无 Traceback |
| 4.14 | `langgraph_supervisor.py` | exit 0，只提示需 --live，不请求模型 |
| 4.16 | `pydantic_ai_agent.py` | exit 0，查询、待审、批准后记录数 1 |
| 4.17 | `native_vs_sdk_gate.py` | exit 0，两边通过率均 1.0 |
| 4.18 | `tool_design.py` | exit 0，查询、分页、待确认与幂等示例 |
| 3.9 | `trajectory_eval.py` | exit 0，保留原 12 场景演示并追加结果评分 |

### 6. --live 缺密钥 / 不可达

以下每行各执行两次 `python tools/run_chapter.py <章号> <脚本名> --live`：

- 共用环境：`LLM_PROVIDER=openai`、`OPENAI_MODEL=offline-unreachable-test`、`OPENAI_BASE_URL=http://127.0.0.1:9/v1`、`DEEPSEEK_BASE_URL=http://127.0.0.1:9/v1`、`DEEPSEEK_API_KEY=`、`NO_PROXY=127.0.0.1,localhost`，关闭 LangSmith/LangChain tracing。
- 缺密钥：`OPENAI_API_KEY=`（空环境变量阻止 dotenv 回填）。
- 不可达：`OPENAI_API_KEY=not-a-real-key`，仅访问本机关闭端口，不发送真实密钥。

| 章号 | 脚本名 | 缺密钥 | 不可达 |
|---|---|---|---|
| 4.5 | `react_agent.py` | exit 1 | exit 1 |
| 4.5 | `react_reliability.py` | exit 1 | exit 1 |
| 4.5 | `react_agent_langchain.py` | exit 1 | exit 1 |
| 4.7 | `structured_routing.py` | exit 1 | exit 1 |
| 4.8 | `plan_and_execute.py` | exit 1 | exit 1 |
| 4.14 | `supervisor_native.py` | exit 1 | exit 1 |
| 4.14 | `langgraph_supervisor.py` | exit 1 | exit 1 |
| 4.16 | `pydantic_ai_agent.py` | exit 1 | exit 1 |
| 4.18 | `tool_design.py` | exit 1 | exit 1 |

18 次适用的失败检查均有可读提示，无 `Traceback` 或 `exception.stacktrace`。还对纯离线 `react_loop.py` 在两组环境下各传过一次 `--live`：均 exit 0、仍只运行待办循环，它不解析 CLI、不支持 live；这两次不是缺密钥/不可达调用的通过证据。4.1、3.9、4.17 同样没有真实模型模式，未给它们编造 live 结果。

### 7. 显式真实模型单次运行

以下每行实际执行一次 `python tools/run_chapter.py <章号> <脚本名> --live`，均 exit 0、无 Traceback。经 `python -c "from common import LLM_PROVIDER, chat_model_name; print(LLM_PROVIDER, chat_model_name())"` 实际记录为 `deepseek deepseek-flash`。使用本机已有配置，未输出密钥、未写仓库根 reports/、未上传追踪。

| 章号 / 脚本名 | 实际观察 |
|---|---|
| 4.5 / `react_agent.py` | 算术与天气工具请求、工具回传和最终回答均运行 |
| 4.5 / `react_reliability.py` | 天气为固定数据；模型回复及增量消息输出运行 |
| 4.7 / `structured_routing.py` | 主管选出 research→writing→review→finish，并完成知识/数据/闲聊路由；专家仍为教学节点 |
| 4.8 / `plan_and_execute.py` | 模型给出 JSON 计划并逐步执行；离线故障恢复示例仍保留 |
| 4.14 / `supervisor_native.py` | 三阶段、两个并行研究分支、摘要委派均运行并保留来源 |
| 4.16 / `pydantic_ai_agent.py` | 查询已发货；待审时实际记录 0；可信本地批准后实际记录 1 |
| 4.18 / `tool_design.py` | 模型实际查询 A100 与分页；未执行未经确认的退款，随后单独演示本地已确认调用缓存 |

**真实模型语义限制（已修复一处）**：4.16 首次 live 批准后记录已登记 1 条，但最终话术仍说“等待人工审批”、`needs_human=True`。复核时给输出校验器加规则（已有退款记录则拒绝该话术并 `ModelRetry`），复跑 live 一次，回复为“已登记退款”、`needs_human=False`、退款数 1，离线演示与 57 项 `test_v3_lessons` 通过。只挡住这一类冲突，不证明整体业务语义正确；未调用真实支付。

### 8. 状态同步契约自检

通过 `python -c` 执行标准库自检脚本，逐项断言 frontmatter 字段唯一且必填、项目 ID、未加引号日期、active 状态、非空摘要，以及 evidence 为项目内现存文件、无隐藏/运行目录/越界/自引用。实际输出：`PROJECT_STATUS contract: PASS; fields=7; evidence=40`，exit 0。未使用跨项目同步工具；历史正文保留。

## 细则偏离与补充口径

1. 4.1 为移除图接口，原 gate 的调用入口从 `build_graph().invoke(initial_state())` 切到 `run_agent(initial_state())`；保留原 8 项名称、顺序与断言行为，再追加 6 项。共享原生测试同步迁移；检查点测试移到已有 4.11 教材，不加兼容壳。
2. 3.9 明确新接口的模糊边界：步数沿用原来的 ai 步；空 partial_checks 计 1；空 runs 总体 0；不足 k 次的 pass^k 为 0；k<1 抛 ValueError；统计结构为 tasks/overall。README、starter、检查一致。为使参考实现满足未改动的旧断言，补上原先缺失的 summarize_trajectories，并取消 keyword_score 的过早两位小数舍入（旧 gate 要求 2/3 误差小于 0.001）。
3. 4.16 当前安装版本标识 2.31.1，但不接受 Agent 构造参数 instrument；按实际 API 使用公开属性 `agent.instrument=False`。provider 通过 common 异步客户端注入 OpenAIProvider，允许细则中的兼容 provider 路径。
4. 4.14 保留对照版时补上显式 --live、common 工厂及可读失败出口，防止历史脚本默认发请求；gate 未改。4.5 保留框架对照的历史演示，框架素养链接按课程编号 L4.16 指向物理目录 4.15，而非新建 4.16。
5. 4.5 的 react_loop 保留“从待办循环理解 ReAct”的纯离线演示，不为它增加没有教学必要的真实模型开关；真实工具循环由 react_agent.py 演示。

## 未验证

- 保留的两个框架对照版真实模型成功路径；真实审批 UI、支付、数据库、跨进程恢复、并发幂等、持久执行引擎、远端 OpenTelemetry、部署及 CI 远端环境。
- 真实模型对八场景的成功率与提示注入抵抗；4.17 只证明固定脚本下两套执行器及评测规则行为一致，不能证明模型安全。
- 本机解释器不是 CI Python 3.11；ruff 以 py311 检查语法，不代替 3.11 实跑。本轮未运行 capstone 测试（该目录未改）。
- 未做跨项目日常同步检查；状态文件只使用本项目契约自检。

## 复现与边界

按本节表中路径运行全部命令即可复现。gate 全部离线；不要在 gate/pytest 中读取 .env 或启用真实模型。真实模型命令只用于显式演示且不保证输出逐字一致；只有参考解 gate 的两次输出做了完全一致比较。学习者仍需自己闭卷实现并填写 workbook，不能将本记录复制为学习通过证据。
