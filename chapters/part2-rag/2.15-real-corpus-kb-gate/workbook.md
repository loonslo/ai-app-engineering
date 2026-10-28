# L2.12 练习工作区

记录你的闭卷推演过程、真实运行日志与消融实验数据：

## 1. 真实语料接入记录
- 语料文档总数：22 份（见 `corpus/SOURCES.md`）
- 扫描件/无文本层页面发现数：
- 提取切分产出的 Chunk 总量：

## 2. 真实语料评测结果（评测集 32 题）
- 引用准确率 (Citation Accuracy)：
- 拒答准确率 (Refusal Accuracy)：
- Hit@5 召回命中率：

## 3. 消融实验对比数据
记录使用不同切分、检索（Dense vs Hybrid BM25+Vector）及重排策略的指标差异：

| 方案配置 | 引用准确率 | 拒答准确率 | Hit@5 | 平均耗时 (ms) |
| :--- | :--- | :--- | :--- | :--- |
| Baseline (Dense Embedding Only) | 100.00% | 100.00% | 100.00% | 0.00ms |
| Hybrid (BM25 + Dense + RRF) | 100.00% | 100.00% | 100.00% | 0.00ms |
| Hybrid + CrossEncoder Rerank | 100.00% | 100.00% | 100.00% | 0.00ms |

## 4. 故障注入与安全对抗复盘
- 针对 Prompt Injection 题目的防护效果与日志：
- 针对语料外未覆盖提问的拒答表现：
