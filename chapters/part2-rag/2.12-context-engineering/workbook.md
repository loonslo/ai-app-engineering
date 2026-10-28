# L2.1 上下文工程总论 · 学习手册与自测记录

## 1. 概念自测与思考

### Q1: 为什么 Prompt Caching 要求静态前缀完全一致？动态变量放在开头会有什么后果？
> 答：大模型服务端（如 Anthropic、DeepSeek 等）基于 KV Cache 的前缀树（Prefix Tree / Radix Tree）实现 Prompt Caching。若开头的字符发生任何变化，整棵前缀树从根节点就会失配，导致后续所有原本固定的内容均无法复用已计算好的 KV Cache。将动态变量（如时间戳、用户 ID）放在开头会导致缓存命中率直接归零。

### Q2: Datadog 报告中“System Prompt 占 69%，可缓存调用仅 28% 命中”说明了什么架构痛点？
> 答：说明大量团队在代码实现中虽然写了庞大的静态 System Prompt，但未做好上下文工程分层隔离，往往在 System Prompt 中动态拼接了当前时间、用户会话 ID 或实时变量，造成原本最应该被缓存的大段文本被频繁击穿。

---

## 2. Gate 闭卷验证记录

- 验收命令：`python chapters/part2-rag/2.12-context-engineering/gate/gate_check.py`
- 检查项数量：11 项
- 骨架初测：0/11 passed (退出码 1，预期)
- 最终通关：11/11 passed (退出码 0)
- 产物报告：`gate/gate_report.json`
