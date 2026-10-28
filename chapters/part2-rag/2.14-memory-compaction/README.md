# 2.14 记忆与上下文压缩 · Gate

[全书目录](../../README.md) · [上一章 2.13 静态上下文与 Skills](../2.13-static-context-skills/README.md) · [下一章 2.15 真实资料知识库 v1](../2.15-real-corpus-kb-gate/README.md)

- **能力**：在预算内压缩长会话而不丢失关键事实；保证静态前缀稳定以最大化 Prompt Caching 命中；实现受写入策略与租户隔离约束的长期记忆库。
- **v3 路径**：L2.10 / 核心（Gate；记忆与压缩）
- **岗位任务 / 面试题型**：T3 / F3
- **前置**：完成 [2.12 上下文工程总论](../2.12-context-engineering/README.md)、[2.13 静态上下文与 Skills](../2.13-static-context-skills/README.md)。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 评测分析）。
- **闭卷规则**：只读本页、`gate/starter.py`；**通过 gate 之前不要打开** `memory_compaction.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.14-memory-compaction/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

在多轮长对话与 Agent 连续交互场景中，上下文窗口会随着轮次迅速膨胀：
1. **纯截断丢弃（Truncation）**：虽然简单，但会遗失早期用户约束（例如“收货地址在海淀区”或“不要用列表输出”），导致智能体遗忘关键信息。
2. **纯摘要化（Summarization）**：如果将全部历史粗暴合为一段摘要，会破坏前缀缓存（Prompt Caching），并且丢失最新轮次的细节语境。
3. **混合预算压缩策略**：
   - **保留系统前缀**：保持首条 System Prompt 不变，最大化利用服务端前缀缓存。
   - **固定关键消息（Pinned Messages）**：包含用户核心约束或关键事实的轮次标记 `pinned=True`，压缩时原样保留并维持拓扑顺序。
   - **保留尾部上下文（Keep Tail）**：保留最近 `keep_last` 轮对话，维持即时语境敏锐度。
   - **提炼摘要并保证预算**：中间未固定轮次提炼为 `[摘要]` 消息；若加入摘要后总 Token 仍超预算，对摘要内容执行截断，严格确保总 Token 不超 budget。
4. **长期记忆治理与安全防线**：
   - **租户与用户隔离**：以 `(tenant_id, user_id)` 复合维度隔离，杜绝跨租户泄露。
   - **写入策略与确认机制**：明确什么值得记（偏好、静态事实），排除敏感临时凭证；模型自主推断的事项必须经用户确认（`confirmed=True`），防范 OWASP Agentic Top 10 的 **ASI06（记忆与上下文投毒）**。

## 概念

### 1. 短期记忆与长期记忆
- **短期记忆（会话历史）**：当前 session 的多轮对话序列，随会话结束或超出上下文窗口而需要压缩/淘汰。
- **长期记忆（事实与偏好）**：跨会话持久存在的结构化键值（如用户语言偏好、邮寄地址、已绑定的设备标识），按租户与用户隔离。

### 2. 压缩策略：截断、摘要与结构化笔记
- **截断**：按滑动窗口丢弃最老轮次，实现简单但可能丢失全局事实。
- **摘要**：小模型异步概括历史，提炼为紧凑事实。
- **结构化笔记（Scratchpad / Notes）**：将会话过程中的实体键值即时落入结构化数据表。

### 3. 压缩与前缀缓存的取舍
对历史进行压缩会改变后续序列的内容。若首条 System Prompt 保持稳定不变，服务端依然能复用头部前缀的 KV Cache；因此摘要消息必须紧随首条 System 之后，不得插入在 System 之前。

### 4. 记忆写入策略与过期机制 (TTL)
- **什么值得记**：用户明确告知的长期偏好、固化事实；
- **何时需要确认**：模型推断的偏好（`source="model"`）必须经用户显式确认后方可写入；未确认的模型自主写入直接拦截，防止提示词注入篡改记忆；
- **TTL 过期时间**：临时上下文会话设定过期 TTL，定期淘汰陈旧记录。

### 5. 记忆评测：20 轮关键事实保留
衡量压缩与记忆机制有效性的核心指标：在经过 20 轮以上的常规往返问答后，第 1 轮声明的关键事实（如修改后的收货地址）是否依然能在上下文中被保留并准确检索。

## 任务与关键约定

在 `gate/starter.py` 中实现下列核心组件与函数：

| 函数 / 类型 | 你要交付的行为 |
|---|---|
| `compact_history` | 在预算内压缩长会话：首条 system 保留；尾部 `keep_last` 保留；`pinned=True` 保留；中间未固定轮次提炼 `[摘要]` 消息；确保压缩后总 Token 严格不超 budget；判断 `prefix_changed` 状态 |
| `MemoryStore` | 多租户与跨用户隔离长期记忆库：实现 `remember`、`recall`、`forget`、`export`，严格拦截未确认的模型写入 (`source="model"` 且 `confirmed=False`) |

关键约定：
1. **压缩后不超预算**：若生成摘要后（system + 摘要 + pinned + tail）总 Token 超出 budget，对摘要内容截断并追加 `...[截断]`，使总 Token 严格不超过 budget；若除去摘要外的必须保留消息本身已超 budget，抛出 `ValueError`。
2. **prefix_changed 准则**：指示首条 system 消息之后的内容（`messages[1:]`）是否发生了实质改变。

## 故障注入自测表

| # | 注入场景 | 预期系统行为 | 验证断言 |
|---|---|---|---|
| 1 | 总 Token 未超预算 | 原样返回全部消息，不插入摘要 | `res.messages == msgs`，`prefix_changed=False` |
| 2 | 超预算且含首条 system | 首条 system 消息原样保留在头部 | `res.messages[0]["role"] == "system"` |
| 3 | 超预算且含 keep_last | 尾部 keep_last 条消息原样保留在末尾 | 尾部消息内容与原消息一致 |
| 4 | 超预算且中间包含 pinned 消息 | 带 `pinned: True` 消息原样保留并维持拓扑顺序 | pinned 消息完整保留且顺序不变 |
| 5 | 摘要生成器抛出异常 | 降级为包含 `[摘要不可用，已截断 N 条]` 的提示 | 消息内容包含截断提示，主流程不中断 |
| 6 | 摘要生成后总 Token 仍超预算 | 截断摘要内容使总 Token 严格不超 budget | `count_tokens(res.messages) <= budget` |
| 7 | 未确认的模型自主写入尝试 | 拦截未确认的记忆写入，返回 False | `store.remember(..., source="model", confirmed=False) == False` |
| 8 | 跨租户或跨用户越权读取 | 返回 None，严格实现多租户隔离 | 跨租户跨用户读取为 None |

## 验收标准

`gate_check.py` 的 11 项断言必须全部 PASS：
1. 01 预算内原样返回
2. 02 首条 system 消息保留
3. 03 末尾 keep_last 条消息保留
4. 04 固定 pinned 消息原样保留
5. 05 摘要消息插入位置与前缀正确
6. 06 摘要失败降级为截断说明
7. 07 压缩后总 token 不超预算
8. 08 压缩时 prefix_changed 判断正确
9. 09 多租户与跨用户严格隔离
10. 10 未确认模型写入被拦截拒绝
11. 11 记忆遗忘与安全副本导出

## 提交物

- `gate/starter.py`：完成实现的闭卷代码。
- `gate/gate_report.json`：包含 11/11 全部通过记录的报告。
- `workbook.md`：记录预测与评测分析。

## 通过后对照参考实现

不要提前看。通过后再阅读并运行 `memory_compaction.py`：
```bash
python tools/run_chapter.py 2.14
```
对照检查：
1. 参考实现如何验证 20 轮长对话后关键事实（收货地址）的保留？
2. 参考实现中的 `--live` 模式是如何调用真实大模型提炼摘要的？

## 概念地图

- **混合压缩**：System 保留 + Pinned 保留 + 尾部滑动窗口 + 中间摘要提炼。
- **ASI06 防护**：模型自主记忆必须经人工确认，避免记忆投毒漏洞。
- **多租户隔离**：复合键 `(tenant_id, user_id)`，物理上杜绝跨租户信息污染。

## 边界

- gate 验收完全离线执行，不消耗大模型 API 额度。
- 本章演示字符数级近距离计量，生产场景建议按需集成对应 tokenizer。
