# 1.7 (L1.2) LLM 工作原理 · Gate 与自测清单

[全书目录](../../README.md) · [上一章 1.1](../1.1-first-call/README.md) · [下一章 1.2](../1.2-control-output/README.md)

- **目标**：用代码讲清采样、KV Cache、余弦相似度、Prompt Caching 计费与分类指标；能流畅回答常见的底层原理与质量工程面试题
- **v2 路径**：L1.1 / 核心阅读（清单验收）
- **课时**：5h（2h 读 + 2h 实现 + 1h 自测）
- **岗位任务 / 面试题型**：T1、T5 / F3、F5，以及技术面试中的原理题
- **验收命令**：
  ```bash
  python chapters/part1-foundations/1.7-llm-internals/gate/gate_check.py
  ```

---

## 1. Token 与分词原理

### 1.1 为什么是 Token 而不是字符或单词？
大模型输入输出的最小离散单元不是人类视觉上的“字”或“词”，而是 Token（词元）。
现代主流大模型普遍采用 **BPE（Byte Pair Encoding，字节对编码）** 或其变体（如 WordPiece、Unigram）：
- 从单字节（0–255）开始构建基础词表；
- 统计大规模语料库中最高频连续出现的字节对并逐步合并，构建约 32,000 到 128,000 大小的固定词表。

### 1.2 中英文 Token 消耗差异与计费本质
- **英文语料丰富**：一个常见英文单词（如 `apple`）通常仅对应 1 个 Token；
- **中文与特殊字符**：中文汉字通常由 3 个 UTF-8 字节编码，早期分词器常将一个汉字拆成 2–3 个 Token。现代分词器通过扩充中文常用词词表，将 1 个汉字压缩至 0.6–1.5 个 Token，但在处理相同信息量时，中文的 Token 消耗量普遍仍略高于英文。
- **按 Token 计费**：模型推理的计算开销直接与处理和生成的 Token 序列长度呈正比，因此所有商业 API 均以 Token（通常以每百万 Token，Mtok）为计费基准。

---

## 2. Next-Token 预测与采样参数

现代自回归语言模型的核心本质，是根据已输入的所有前文序列，计算词表中每一个词作为下一个 Token 的条件概率分布：
$$P(x_t \mid x_1, x_2, \dots, x_{t-1})$$

```text
前文序列 ──> Transformer 网络 ──> Logits (非归一化分数) ──> Softmax(Logits / T) ──> 概率分布 ──> Top-k / Top-p 截断 ──> 采样
```

### 2.1 Softmax 与 Temperature（温度）缩放
模型最后一层线性输出的是维度等于词表大小的实数向量，称为 **Logits**。通过 Softmax 函数将 Logits 转化为和为 1 的概率分布：
$$P_i = \frac{e^{z_i / T}}{\sum_j e^{z_j / T}}$$

- **数值稳定性处理**：当 Logits 很大时（如 1000），$e^{1000}$ 会导致浮点数溢出（Overflow）。标准工程实现中必须先减去最大值：$z_i' = z_i - \max(z)$。
- **Temperature ($T$) 的物理意义**：
  - **$T \to 0$（极低温）**：最大 Logit 的概率无限逼近 1.0，模型蜕变为贪心搜索（Greedy Search），输出完全确定、无发散性，适合结构化提取和代码生成；
  - **$T = 1.0$（标准温）**：保留原始训练分布；
  - **$T > 1.0$（高温）**：分布趋于平缓平滑，低概率词被选中的几率增加，输出更具创意和发散性，但事实错误风险急剧上升。

### 2.2 Top-k 与 Top-p (Nucleus) 截断
为了防止采样到词表长尾处的荒谬低概率词（如语法错误的生僻字），必须对概率分布进行截断：
- **Top-k**：硬性只保留概率最高的前 $k$ 个 Token，将其余置 0 后重新归一化；
- **Top-p（核采样）**：按概率降序排序，累计概率首次达到阈值 $p$（如 0.85）的最小集合被保留，其余置 0 后重新归一化。动态适应不同语境（候选词多时保留更多，候选词确定时仅保留少数）。
- **组合顺序**：工业界（如 vLLM）通常**先执行 Top-k 截断，再在保留集合中执行 Top-p 过滤**。

---

## 3. 上下文窗口与 KV Cache 显存占用

### 3.1 为什么解码需要 KV Cache？
Transformer 的自注意力机制（Self-Attention）在计算当前第 $t$ 个 Token 时，需要与前文所有 Token 的 Key 和 Value 张量做点积。
如果在每生成一个新 Token 时都重新从头计算前文所有 Token 的 $K$ 和 $V$，生成 $N$ 个 Token 的时间复杂度将高达 $O(N^2)$。
**KV Cache 将之前生成过的历史 Token 的 Key 和 Value 保存在显存中**，使得每步解码只需计算当前单个 Token 的 Query 并与 Cache 交互，将单步解码复杂度降为 $O(N)$。

### 3.2 显存容量推导公式
单个请求的 KV Cache 字节数计算公式为：
$$\text{KV Cache Bytes} = 2 \times \text{layers} \times \text{kv\_heads} \times \text{head\_dim} \times \text{seq\_len} \times \text{batch} \times \text{bytes\_per\_value}$$
- 系数 $2$：分别存储 Key 和 Value 两个张量；
- `bytes_per_value`：半精度 FP16 / BF16 为 2 字节，FP8 为 1 字节。

> **数值示例（以典型 7B 模型为例）**：
> 32 层、32 个 KV 头（若采用 MHA）、head_dim = 128、seq_len = 4096、batch = 1、FP16（2 字节）：
> $$2 \times 32 \times 32 \times 128 \times 4096 \times 1 \times 2 = 2,147,483,648 \text{ 字节} = 2.0 \text{ GB}$$
> 这解释了为什么长上下文服务对显存消耗极大，并且高并发服务通常采用 GQA（分组查询注意力）减少 KV 头数来降低 Cache 显存。

### 3.3 Prompt Caching 为什么能大幅降本？
- **原理**：很多请求带有长且固定的前缀（如庞大的 System Prompt、固定的几篇企业参考资料）。服务商在服务端将这部分前缀计算好的 KV Cache 驻留在显存或高速存储中；
- **前缀严格匹配契约**：Prompt Caching 能够命中的严格前提是**输入 Token 序列的前缀完全一致**（从第一个 Token 开始，连续无任何变动）。哪怕在最前面插入了一个动态时间戳或随机 User ID，都会破坏整个前缀导致缓存彻底失效！

---

## 4. Embedding 与向量空间余弦相似度

Embedding 将离散的文本映射到连续的稠密高维向量空间（通常为 512–1536 维）。
在归一化向量空间中，两段文本语义的相似程度通过向量夹角的余弦值度量：
$$\text{cosine\_similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|} = \frac{\sum A_i B_i}{\sqrt{\sum A_i^2} \sqrt{\sum B_i^2}}$$

- 相同方向向量相似度为 $1.0$；
- 正交（完全无关）向量相似度为 $0.0$；
- 全零向量因为模长 $\|A\|=0$ 无法除零，计算时必须防御性抛出异常。

---

## 5. 推理模型（Reasoning Models）与思考 Token

以 DeepSeek-R1、OpenAI o1/o3 为代表的推理模型，在输出最终答案之前，会在后台执行一段思维链推导（Thinking Process）：
1. **思考 Token 真实计费**：思考过程产生的 Token 同样消耗 GPU 计算量，完全计入 API 的 Completion/Output Token 费用，并且大幅拉长了响应延迟（TTFT 与总耗时）；
2. **何时必须关闭思考**：
   - 严格 JSON 结构化提取任务（如工单属性提取）：思考过程可能破坏预设的格式契约；
   - 实时交互与严格延迟预算场景（如用户界面实时自动补全）；
   - 简单分类与确定性路由（如二分类意图判断）：小步快跑比深度思考性价比高数十倍。

---

## 6. 事实性幻觉的来源与缓解方案

大模型产生幻觉（Hallucination）的根本机理：
1. **训练目标决定**：自回归模型的损失函数是“最大化下个 Token 的概率相关性”，模型追求的是语言通顺与分布匹配，并不具备内在的事实验证逻辑；
2. **知识边界与参数压缩**：世界知识被有损压缩在神经网络权重中，对于长尾、私有或时效性知识，模型无法检索到真实记忆，只能凭借概率“脑补”；
3. **解码随机性**：采样参数引入了发散扰动。

**企业级工程缓解方案**：
- **RAG（检索增强生成）**：将真实事实作为上下文显式注入提示词中；
- **带引用约束（Citations）**：强制要求模型在给出结论时标注上下文来源段落编号，结合正则与语义匹配进行断言核验；
- **确定性后置评测**：通过 Eval Harness 建立 Golden Set，持续监控幻觉率。

---

## 7. 微调、LoRA、蒸馏与量化技术概念区分

| 技术方案 | 核心概念与解决的问题 | 适用场景与工程代价 |
|---|---|---|
| **全参微调（Full Fine-Tuning）** | 调整模型的所有参数权重以适应特定领域 | 算力成本极其高昂，极易导致灾难性遗忘（Catastrophic Forgetting） |
| **LoRA（低秩自适应）** | 冻结底座大模型，仅在注意力层旁路训练低秩矩阵 $\Delta W = A \times B$ | 显存与算力开销大幅降低，适合定制特定的语言口吻与专属任务格式 |
| **知识蒸馏（Distillation）** | 用大规模强模型（Teacher）的输出概率或推理过程监督训练小模型（Student） | 将大模型的推理逻辑“压缩”到轻量模型（如 7B/1.5B），大幅降低端侧部署成本 |
| **模型量化（Quantization）** | 将权重精度从 FP16 降到 INT8、INT4 甚至 FP8 | 显存占用成倍降低，吞吐量提升，但极端低比特下可能损失部分精度 |

> [!WARNING]
> **架构取舍原则**：在企业应用开发中，“能用 Prompt 工程与 RAG 解决的问题，绝不上微调”。微调无法可靠解决私有知识的时效性更新问题，且维护自建模型服务的运维成本远超 API 调用。

---

## 8. 分类与抽取质量评估指标（Precision, Recall, F1）

在后续 L1.10 的工单打标签与敏感信息提取中，我们将使用标准的混淆矩阵指标：
- **TP (True Positive)**：真正例（模型正确提取或命中的目标）；
- **FP (False Positive)**：假正例（模型错误提取了无关内容，属于“误报”）；
- **FN (False Negative)**：假负例（模型遗漏了应该提取的目标，属于“漏报”）。

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
$$F_1 = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

- **业务侧重差异**：
  - **追求高 Precision**：如对外客服自动退款操作，误报会导致资金损失；
  - **追求高 Recall**：如合规检测、敏感词拦截、高风险工单筛选，宁可误报让人工复核，绝不能漏报任何一条事故隐患！
- **除零防御**：当没有任何正样本被预测时（$\text{TP}+\text{FP}=0$），指标必须返回 $0.0$，严禁抛出除零异常。

---

## 9. 真实价格示例（Prompt Caching 对比）

> [!NOTE]
> 价格参考自主流大模型服务商（以 DeepSeek 官方公开定价为例，基准数据核验于 **2026-10-27**；注意服务商价格策略动态变化，生产中必须以调用时的实时价目表为准）：
> - 缓存未命中输入单价：¥2.0 / 百万 Token
> - 缓存命中输入单价：¥0.5 / 百万 Token（低至原价的 25%）
> - 输出单价：¥8.0 / 百万 Token

若一次系统调用包含 100,000 Token 上下文，其中 80% 命中前缀缓存，单次调用的输入成本将从 ¥0.20 骤降至 ¥0.08，成本节省超过 **55%**！

---

## 10. 动手练习与 Gate 验收

1. **阅读接口定义**：
   查看 [gate/starter.py](gate/starter.py)，在其中实现 7 个核心原理与计算函数：
   - `softmax`、`top_p_filter`、`top_k_filter`、`kv_cache_bytes`、`cosine_similarity`、`estimate_cost`、`precision_recall_f1`。
2. **运行离线 Gate 验证**：
   ```bash
   python chapters/part1-foundations/1.7-llm-internals/gate/gate_check.py
   ```
   确保全部 13 项断言检查全绿通过（退出码 0）。
3. **完成原理面试自测题**：
   对照 [gate/CHECKLIST.md](gate/CHECKLIST.md) 的 20 道题目，在 [workbook.md](workbook.md) 中闭卷作答并核对纠偏。
4. **运行参考演示**：
   查看 [llm_principles.py](llm_principles.py) 的演示：
   ```bash
   python chapters/part1-foundations/1.7-llm-internals/llm_principles.py
   ```
   若配置了密钥，可加 `--live` 参数对比不同温度下真实模型的输出。
