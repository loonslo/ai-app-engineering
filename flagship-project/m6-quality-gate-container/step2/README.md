# 里程碑 7.6 / step2 · 容器与启动检查

[项目目录](../../README.md) · [上一步](../step1/README.md) · [下一步](../../m7-capacity-feedback-recovery/step1/README.md)

## 问题：交给别人时，依赖怎样一起被检查？

容器和统一启动入口把运行条件整理起来，但依赖不就绪时需要明确反馈。我们检查启动链是否实际建立业务所需资源。

## 概念

镜像定义环境，bootstrap 构造依赖，ensure_ready 确认可服务条件。离线构建逻辑测试不代表镜像部署成功。

## 动手与观察

用配置替身检查缺依赖与正常启动，再记录真正 Docker 构建和服务启动尚需哪些环境。

结果记入 [workbook.md](workbook.md)。

## 实现与验证参考

快照包含此前步骤的累积实现；本步骤目录只保存变更集。

| 文件 | 变更 | 职责 |
|---|---|---|
| `.dockerignore` | 新增 | 配置、运行入口或交付证据 |
| `Dockerfile` | 新增 | 配置、运行入口或交付证据 |
| `src/customer_support/readiness.py` | 新增 | 启动检查 |
| `tests/test_readiness.py` | 新增 | 保护行为及失败边界的测试 |
| `src/customer_support/bootstrap.py` | 修改 | 创建真实依赖并接入正式主链 |

调用过程：容器/CLI/API 启动 → bootstrap.build_application → ensure_ready → 构建依赖。另有 60 个继承文件未修改，完整差异可用 --diff 查看。

### 阅读实现

1. `src/customer_support/bootstrap.py`：`build_embeddings`、`build_chat_model`、`build_assistant`、`build_application`。
2. `src/customer_support/readiness.py`：`readiness`、`ensure_ready`。
3. `tests/test_readiness.py`：`test_missing_runtime_requirements_block_readiness`。

### 还原与累计验证

```powershell
$python = (Resolve-Path .venv/Scripts/python.exe).Path
& $python tools/materialize.py flagship m6-quality-gate-container/step2
cd .build/flagship/m6-quality-gate-container/step2/customer-support
$env:PYTHONDONTWRITEBYTECODE="1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
& $python -m pytest -p no:cacheprovider --basetemp=.pytest-tmp -q
```

这是离线测试路径，实际模型和远端服务需另行验证。尚未发布真实 staging。运行结果写入本章 workbook.md。
