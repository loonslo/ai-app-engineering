# V3-0 基础设施细则

为后续批次准备共用能力：原生模型工厂、依赖锁定、v3 映射与打标工具、v3 测试入口。本批次不改任何章节内容。

## 任务 1：`common.py` 新增原生工厂

只新增函数，不改现有函数的签名与行为。`get_llm()`、`get_embeddings()`、`get_reliable_llm()` 仍供旧章节与 capstone 使用。

| 函数 | 行为 |
|---|---|
| `get_openai_client(*, timeout: float = 30.0, max_retries: int = 0) -> openai.OpenAI` | 按 `LLM_PROVIDER` 返回 OpenAI 兼容客户端，规则见下表；构造时不发网络请求 |
| `get_async_openai_client(*, timeout: float = 30.0, max_retries: int = 0) -> openai.AsyncOpenAI` | 同上，异步版本 |
| `chat_model_name(model: str \| None = None) -> str` | 返回 `model` 或 `active_model_name()`；结果为空时抛 `RuntimeError`，消息写明应设置哪个环境变量 |
| `get_sentence_embedder()` | 用 `functools.lru_cache` 缓存的 `sentence_transformers.SentenceTransformer(EMBED_MODEL_PATH)`；函数内延迟导入；路径不存在时抛 `RuntimeError`，提示见根目录 README“准备本地 embedding 模型” |
| `embed_texts(texts: list[str], *, normalize: bool = True) -> list[list[float]]` | 空列表返回 `[]`；调用 embedder 的 `encode(..., normalize_embeddings=normalize)` 并转成列表 |
| `get_cross_encoder()` | 用 `lru_cache` 缓存的 `sentence_transformers.CrossEncoder(RERANKER_MODEL_PATH)`；规则同上 |

客户端规则：

| `LLM_PROVIDER` | base_url | api_key |
|---|---|---|
| `deepseek` | `DEEPSEEK_BASE_URL` | `_deepseek_api_key()`；本地 URL 且无密钥时用 `"local-model"` |
| `openai` | `OPENAI_BASE_URL`，未设置则用 SDK 默认值 | `OPENAI_API_KEY`（必需） |
| `openai_compatible` | `OPENAI_COMPATIBLE_BASE_URL`（必需） | `OPENAI_COMPATIBLE_API_KEY`；本地 URL 且无密钥时用 `"local-model"` |
| `ollama` | `f"{OLLAMA_BASE_URL}/v1"` | `"ollama"` |
| `azure` | 使用 `openai.AzureOpenAI` / `AsyncAzureOpenAI`，参数取 `AZURE_ENDPOINT`、`AZURE_API_KEY`、`AZURE_API_VERSION` | 同左 |
| `bedrock` | 抛 `RuntimeError`，提示改用 OpenAI 兼容网关或旧接口 `get_llm()` | — |

要求：

- 运行时读取模块级常量（如 `LLM_PROVIDER`），不要把它们固化成函数参数的默认值，便于测试时 monkeypatch。
- 缺少必需配置时抛 `RuntimeError`，消息只列出变量名，不打印密钥。
- 函数 docstring 写明用途，以及 v3 章节应该用它而不是 `get_llm()`。

## 任务 2：核对默认模型 ID

- 查 DeepSeek 官方 API 文档（英文版）的当前模型列表。若 `deepseek-chat` 已下线或只剩兼容别名，把 `DEEPSEEK_MODEL` 的默认值改为当前推荐的 ID，并同步 `.env.example` 的注释。
- 用同样方式核对 `OPENAI_MODEL` 的默认值 `gpt-4o-mini`。
- 不读取、不修改 `.env`。
- 在验证记录中写明文档链接、读取日期、改动前后的值。已知线索：Pydantic AI 的 issue #5193 称旧别名已于 2026-07-24 下线；以官方文档为准。

## 任务 3：依赖锁定与环境核对

- 在 `requirements-course.txt` 新增并锁定版本：
  - `pydantic-ai-slim[openai]==<V3-0 当天 PyPI 最新稳定版>`，注释写“v3：L1.10、L4.5、L4.8、L4.17”；
  - `opentelemetry-sdk==<与本机 opentelemetry-api 相同的版本>`，注释写“v3：L3.7、L5.6”。
- 核对 Pydantic AI 锁定版本支持的 Python 版本，写进验证记录。
- 记录本机 `.venv` 与锁定文件的差异：2026-10-27 已知缺少 `langchain` 顶层包，`fastapi` 为 0.141.1 而锁定的是 0.139.2。按 `requirements-course.txt` 重新安装后再跑测试；装不上的写进“未验证”。

## 任务 4：`docs/course-v3-map.json`

- 结构与 `docs/course-v2-map.json` 相同：`{"<章节号>": {"stage": "...", "role": "...", "note": "..."}}`。
- 覆盖 outline.md 第 4 节的全部目录（含尚未创建的新目录）和第 5 节的全部选修 / 阅读章节。
- 字段规则：

| 情况 | stage | role | note |
|---|---|---|---|
| 核心 gate 章 | v3 编号，如 `L1.10` | `核心` | `Gate；<标题短名>` |
| 核心清单章 | v3 编号 | `核心` | `清单验收` |
| 一个 v3 章节对应多个目录 | 各目录写同一个 v3 编号 | `核心` | 用短名区分，如 `Gate；PDF 与来源` |
| 核心阅读 | 归入的 v3 编号 | `核心阅读` | `归入 L3.4` 之类 |
| L4.15 | `L4.15` | `选做` | `清单验收；实操选做` |
| P 章 | `P1`–`P6` | `项目` | `清单验收` |
| J 章 | `J1`–`J7` | `就业` | `清单验收` 或 `演练测试` |
| 选修 | `选修` | `选修` | 写原因，如 `被 L4.14 取代` |

## 任务 5：`tools/apply_v3_map.py`

参照 `tools/apply_v2_map.py` 实现：

- `--check`：列出需要改动的 README，有改动时退出码为 1；`--apply`：写入。
- 写入的行：`- **v3 路径**：<stage> / <role>（<note>）`。
- 插入位置：已有 `v3 路径` 行时原地替换；否则若有 `v2 路径` 行，插在它的上一行；两者都没有时，插在第一个头部字段行（`- **能力**` 或 `- **目标**`）之后。
- 永远不修改 `v2 路径` 行。用户已决定保留 v2 行（2026-10-27），不实现替换选项。
- 不处理 `flagship-project/` 的步骤 README（已冻结）。
- 映射中存在、但目录尚未创建的章节输出为“待建”，不算错误，也不影响退出码。
- 幂等：连续运行两次 `--apply`，第二次没有改动。

## 任务 6：测试

- 新建 `tools/test_apply_v3_map.py`：用临时目录构造 README，覆盖三种插入位置、幂等性、“待建”目录、不碰 v2 行。
- 新建 `chapters/test_v3_lessons.py`，先放任务 1 的离线测试：
  - 每个 provider 的 base_url、api_key 来源、timeout、max_retries；
  - `ollama` 的 base_url 以 `/v1` 结尾；
  - `bedrock` 抛出带提示的 `RuntimeError`；
  - 缺少密钥时报错信息含变量名、不含密钥值；
  - `chat_model_name()` 为空时报错；
  - `embed_texts` 通过 monkeypatch 替换 embedder，不下载模型。
- 测试不联网、不读 `.env`。
- 后续批次给换实现章节的纯函数补测试时，追加到这个文件。

## 任务 7：CI

在 `.github/workflows/eval-gate.yml` 的 “Verify course tools and unified project baseline” 步骤里，把 pytest 命令改为：

```bash
python -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
```

确认 `chapters/test_v3_lessons.py` 只依赖 `requirements-dev.txt` 已锁定的包。

## 验收

- conventions.md 第 11 节命令 4、5、6、8、9 全部通过；本批次没有 gate，命令 1–3、7、10 不适用。
- `python tools/apply_v3_map.py --check` 只列出“待建”与需要添加 v3 行的旧章节，不报错。
- 写验证记录 `docs/gate-v3-0-validation.md`，内容含任务 2 的依据与任务 3 的环境差异。

## 审核重点

- 新函数没有改变旧函数的行为；capstone 测试仍然通过（`python -m pytest capstone/test_production.py -q`）。
- 不打印密钥；构造客户端不联网。
- map 与 outline.md 逐条一致。
- `apply_v3_map.py` 不碰 v2 行，且幂等。
