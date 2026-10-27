# 1.9 (L1.7) Provider 抽象、第二厂商与成本 · Gate

- **课时**：5h（1.5h 读 + 2.5h 实现 + 1h 记录）
- **v3 路径**：L1.7 / 核心（Gate；Provider 与成本）
- **岗位任务 / 面试题型**：T5、T1 / F3、F4
- **前置依赖**：已完成 [1.5 工具调用协议](../1.5-tool-calling/README.md)
- **学完能做**：定义与厂商无关的调用接口；按错误类型决定是否切换备用厂商；把不同厂商的 usage 归一化，按缓存命中与峰谷时段计算成本；把同一套评测分别跑在两家模型上并对比。
- **验收命令**：
  ```bash
  python chapters/part1-foundations/1.9-provider-cost/gate/gate_check.py
  ```

---

## 1. 为什么必须建立 Provider 抽象层？

在企业级 AI 应用开发中，直接将代码与某一家特定的大模型厂商深度绑定是极其危险的。主要驱动因素包括：
1. **防范供应商锁定（Vendor Lock-in）**：避免被单一厂商的价格调整或商业条款卡死；
2. **高可用容灾（Disaster Recovery & High Availability）**：大模型 API 的日常可用性（SLA）普遍在 99%–99.9% 之间，单家服务商出现偶发性 503 宕机或网络抖动十分常见；
3. **成本动态优化（Cost Arbitrage）**：利用各服务商的降价促销或夜间峰谷折扣，动态路由非实时批量任务；
4. **数据安全与数据出境合规（Compliance）**：根据不同客户数据涉密等级，动态路由至境内私有化模型或公网合规服务。

---

## 2. OpenAI 兼容协议：最低公共层与其“深水坑”

目前绝大多数大模型厂商（DeepSeek、智谱、Moonshot、Qwen、vLLM、Ollama 等）都宣称提供“OpenAI Compatible API”。这构成了事实上的行业最低公共层，但**兼容不等于完全等价**：

| 差异维度 | 实际差异与坑点 |
|---|---|
| **结构化输出支持** | OpenAI 原生支持严格 JSON Schema，而部分兼容端点（如 DeepSeek Completions 端点）只支持 JSON Object 或 Tool Calling，传入严格语法会直接报错 |
| **Usage 统计字段命名** | OpenAI 缓存命名为 `prompt_tokens_details.cached_tokens`；DeepSeek 使用 `prompt_cache_hit_tokens`；Anthropic 原生为 `cache_read_input_tokens` |
| **思考模型行为差异** | 部分新模型（如 DeepSeek V4 / R1）默认开启内部思考，在思考模式下可能拒绝接受强制 `tool_choice` |
| **Rate Limit 响应头** | 429 报错时，返回的 `Retry-After`、`x-ratelimit-remaining` 字段格式与单位各不相同 |

---

## 3. 错误分类：哪些能重试，哪些必须立即熔断？

在设计故障转移（Fallback）机制时，绝不能把所有异常一视同仁：

### 3.1 可重试 / 可转移错误（Transient Errors）
- **网络读取超时（Timeout）**：网络链路抖动；
- **速率限制（HTTP 429 / Rate Limit）**：触发当前厂商并发上限，可退避后重试或直接换备用厂商；
- **服务端故障（HTTP 500 / 502 / 503 / Server Error）**：服务商上游算力池过载或服务宕机。

### 3.2 不可重试 / 致命错误（Fatal Errors）
- **认证失败（HTTP 401 / Authentication Error）**：API Key 错误、过期或欠费，切换下一家无法修复此问题，且盲目重试会导致日志爆炸，必须立即告警并熔断；
- **请求格式与参数错误（HTTP 400 / Bad Request）**：参数不合法，换厂商通常同样失败；
- **内容安全策略拦截（Content Filter）**：触发服务商安全审核红线，不可降级重试；
- **上下文超长（Context Length Exceeded）**：提示词超出模型最大窗口，必须裁剪后才能重试。

---

## 4. 降级的代价：“换模型”绝不是免费的高可用

许多工程师误以为给系统配置一个 Fallback 厂商就万事大吉了。但必须清醒认识到：**换了模型，系统的整体行为就会发生漂移**！
- 模型 A 擅长的逻辑抽取，模型 B 可能会漏掉字段；
- 模型 B 生成的 JSON 格式可能与模型 A 的微调风格不同；
- 模型间 Prompt 敏感度差异极大。

> [!WARNING]
> **黄金法则**：主备模型必须跑在同一套评测集（Golden Set）上，只有当备用模型的通过率、延迟和退化用例在可控容忍度内，该降级策略才算真正成立。绝不能把降级当成“不用测试的免费高可用”。

---

## 5. API 网关的作用与定位

在规模化架构中，企业往往引入统一大模型网关（如 LiteLLM、OpenRouter 或自建 API Gateway）承担统一鉴权、路由分发、成本记账与协议归一化。
网关将各厂商差异屏蔽在基础设施层，但核心的应用级降级逻辑与评测监控依然需要应用层深度把控。

---

## 6. Token 成本模型与峰谷时段计费

大模型调用的真实成本由三部分组成：
$$\text{Cost} = \frac{\text{Cached Tokens} \times P_{\text{cached}} + \text{Uncached Tokens} \times P_{\text{input}} + \text{Output Tokens} \times P_{\text{output}}}{1,000,000}$$

### 峰谷折扣计费示例
以主流厂商（以 DeepSeek 官方公开实行的峰谷计价为例，参考核验日期：**2026-10-27**，注意价格会随市场动态调整）：
- 每日低峰时段（北京时间凌晨 00:30 至 08:30，即 UTC 16:30 至次日 00:30）所有调用享受 **5 折优惠**；
- 结合高达 75% 的前缀缓存命中折扣，非实时批量评测任务跑在低峰时段，整体成本甚至能压缩至原价的 **12.5%**！

### 缓存命中与稳定前缀
Prompt Caching 的核心命中规则是**前缀完全一致**。这要求系统在设计 Prompt 结构时，必须将固定的 System Prompt 和静态知识库放在最前，动态的时间戳、会话历史和临时参数严格后置（与后续 L2.1 上下文工程紧密联动）。

---

## 7. 动手练习与 Gate 验收

1. **阅读接口定义**：
   打开 [gate/starter.py](gate/starter.py)，实现 5 个关键接口：
   - `normalize_usage`（多厂商 Usage 归一化）
   - `estimate_cost`（缓存与峰谷窗口核算）
   - `is_retryable`（错误可重试性研判）
   - `call_with_fallback`（多厂商故障转移）
   - `compare_runs`（双模型评测分析与退化定位）
2. **执行离线 Gate 验证**：
   ```bash
   python chapters/part1-foundations/1.9-provider-cost/gate/gate_check.py
   ```
   检查全部 13 项断言是否全部通过。
3. **真实环境双厂商评测（可选）**：
   若需调用真实备用模型，可在 `.env` 中补充第二厂商配置：
   ```env
   SECOND_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
   SECOND_API_KEY="sk-..."
   SECOND_MODEL="qwen-turbo"
   ```
   运行演示：
   ```bash
   python chapters/part1-foundations/1.9-provider-cost/provider_cost.py --live
   ```
4. **记录学习证据**：
   在 [workbook.md](workbook.md) 中记录自评与分析，完成 [gate/CHECKLIST.md](gate/CHECKLIST.md)。
