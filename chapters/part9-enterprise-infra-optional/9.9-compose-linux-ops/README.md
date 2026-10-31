# L9 Compose 与运维 · Gate（原 9.9）

[全书目录](../../README.md) · [上一章 9.8](../9.8-vectorstore-selection/README.md) · [下一章 9.10](../9.10-openai-compatible-provider/README.md)

- **能力**：启动前检查数据库/Redis/Qdrant 协议；生产禁止示例密码；一次收集全部错误。
- **v2 路径**：L9 / 选做（Gate；Compose/运维配置）
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：5.5（容器）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/runtime.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.9-compose-linux-ops/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

“能启动”不等于配置正确：

- DATABASE_URL 用 sqlite，生产直接坏；
- Redis/Qdrant 协议写错，运行时才报；
- 生产继续用 `change-me` 示例密码；
- 只报第一个错，修完再跑又冒一个。

这个 gate 用配置字典验证形状，不连服务。

## 任务

实现 `configuration_errors(settings)`，返回错误元组：

| 检查 | 条件 |
|---|---|
| 数据库 | `postgresql://` 开头 |
| Redis | `redis://` 开头 |
| Qdrant | `http(s)://` 开头 |
| 生产密码 | `app_env=production` 且含 `change-me` |

关键口径：一次收集全部错误；空元组通过；开发环境允许示例密码。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 合法配置 | () |
| 2 | sqlite 数据库 | 报错 |
| 3 | http redis / grpc qdrant | 报错 |
| 4 | 生产 + change-me | 报错 |
| 5 | 三个都错 | 3 条 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 只检查形状，不验证连通性。
- 真实 Compose/服务未启动。
