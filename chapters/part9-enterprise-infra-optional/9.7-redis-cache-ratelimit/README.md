# L5.2 扩展：Redis 缓存/限流 · Gate（原 9.7）

[全书目录](../../README.md) · [上一章 9.6](../9.6-readonly-sql-explain/README.md) · [下一章 9.8](../9.8-vectorstore-selection/README.md)

- **能力**：按租户/知识版本/权限版本/模型隔离缓存键；TTL 缓存；固定窗口限流；后端故障失败关闭。
- **v2 路径**：L5.2 / 选读（Gate；Redis 缓存/限流）
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：5.3（缓存）、5.7（权限）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/redis_store.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.7-redis-cache-ratelimit/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

缓存/限流最容易出这些错：

- 缓存键不含租户/权限版本，跨用户串答案；
- 问题空白不同导致重复缓存；
- 不设 TTL，旧答案永不过期；
- 限流 key 不含用户/窗口，互相影响；
- Redis 故障时“放行”，等于没有限流。

这个 gate 用假 Redis，验证键隔离、TTL、限流和失败关闭。

## 任务

实现 `cache_key`、`RedisAnswerCache`、`FixedWindowRateLimiter`：

| 接口 | 你要交付的行为 |
|---|---|
| `cache_key` | 作用域+合并空白问题 SHA-256；前缀 answer: |
| `RedisAnswerCache` | get 解码 bytes；set 带 ex=ttl |
| `FixedWindowRateLimiter` | incr + 首次 expire；<=limit 放行；异常 RuntimeError |

关键口径：

- scope 四项任一变化 -> 新键。
- 问题合并连续空白后参与哈希。
- Redis 异常不能放开限流。
- 限流 key 含 tenant/user/window。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 租户/版本变化 | 键不同 |
| 2 | 空白不同 | 同键 |
| 3 | 未命中/命中 | None/answer |
| 4 | set | ex=ttl |
| 5 | bytes 值 | decode |
| 6 | 连续 3 次 limit=2 | 前 2 放行，第 3 拒绝 |
| 7 | Redis 故障 | RuntimeError |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 假 Redis，不验证真实 Redis/Lua 原子性。
- 通过 gate 不证明缓存命中率/限流精度。
