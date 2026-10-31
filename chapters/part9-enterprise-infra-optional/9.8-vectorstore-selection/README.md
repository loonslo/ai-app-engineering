# L9 向量存储选型 · Gate（原 9.8）

[全书目录](../../README.md) · [上一章 9.7](../9.7-redis-cache-ratelimit/README.md) · [下一章 9.9](../9.9-compose-linux-ops/README.md)

- **能力**：按事务/租户/独立服务/K8s/规模选择 pgvector/Qdrant/Milvus；生成租户过滤。
- **v2 路径**：L9 / 选做（Gate；向量库选型）
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：2.2（向量库）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/vector_store.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.8-vectorstore-selection/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

选型最容易拍脑袋：

- 只要大规模就上 Milvus，忽略 K8s 前提；
- 有事务需求却选独立向量服务；
- 租户过滤写成客户端自报；
- 默认引入多余组件。

这个 gate 用需求组合验证优先级和租户过滤。

## 任务

实现 `choose_vector_backend` 和 `tenant_filter`：

| 条件 | 结果 |
|---|---|
| 大规模 + K8s | milvus |
| 事务 + 无独立服务 | pgvector |
| 租户过滤或独立服务 | qdrant |
| 其他 | pgvector |

关键口径：固定优先级；空的 tenant_id -> `ValueError`；过滤条件必须带 tenant_id match。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 大规模+K8s | milvus |
| 2 | 仅大规模 | pgvector |
| 3 | 事务 | pgvector |
| 4 | 租户/独立服务 | qdrant |
| 5 | 空 tenant_id | `ValueError` |

## 验收标准

`gate_check.py` 的 4 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 只做选型建议，不是性能结论。
- 真实 Qdrant/Milvus 未连接。
