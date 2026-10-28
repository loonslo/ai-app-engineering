# 2.14 记忆与上下文压缩 · Gate

[全书目录](../../README.md) · [上一章 2.13 静态上下文与 Skill 发现](../2.13-static-context-skills/README.md) · [下一章 2.15 真实资料知识库 v1](../2.15-real-corpus-kb-gate/README.md)

- **能力**：掌握长会话历史的预算压缩与前缀缓存友好的消息排列，实现跨租户、跨用户严格隔离且受策略管控的长期事实记忆库。
- **v3 路径**：L2.10 / 核心（Gate；记忆与压缩）
- **岗位任务 / 面试题型**：T2、T3 / F3
- **前置**：完成 [2.12 上下文工程与结构化装配](../2.12-context-engineering/README.md)、[2.13 静态上下文与 Skill 发现](../2.13-static-context-skills/README.md)。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页、`gate/starter.py`；通过 gate 之前不要打开 `memory_compaction.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.14-memory-compaction/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

在多轮长对话与 Agent 连续执行场景中，上下文窗口会随着交互迅速膨胀：
1. **纯截断丢弃（Truncation）**：虽然简单，但会遗失早期用户约束（例如“我的订单号是 ORD-1001”或“不要使用 Markdown 列表”），导致 Agent 产生逆行幻觉。
2. **纯摘要化（Summarization）**：如果将全部历史完全压缩为一段摘要，会破坏前缀缓存（Prompt Caching），并且丢失最新的几轮细节轮次，降低模型当前的语义敏锐度。
3. **混合预算压缩策略**：
   - **保留系统前缀**：保持第一条 System Prompt 不变，最大化利用服务端前缀缓存。
   - **固定重要消息（Pinned Messages）**：对于包含地址变更、用户指令、安全授权的关键轮次打上 `pinned=True`，压缩时原样保留。
   - **滑动尾部保留（Keep Tail）**：最近 `keep_last` 轮对话保留原貌，确保即时多轮意图无损。
   - **中间轮次提炼摘要**：将中间未固定的多轮对话交由小模型提炼为结构化摘要，作为紧随系统前缀后的补充上下文。当摘要模型故障时，安全降级为明确的截断提示标记。
4. **长期记忆治理（Memory Governance）**：
   - **隔离边界**：按 `(tenant_id, user_id)` 形成复合主键，禁止任何跨租户或越权跨用户读写。
   - **写策略审查**：大模型自主推断的记忆项必须打上 `source="model"` 且经过显式确认（`confirmed=True`），未确认的自主写入直接拦截，防止模型被 Prompt Injection 注入恶意事实。

## 故障注入与诊断表

| 故障现象 | 根因定位 | 修复策略 |
| :--- | :--- | :--- |
| 每次压缩后 API 调用首字耗时暴增 | 摘要消息插在 System Prompt 之前，导致全局前缀缓存全部未命中 | 保持首条 System 消息位置不变，摘要消息紧随其后作为辅助说明 |
| 用户多轮前声明的限制条件在压缩后丢失 | 简单按轮次裁切丢弃了中间关键约束 | 对关键交互标记 `pinned: True`，在压缩过滤中跳过并维持顺序 |
| 跨用户查询偶现他人历史偏好 | 记忆存储仅使用 `user_id` 单维度或全局共享字典 | 统一以 `(tenant_id, user_id)` 元组作为主键隔离空间 |
| 模型总结失败导致整个请求抛出 500 | 摘要生成器异常未捕获，阻断主流程 | 捕获 `summarize_fn` 异常并降级为 `[摘要不可用，已截断 N 条]` |

## 闭卷完成后的对照

通过 gate 验收后，请阅读 `memory_compaction.py` 并对比：
- 消息切分是否正确处理了 `head`、`middle`（包含 pinned 与 to_summarize）与 `tail` 的相对拓扑顺序？
- `export` 是否返回了内部存储的浅/深拷贝副本，杜绝外部调用方对原存储的非法篡改？
- 运行参考实现：
  ```bash
  python tools/run_chapter.py 2.14
  ```

## 深入思考

1. 在 Anthropic Prompt Caching 或 OpenAI 自动缓存机制下，频繁变动的 `[摘要]` 消息放在 System 之后是否会影响 System Prompt 本身的命中？（答：System Prompt 位于头部，只要头部字节不变，头部命中的前缀缓存依然生效，变化的摘要仅影响后续 token）。
2. 当长期记忆库需要持久化并支持语义召回（Semantic Memory）时，如何兼顾 `tenant_id` 过滤与向量索引的性能？
