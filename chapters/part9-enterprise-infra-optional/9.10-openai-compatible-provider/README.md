# L5.10 兼容模型配置 · Gate（原 9.10）

[全书目录](../../README.md) · [上一章 9.9](../9.9-compose-linux-ops/README.md) · [下一章 9.11](../9.11-vllm-gpu/README.md)

- **能力**：拼接 chat/completions URL；校验 base_url/model/api_key_env/生产 HTTPS。
- **v2 路径**：L5.10 / 选读（Gate；兼容模型配置）
- **v3 路径**：选修 / 选修（企业数据与推理设施）
- **前置**：5.1（服务配置）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `src/enterprise_support/providers.py`。
- **验收命令**：

```bash
python chapters/part9-enterprise-infra-optional/9.10-openai-compatible-provider/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

兼容接口“配置看起来一样”，但边界容易错：

- base_url 不带 /v1，请求 404；
- 末尾多 `/`，拼出 `//chat/completions`；
- api_key_env 写成密钥值，密钥进配置；
- 生产用 http，明文传输；
- model 为空，运行时才报错。

这个 gate 用配置字典验证形状，不发请求。

## 任务

实现 `chat_completions_url` 和 `validate_provider`：

| 函数 | 你要交付的行为 |
|---|---|
| `chat_completions_url` | 去末尾 `/` + `/chat/completions`；空/非字符串报错 |
| `validate_provider` | 返回错误列表；URL/`/v1`/model/env/生产 HTTPS |

关键口径：

- base_url 必须是完整 http(s) URL。
- path 必须以 `/v1` 结束。
- `api_key_env` 不能为空、不能含 `=`。
- `app_env=production` 必须 https。
- 空元组表示通过。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 合法配置 | () |
| 2 | 缺 scheme/非 http(s) | 报错 |
| 3 | 不以 /v1 结束 | 报错 |
| 4 | 空 model/空 env/env 含 = | 报错 |
| 5 | 生产 http | 报错 |
| 6 | 末尾 `/` 拼接 | 不出现 `//chat` |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- 只校验形状，不验证真实模型能力/兼容性。
- 密钥值/网络请求未涉及。
