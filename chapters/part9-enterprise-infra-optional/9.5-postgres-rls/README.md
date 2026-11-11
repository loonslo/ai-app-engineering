# L5.4 扩展：Postgres 与 RLS · Gate（原 9.5）

[全书目录](../../README.md) · [上一章 9.4](../9.4-intent-workflow/README.md) · [下一章 9.6](../9.6-readonly-sql-explain/README.md)

- **能力**：事务内设置租户；参数化读写；查询带 tenant/user/session；limit 边界；游标关闭/提交。
- **v3 路径**：L5.4 / 核心阅读（归入 L5.4）
- **前置**：5.4（SQLite 持久化）、5.7（权限）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/postgres.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.5-postgres-rls/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

租户隔离不能只靠应用层 WHERE：

- 忘记设置 `app.tenant_id`，RLS 失效；
- SQL 字符串拼接，注入风险；
- 查询漏 tenant 条件，跨租户读；
- limit 无边界，一次拉全表；
- 游标不关/不提交，租户设置泄漏到下个请求。

这个 gate 用假连接/游标，验证 SQL 形状和资源边界。

## 任务

实现 `PostgresConversationStore`：

| 方法 | 你要交付的行为 |
|---|---|
| `append` | set_config + 参数化 INSERT + commit + close；role 校验 |
| `history` | set_config + 带 tenant/user/session 的 SELECT；limit 1–100；旧->新；commit + close |

关键口径：

- 先执行 `set_config('app.tenant_id', %s, true)`。
- INSERT/SELECT 参数化，tenant 同时进入参数。
- role 只能是 user/assistant。
- 无论成败都 close 游标。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 正常查询 | 先设租户、SQL 带三条件、旧->新 |
| 2 | limit 0/101 | `ValueError` |
| 3 | 写入 | INSERT 参数含 tenant/user/session |
| 4 | role=system | `ValueError` |
| 5 | 成功/失败 | commit + close 执行 |

## 验收标准

`gate_check.py` 的 4 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 假连接，不连真实 Postgres/RLS。
- 事务隔离/连接池行为未验证。
