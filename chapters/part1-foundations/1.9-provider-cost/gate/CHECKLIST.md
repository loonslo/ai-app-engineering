# L1.7 验证清单：Provider 抽象、第二厂商与成本

本章为自动化 Gate。在 `gate/starter.py` 中实现接口并通过离线 Gate 检查：

- [ ] 实现 `normalize_usage`：
  - [ ] 兼容 OpenAI / DeepSeek 风格 Usage（prompt_tokens、completion_tokens、cached_tokens）；
  - [ ] 兼容 Anthropic 风格 Usage（input_tokens、output_tokens、cache_read_input_tokens）；
  - [ ] 字段缺失时降级记 0，且标记 `complete=False`。
- [ ] 实现 `estimate_cost`：
  - [ ] 结合前缀缓存命中率核算单次成本；
  - [ ] 支持 UTC 峰谷时段窗口判定与折扣乘数计算（支持跨零点）；
  - [ ] 非法小时参数抛出 `ValueError`。
- [ ] 实现 `is_retryable`：
  - [ ] 准确识别可重试错误（timeout, rate_limit, server_error）；
  - [ ] 准确识别不可重试错误（auth, bad_request, content_filter, context_length）。
- [ ] 实现 `call_with_fallback`：
  - [ ] 按优先级遍历候选供应商；
  - [ ] 依据请求约束过滤能力不匹配的厂商（如 `needs_json_schema`）；
  - [ ] 遇可重试故障降级，遇不可重试故障立即熔断终止；
  - [ ] 记录完整 `attempts` 审计轨迹。
- [ ] 实现 `compare_runs`：
  - [ ] 计算两个模型在相同测试集上的通过率差与成本差；
  - [ ] 采用最近秩法计算 p95 延迟差；
  - [ ] 准确提取出在模型 A 通过而在模型 B 退化的用例列表（`regressions`）；
  - [ ] 两侧用例集不一致时抛出 `ValueError`。
- [ ] 运行离线验证并全部通过：
  ```bash
  python chapters/part1-foundations/1.9-provider-cost/gate/gate_check.py
  ```
