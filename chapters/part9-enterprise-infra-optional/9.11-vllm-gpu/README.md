# L9 vLLM 启动配置 · Gate（原 9.11）

[全书目录](../../README.md) · [上一章 9.10](../9.10-openai-compatible-provider/README.md) · [下一章 9.12](../9.12-inference-benchmark/README.md)

- **能力**：校验模型/端口/TP/上下文/显存/密钥 env；生成参数元组且密钥只放占位符。
- **v3 路径**：选修 / 选修（推理服务）
- **前置**：9.10（兼容配置）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/vllm.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.11-vllm-gpu/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

vLLM 启动参数错，通常要等加载模型/占满 GPU 才暴露：

- model 为空或含空格；
- port/TP/上下文越界；
- 显存利用率过高/过低；
- 密钥值直接写进命令；
- 用 shell 字符串拼接，注入风险。

这个 gate 用配置字典验证参数和命令元组。

## 任务

实现 `validate_vllm_spec` 和 `vllm_command`：

| 字段 | 范围 |
|---|---|
| model | 非空、无空白 |
| port | 1–65535 |
| tensor_parallel_size | 1–16 |
| max_model_len | 512–262144 |
| gpu_memory_utilization | 0.5–0.98 |
| api_key_env | 非空、不含 `=` |

关键口径：命令是 tuple 而非 shell 字符串；密钥参数为 `${ENV}`；非法配置 `ValueError`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 合法配置 | () |
| 2 | 空/含空格 model | 报错 |
| 3 | port/TP/len/gpu 越界 | 报错 |
| 4 | env 空/含 = | 报错 |
| 5 | 生成命令 | vllm serve + 参数 + `${VLLM_API_KEY}` |
| 6 | 非法配置生成命令 | `ValueError` |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 只生成/校验参数，不启动 GPU 服务。
- 真实吞吐/显存未验证。
