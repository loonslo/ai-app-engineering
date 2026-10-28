# L2.1 练习工作区：上下文工程总论

任务书见 [README](README.md)。先写预测，再实现，最后填结果；通过 gate 之前不要打开 `context_engineering.py`。

## 闭卷记录

- 开始时间：待填写
- 是否看过 `context_engineering.py`：否（若看过，本次 gate 作废，换题目重做）
- 遇到卡点记录：待填写

## 实现前预测

| 检查项 | 预测结果（PASS/FAIL） | 预测卡点 / 关键条件 |
|---|---|---|
| 01 count_tokens 近似计数 | 待填写 | 待填写 |
| 02 static 在前 dynamic 在后 | 待填写 | 待填写 |
| 03 required 段落始终保留 | 待填写 | 待填写 |
| 04 required 超预算报错 | 待填写 | 待填写 |
| 05 按 priority 降序丢弃 | 待填写 | 待填写 |
| 06 达到预算上限时截断放入 dropped | 待填写 | 待填写 |
| 07 段落去重并在 warnings 记录 | 待填写 | 待填写 |
| 08 dynamic 变动时不影响 static 哈希 | 待填写 | 待填写 |
| 09 static 变动时 static 哈希必改变 | 待填写 | 待填写 |
| 10 static 中含时间戳发出 Lint 告警 | 待填写 | 待填写 |
| 11 单段超 50% 预算发出 Lint 告警 | 待填写 | 待填写 |

## Gate 运行结果

- 首次运行通过数：待填写 / 11
- 修复后通过数：待填写 / 11
- 完整命令与输出摘要：待填写

## 解释题

### Q1: 为什么 Prompt Caching 要求静态前缀完全一致？动态变量放在开头会有什么后果？
- 回答：待填写

### Q2: Datadog 报告中“System Prompt 占 69%，可缓存调用仅 28% 命中”说明了什么架构痛点？
- 回答：待填写

## 通过后对照

运行 `python chapters/part2-rag/2.12-context-engineering/context_engineering.py` 对照：

1. 参考实现中的 `assemble_context` 排序装配逻辑与你的实现有何异同？
   - 记录：待填写
2. 参考实现中的 Lint 审查规则是否覆盖了你考虑到的易失性注入风险？
   - 记录：待填写

## 未验证边界

- 本门禁仅在本地离线环境下测试纯函数逻辑与断言；
- 真实大模型 Prompt Caching 的服务端命中率与延迟节省，需配置有效密钥后加 `--live` 在真实云端环境下验证。
