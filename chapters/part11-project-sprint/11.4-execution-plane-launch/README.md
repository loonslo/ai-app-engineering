# P4 迭代 2：执行面与真实证据 · 项目章

[全书目录](../../README.md) · [上一章 P3](../11.3-control-plane-hardening/README.md) · [篇首](../README.md) · [下一章 P5](../11.5-demo-web-ui/README.md)

- **目标**：把一个长任务改成执行面上线，并产出真实模型评测、judge 校准、事故复盘、SLO 与成本报告。
- **v3 路径**：P4 / 项目（清单验收）
- **岗位任务 / 面试题型**：T3、T4、T5 / F3、F5、F6
- **节奏**：10 小时，第 13–14 周。
- **前置**：L4.17（[4.23 异步 Agent Gate](../../part4-agents-langgraph/4.23-async-agent-gate/README.md)）、L5.4（[5.15 认证与多租户](../../part5-production/5.15-auth-multitenancy/README.md)）、L5.6（[5.9 OpenTelemetry](../../part5-production/5.9-otel-observability/README.md)）、L5.7（[5.10 控制面与执行面](../../part5-production/5.10-control-execution-plane/README.md)）、L5.9（[5.12 容量与 SLO](../../part5-production/5.12-capacity-slo-recovery/README.md)）。

## 为什么

控制面加固之后，系统“能用、可测”。这一轮补上招聘方真正想看的东西：**真实运行的证据**——长任务怎么可靠地跑完、质量有多少数字支撑、出过什么问题又怎么改。

## 步骤与要点

1. **把一个长任务改成执行面**（L4.11、L5.7）：例如批量工单分诊、周报生成。提交即返回 task_id，状态写数据库，worker 可以重启恢复。
2. **审批与幂等**：写操作要有人工审批或明确的权限；同一个请求重发不会产生两次副作用（幂等键，见 [5.10](../../part5-production/5.10-control-execution-plane/README.md)）。
3. **认证与多租户检查**（L5.4）：按 [5.15 的威胁模型模板](../../part5-production/5.15-auth-multitenancy/templates/threat-model.md)过一遍，并用测试证明隔离。
4. **OpenTelemetry**（L5.6）：给模型调用和工具调用打点，默认不采集正文。
5. **真实模型评测**：golden set **≥50 条**；judge（LLM 裁判）用 **≥30 条人工标注**校准，并报告一致率（方法见 [3.3](../../part3-evals/3.3-llm-judge/README.md)、[3.8](../../part3-evals/3.8-prompt-ab-judge/README.md)）。报告里写明模型 ID、日期、数据集版本；离线替身跑出来的数字不能当作真实评测。
6. **事故复盘**：**必须是真实发生的问题**——怎样发现的、怎样止损、怎样定位根因、怎样预防。没有发生过就如实写“尚无”，不要虚构；E1 要求 ≥2 份，达不到就如实记录达到几份。
7. **SLO 与成本报告**（L5.9）：p95 延迟、单次请求成本、缓存命中率，对照 [11.1](../11.1-requirements-metrics/README.md) 里定义的门槛。

## 模板

- [`templates/eval-report.md`](templates/eval-report.md)：数据集、模型 ID、日期、指标、失败分类、与上次对比；
- [`templates/postmortem.md`](templates/postmortem.md)；
- [`templates/slo-report.md`](templates/slo-report.md)。

## 产物与验收

见 [CHECKLIST](gate/CHECKLIST.md)。验收看：报告里的每个数字能回到原始数据或命令；事故是真实发生的、有时间线；judge 一致率有人工标注作为依据，样本量写明。

## 常见失败

- 把离线替身的结果写成“真实评测”；
- 用模型自己生成的“标准答案”当 golden set，再用同一个模型打分；
- 为了凑 2 份事故复盘而虚构事件；
- 只报平均延迟，不报 p95；只报成本总数，不报单次请求成本。

## 边界

- 本章没有可执行 gate；真实评测需要你自己的模型密钥与预算，课程不替你跑。
- 一份 50 条的 golden set 只能给出粗略的信号，不要把小数点后几位当作精确结论。
