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
   - 查阅官方文档：DeepSeek 官方 API 英文定价文档 Models & Pricing（https://api-docs.deepseek.com/quick_start/pricing，读取日期 2026-10-27）。
   - 官方状态：官方文档已不再列出 `deepseek-chat`；`deepseek-v4-flash` 仍被接受，但会路由到 V4.1-Flash；当前官方推荐推荐的主力生产模型为 `deepseek-flash`（由 DeepSeek-V4.1-Flash 提供，支持 1M token 上下文，具备原生多模态输入与推理/非推理双模式）及 `deepseek-v4-pro`（旗舰推理）。
   - 改动结果：`common.py` 中 `DEEPSEEK_MODEL` 默认值更新为 `"deepseek-flash"`；`.env.example` 同步更新默认值与注释。
2. **OpenAI 官方模型核对**：
   - 查阅官方文档：OpenAI API Deprecations 页面（https://developers.openai.com/api/docs/deprecations，读取日期 2026-10-27）。
   - 官方状态：`gpt-4o-mini-2024-07-18` 已于 2026-10-14 宣布弃用，将于 2027-01-14 停用；当前官方推荐替代型号为 `gpt-6-luna`。
   - 改动结果：`common.py` 中 `OPENAI_MODEL` 默认值更新为 `"gpt-6-luna"`；`.env.example` 同步更新弃用时间说明与替代模型注释。

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


## 复核修复（2026-10-28）

审核记录（`docs/v3/reviews/V3-0.md`）退回了 V3-0，指出了 2 个阻断项、2 个主要问题与 2 个次要问题。本节记录针对必改项的完整修复与复核验证：

### 1. B1 依赖冲突解决与环境恢复（方案 A）
- **选型理由**：选方案 A（锁定兼容 `openai<3` 的 `pydantic-ai-slim` 版本）。锁定文件 `requirements.txt` 中 `langchain-openai==1.3.3` 要求 `openai<3.0.0,>=2.26.0`。经全量检索 PyPI 元数据，`pydantic-ai-slim[openai]` 在版本 `2.31.1` 及之前要求 `openai>=2.45.0`，自 `2.32.0` 起要求 `openai>=3.0.0`。因此将 `requirements-course.txt` 锁定为 `pydantic-ai-slim[openai]==2.31.1`，其依赖区间 `[2.45.0, 3.0.0)` 与 `langchain-openai==1.3.3` 完美交集，既保障了 LangChain 历史章节与 capstone 不被大版本变更破坏，又提供了完整的 Pydantic AI 原语能力。
- **DeepSeekProvider 识别核对**：检查 `pydantic-ai-slim==2.31.1` 源码，其 `DeepSeekModelName` 预置枚举为 `Literal['deepseek-chat', 'deepseek-reasoner', 'deepseek-v4-flash', 'deepseek-v4-pro']`，尚未包含当前官方新 ID `deepseek-flash`。因此在后续 L1.10 与 L4.5 的真实模型调用时，按细则要求显式配置关闭思考参数，并将在章节记录中注明。
- **干净临时环境解析证明**：在全新创建的临时虚拟环境（`$env:TEMP\v3_clean_venv`）中执行 `pip install --dry-run -r requirements-course.txt`，pip 解析器顺利求解全部依赖，输出计划安装：`langchain-openai-1.3.3`、`openai-2.54.0`、`pydantic-2.13.4`、`pydantic-ai-slim-2.31.1`、`opentelemetry-sdk-1.44.0`，退出码为 0，零冲突。
- **本机环境恢复**：本机 `.venv` 执行 `pip install -r requirements-course.txt` 完成同步，`openai` 恢复为 2.54.0，`langchain-openai` 恢复为 1.3.3，`pydantic-ai-slim` 为 2.31.1。执行 `pip check` 输出：`No broken requirements found.`。

### 2. B2 OpenAI 默认模型与事实修正
- 查阅 OpenAI 官方弃用说明（https://developers.openai.com/api/docs/deprecations，读取于 2026-10-27），`gpt-4o-mini-2024-07-18` 已于 2026-10-14 宣布弃用、2027-01-14 停用，替代型号为 `gpt-6-luna`。
- 修改 `common.py` 中 `active_model_name()` 的默认值为 `os.getenv("OPENAI_MODEL", "gpt-6-luna")`。
- 同步修正 `.env.example` 中的注释说明与推荐值。
- 在 `chapters/test_v3_lessons.py` 的 `test_chat_model_name` 中增加对 `OPENAI_MODEL` 默认 fallback 为 `gpt-6-luna` 的断言测试。

### 3. M1 DeepSeek 依据与措辞修正
- 依据改引 DeepSeek 官方英文定价文档：`https://api-docs.deepseek.com/quick_start/pricing`（读取于 2026-10-27）。
- 措辞纠正为“官方文档已不再列出 deepseek-chat”，并补充记录“`deepseek-v4-flash` 仍被接受，但会路由到 V4.1-Flash”。
- 同步更新 `.env.example` 注释与验证文档说明。

### 4. M2 客户端工厂去重与 m2 延迟导入
- 在 `common.py` 抽出内部公共解析函数 `_resolve_openai_client_kwargs(*, timeout: float = 30.0, max_retries: int = 0) -> tuple[str, dict[str, Any]]`，集中处理 provider 判断、环境变量检查（缺失变量时抛出清晰的 RuntimeError 变量名提示，绝不泄露敏感密钥）、本地 URL 识别与构造参数拼装。
- `get_openai_client` 与 `get_async_openai_client` 共享此函数，分别实例化同步与异步客户端，消除两处共约 50 行的重复代码。
- 实施次要项 m2：顶层移除 `import openai`，改为 `from typing import TYPE_CHECKING; if TYPE_CHECKING: import openai`，并在工厂函数执行时按需 `import openai`，使仅导入 `common` 配置的章节免去 OpenAI 庞大 SDK 的导入开销。

### 5. S1 跟进与死代码清理（m1）
- 细则任务 5 修正：`tools/apply_v3_map.py` 的插入规则由“插在 v2 行上方”改为“插在 v2 行下方”，避免打乱 `apply_v2_map.py` 的首字段相对定位。
- 实施次要项 m1：在 `chapter_readme` 中识别同一章节匹配到多个目录的情形，并写入 `problems` 列表，使 `problems` 真正参与错误检测与非零退出控制。
- 更新 `tools/test_apply_v3_map.py`：测试用例更新为 `test_upsert_insert_after_v2`，断言 v3 紧随 v2 之后且 v2 内容与行位置完全不变；新增 `test_multiple_directory_match_records_problem` 覆盖多目录异常（共 6 项单测全部 PASSED）。
- **S1 契约验证**：在独立副本（临时 git worktree）中连续执行两次 `python tools/apply_v3_map.py --apply`，再次执行 `python tools/apply_v2_map.py --check`，输出结果保持为：
  `合计：111 个 README；inserted=0 updated=0 unchanged=111`，退出码 0。彻底消除原有 82 updated 的规则互斥。

### 6. 复核执行命令与结果

| 验证项 | 执行命令 | 实际结果 |
|---|---|---|
| 干净环境依赖解析 | `pip install --dry-run -r requirements-course.txt` | 退出码 0，成功解析 `openai-2.54.0` + `pydantic-ai-slim-2.31.1` |
| 本机环境一致性 | `.venv/Scripts/python.exe -m pip check` | `No broken requirements found.` |
| 工具与章节离线测试 | `.venv/Scripts/python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q` | 45 passed in 11.13s |
| Capstone 生产测试 | `.venv/Scripts/python.exe -m pytest capstone/test_production.py -q` | 34 passed in 7.31s |
| 断链检查 | `python tools/check_course_links.py` | 检查 308 个 Markdown 文件，0 处断链 |
| 静态代码检查 | `.venv/Scripts/python.exe -m ruff check --target-version py311 common.py tools/apply_v3_map.py tools/test_apply_v3_map.py chapters/test_v3_lessons.py` | `All checks passed!` |
| v2 标签检查 | `python tools/apply_v2_map.py --check` | `111 unchanged`，退出码 0 |
| v3 映射检查 | `python tools/apply_v3_map.py --check` | `inserted=82 待建=37`，退出码 1（符合 V3-10 前预期） |
