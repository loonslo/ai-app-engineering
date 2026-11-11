# L3.1 失败分析 · Gate（原 3.1）

[全书目录](../../README.md) · [上一章 L2.12](../../part2-rag/2.15-real-corpus-kb-gate/README.md) · [下一章 L3.2](../3.4-eval-dataset-build/README.md)

- **能力**：按“来源 → 切分 → 召回 → 重排 → 上下文 → 生成 → 引用”定位最早失败环节。
- **v3 路径**：L3.1 / 核心（Gate；失败定位）
- **前置**：2.4（切分策略）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 失败样例）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `error_analysis.py`。
- **验收命令**：

```bash
python chapters/part3-evals/3.1-error-analysis/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

错误答案只是症状。证据没进上下文、召回没命中、切分截断、拒答策略错，都会长得像“模型答错了”。如果直接改提示词，往往改错层。

这个 gate 用固定 Trace，验证诊断顺序：**源头优先于下游，证据优先于生成，引用最后核对**。

## 任务

实现 `gate/starter.py` 的 `diagnose(trace)`，返回 `(环节, 下一步检查)`。

判定顺序：

1. `should_refuse`：未拒答 -> `refusal`；拒答但带引用 -> `citation`；否则 `pass`；
2. 资料内没有 `expected_ids` -> `labeling`；
3. `source_available=False` -> `source`；
4. `chunk_contains_fact=False` -> `chunking`；
5. 期望片段不在召回 -> `retrieval`；
6. 不在重排 -> `reranking`；
7. 不在上下文 -> `context`；
8. 拒答或答案错 -> `generation`；
9. 引用不覆盖期望/引用上下文外 ID -> `citation`；
10. 否则 `pass`。

关键口径：

- 只报告**最早失败**的已记录环节，下游可能还有别的问题。
- 资料外样本不看召回/重排，只看拒答和引用。
- 资料内样本没有 `expected_ids` 时不能诊断检索，先报 `labeling`。
- 不把“字段缺失”当成成功；缺标签就报标注问题。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 全部正常 | `pass` |
| 2 | 应拒未拒 | `refusal` |
| 3 | 拒答但带引用 | `citation` |
| 4 | 资料内无 expected_ids | `labeling` |
| 5 | 来源不可用 | `source` |
| 6 | 切分截断事实 | `chunking` |
| 7 | 召回/重排/上下文逐层丢失 | `retrieval` / `reranking` / `context` |
| 8 | 源头失败 + 召回失败 | `source`（源头优先） |
| 9 | 证据齐全但答错/误拒答 | `generation` |
| 10 | 缺引用/引用外部 ID | `citation` |

## 验收标准

`gate_check.py` 的 8 项全部 PASS：

- 正常、拒答、标注、来源/切分、召回/重排/上下文、源头优先、生成、引用。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么“来源失败 + 召回失败”要先报来源？
2. 资料内没有 `expected_ids` 时，为什么不能直接报 retrieval？
3. 症状相同但层不同，对修复顺序有什么影响？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（8/8）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 3.1
```

对照时只回答：

1. 参考实现的 `diagnose` 顺序和你的实现一致吗？哪一步最容易写反？
2. 参考实现用 dataclass 默认值表示“正常”；你的 dict 版本怎么处理缺失字段？
3. 这个诊断只能定位“已记录”的环节；真实系统还缺哪些日志？

## 概念地图

- **症状 vs 根因**：最终答案错只是症状；最早失败的环节才是修复入口。
- **管线顺序**：来源 → 切分 → 召回 → 重排 → 上下文 → 生成 → 引用。
- **源头优先**：上游失败会让下游看起来也错；先修源头。
- **标注**：没有 expected_ids 就无法判断检索，先补标签。
- **拒答与引用**：资料外只看拒答和引用；拒答不应附来源。

## 边界

- 示例是确定性规则，不是自动理解答案；真实诊断需要可靠日志和人工复核。
- 通过 gate 只证明规则顺序正确，不证明你的系统日志完整。
- 延迟、成本、真实模型 trace 见 3.6/3.7。
