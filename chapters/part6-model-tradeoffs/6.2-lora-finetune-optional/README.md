# L6 LoRA 质量门禁 · Gate（原 6.2）

[全书目录](../../README.md) · [上一章 6.1](../6.1-choose-prompt-rag-finetune/README.md) · [下一章 项目实战](../../../flagship-project/README.md)

- **能力**：比较基座/适配器 held-out 得分；校验 LoRA 学习率/epoch/rank/alpha。
- **v2 路径**：L6 / 选做（Gate；LoRA 质量门禁）
- **v3 路径**：选修 / 选修（概念并入 L5.12）
- **前置**：6.1（选型）。
- **时间盒**：4 小时（不含真实训练）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `lora_finetune.py`。
- **验收命令**：

```bash
python chapters/part6-model-tradeoffs/6.2-lora-finetune-optional/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

微调最常见的“假成功”：只看 train loss、适配器没比基座好就发版、lr 用全参默认值（5e-5）导致几乎不动、rank/alpha 为 0。

## 任务

实现 `quality_gate` 和 `validate_training_config`：

| 接口 | 要求 |
|---|---|
| quality_gate | adapter>=0.75 且增益>=0.25 才通过；得分越界报错 |
| config | lr 1e-4–2e-4；epochs/rank/alpha >=1；一次收集错误 |

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | base .3 / adapter .8 | 通过 |
| 2 | adapter .7 | 拒绝 |
| 3 | base .8 / adapter .9 | 增益不足拒绝 |
| 4 | 得分 -0.1/1.1 | `ValueError` |
| 5 | lr 5e-5、epoch/rank/alpha 0 | 4 条错误 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 不训练、不加载模型/适配器。
- 真实 held-out 质量与重新加载未验证。
