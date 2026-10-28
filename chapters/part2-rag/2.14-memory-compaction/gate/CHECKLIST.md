# L2.10 记忆与上下文压缩 · 验收检查清单

## 检查项对应表

| 编号 | 检查项 | 验证内容 | 评分点 |
| :--- | :--- | :--- | :--- |
| 01 | 预算内原样返回 | 消息字符未超 budget 时返回原消息，summarized_count=0，prefix_changed=False | 1 |
| 02 | 首条 system 消息保留 | 压缩发生后首条消息依然是原 system prompt | 1 |
| 03 | 末尾 keep_last 消息保留 | 最近 keep_last 条消息原样保留在末尾 | 1 |
| 04 | 固定 pinned 消息原样保留 | 中间被标记 pinned=True 的消息不被丢弃或摘要 | 1 |
| 05 | 摘要消息插入位置与前缀正确 | 中间未固定消息摘要后作为 role=system 插在首条消息之后，以 [摘要] 开头 | 1 |
| 06 | 摘要失败降级为截断说明 | summarize_fn 异常时捕获并降级生成 [摘要不可用，已截断 N 条] | 1 |
| 07 | 压缩时 prefix_changed 标真 | 触发压缩重排时 prefix_changed 为 True | 1 |
| 08 | 多租户与跨用户严格隔离 | 不同 tenant_id 或 user_id 间数据互不可见 | 1 |
| 09 | 未确认模型写入被拦截拒绝 | source="model" 且 confirmed=False 时返回 False 且不写入 | 1 |
| 10 | 合规用户与确认模型写入通过 | source="user" 或 confirmed=True 的 model 写入成功 | 1 |
| 11 | 记忆遗忘与安全副本导出 | forget 删除键；export 返回深浅安全的独立字典副本 | 1 |
