# L5.8 容器、CI 评测门禁与云部署 · 清单（5.11 云部署）

[全书目录](../../README.md) · [上一章 L5.7](../5.10-control-execution-plane/README.md) · [下一章 L5.9](../5.12-capacity-slo-recovery/README.md)

- **目标**：按目标雇主选一个主流云，把容器部署到托管服务或 VPS，并完成健康检查、密钥管理、预算告警、回滚与清理；留下一份可复查的部署记录。
- **v3 路径**：L5.8 / 核心（清单验收）
- **岗位任务 / 面试题型**：T5 / F3
- **前置**：[5.5 Docker 打包](../5.5-docker-packaging/README.md)（gate 不变）、核心阅读 [8.9 分层 CI 门禁](../../part8-ai-quality-optional/8.9-ci-layered-gate/README.md)、[5.1 服务](../5.1-serve-fastapi/README.md)。
- **环境**：**需要你自己的云账号或 VPS，可能产生费用**。课程不替你创建账号、不保存任何云凭据；没有账号时本章只能完成“纸面部分”，并把实操项如实标为“未运行”。
- **时间盒**：5.5 与 8.9 共 4 小时；本章 4 小时（1h 读 + 2.5h 部署 + 0.5h 清理与记录）。

## 问题

容器在本机跑得通，不等于上线了。上线要回答：它跑在哪、怎么访问（HTTPS）、怎么知道它活着（健康检查）、密钥放哪、日志看哪、花了多少钱、出问题怎么回滚、不用了怎么删。本章要你把这些都做一遍，并写下来。

## 概念

1. **按目标雇主选一个主流云**：不需要三家都学。看你投递的岗位常用哪家，选一家做透，其余了解同类服务的对应关系。选择理由写进记录：目标雇主常用、成本、合规。
2. **托管容器服务 / Serverless 容器 / VPS** 是三类不同的取舍：
   - 托管容器服务与 Serverless 容器：你交付镜像，平台负责调度、扩缩、证书与健康检查；
   - VPS：自己管系统与容器运行时，最便宜、最透明，但更新、监控、加固都要自己做。
3. **示例产品**（只为让你知道各家有哪一类服务；产品、定价、免费额度会变，一律以官方文档为准）。以下为 2026-10-31 通过官方文档页面核对的描述：
   - Google Cloud：**Cloud Run**，“fully managed application platform for running your code, function, or container”（[What is Cloud Run](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run)）；
   - Microsoft Azure：**Azure Container Apps**，“Run modern apps and agents using serverless containers”（[产品页](https://azure.microsoft.com/en-us/products/container-apps)；[概览文档](https://learn.microsoft.com/en-us/azure/container-apps/overview)）；
   - AWS：**Amazon ECS + AWS Fargate**，Fargate 是与 ECS 搭配、无需自己管理服务器或集群即可运行容器的技术（[文档](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.md)）。
4. **密钥**：不写进镜像、不提交到仓库、不放在构建参数里；用平台的密钥管理服务注入为运行时环境变量或挂载文件，并限制谁能读取。
5. **HTTPS 与健康检查**：对外只开 HTTPS；探针沿用 [5.1](../5.1-serve-fastapi/README.md) 的 `/health`（存活）和 `/ready`（就绪）区分。
6. **日志与预算告警**：日志要能按 `trace_id` 检索（[5.9](../5.9-otel-observability/README.md)）；**先设预算告警再部署**，避免忘了关闭的资源持续扣费。
7. **用完即删**：记录里要写清创建了哪些资源、怎么删、删完怎么确认没有残留。

## 流程

1. 按 [CHECKLIST](gate/CHECKLIST.md) 逐项完成，证据写在 [workbook.md](workbook.md)。
2. 部署记录按 [`templates/deploy-record.md`](templates/deploy-record.md) 填写。
3. 完成后做一次回滚演练，再删除资源。

## 练习

1. 用 5.5 的镜像（或你自己的服务镜像）部署到你选的云；
2. 配置密钥与预算告警，访问 HTTPS 地址验证健康检查；
3. 发布一个故意有问题的新版本，按你写的回滚步骤回滚一次；
4. 记录每日成本，清理资源。

## 产物与验收

- 填写完的 `deploy-record.md`；
- CHECKLIST 全部勾选，或对未完成项写明原因（例如“没有云账号，未部署”）；
- 验收看：记录里的 URL、区域、日期、每日成本是否真实可复查（可以只记私有地址）；回滚步骤是否真的演练过。

## 边界

- 本章没有可执行 gate，也不调用任何云 API；课程没有替你部署过，**没有任何一次真实的云部署证据**。
- 示例产品只说明服务类别，没有比较价格、性能或可用区；各家的免费额度、计费与限额请以官方页面为准。
- 不覆盖多区域、蓝绿/金丝雀发布、基础设施即代码、合规审计。
- 预算告警只提醒，不会自动停止扣费；不用的资源必须手动删除。
