# 1.9 (L1.7) Provider 抽象、第二厂商与成本 · Gate

[全书目录](../../README.md) · [上一章 L1.6](../1.5-tool-calling/README.md) · [下一章 L1.8](../../part2-rag/2.5-raw-sdk-rag-agent-loop/README.md)

- **能力**：定义厂商无关的调用接口；按错误类型（暂时性故障 vs 致命错误）执行多厂商故障转移（Fallback）；标准化各厂商不同命名的 Usage 统计；结合前缀缓存命中与 UTC 峰谷时段计算实际成本；对比两组模型评测运行并输出退化用例清单。
- **v3 路径**：L1.7 / 核心（Gate；Provider 与成本）
- **岗位任务 / 面试题型**：T5、T1 / F3、F4
- **前置**：已完成 [L1.6 工具调用协议](../1.5-tool-calling/README.md)
- **时间盒**：5 小时（1.5h 读 + 2.5h 实现 + 1h 记录）
- **闭卷规则**：只读本页、`gate/starter.py` 和 Python 标准库文档；通过 gate 之前不要打开参考实现。
- **验收命令**：

```bash
python chapters/part1-foundations/1.9-provider-cost/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 来绕过检查。

---

## 为什么做这个 gate

在企业级 AI 应用落地中，直接将代码与某一家特定的大模型厂商深度绑定是极其危险的架构反模式：
1. **高可用容灾（Disaster Recovery & High Availability）**：大模型 API 的日常可用性（SLA）普遍在 99%–99.9% 之间，单家服务商出现偶发性 503 宕机或网络抖动十分常见；
2. **防范供应商锁定（Vendor Lock-in）**：避免被单一厂商的价格调整或商业条款卡死；
3. **成本动态优化（Cost Arbitrage）**：利用各服务商的降价促销或夜间峰谷折扣，动态路由非实时批量任务。

这个 gate 要求你构建一个无框架依赖、具备确定性能力过滤与故障转移策略的通用 Provider 底座。

---

## 概念

### 1. OpenAI 兼容协议的最低公共层与其“深水坑”
绝大多数厂商（DeepSeek、Qwen、Moonshot、vLLM、Ollama 等）都宣称提供“OpenAI 兼容接口”，但**兼容不等于完全等价**：
- **结构化输出支持**：OpenAI 原生支持严格 JSON Schema，而部分兼容端点（如 DeepSeek Completions 端点）只支持 JSON Object 或 Tool Calling，传入严格语法会直接报错；
- **Usage 统计字段命名**：OpenAI 缓存命名为 `prompt_tokens_details.cached_tokens`；DeepSeek 使用 `prompt_cache_hit_tokens`；Anthropic 原生为 `cache_read_input_tokens`；
- **思考模型行为差异**：部分新模型（如 DeepSeek V4.1 / R1）默认开启内部思考，在思考模式下可能拒绝接受强制 `tool_choice`。

### 2. 错误分类与故障转移决策树
在设计故障转移（Fallback）机制时，绝不能把所有异常一视同仁：
- **可重试 / 可转移错误（Transient Errors）**：
  - 网络读取超时（Timeout）
  - 速率限制（HTTP 429 / Rate Limit）
  - 服务端过载（HTTP 500 / 502 / 503 / Server Error）
  策略：记录失败原因并平滑切换到下一家候选厂商重试。
- **不可重试 / 致命错误（Fatal Errors）**：
  - 认证失败（HTTP 401 / Authentication Error）：密钥无效或欠费，换厂商无法自愈，必须立即熔断告警；
  - 请求格式错误（HTTP 400 / Bad Request）；
  - 内容安全策略拦截（Content Filter）。
  策略：立即终止调度流程，严禁无效重试导致日志爆炸。

### 3. 多模型评测对比与退化归因
更换新模型或新版本时，必须对相同用例集进行 A/B 对比评测，测量：
- 通过率变化（Pass Rate Diff）
- 平均单次调用成本变化（Cost Diff）
- p95 响应延迟变化（p95 Latency Diff，采用最近秩法）
- 退化用例清单（Degraded Cases：A 成功但 B 失败的用例）

---

## 任务

在 `gate/starter.py` 中实现以下 5 个核心组件：

| 函数 | 你要交付的行为 |
|---|---|
| `normalize_usage(raw)` | 标准化 OpenAI（含 details.cached）、DeepSeek（prompt_cache_hit）与 Anthropic（cache_read）的 Usage；缺失字段补 0 且 `complete=False` |
| `estimate_cost(usage, price, at_utc_hour)` | 计算成本；`at_utc_hour` 必须在 0–23，落在 offpeak 窗口内整笔成本乘以系数；支持跨午夜窗口（如 22点至次日4点） |
| `is_retryable(error)` | 判定错误类型：timeout, rate_limit, server_error 返回 True；auth, bad_request, content_filter, context_length 返回 False |
| `call_with_fallback(providers, request, call_fn)` | 检查能力（`needs_json_schema`）；按序调用候选厂商；可重试错误记录并换下一家；不可重试立即终止；记录完整 attempts 轨迹 |
| `compare_runs(run_a, run_b)` | 对比两组评测结果；用例集不一致抛 `ValueError`；计算 pass_rate 差值、平均成本差、p95 延迟差与退化用例列表 |

---

## 关键约定

- `Usage` 字段：`input_tokens`, `output_tokens`, `cached_input_tokens`, `complete`；
- `ProviderError` 的 `kind` 属于 `{"timeout", "rate_limit", "server_error", "auth", "bad_request", "content_filter", "context_length"}`；
- `call_with_fallback` 结果中的 `attempts` 记录列表格式为 `[("name", "status"), ...]`；
- 成本折算公式为每百万 Token（Mtok）实际金额。

---

## 故障注入（必须亲手触发）

| # | 注入场景 | 期望行为 |
|---|---|---|
| 1 | 传入空 Usage 或缺失字段的字典 | 返回全 0 且 `complete=False` |
| 2 | `estimate_cost` 传入非法小时 `at_utc_hour=24` 或 `-1` | 抛出 `ValueError` |
| 3 | 第一家候选厂商抛出 `ProviderError("timeout")` | 记录 `("name", "error:timeout")` 并成功降级调用第二家 |
| 4 | 第一家候选厂商抛出 `ProviderError("auth")` | 记录 `("name", "error:auth")` 并立即终止，不调用第二家 |
| 5 | 请求要求 `needs_json_schema=True` 但候选厂商不支持 | 记录 `("name", "skipped:capability")` 并跳至下一家 |
| 6 | 所有候选厂商全部失败 | 返回 `{"ok": False, "provider": None, ...}` 并保留完整 attempts |
| 7 | `compare_runs` 传入两侧 case_id 不一致的数据集 | 抛出 `ValueError` |

---

## 验收标准

`gate_check.py` 的 13 项检查全部 PASS：
- **Usage 归一化 (1-3)**：OpenAI 风格、Anthropic 风格、缺失字段降级处理；
- **成本与时段 (4-6)**：前缀缓存计费、跨零点低峰折扣计算、非法 UTC 小时报错；
- **错误分类与调度 (7-11)**：错误重试分类断言、超时触发降级、认证错误立即熔断、能力缺失跳过、全失败完整轨迹记录；
- **对比评测 (12-13)**：差值与退化列表计算、用例集不一致校验报错。

---

## 提交物

- `gate/starter.py`（完成实现的闭卷代码）
- `gate/gate_report.json`（13/13 全部通过报告）
- [workbook.md](workbook.md) 中记录多厂商容灾设计分析

---

## 通过后对照参考实现

通过 gate 之前不要阅读参考解。通过后运行参考实现进行对照：

```bash
python chapters/part1-foundations/1.9-provider-cost/provider_cost.py
```

若配置了第二厂商凭据，可加 `--live` 运行真实双模型请求：
```env
SECOND_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
SECOND_API_KEY="sk-..."
SECOND_MODEL="qwen-turbo"
```
> [!NOTE]
> `qwen-turbo` 参考自阿里云百炼 DashScope 官方模型列表与定价页（https://help.aliyun.com/zh/model-studio/getting-started/models ，读取于 2026-10-28）。

对照思考以下问题：
1. 参考实现如何通过生成器或循环实现优雅的 attempts 轨迹收集？与你的实现有何差异？
2. 为什么在认证错误（401）时坚决不能降级到第二厂商？盲目重试会带来什么线上事故？
3. 在计算 p95 响应延迟时，参考实现采用了什么分位数算法？当样本量很小（如 5 条用例）时，最近秩法有什么表现？

---

## 概念地图

- **Provider 隔离**：屏蔽底层端点差异；
- **能力契约**：结构化输出与工具调用能力前置检查；
- **容灾调度**：区分暂时性故障（转移）与配置级致命故障（熔断）；
- **成本透视**：时段折扣、缓存命中与 Token 归一化；
- **质量门禁**：A/B 评测与退化用例归因。

---

## 边界

- **无状态调度边界**：本章实现为纯请求级故障转移，生产环境多节点网关通常需结合熔断器（Circuit Breaker）与健康探测状态机；
- **定价表静态配置**：价目表为传入参数，真实业务需定时与各服务商实时 Billing API 或配置中心同步；
- **双模型能力差异**：备用模型虽然能防止接口 500，但其输出质量、格式遵循率可能与主模型存在退化，需配合 1.10 的 Eval Harness 持续监控。
