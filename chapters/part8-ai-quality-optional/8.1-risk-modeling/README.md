# L8 风险建模 · Gate（原 8.1）

[全书目录](../../README.md) · [上一章 7.8](../../../flagship-project/m8-evidence-final-frontend/step3/README.md) · [下一章 8.2](../8.2-eval-data-engineering/README.md)

- **能力**：计算风险分/等级；风险入表去重；稳定排序；发现未覆盖领域。
- **v3 路径**：选修 / 选修（AI 质量工程专项，评测岗加分）
- **前置**：3.1（失败分析）。
- **时间盒**：4 小时。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/ai_testing/risk.py`。
- **验收命令**：

```bash
python chapters/part8-ai-quality-optional/8.1-risk-modeling/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

测试策略不能凭感觉：impact/likelihood 越界、编号重复、排序不稳定、风险领域空白，都会让“风险清单”变成摆设。

## 任务

实现 `RiskMatrix` 与 `risk_level`：

| 接口 | 要求 |
|---|---|
| risk_level | score=impact×likelihood；≥16 critical、≥9 high、≥4 medium、否则 low；越界报错 |
| add | id/area 非空；1–5 分；重复 id -> ValueError |
| prioritized | score 降序，同分 id 升序 |
| uncovered_areas | required 中没有条目的领域 |

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 4×4/3×3/2×2/1×1 | critical/high/medium/low |
| 2 | 分数 0/6 | `ValueError` |
| 3 | 重复 id | `ValueError` |
| 4 | 同分不同 id | 按 id 稳定排序 |
| 5 | 缺少领域 | uncovered 返回 |

## 验收标准

`gate_check.py` 的 4 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 只验证风险算术/排序，不证明风险清单完整。
- 真实业务风险需领域专家评审。
