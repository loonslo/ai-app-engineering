# L3.3 扩展：pytest 回归 · Gate（原 5.8）

[全书目录](../../README.md) · [上一章 L3.3（3.2）](../../part3-evals/3.2-eval-basics/README.md) · [下一章 L3.4](../../part3-evals/3.3-llm-judge/README.md)

- **能力**：归一化答案；判拒答；按同义词组检查关键词；合并用例；汇总 passed/failed/skipped。
- **v2 路径**：L3.3 / 核心（Gate；pytest 回归（3.2 后读））
- **v3 路径**：L3.3 / 核心（Gate；pytest 回归）
- **前置**：3.2（基础评测）、5.4（失败数据）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `rag_regression.py`。
- **验收命令**：

```bash
python chapters/part5-production/5.8-pytest-regression/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

回归测试最容易变成“假绿灯”：

- 全角/空格不同，关键词匹配失败；
- 拒答语没归一化，误判为答对；
- 关键词写成单同义词，换措辞就红；
- 外置用例同 id 不覆盖，旧期望一直生效；
- skip 和 fail 混在一起，环境问题掩盖质量退化。

这个 gate 用纯字符串断言，不调用模型。

## 任务

实现 `gate/starter.py`：

| 函数 | 你要交付的行为 |
|---|---|
| `normalize` | NFKC + 小写 + 去空白；非字符串报错 |
| `refused` | 归一化后命中拒答词 |
| `missing_keyword` | 组内任选其一；返回第一个未覆盖组；空组报错 |
| `merge_cases` | 按 id 合并，extra 覆盖，保持顺序 |
| `summarize` | total/passed/failed/skipped |

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 全角/空格 | 归一化后匹配 |
| 2 | “文档中没有提到” | refused=True |
| 3 | 组内同义词 | 任一命中即覆盖 |
| 4 | 缺关键词 | 返回该组 |
| 5 | extra 同 id | 覆盖 base |
| 6 | 2 pass/1 fail/1 skip | 汇总正确 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- gate 不调用模型，不跑真实 RAG。
- 通过 gate 只证明断言/合并/汇总逻辑正确；真实回归需 API key + 模型。
