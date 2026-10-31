# L4.5 结构化路由 · Gate（原 4.7）

[全书目录](../../README.md) · [上一章 L4.3](../4.18-tool-design/README.md) · [下一章 L4.4（4.8）](../4.8-plan-and-execute/README.md)

- **能力**：把模型路由输出限制在枚举集合内；解析失败/非法值有明确出口。
- **v2 路径**：L4.5 / 核心（Gate；结构化路由）
- **v3 路径**：L4.4 / 核心（Gate；结构化路由）
- **岗位任务 / 面试题型**：T3 / F3、F4。
- **前置**：4.6（节点可靠性）、1.3（结构化输出）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `structured_routing.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.7-structured-routing/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

用关键词匹配猜模型意图，是生产路由最常见的脆弱点：

- 模型说“先 RESEARCH 再 WRITING”，两个关键词同时命中；
- 输出缺字段/多解释，解析崩；
- 值不在允许集合里，路由到不存在的节点；
- 分类标签拼错，分支永远走不到。

这个 gate 用固定 JSON 文本，验证解析、枚举校验、路由函数和意图分类。

## 任务

实现 `gate/starter.py` 的三个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `parse_route` | 解析 `{"next":...}`；缺字段/非法 JSON/值不在 allowed -> `ValueError` |
| `route_next` | done -> `"end"`；否则返回 `_next`；非法 -> `ValueError` |
| `parse_intent` | 解析 `{"category":...}`；只允许三类 |

关键口径：

- 允许集合由调用方传入，不在集合内就失败。
- 解析失败不返回默认值，避免“静默走错分支”。
- `route_next` 的 `_next` 只允许 `research/writing/review`。
- 意图只允许 `knowledge/data_query/chitchat`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 合法 route JSON | 返回 next |
| 2 | 非 JSON / 数组 / 缺 next | `ValueError` |
| 3 | next 不在 allowed | `ValueError` |
| 4 | done=True | `"end"` |
| 5 | `_next` 非法 | `ValueError` |
| 6 | 意图三类 / 未知类别 | 正常 / `ValueError` |

## 验收标准

`gate_check.py` 的 4 项全部 PASS：

- 枚举路由解析、拒绝非法路由、路由函数、意图解析。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么路由失败不能默认走某条分支？
2. 枚举校验和关键词匹配的差别是什么？
3. 解析失败时，程序应该重试、降级还是转人工？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（4/4）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 4.7
python tools/run_chapter.py 4.7 --live
```

对照时只回答：

1. 参考实现以工具参数输出枚举，你的 gate 从 JSON 文本解析枚举；两者分别在哪一侧约束、在哪一侧校验？
2. 参考实现的路由为什么能直接按确定字段分支？枚举合法能否证明语义分类正确？
3. 模型没有调用输出工具、调用两次或返回非法值时，参考实现怎样停止？业务需要重试还是转人工？

### 从 JSON gate 到“工具即输出”

“工具即输出”指把 `submit_decision` 注册为一个函数工具，但不执行外部业务：
模型的工具参数本身就是分类结果。schema 的 `enum` 列出合法值，真实调用强制选择
`submit_decision`；代码仍检查只能有一次该调用、参数必须是 JSON 对象、字段必须属于枚举。
约束能减少格式歧义，不能保证模型把问题分对。

参考实现保留两组完整演示：

1. 主管按 `research/writing/review/finish` 选择专家，专家完成后再次决策；`max_steps`
   限制主管调用数，没有 `finish` 就明确失败，不能无限循环。
2. 把知识、数据查询、闲聊问题分别分到 `knowledge/data_query/chitchat`。分支只是教学节点，
   不会真的检索、执行 SQL 或查到利润数据。

默认使用脚本化工具调用，仍经过同一套解析和枚举校验。`--live` 才创建
`common.get_openai_client()` 客户端，模型名来自 `common.chat_model_name()`；
缺密钥、服务不可达或非法输出均给可读提示并以 1 退出，不打印堆栈。解析失败不会默认去某条分支，
本章也不添加自动重试。

DeepSeek 默认思考模式不适合本例的强制工具选择，因此显式关闭思考：
`extra_body={"thinking":{"type":"disabled"}}`。本例不使用严格 JSON Schema 响应格式；
Chat Completions 的函数工具也必须在本地复核参数。
参见 [DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode)、
[OpenAI Function calling](https://platform.openai.com/docs/guides/function-calling)
（均读取于 2026-10-31）。真实兼容性与分类准确率未由离线 gate 证明。


## 概念地图

- **结构化路由**：模型输出枚举/JSON，代码读确定字段。
- **枚举**：把选择限制在可验证集合内。
- **解析失败**：不能默认走某条路，要明确失败/降级。
- **意图分类**：knowledge/data_query/chitchat 分流。
- **代价**：多一次约束，换可测/可复现。

## 边界

- gate 用固定文本，不调用真实模型。
- 通过 gate 只证明解析/校验结构正确，不证明模型分类准确。
- 原生工具即输出、主管循环与意图分支见参考实现；没有实现真实 RAG / SQL 专家。
