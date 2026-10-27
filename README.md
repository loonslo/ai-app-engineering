# LangChain 学习记录 · 测试工程师转 AI 应用开发

从模型调用、RAG、评测和 Agent 基础，走到一个生产导向的企业客服 Copilot，再按目标岗位选学质量工程、企业基础设施与多 Agent 协作。

**从 [章节总地图](chapters/README.md) 开始。** 每章先读 README，再运行和阅读代码；目录存在、离线测试通过和真实环境验收是三件事，要分别记录。

## 准备环境

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
| `requirements-course.txt` | 课程依赖（推荐）：锁定依赖 + 各章直接导入的其他包 |
| `requirements-dev.txt` | 锁定依赖 + 测试工具（pytest、ruff、locust） |
| `requirements.txt` | 锁定的运行依赖，capstone 与 Docker 镜像使用 |
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

> 本仓库基于 langchain 1.x / langgraph 1.x。langchain-community 已停止维护，FAISS 等集成仍从 `langchain_community` 导入；部分检索器已迁到 `langchain_classic`（2.8、2.9、2.11 已使用新路径）。

## 课程结构

| 篇 | 内容 | 入口 | 定位 |
|---|---|---|---|
| 0 | 启程准备 | [环境与学习方法](chapters/part0-setup/README.md) | 必修 |
| 1 | 模型调用与上下文基础 | [第 1 篇](chapters/part1-foundations/README.md) | 必修 |
| 2 | 检索增强生成 RAG | [第 2 篇](chapters/part2-rag/README.md) | 必修 |
| 3 | 评测方法论 | [第 3 篇](chapters/part3-evals/README.md) | 必修 |
| 4 | Agent 与 LangGraph | [第 4 篇](chapters/part4-agents-langgraph/README.md) | 必修 |
| 5 | 服务化与工程可靠性 | [第 5 篇](chapters/part5-production/README.md) | 必修 |
| 6 | 模型方案取舍 | [第 6 篇](chapters/part6-model-tradeoffs/README.md) | 必修，LoRA 实操选做 |
| 7 | 企业客服 Copilot · 8 个里程碑 | [项目教程](flagship-project/README.md) · [整合实现 capstone](capstone/README.md) | 必修综合项目；项目教程已于 2026-10-27 冻结为历史快照，后续以 capstone 为准 |
| 8 | AI 质量工程专项 | [第 8 篇](chapters/part8-ai-quality-optional/README.md) | 选修 |
| 9 | 企业数据与推理设施专项 | [第 9 篇](chapters/part9-enterprise-infra-optional/README.md) | 选修 |
| 10 | MCP 鉴权与 A2A | [第 10 篇](chapters/part10-mcp-a2a-optional/README.md) | 选修 |

> 岗位对标、核心/选修取舍与 12 周路径提案见 [docs/curriculum-v2.md](docs/curriculum-v2.md)；每章标题下的 `v2 路径` 写明阶段与必做/选做，速查见 [章节总地图](chapters/README.md#v2-路径速查)。

## 目录说明

```text
chapters/          第 0–6、8–10 篇，每章一个目录（README、脚本、workbook.md）
  shared-data/     多章共用的示例文档和评测集
flagship-project/  第 7 篇：企业客服 Copilot 的 29 步教学快照
capstone/          整合实现：另一套入口，与教学快照分别验收
tools/             运行入口 run_chapter.py、还原工具 materialize.py
common.py          共享配置：模型、embedding、资料路径
docs/              验证记录与历史架构决策
memory/            个人背景与项目约定
reports/           评测报告输出
```

`面试题/`、`pdf-course/` 是面试笔记和课程 PDF 的整理与生成脚本，不属于学习路线。

## 运行独立练习

第 0–6 篇的脚本统一从仓库根目录用 `run_chapter.py` 运行（参数与工作目录的约定见 [章节总地图](chapters/README.md#怎样运行)）：

```bash
python tools/run_chapter.py 1.1
python tools/run_chapter.py 2.1 load_split.py
python tools/run_chapter.py 3.7 --no-upload
```

> 82 章全部有验收方式：75 章 gate、7 章清单（0.1、0.2、1.6、1.7、3.6、4.15、5.6）；项目 29 步用 [flagship-project/ACCEPTANCE.md](flagship-project/ACCEPTANCE.md) 总清单。gate 先按各章 README 闭卷实现，再运行该章 `gate/gate_check.py`，全部 PASS 后再看参考实现。批次记录见 [docs/gate-b6i-validation.md](docs/gate-b6i-validation.md) 等 `docs/gate-*-validation.md`。

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
python -m pytest tools chapters/test_new_lessons.py -q
python -m pytest -c flagship-project/m1-rag-mvp/step1/pyproject.toml flagship-project/m1-rag-mvp/step1/tests -q
python -m pytest capstone/test_production.py -q
python -m capstone.milestones --strict-evidence
python -m capstone.project_baseline --json
# 会调用真实模型；先确认本机模型、密钥和评测数据
python -m pytest capstone/test_regression.py -v
```

实质性进展先写 [TASKS.md](TASKS.md) 与验证记录，再更新 [PROJECT_STATUS.md](PROJECT_STATUS.md)。个人背景见 `memory/`，历史架构决策见 [docs/legacy/](docs/legacy/README.md)。

学习时解释输入、输出、调用链和失败分支，并用测试证明自己的理解。真实模型、远端 CI、staging、容量与恢复证据仍需单独核实。
