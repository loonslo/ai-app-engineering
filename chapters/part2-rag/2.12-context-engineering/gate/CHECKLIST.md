# L2.1 上下文工程 · 自测清单

完成 `gate/starter.py` 实现后，对照本清单自查：

- [ ] **接口契约**：定义了 `ContextBudgetError`、`Section`、`AssembledContext` 数据类。
- [ ] **近似计数**：CJK 字符按 1 计算，非 CJK 按空白分词计算。
- [ ] **前缀顺序**：组装文本中所有纳入的 static 段落严格排在 dynamic 段落之前。
- [ ] **必须项约束**：`required=True` 的段落全部纳入；若仅必须项就超过 budget，立即抛出 `ContextBudgetError`。
- [ ] **优先级裁剪**：非必须项按 priority 降序尝试纳入，放不下的放入 dropped。
- [ ] **同优稳定**：相同 priority 的段落保持输入稳定相对顺序。
- [ ] **重复过滤**：同名或文本重复的段落去重并生成 warning。
- [ ] **缓存哈希**：仅对纳入的 static 段落文本以 `\n\n` 连接后计算 SHA-256，仅改 dynamic 时哈希不变。
- [ ] **时间戳审查**：static 段落中包含日期或时间格式时生成 `volatile_in_static` 告警。
- [ ] **超限审查**：单个段落 Token 超过 50% budget 时生成 `oversized` 告警。
