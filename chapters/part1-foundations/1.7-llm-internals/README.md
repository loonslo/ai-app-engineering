# 1.7 (L1.2) LLM 工作原理 · Gate

[全书目录](../../README.md) · [上一章 L1.1](../1.1-first-call/README.md) · [下一章 L1.3](../1.2-control-output/README.md)

- **能力**：用纯 Python 代码实现自回归模型的核心算子：带温度的 Softmax 数值稳定计算、Top-p/Top-k 采样截断、KV Cache 显存容量公式、余弦相似度几何度量、Prompt Caching 计费模型与分类评测指标（Precision/Recall/F1 除零保护）。
- **v3 路径**：L1.2 / 核心（Gate；LLM 原理）
- **岗位任务 / 面试题型**：T1、T5 / F3、F5
- **前置**：已完成 [L1.1 一次调用与 LLM 边界](../1.1-first-call/README.md)
- **时间盒**：5 小时（2h 读 + 2h 实现 + 1h 自测与记录）
- **闭卷规则**：只读本页、`gate/starter.py` 和 Python 标准库文档；通过 gate 之前不要打开参考实现。
- **验收命令**：

```bash
python chapters/part1-foundations/1.7-llm-internals/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 来绕过检查。

---

## 为什么做这个 gate

在技术面试与生产事故排查中，考官经常会问到大模型的底层数学与显存机制：
- 为什么 temperature 调低模型输出更确定？底层概率分布发生了什么变化？
- Top-p 过滤到底是怎么从几万个 Token 词表中截取最小候选集的？
- 为什么长文本 Agent 运行会把显卡撑爆？KV Cache 的显存公式是什么？
- 向量检索为什么要归一化算余弦相似度？全零向量怎么防御？
- 厂商宣传的 Prompt Caching 到底能省多少钱？计费怎么算？
- 分类提取如果全是负样本，除零异常怎么防御？

这个 gate 要求你脱离任何第三方深度学习框架，只用 Python 标准库纯数学实现这 7 个基础算子，将抽象概念固化为肌肉记忆。

---

## 概念

### 1. Token 与 BPE 分词
大模型输入输出的最小离散单元是 Token（词元）。现代模型普遍采用 BPE（字节对编码），中文字符通常由于 UTF-8 编码需要消耗 0.6–1.5 个 Token。模型推理的计算开销与序列长度正相关，因此商业 API 均以 Token 为计费基准。

### 2. Next-Token 预测与采样
自回归语言模型在每一步计算词表中每一个词作为下一个 Token 的条件概率分布：
$$\text{Softmax}(z_i / T) = \frac{e^{z_i / T}}{\sum_j e^{z_j / T}}$$
- **数值稳定**：为了防止指数爆炸，计算前必须先减去最大值 $\max(z)$；
- **Temperature ($T$)**：$T < 1$ 使高概率 Token 更加显著，分布变尖锐；$T > 1$ 使分布趋于平缓。非法温度（$T \le 0$）必须拒绝；
- **Top-p (Nucleus) 过滤**：按概率降序累加，保留累计概率首次 $\ge p$ 的最小集合，其余概率置 0 并重新归一化；
- **Top-k 过滤**：仅保留概率最大的 $k$ 个候选 Token，其余置 0 并重新归一化。

### 3. KV Cache 显存容量计算
在生成每一个新 Token 时，自注意力机制需要访问之前所有历史 Token 的 Key 和 Value 向量。为了避免每轮重复前向计算，系统将历史的 KV 向量缓存在显存中（KV Cache）。
$$\text{Bytes} = 2 \times \text{layers} \times \text{kv\_heads} \times \text{head\_dim} \times \text{seq\_len} \times \text{batch} \times \text{bytes\_per\_value}$$
一个 7B 模型（32层、32头、128维度、FP16 占用 2 字节）在并发批次 4、上下文 4096 时，仅 KV Cache 显存就需占用约 4GB！

### 4. 余弦相似度
$$\cos(\theta) = \frac{\mathbf{a} \cdot \mathbf{b}}{\|\mathbf{a}\| \|\mathbf{b}\|}$$
衡量两段文本 Embedding 向量在超球几何空间中的方向一致性。当长度不一致或任一向量模长为 0（全零向量）时必须防御性报错。

### 5. Prompt Caching 计费机制
现代大模型服务商（如 DeepSeek、Anthropic、OpenAI）对命中前缀缓存的上下文给予高达 50%–75% 的价格折扣。单次调用成本计算：
$$\text{Cost} = \frac{\text{cached} \times P_{\text{cached}} + (\text{input} - \text{cached}) \times P_{\text{input}} + \text{output} \times P_{\text{output}}}{10^6}$$

### 6. 分类与抽取评估指标
$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad F_1 = \frac{2 \times P \times R}{P + R}$$
当分母为 0 时返回 0.0，杜绝除零崩溃。

---

## 任务

在 `gate/starter.py` 中实现以下 7 个纯数学/纯函数组件：

| 函数 | 你要交付的行为 |
|---|---|
| `softmax(logits, temperature)` | 数值稳定计算（减去最大值）；$T \le 0$ 抛 `ValueError`；返回值之和为 1.0 |
| `top_p_filter(probs, p)` | 降序累加保留首次 $\ge p$ 的最小集合并归一化；$p \notin (0, 1]$ 抛 `ValueError` |
| `top_k_filter(probs, k)` | 保留概率最大的 $k$ 个并归一化；$k \le 0$ 抛 `ValueError`；$k > len$ 全部保留 |
| `kv_cache_bytes(...)` | 按 KV Cache 公式计算显存字节数；任一参数 $\le 0$ 抛 `ValueError` |
| `cosine_similarity(a, b)` | 计算余弦相似度；长度不一致或全零向量抛 `ValueError` |
| `estimate_cost(...)` | 结合未命中、命中前缀与输出计算成本；`cached > input` 或为负抛 `ValueError` |
| `precision_recall_f1(tp, fp, fn)` | 计算三项分类指标；除零返回 0.0；任一参数为负抛 `ValueError` |

---

## 关键约定

- 所有浮点计算采用 Python 标量浮点，不依赖 numpy/scipy；
- 浮点求和断言容忍误差 `abs_tol=1e-5`；
- 所有非法入参（负数、非正数、范围越界、维度错配）统一抛出 `ValueError`。

---

## 故障注入（必须亲手触发）

| # | 注入场景 | 期望行为 |
|---|---|---|
| 1 | `softmax` 传入非正温度 `temperature=0.0` 或 `-1.0` | 抛出 `ValueError` |
| 2 | `top_p_filter` 传入非法阈值 `p=0.0` 或 `p=1.5` | 抛出 `ValueError` |
| 3 | `top_k_filter` 传入非法 `k=0` 或负数 | 抛出 `ValueError` |
| 4 | `kv_cache_bytes` 传入负数或 0 维度 | 抛出 `ValueError` |
| 5 | `cosine_similarity` 传入不同维度的向量 `[1, 2]` 与 `[1, 2, 3]` | 抛出 `ValueError` |
| 6 | `cosine_similarity` 传入全零向量 `[0, 0, 0]` | 抛出 `ValueError` |
| 7 | `estimate_cost` 传入 `cached_tokens > input_tokens` | 抛出 `ValueError` |
| 8 | `precision_recall_f1` 传入 `tp=0, fp=0, fn=0` | 返回 `(0.0, 0.0, 0.0)`，不抛除零异常 |

---

## 验收标准

`gate_check.py` 的 13 项离线检查全部 PASS：
- **采样计算 (1-5)**：Softmax 温度效应、非法温度报错、Top-p 最小集合过滤与归一化、Top-p 边界、Top-k 过滤与边界；
- **显存与几何度量 (6-10)**：7B 模型 KV Cache 计算、相同向量余弦为 1.0、正交向量为 0.0、全零向量报错、长度不一致报错；
- **计费与评测 (11-13)**：Prompt Caching 命中计费计算、缓存超出或负数报错、Precision/Recall/F1 除零保护与负数防御。

---

## 提交物

- `gate/starter.py`（完成实现的闭卷代码）
- `gate/gate_report.json`（13/13 全部通过报告）
- [workbook.md](workbook.md) 中完成 20 道原理自测题

---

## 通过后对照参考实现

通过 gate 之前不要阅读参考解。通过后运行参考实现进行对照：

```bash
python chapters/part1-foundations/1.7-llm-internals/llm_principles.py
```

对照思考以下问题：
1. 参考实现中的 `softmax` 如何利用 `max(logits)` 避免浮点上溢？你的实现有做数值稳定处理吗？
2. 在 `top_p_filter` 中，当多个 Token 具有相同概率时，你的实现如何保证排序与截断的确定性？
3. 对比 7B 模型与 70B 模型在长上下文（如 32k、128k）下的 KV Cache 显存消耗，为什么多查询注意力（MQA/GQA）成为现代模型的标配？

---

## 概念地图

- **自回归本质**：Next-Token 离散预测；
- **温度与随机性**：Softmax 尖锐度调节；
- **长文本显存瓶颈**：KV Cache 随序列线性膨胀；
- **向量检索基石**：余弦相似度与归一化；
- **质量度量底线**：除零防御与业务侧重（高 Precision 防资损 vs 高 Recall 防漏报）。

---

## 边界

- **纯 Python 性能边界**：本章纯函数用于厘清底层原理与数学公式，生产环境深度学习推理通常由 C++/CUDA、vLLM 或 TensorRT-LLM 算子执行；
- **注意力优化变体**：公式基于标准多头注意力（MHA）推导，GQA（分组查询注意力）和 MLA（多头潜变量注意力）显存系数有所缩减；
- **未连接真实 GPU 测量**：通过公式估算显存占用，真实显卡运行还需加上模型权重、激活值与 CUDA 上下文常驻显存。
