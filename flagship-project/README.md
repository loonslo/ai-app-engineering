# 第 7 篇：企业客服 Copilot · 项目教程

> **已冻结（2026-10-27）**：本篇是基于 LangChain 1.x 的历史教学快照，不再更新。快照仍可用 `tools/materialize.py` 还原并运行，CI 继续跑 m1/step1 的基线测试。新的项目实践以 `capstone/` 与 v3 路线的项目主线为准，见 [docs/v3/outline.md](../docs/v3/outline.md)。

前面各篇学习组件和机制，这里围绕同一个业务逐步组合：从政策问答，到订单工具、可信身份、安全与恢复，再到网页交互。共 8 个里程碑、29 个步骤，每一步都在上一步的基础上改动，最终得到一个完整的应用。

**前置**：第 1–5 篇。**怎样对应目录**：“里程碑 7.3”对应目录 `m3-…`（编号取中间的数字），“step2”对应其下的 `step2/`。

> 每个 step README 顶部有 `v2 路径`，标明它服务哪个 L 阶段。项目本身仍按 7.1 → 7.8 顺序做，不要按 L 编号跳步；v2 标签用于把项目证据挂到学习路径上。

## 每一步怎么学

1. 读 README 的“问题”和“概念”，先用一段话预测：输入、处理、输出和失败出口分别是什么；新职责由谁调用，结果交给谁。
2. 每步目录只保存新增或修改的文件。先用 `tools/materialize.py` 还原成完整快照，再对照 README 的“实现与验证参考”阅读代码。
3. 运行还原后项目的累计测试：它同时包含此前所有步骤的测试，才能证明新改动没有破坏旧能力。
4. 在该步的 `workbook.md` 记录输入、命令、结果和解释；用了测试替身时，写出未验证的真实依赖。

离线累计测试、真实模型质量和实际部署是三件事，分别验收；个人学习进度由自己的记录决定。`capstone/` 保存另一个能力整合实现，不要混用两者的结论。

| 里程碑与步骤 | 目录 | 文字教程 |
|---|---|---|
| 7.1 / step1 | `m1-rag-mvp/step1` | [可自由使用的客服 RAG 最小产品](m1-rag-mvp/step1/README.md) |
| 7.1 / step2 | `m1-rag-mvp/step2` | [多文档知识库正式接入问答链](m1-rag-mvp/step2/README.md) |
| 7.1 / step3 | `m1-rag-mvp/step3` | [用真实产品链执行离线评测](m1-rag-mvp/step3/README.md) |
| 7.1 / step4 | `m1-rag-mvp/step4` | [混合检索正式进入产品主链路](m1-rag-mvp/step4/README.md) |
| 7.2 / step1 | `m2-session-langgraph/step1` | [连续追问与会话隔离](m2-session-langgraph/step1/README.md) |
| 7.2 / step2 | `m2-session-langgraph/step2` | [LangGraph 显式控制流](m2-session-langgraph/step2/README.md) |
| 7.3 / step1 | `m3-order-tool-reliability/step1` | [受控订单查询工具](m3-order-tool-reliability/step1/README.md) |
| 7.3 / step2 | `m3-order-tool-reliability/step2` | [工具超时与有限重试](m3-order-tool-reliability/step2/README.md) |
| 7.3 / step3 | `m3-order-tool-reliability/step3` | [人工升级闭环](m3-order-tool-reliability/step3/README.md) |
| 7.3 / step4 | `m3-order-tool-reliability/step4` | [SQLite 会话持久化](m3-order-tool-reliability/step4/README.md) |
| 7.4 / step1 | `m4-api-identity-security/step1` | [FastAPI 服务边界](m4-api-identity-security/step1/README.md) |
| 7.4 / step2 | `m4-api-identity-security/step2` | [写操作幂等](m4-api-identity-security/step2/README.md) |
| 7.4 / step3 | `m4-api-identity-security/step3` | [可信身份](m4-api-identity-security/step3/README.md) |
| 7.4 / step4 | `m4-api-identity-security/step4` | [增量知识同步](m4-api-identity-security/step4/README.md) |
| 7.5 / step1 | `m5-injection-pii-observability/step1` | [提示词注入防护](m5-injection-pii-observability/step1/README.md) |
| 7.5 / step2 | `m5-injection-pii-observability/step2` | [PII 脱敏](m5-injection-pii-observability/step2/README.md) |
| 7.5 / step3 | `m5-injection-pii-observability/step3` | [可观测性](m5-injection-pii-observability/step3/README.md) |
| 7.5 / step4 | `m5-injection-pii-observability/step4` | [安全缓存](m5-injection-pii-observability/step4/README.md) |
| 7.6 / step1 | `m6-quality-gate-container/step1` | [CI 质量门](m6-quality-gate-container/step1/README.md) |
| 7.6 / step2 | `m6-quality-gate-container/step2` | [容器与启动检查](m6-quality-gate-container/step2/README.md) |
| 7.7 / step1 | `m7-capacity-feedback-recovery/step1` | [向量库迁移契约](m7-capacity-feedback-recovery/step1/README.md) |
| 7.7 / step2 | `m7-capacity-feedback-recovery/step2` | [容量与压测判定](m7-capacity-feedback-recovery/step2/README.md) |
| 7.7 / step3 | `m7-capacity-feedback-recovery/step3` | [用户反馈闭环](m7-capacity-feedback-recovery/step3/README.md) |
| 7.7 / step4 | `m7-capacity-feedback-recovery/step4` | [模型供应商降级](m7-capacity-feedback-recovery/step4/README.md) |
| 7.7 / step5 | `m7-capacity-feedback-recovery/step5` | [备份与恢复验证](m7-capacity-feedback-recovery/step5/README.md) |
| 7.7 / step6 | `m7-capacity-feedback-recovery/step6` | [统一业务应用](m7-capacity-feedback-recovery/step6/README.md) |
| 7.8 / step1 | `m8-evidence-final-frontend/step1` | [面试证据与项目讲解](m8-evidence-final-frontend/step1/README.md) |
| 7.8 / step2 | `m8-evidence-final-frontend/step2` | [最终验收](m8-evidence-final-frontend/step2/README.md) |
| 7.8 / step3 | `m8-evidence-final-frontend/step3` | [前端工作台对接 里程碑 7.8 / step2 API](m8-evidence-final-frontend/step3/README.md) |

## 还原与累计测试

从仓库根目录还原目标，然后进入快照目录。下面使用现有项目虚拟环境离线运行；记录解释器的绝对路径后再切换目录，防止找错虚拟环境。

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m8-evidence-final-frontend/step2
cd .build/flagship/m8-evidence-final-frontend/step2/customer-support
& $python -m pytest --basetemp=.pytest-tmp -q
```

还原会重建目标快照，改动应保存在源步骤目录。查看某一步相对上一步的变更：在还原命令后加 `--diff`。

前端运行条件见最后一步；整合实现见 [capstone](../capstone/README.md)；全书见 [章节总地图](../chapters/README.md)。
