# V3-0 基础设施验证 · 2026-10-27

本批次完成了 v3 课程改造的基础设施支持（原生 OpenAI 客户端与异步工厂、本地嵌入与重排工厂、模型 ID 官方核对、依赖锁定、course-v3-map 映射源、apply_v3_map 标签工具、v3 离线测试入口与 CI 更新），未改动任何章节内容或现有 gate，未调用真实模型与外部网络。

## 范围

| v3 编号 | 目录 / 文件 | 类型 | 新增 / 修改 / 删除的文件 |
|---|---|---|---|
| V3-0 | `common.py` | 任务 1 & 2 | 修改：新增 `get_openai_client`、`get_async_openai_client`、`chat_model_name`、`get_sentence_embedder`、`embed_texts`、`get_cross_encoder`；默认模型更新为 `deepseek-flash` |
| V3-0 | `.env.example` | 任务 2 | 修改：同步推荐模型 ID 注释与默认值 `DEEPSEEK_MODEL=deepseek-flash` |
| V3-0 | `requirements-course.txt` | 任务 3 | 修改：新增锁定 `pydantic-ai-slim[openai]==2.62.0`、`opentelemetry-sdk==1.44.0` |
| V3-0 | `docs/course-v3-map.json` | 任务 4 | 新增：覆盖 outline.md 全部 119 个章节条目（82 个现有章 + 37 个规划新章） |
| V3-0 | `tools/apply_v3_map.py` | 任务 5 | 新增：v3 路径标签写入与检查工具，支持 `--check` / `--apply`，保留 v2 行，待建章节不报错 |
| V3-0 | `tools/test_apply_v3_map.py` | 任务 6 | 新增：测试三种插入位置、幂等性、“待建”目录不影响退出码、不碰 v2 行 |
| V3-0 | `chapters/test_v3_lessons.py` | 任务 6 | 新增：任务 1 原生工厂离线测试（各 provider 配置、密钥报错脱敏、模型名、embedder monkeypatch） |
| V3-0 | `.github/workflows/eval-gate.yml` | 任务 7 | 修改：CI 测试命令加入 `chapters/test_v3_lessons.py` |
| V3-0 | `docs/gate-v3-0-validation.md` | 验收 | 新增：本验证记录 |

## 任务 2 模型 ID 核对依据

1. **DeepSeek 官方模型核对**：
   - 查阅官方文档：DeepSeek 官方 API 文档 Models & Pricing（https://api.deepseek.com/models，读取日期 2026-10-27）。
   - 官方状态：早期别名 `deepseek-chat`（V3）与 `deepseek-reasoner`（R1）已下线并退出主推；当前官方最新推荐的主力生产模型为 `deepseek-flash`（由 DeepSeek-V4.1-Flash 提供，支持 1M token 上下文，具备原生多模态输入与推理/非推理双模式）及 `deepseek-v4-pro`（高智能旗舰推理）。
   - 改动结果：`common.py` 中 `DEEPSEEK_MODEL` 默认值由 `"deepseek-chat"` 改为 `"deepseek-flash"`；`.env.example` 同步更新默认值与注释。
2. **OpenAI 官方模型核对**：
   - 查阅官方文档：OpenAI Platform Documentation Models（https://platform.openai.com/docs/models，读取日期 2026-10-27）。
   - 官方状态：`gpt-4o-mini` 仍为官方推荐的高性价比、低延迟文本与多模态模型，支持 Structured Outputs 与 Tool Calling。
   - 改动结果：`OPENAI_MODEL` 默认值保持 `gpt-4o-mini` 不变。

## 任务 3 依赖锁定与环境核对

1. **依赖锁定**：
   - `pydantic-ai-slim[openai]==2.62.0`：2026-10-27 当天 PyPI 最新稳定版本为 2.62.0。查询 PyPI 元数据 `requires_python` 为 `>=3.11`，完全兼容 GitHub Actions CI 指定的 Python 3.11。
   - `opentelemetry-sdk==1.44.0`：与本地虚拟环境已安装的 `opentelemetry-api` 1.44.0 版本完全一致。
2. **本机环境核对与差异记录**：
   - 本机 `.venv` 解释器版本为 Python 3.14.4。
   - 顶层 `langchain` 包未直接安装（历史已重构为按需导入模块化包 `langchain-core` 1.5.3、`langchain-openai` 1.4.1、`langchain-classic` 1.0.8 等）。
   - 本机 `fastapi` 为 0.141.1（锁定文件为 0.139.2）。
   - 安装 `pydantic-ai-slim[openai]==2.62.0` 时将 `openai` 升级为 3.39.0，虽触发 pip 对 `langchain-openai 1.4.1` 依赖约束 `openai<3.0.0` 的冲突警告，但实测所有 34 项生产测试（`capstone/test_production.py`）及 44 项工具与章节测试在 Python 3.14 下全部无报错通过。

## 实际执行

### 1. Gate：骨架与临时参考解
本批次为纯基础设施批次，不包含章节 gate 与临时参考解，命令 1–3 不适用。

### 2. 测试

```bash
# 执行 conventions.md 第 11 节命令 4
.venv/Scripts/python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
# 输出：44 passed in 4.61s

# capstone 生产回归基线复测
.venv/Scripts/python.exe -m pytest capstone/test_production.py -q
# 输出：34 passed in 7.10s
```

### 3. 断链与静态检查

```bash
# 执行 conventions.md 第 11 节命令 5（断链检查）
.venv/Scripts/python.exe tools/check_course_links.py
# 输出：检查 306 个 Markdown 文件，0 处断链

# 执行 conventions.md 第 11 节命令 6（静态检查）
.venv/Scripts/python.exe -m ruff check --target-version py311 common.py tools/apply_v3_map.py tools/test_apply_v3_map.py chapters/test_v3_lessons.py
# 输出：All checks passed!
```

### 4. LangChain 边界与标签检查

```bash
# 执行 conventions.md 第 11 节命令 8（v2 标签未被改动）
.venv/Scripts/python.exe tools/apply_v2_map.py --check
# 输出：合计：111 个 README；inserted=0 updated=0 unchanged=111，退出码 0

# 执行 conventions.md 第 11 节命令 9（v3 映射检查）
$env:PYTHONUTF8=1; .venv/Scripts/python.exe tools/apply_v3_map.py --check
# 输出：合计：119 个章节；inserted=82 updated=0 unchanged=0 待建=37，退出码 1
```

## 细则偏离

- 细则任务 5 规定 `--check` 在存在需要改动的 README 时退出码为 1；验收一节写道“命令 4、5、6、8、9 全部通过”以及“`python tools/apply_v3_map.py --check` 只列出‘待建’与需要添加 v3 行的旧章节，不报错”。在 V3-0 批次下，按用户决策（2026-10-27）所有旧章节的 v3 标签统一在 V3-10 添加，因此当前 82 个旧章节尚未写入 v3 路径行，执行 `tools/apply_v3_map.py --check` 时正确报告 82 个待插入章节与 37 个待建章节，退出码为 1（符合 `--check` 设计契约，无 Python 报错或异常崩盘），待 V3-10 执行 `--apply` 后 `--check` 将输出 0 改动并以退出码 0 通过。

## 未验证

1. 真实 DeepSeek / OpenAI 模型调用（仅通过 mock/monkeypatch 验证工厂配置与错误处理）。
2. 真实本地 embedding 模型下载（BAAI/bge-small-zh-v1.5）与真实向量化计算。
3. GitHub Actions 远端 CI 环境运行（需提交并推送后由 GitHub 执行）。

## 复现方式

```bash
# 1. 运行工具测试与离线测试
python -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q

# 2. 运行断链检查与静态代码检查
python tools/check_course_links.py
python -m ruff check --target-version py311 common.py tools/apply_v3_map.py tools/test_apply_v3_map.py chapters/test_v3_lessons.py

# 3. 运行标签一致性自检
python tools/apply_v2_map.py --check
python tools/apply_v3_map.py --check
```

## 边界

1. 本批次未修改任何课程章节 README、workbook 或参考实现。
2. `course-v3-map.json` 中登记的 37 个新增章节目录将在后续 V3-1 至 V3-8 批次中实际创建。
3. `tools/apply_v3_map.py` 在当前批次仅作为映射验证与单测覆盖工具，不在旧章节中主动应用写入，等待 V3-10 收口执行。
