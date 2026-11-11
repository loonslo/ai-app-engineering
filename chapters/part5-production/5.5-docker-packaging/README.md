# L5.7 容器与配置 · Gate（原 5.5）

[全书目录](../../README.md) · [上一章 L5.7](../5.10-control-execution-plane/README.md) · [下一章 L5.8（5.11）](../5.11-cloud-deploy/README.md)

- **能力**：生成生产可用的 Dockerfile/.dockerignore；审计缺 EXPOSE、明文密钥、ADD 远端、root 运行。
- **v3 路径**：L5.8 / 核心（Gate；Docker 打包）
- **前置**：5.1（服务）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `docker_examples.py`。
- **验收命令**：

```bash
python chapters/part5-production/5.5-docker-packaging/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

“本机能跑”不等于能交付。容器配置常见问题：

- 依赖层和代码层顺序反了，每次改代码都重装依赖；
- 忘了 EXPOSE/CMD，容器起不来；
- 把 `.env`、密钥打进镜像；
- 用 ADD 拉远端 URL，构建不可复现；
- 以 root 运行，逃逸风险高。

这个 gate 用文本渲染和审计，不要求本机装 Docker。

## 任务

实现 `gate/starter.py`：

| 函数 | 你要交付的行为 |
|---|---|
| `render_dockerfile` | FROM/WORKDIR/分层 COPY/pip --no-cache-dir/EXPOSE/非 root USER/CMD 0.0.0.0 |
| `render_dockerignore` | 排除 .env/.git/.venv/__pycache__ |
| `audit` | 报缺 FROM/CMD/EXPOSE/USER、明文密钥、ADD 远端 |

关键口径：

- 先 COPY requirements 再 RUN pip，最后 COPY . .。
- 不出现 `sk-`、`API_KEY=`、`.env` 明文。
- `audit` 对生成的 Dockerfile 返回 []。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 生成的 Dockerfile | 结构齐全、顺序正确 |
| 2 | 扫描密钥 | 无 sk-/API_KEY/.env |
| 3 | .dockerignore | 排除敏感/缓存 |
| 4 | audit(生成文件) | [] |
| 5 | 缺 EXPOSE + API_KEY + ADD http | 全部报出 |

## 验收标准

`gate_check.py` 的 5 项全部 PASS；通过后写 workbook 三个问题。

## 边界

- gate 只做文本审计，不构建镜像/不跑容器。
- 通过 gate 不证明镜像可运行；真实构建需 Docker。
