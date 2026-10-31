# L5.7 控制面与执行面集成 · Gate

[全书目录](../../README.md) · [上一章 L5.6](../5.9-otel-observability/README.md) · [下一章 L5.8（5.5）](../5.5-docker-packaging/README.md)

- **能力**：用 FastAPI 提供任务提交、查询、取消、审批接口，接入 L4.11 的执行面；用签名、带重试与去重的 webhook 回调结果。
- **v3 路径**：L5.7 / 核心（Gate；控制面与执行面）
- **岗位任务 / 面试题型**：T5、T3 / F3
- **前置**：L4.11（[4.19 执行面](../../part4-agents-langgraph/4.19-agent-execution-plane/README.md)）、L5.1（FastAPI）、L5.2（重试）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 故障与记录）。
- **闭卷规则**：只读本页、`gate/starter.py` 和 FastAPI、标准库的官方文档；通过 gate 之前不要打开 `control_execution_plane.py`。
- **验收命令**：

```bash
python chapters/part5-production/5.10-control-execution-plane/gate/gate_check.py
```

14 项全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。gate 用 FastAPI `TestClient` 与内存 store / queue，不启动服务、不联网、不起线程。

## 为什么做这个 gate

Agent 任务常常跑几分钟甚至几小时，还要停下来等人审批。把它放进一个 HTTP 请求里同步等，请求会超时、进程一重启任务就没了。常见做法是拆成两层：

- **控制面**（本章的 API）：收任务、查状态、取消、转交审批。请求立刻返回，不跑任务。
- **执行面**（[4.19](../../part4-agents-langgraph/4.19-agent-execution-plane/README.md)）：worker 从队列取任务，按阶段执行，状态写数据库。

两层只通过“任务表 + 队列”交流，所以 API 进程重启不会丢任务，worker 崩了也能从数据库里的状态继续。最容易出的错：

- 客户端超时后重发，同一个请求变成两个任务（没有幂等键）；
- 幂等键不按租户隔离，A 租户的 key 撞上 B 租户；
- 查别人的任务返回 403，等于告诉对方“这个 id 存在”；
- 审批接口没有角色检查，谁都能批准发布；
- webhook 无签名（接收方无法确认来源）、无限重试（打爆对方）、4xx 也重试、重复投递。

## 任务

实现 `gate/starter.py` 中的三个接口。`MemoryStore` 与 `MemoryQueue` 是已给出的内存实现，不要改：任务是字典，字段 `task_id`、`tenant_id`、`status`、`cancel_requested`、`approvals`。

| 接口 | 你要交付的行为 |
|---|---|
| `create_app` | 四个路由：`POST /tasks`、`GET /tasks/{id}`、`POST /tasks/{id}/cancel`、`POST /tasks/{id}/approval`；身份取自 `X-Tenant`、`X-Role` |
| `sign_payload` | HMAC-SHA256 十六进制摘要 |
| `send_webhook` | 带 `X-Signature` 的回调；5xx 与连接错误有限重试；4xx 不重试；同一 `task_id` 只投递一次 |

关键口径：

- 缺少 `X-Tenant` 返回 401；缺少 `Idempotency-Key` 返回 400；新任务返回 202 和 `{"task_id"}`。
- 相同租户 + 相同幂等键返回同一个 `task_id`，不重复创建、不重复入队；不同租户的相同键是不同任务。
- 任务不存在和属于其他租户都返回 404。
- 审批先检查角色（非 `approver_role` 返回 403），再查任务；批准后重新入队让 worker 继续；`decision` 只能是 `approve` 或 `reject`，否则 422。
- webhook 请求体是 `json.dumps(task, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`，接收方才能用同一份字节重算签名。
- `http_post(url, body, headers) -> 状态码` 由调用方注入；`send_webhook` 不做退避等待，真实系统要加（见 [5.2](../5.2-reliability-retry/README.md)）。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 提交一个任务 | 202，`task_id` 在 store 里，队列里入队一次 |
| 2 | 同一租户重发相同 `Idempotency-Key` / 另一个租户用相同的键 | 同一个 `task_id`、不重复入队 / 不同任务 |
| 3 | 不带 `Idempotency-Key` | 400，不创建任务 |
| 4 | 不带 `X-Tenant` | 401 |
| 5 | 租户 B 查询、取消租户 A 的任务 | 404 |
| 6 | 直接改 store 里的状态再查询 | 返回的是 store 里的状态 |
| 7 | 取消 | 标志写入 store，返回最新状态 |
| 8 | 普通成员（或没有角色）调用审批 | 403，不写入、不入队 |
| 9 | 审批人批准、拒绝、传 `maybe`、租户 B 的审批人 | 记录 True / False、重新入队；422；404 |
| 10 | 签名 | 与 `hmac.new(secret, body, sha256)` 一致，换密钥或内容就变 |
| 11 | webhook 回 200 | True，请求头带签名，请求体是任务 JSON |
| 12 | 503、502、200 / 一直 500 / 连接错误 | 第 3 次成功 / 恰好 3 次后 False / 重试后成功 |
| 13 | webhook 回 400 | False，只发一次，不记入 `delivered` |
| 14 | 同一 `task_id` 投递两次；`max_attempts=0` | 只发送一次，第二次返回 True；`ValueError` |

## 验收标准

`gate_check.py` 的 14 项全部 PASS：提交与入队、幂等与租户隔离、缺幂等键、缺租户头、跨租户 404、状态取自 store、取消、审批 403、审批记录与校验、签名、webhook 成功、重试与上限、4xx 不重试、去重。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么跨租户访问回 404 而不是 403？
2. 审批接口为什么先查角色再查任务？
3. webhook 为什么既要重试又要去重？二者缺了哪一个会出什么问题？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（14/14）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 5.10
```

脚本在进程内用 `TestClient` 提交任务，后台线程充当 worker，运行 4.19 的执行面：任务停在“等待审批”，普通成员审批被 403 拒绝，审批人批准后继续，最后回调一个假的 webhook（第一次回 503、被重试，接收方验证签名通过）。不需要网络和密钥。

对照时只回答：

1. `PlaneStore` 为什么每次操作都新开一个 SQLite 连接？
2. worker 是怎样知道“审批之后可以继续”的？
3. 参考实现里的 worker 是同进程线程；真实系统这里要换成什么，换了之后哪些保证要重新考虑？

## 概念地图

- **控制面 / 执行面**：API 快速返回，任务在 worker 里跑；二者通过任务表和队列解耦。
- **幂等键**：让重发不重复创建；按租户隔离。
- **租户隔离**：查不到就是 404。
- **审批**：权限问题，先查角色；批准后重新入队。
- **webhook**：签名证明来源，有限重试抗抖动，4xx 不重试，按 `task_id` 去重。

## 边界

- gate 用内存 store、内存 queue 与注入的 `http_post`，不启动服务，也不验证并发（两个请求同时用同一个幂等键）。
- 身份取自请求头是简化；真实系统用 L5.4 的认证与授权，不能信任客户端自报的租户和角色。
- webhook 只验证签名生成，不含时间戳与重放防护，也不含接收方的验签实现和密钥轮换。
- 参考实现的 worker 是同进程线程，没有验证 worker 崩溃后的恢复（见 4.19）、持久队列、取消对正在运行的阶段的效果。
