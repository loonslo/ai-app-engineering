# L8 RAG 分层检索评测 · Gate（原 8.4）

[全书目录](../../README.md) · [上一章 8.3](../8.3-mock-contract-invariant/README.md) · [下一章 8.5](../8.5-judge-calibration/README.md)

- **能力**：计算 recall@k、precision@k、MRR、citation coverage；处理拒答样本和 k 截断。
- **v3 路径**：选修 / 选修（AI 质量工程专项，评测岗加分）
- **前置**：3.2（指标）、2.2（检索）。
- **时间盒**：5 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/rag_eval.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.4-rag-layered-testing/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

RAG 只看最终答案，分不清召回、排序、引用哪层坏了；分位数/去重/拒答样本也容易算错。

## 任务

实现 `evaluate_retrieval(cases, k=3)`，返回四个平均指标：

| 指标 | 口径 |
|---|---|
| recall@k | 命中相关来源 / 全部相关来源 |
| precision@k | 命中数 / 去重后召回数 |
| MRR | 第一个相关来源排名倒数 |
| citation_coverage | 被引用相关来源 / 全部相关来源 |

关键口径：先截前 k 再去重；拒答样本 recall/citation=1、precision/MRR=0；k<1 报错；空集全 0。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 2 相关/召回含重复 | recall .5、precision .5、citation .5 |
| 2 | 相关在第 2 位 | MRR .5 |
| 3 | 拒答样本 | recall/citation 1，precision/MRR 0 |
| 4 | k=1 截断 | 未命中 |
| 5 | 平均/空集 | .5 / 全 0 |
| 6 | k=0 | `ValueError` |

## 验收标准

`gate_check.py` 的 6 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 不调用模型，只算检索指标。
- 真实召回质量仍要真实索引/数据。
