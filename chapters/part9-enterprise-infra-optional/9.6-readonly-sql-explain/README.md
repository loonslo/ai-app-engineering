# L9 只读 SQL 护栏 · Gate（原 9.6）

[全书目录](../../README.md) · [上一章 9.5](../9.5-postgres-rls/README.md) · [下一章 9.7](../9.7-redis-cache-ratelimit/README.md)

- **能力**：校验只读单语句、表白名单、显式 LIMIT；按目录+角色取 SQL；拒绝超阈值顺扫。
- **v2 路径**：L9 / 选做（Gate；只读 SQL/执行计划）
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：9.5（Postgres/RLS）。
- **时间盒**：5 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/sql_guard.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.6-readonly-sql-explain/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

让 Agent 写 SQL，等于把数据库暴露给它：多语句/注释夹带 DROP、表越权、无 LIMIT 拉全表、未知 query_id/角色不匹配仍执行、顺扫百万行。

## 任务

实现 `validate_read_only_sql`、`QueryCatalog`、`reject_expensive_plan`：

| 接口 | 要求 |
|---|---|
| validate | SELECT/WITH；无 `;`/注释；禁词；表白名单；显式 LIMIT |
| Catalog | 未知 id -> SqlPolicyError；角色不匹配 -> PermissionError；取出前再校验 |
| plan | Seq Scan Plan Rows 超阈值 -> SqlPolicyError |

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 合法 SELECT | 压缩后返回 |
| 2 | DELETE/多语句 | 拒绝 |
| 3 | for update/注释/insert | 拒绝 |
| 4 | 非白名单/无 LIMIT | 拒绝 |
| 5 | 未知 id/无角色 | 报错/PermissionError |
| 6 | 超阈值顺扫/坏 EXPLAIN | 报错 |

## 验收标准

`gate_check.py` 的 6 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 不连接真实 Postgres，不执行 SQL。
- 关键词防线可被绕过；生产应加只读账号/RLS/目录。
