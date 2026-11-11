# AI 应用与 Agent 开发学习手册

面向测试与质量工程师的 AI 应用开发课程与练习。

## 开始学习

打开[报销实战课程](course/README.md)。首课的文章、示例和测试放在同一目录，可以离线运行。

[配套练习](chapters/README.md)适合按主题补课。做完独立练习后，可以打开 [capstone](capstone/README.md) 查看完整应用。

## 配套练习与整合项目

### 准备环境

需要 Python 3.11 及以上（仓库默认 3.14，CI 用 3.11）。在仓库根目录：

```bash
python -m venv .venv
.venv\Scripts\activate                 # macOS / Linux：source .venv/bin/activate
python -m pip install -r requirements-course.txt
python tools/run_chapter.py 0.1        # 自检：缺哪一篇的依赖会直接列出
```

依赖文件的分工：

| 文件 | 内容 |
|---|---|
| `requirements-course.txt` | 课程依赖（推荐）：课程与选修章节所需依赖 |
| `requirements-dev.txt` | 锁定依赖 + 测试工具（pytest、ruff、locust） |
| `requirements.txt` | 课程/冻结旗舰项目的锁定依赖 |
| `requirements-capstone.txt` | capstone 与 Docker 镜像的最小锁定运行依赖，不含未使用的 LangChain 组件 |
| `requirements-pgvector.txt`、`requirements-bedrock.txt` | capstone 的可选后端 |

**密钥**：把 `.env.example` 复制为 `.env`。第 0–6 篇只需要一项：

```
DEEPSEEK_API_KEY=你的密钥
# 按需：LANGSMITH_API_KEY（3.6–3.8）、TAVILY_API_KEY（4.12）
```

`.env.example` 里其余变量供 capstone 使用。`.env` 不进入 Git，密钥也不要贴进学习记录。

### 准备本地 embedding 模型

第 2 篇起的检索章节使用本地中文 embedding 模型。推荐用魔搭 ModelScope 下载（国内免代理）：

```python
# 先 pip install modelscope
from modelscope import snapshot_download
print(snapshot_download('BAAI/bge-small-zh-v1.5'))   # 打印模型所在的本地路径
```

默认路径是 `~/.cache/modelscope/hub/models/BAAI/bge-small-zh-v1___5`（ModelScope 把点号换成了三个下划线）。模型在别处时，在 `.env` 里设置 `EMBED_MODEL_PATH=模型目录`。2.11 的 reranker 同理：下载 `BAAI/bge-reranker-base`，用 `RERANKER_MODEL_PATH` 指定。

> **技术路线**：默认使用原生 SDK + Pydantic；LangGraph 用于状态图、检查点与人工介入（第 4 篇相关章节）；LangChain 只作为框架对照（如 4.15）与选修章节、冻结的历史快照中的实现。Pydantic AI 用于 4.16 等章，当前统一锁定 `pydantic-ai-slim[openai]==2.53.0`；旧版 2.31.1 的安全限制只作为历史记录。OpenTelemetry 用于 3.6、5.9 与 capstone（`opentelemetry-sdk` 已锁定，向 OTLP 后端发送另需 `opentelemetry-exporter-otlp-proto-http`，未锁定、可选）。

## 课程结构

v3 路线（大纲、章节总表、就业出口标准 E1–E4 与 16 周排期见 [docs/v3/outline.md](docs/v3/outline.md)；逐章速查见 [章节总地图](chapters/README.md)）：

| 线 | 内容 | 入口 | 定位 |
|---|---|---|---|
| L0 | 定位与工具链：环境、证据式学习法、编码 Agent 工作流、Python 工程底座、岗位地图 | [第 0 篇](chapters/part0-setup/README.md) | 必修 |
| L1 | 模型 API 原语与嵌入式功能 | [第 1 篇](chapters/part1-foundations/README.md) | 必修 |
| L2 | 上下文工程与检索（含真实资料知识库 v1） | [第 2 篇](chapters/part2-rag/README.md) | 必修 |
| L3 | 质量闭环：评测集、Judge、回归、追踪 | [第 3 篇](chapters/part3-evals/README.md) | 必修 |
| L4 | Agent：控制流、状态图、执行面、沙箱、安全、MCP | [第 4 篇](chapters/part4-agents-langgraph/README.md) | 必修 |
| L5 | 服务化与生产：可靠性、成本、护栏、OTel、控制面与执行面、容量与恢复、云部署 | [第 5 篇](chapters/part5-production/README.md) · [第 6 篇](chapters/part6-model-tradeoffs/README.md) | 必修；LoRA 实操选做 |
| P | 项目主线：需求与指标 → 最小上线 → 两次迭代 → 前端 → 作品叙事 | [第 11 篇](chapters/part11-project-sprint/README.md) | 必修（指南、清单与模板） |
| J | 就业轨道：简历、公开作品、编码与系统设计面试、take-home、行为面、投递 | [第 12 篇](chapters/part12-job-track/README.md) | 必修（指南、清单与演练） |
| 选修 | AI 质量工程 / 企业数据与推理设施 / MCP 鉴权与 A2A | [第 8 篇](chapters/part8-ai-quality-optional/README.md) · [第 9 篇](chapters/part9-enterprise-infra-optional/README.md) · [第 10 篇](chapters/part10-mcp-a2a-optional/README.md) | 按岗位选学 |

整合实现 [capstone](capstone/README.md)：主问答链路使用原生 openai SDK 与 chromadb，业务行为以它为准。**历史教学快照（已冻结）**：[企业客服 Copilot 项目教程（第 7 篇）](flagship-project/README.md)，基于 LangChain 1.x，2026-10-27 冻结，不再修改。

## 目录说明

```text
course/            报销课程入口与可运行课件
chapters/          第 0–6、8–12 篇，每章一个目录（README、脚本、workbook.md 或清单与模板）
  shared-data/     多章共用的示例文档和评测集
flagship-project/  第 7 篇：企业客服 Copilot 的 29 步教学快照（已冻结的历史快照）
capstone/          整合实现：另一套入口，与教学快照分别验收
tools/             运行入口 run_chapter.py、还原工具 materialize.py
common.py          共享配置：模型、embedding、资料路径
docs/              课程大纲、验证记录与历史架构决策
memory/            个人背景与项目约定
reports/           评测报告输出
```

`面试题/` 是面试笔记与题库参考，不属于学习路线。

## 运行独立练习

第 0–6 篇的脚本统一从仓库根目录用 `run_chapter.py` 运行；第 11、12 篇多数章节没有脚本（指南、清单与模板），有脚本的两处（12.3 演练、12.5 检查器）用法见各章 README（参数与工作目录的约定见 [章节总地图](chapters/README.md#怎样运行)）：

```bash
python tools/run_chapter.py 1.1
python tools/run_chapter.py 2.1 load_split.py
python tools/run_chapter.py 3.7 --no-upload
```

> 每章都有验收方式：gate 章先按各章 README 闭卷实现，再运行该章 `gate/gate_check.py`，全部 PASS 后再看参考实现；清单章用 `gate/CHECKLIST.md`；第 11、12 篇以清单、模板与产物为主。累积项目 29 步（已冻结）用 [flagship-project/ACCEPTANCE.md](flagship-project/ACCEPTANCE.md) 总清单。批次记录见 `docs/gate-*-validation.md`（v3 批次是 `gate-v3-*-validation.md`）。**这些记录证明课件结构与离线 gate 已逐批复跑；真实学习者的使用与真实环境（云部署、真实用户、远端 CI、容量与恢复）证据尚未取得。**

## 还原累积项目

第 7 篇和第 8–10 篇的每个步骤只保存新增或修改的完整文件，README 记录该步的结构；还原工具按顺序覆盖文件并处理删除清单：

```bash
python tools/materialize.py flagship m3-order-tool-reliability/step2 --diff
python tools/materialize.py flagship m8-evidence-final-frontend/step2
python tools/materialize.py quality 8.10-production-feedback-loop
python tools/materialize.py enterprise 10.4-cross-agent-delegation
```

输出依次位于 `.build/flagship/<里程碑>/<步骤>/customer-support/`、`.build/quality/<章节>/ai-testing/`、`.build/enterprise/<章节>/enterprise-support/`。重复还原会重建该目标，请在源目录保存修改。

教学快照与 `capstone/` 的接口和功能要分别验收。浏览器前端按 [7.8 / step3](flagship-project/m8-evidence-final-frontend/step3/README.md) 对接还原出的 step2 后端。

## 验证与进度

```bash
python -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
python -m pytest -c flagship-project/m1-rag-mvp/step1/pyproject.toml flagship-project/m1-rag-mvp/step1/tests -q
python -m pytest capstone/test_production.py -q
python -m capstone.milestones --strict-evidence
python -m capstone.project_baseline --json
# 会调用真实模型；先确认本机模型、密钥和评测数据
python -m pytest capstone/test_regression.py -v
```

实质性进展先写 [TASKS.md](TASKS.md) 与验证记录，再更新 [PROJECT_STATUS.md](PROJECT_STATUS.md)。个人背景见 `memory/`，历史架构决策见 [docs/legacy/](docs/legacy/README.md)。

学习时解释输入、输出、调用链和失败分支，并用测试证明自己的理解。真实模型、远端 CI、staging、容量与恢复证据仍需单独核实。
