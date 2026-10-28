# L1.6 手写 Harness · Gate（原 2.5）

[全书目录](../../README.md) · [上一章 2.4](../2.4-eval-seed/README.md) · [下一章 2.6](../2.6-pdf-sources/README.md)

- **能力**：不用框架实现切分、检索、带引用的回答和最小 ReAct 循环；能解释框架封装了哪一层。
- **v2 路径**：L1.6 / 核心（Gate；手写 Harness）
- **前置**：L1.6（工具调用协议）。本章检索使用基于字符与词频的简化评分，不依赖第 2 篇。
- **时间盒**：7 小时（2h 读 + 4h 实现 + 1h 故障与记录）。
- **闭卷规则**：只读本页、`gate/starter.py` 和 Python 标准库文档；**通过 gate 之前不要打开** `raw_sdk_rag_agent_loop.py`，也不要搜索完整实现。
- **验收命令**：

```bash
python chapters/part2-rag/2.5-raw-sdk-rag-agent-loop/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 来绕过检查。

## 为什么做这个 gate

第 2 篇会用真实 embedding 与混合检索替换这里的简化评分。但线上出错时，问题往往不在框架：切片边界、检索分数、上下文拼接、工具解析、循环终止、异常兜底，任何一层都能让回答看起来“模型很笨”。

这个 gate 不考“能不能跑通一个 demo”，而是考：

> 把模型调用当成一个不可靠的外部依赖，手写一层可解释、可失败、可终止的 harness。

## 任务

实现 `gate/starter.py` 的四个函数，接口以该文件的 docstring 为准：

| 函数 | 你要交付的行为 |
|---|---|
| `split_text` | 空文本返回 `[]`；按 `chunk_size`/`overlap` 切分；非法参数抛 `ValueError` |
| `retrieve` | 只返回分数 > 0 的片段，按分数降序，最多 `k` 个；不改传入列表 |
| `answer` | 有证据时调用 `chat_fn` 并返回 `sources`；无证据/空问题/模型失败时拒答，不抛未处理异常 |
| `run_agent` | 解析 `Action:`/`Final:`；未知工具、工具异常、模型异常、超步数都有可读出口和 `trace` |

关键约定：

- 引用格式固定为 `"source#index"`，例如 `refund.md#1`。
- 拒答时 `sources=[]`；不要给拒答附上无关来源。
- `answer` 的 `error` 用可读字符串：`timeout`、`model_error`、`empty_response`。
- `run_agent` 的 `trace` 每步至少包含 `step`、`tool`、`arg`、`ok`、`observation`；失败步骤加 `error`。
- `stopped_reason` 只能是 `final`、`max_steps`、`unparsed`、`model_error`。

## 故障注入（必须亲手触发）

实现后，用下面的场景逐一验证；这些也是 gate 的核心检查项。

| # | 注入 | 期望 |
|---|---|---|
| 1 | 问题在资料外 | 拒答，`sources=[]`，不调用 `chat_fn` |
| 2 | `chat_fn` 抛 `TimeoutError` | 不崩溃；`refused=True`，`error` 含 `timeout` |
| 3 | `chat_fn` 返回空串 | `refused=True`，`error` 含 `empty_response` |
| 4 | 模型请求未知工具 | `trace` 中 `ok=False`、`error=unknown_tool`，循环仍可收尾 |
| 5 | 工具函数抛异常 | `trace` 中 `error=tool_error`，不把异常抛给调用方 |
| 6 | 模型一直请求工具 | 到 `max_steps` 停止，`stopped_reason=max_steps` |
| 7 | 模型输出既不是 Action 也不是 Final | 保留原文，`stopped_reason=unparsed` |

## 验收标准

`gate_check.py` 的 16 项全部 PASS：

- 切分：空文本、基本切分、overlap、非法参数。
- 检索：排序、过滤、`k`、空查询。
- 回答：有证据引用、无证据拒答、空问题、超时、空响应。
- Agent：正常收尾、未知工具、工具异常、最大步数、无法解析、模型异常。

通过后，把 `gate/gate_report.json` 和一段 5 行以内的失败分析写进 [workbook.md](workbook.md)：

1. 哪一项最容易写错？
2. 你的实现如何处理“模型输出不可信”？
3. 如果把 `max_steps` 改成 1，哪个测试会失败，为什么？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（16/16）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 2.5 raw_sdk_rag_agent_loop.py
```

对照时只回答三个问题，不要逐行抄：

1. 参考实现把“检索失败”和“生成失败”分开处理了吗？你的呢？
2. 参考实现的 `TOOLS` 用了 `eval`；为什么这在生产里不可接受？你的 gate 实现有没有类似风险？
3. 参考实现的循环有没有 `max_steps` 之外的终止条件？缺了会怎样？

## 概念地图

- **Harness**：模型之外的工程层，包括检索、prompt 拼接、工具解析、循环控制、停止条件、错误兜底和日志。
- **可追溯**：每个答案能回到具体片段；没有来源的答案不可信。
- **有界循环**：Agent 必须有步数上限和明确出口，否则一次错误决策会烧钱、拖延迟。
- **失败降级**：上游超时/异常时，服务给用户可读结果，而不是 500 或堆栈。
- **框架的边界**：框架封装的是这些 harness；理解它们，才知道何时该手写、何时该用框架。

## 边界

- 本章参考实现面向 DeepSeek 官方兼容 HTTP 端点（`DEEPSEEK_BASE_URL`）并使用 `DEEPSEEK_MODEL`（默认 `deepseek-flash`）；密钥查找顺序为显式进程环境变量（`DEEPSEEK_API_KEY`） > Windows 用户环境变量 > 本地 `.env` 文件。未配置密钥时运行为全离线模拟提示；若遇网络不可达，脚本会捕获 `URLError` 并输出友好提示，不会直接报出底层堆栈。
- 本章的检索用简化评分，不追求效果；真实系统用 embedding/BM25/混合检索（第 2 篇后半）。
- 本章的工具是无副作用示例；有副作用的工具需要授权、审批和审计（4.11、4.12）。
- 通过 gate 只证明 harness 结构正确，不证明 RAG 答案质量；质量要看 2.9 的评测。
