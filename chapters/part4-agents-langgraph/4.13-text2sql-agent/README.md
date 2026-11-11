# L4.12 Text2SQL 安全门 · Gate（原 4.13）

[全书目录](../../README.md) · [上一章 4.12](../4.12-tool-safety-search/README.md) · [下一章 4.14](../4.14-supervisor-fanout/README.md)

- **能力**：SELECT-only；危险关键字；表白名单；强制 LIMIT；结构化/非结构化分流。
- **v3 路径**：选修 / 选修（数据类岗位再学）
- **前置**：9.6（只读 SQL）。
- **时间盒**：4 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `text2sql_agent.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.13-text2sql-agent/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

让模型生成 SQL，最大风险是写操作/越权表/全表扫描；分流错还会把概念问题送进数据库。

## 任务

实现 `validate_sql` 与 `route_question`：

| 守卫 | 规则 |
|---|---|
| 前缀 | 必须 SELECT |
| 关键字 | insert/update/delete/drop/alter/create/pragma/attach/detach/replace |
| 表 | 只允许 sales/conversations |
| LIMIT | 必须显式出现 |

分流：营收/利润/历史/SQL 等 -> text2sql，否则 rag。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 合法 SELECT | 通过 |
| 2 | DELETE/多语句 | 拒绝 |
| 3 | pragma/非白名单/无 LIMIT | 拒绝 |
| 4 | 营收/历史问题 | text2sql |
| 5 | 概念问题 | rag |

## 验收标准

`gate_check.py` 的 4 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 不执行真实 SQL；只验证安全门/分流。
- 生产仍需只读连接/RLS/参数化。
