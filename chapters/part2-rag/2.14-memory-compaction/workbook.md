# L2.10 练习工作区

记录你的闭卷推演过程与实验日志：

## 1. 预算计算与边界分析
- 首条 System Prompt 长度
- 滑动窗口保留条数与字符数
- 压缩后预估节省的 token 比例

## 2. 故障注入记录
- 模拟 Summarizer 抛出 `TimeoutError` 或 `RateLimitError`
- 验证降级截断后系统行为

## 3. 记忆库安全攻防推演
- 模拟恶意 Prompt 要求模型向 `MemoryStore` 注入越权指令
- 验证 `confirmed=False` 拦截有效性
