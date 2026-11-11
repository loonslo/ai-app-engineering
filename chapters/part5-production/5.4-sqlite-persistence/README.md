# L5.4 SQLite 持久化 · Gate（原 5.4）

[全书目录](../../README.md) · [上一章 L5.2](../5.3-cost-cache-routing/README.md) · [下一章 L5.4](../5.15-auth-multitenancy/README.md)

- **能力**：建对话/反馈表；trace_id 幂等写入；游标分页；反馈校验。
- **v3 路径**：L5.3 / 核心（Gate；持久化）
- **前置**：4.10（检查点）。
- **时间盒**：6 小时（1h 读 + 4h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `sqlite_persistence.py`。
- **验收命令**：

```bash
python chapters/part5-production/5.4-sqlite-persistence/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

对话日志表最容易出这些错：

- 每次 `with sqlite3.connect` 只提交不关闭，连接泄漏；
- trace_id 不唯一，重试写出两条；
- 用 OFFSET 分页，写入时漏数据/重复；
- created_at 存本地时间，跨机器无法比较；
- 反馈引用不存在的会话，脏数据；
- 不建索引，历史查询全表扫。

这个 gate 用临时 DB，验证建表、幂等、游标分页和反馈外键。

## 任务

实现 `gate/starter.py` 的四个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `init_db` | 建 conversations/feedback，版本 1，幂等 |
| `save_qa` | 写入；trace_id 重复返回已有 id |
| `get_history` | 按 id 倒序；before_id 游标；sources 还原 list |
| `save_feedback` | rating 1/-1；会话不存在报 `ValueError` |

关键口径：

- `created_at` 用 UTC ISO8601（含 `+00:00`）。
- `trace_id` 唯一；重复写入不新增记录。
- 分页用 `id < before_id`，不用 OFFSET。
- `sources` 存 JSON 字符串，读出转 list。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | init 两次 | 版本 1，幂等 |
| 2 | 写 3 条查 u1 | 2 条、倒序、sources=list |
| 3 | before_id 分页 | 只返回更早一条 |
| 4 | 同 trace 写两次 | 同 id、不新增 |
| 5 | rating=0 | `ValueError` |
| 6 | 不存在会话反馈 | `ValueError` |

## 验收标准

`gate_check.py` 的 4 项全部 PASS：

- 建表/幂等、写入/历史/分页、trace 幂等、反馈校验。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么 trace_id 要唯一？
2. 游标分页比 OFFSET 好在哪？
3. created_at 为什么必须存 UTC？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（4/4）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 5.4
```

对照时只回答：

1. 参考实现的 `save_qa` 怎么做到幂等？
2. 参考实现为什么用 thread-local 连接？
3. 参考实现的 `daily_stats` 怎么算 p95？

## 概念地图

- **连接管理**：thread-local + 显式 close；`with conn` 不关连接。
- **PRAGMA**：WAL/busy_timeout/foreign_keys。
- **迁移**：user_version 幂等。
- **幂等**：trace_id 唯一 + ON CONFLICT。
- **游标分页**：id < before_id，避免漂移。
- **UTC**：存储统一 UTC，展示再转时区。

## 边界

- gate 用临时 DB，不验证并发/迁移旧库/WAL 性能。
- 通过 gate 只证明表结构/幂等/分页/反馈正确。
- 生产多副本、迁移、p95 见参考实现与 7.x。
