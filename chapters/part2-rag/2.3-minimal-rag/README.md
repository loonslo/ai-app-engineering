# L2.3 最小 RAG · Gate（原 2.3）

[全书目录](../../README.md) · [上一章 L2.3](../2.2-embed-retrieve/README.md) · [下一章 L2.5](../2.7-chunk-strategy/README.md)

- **能力**：检索 → 拼带来源的上下文 → 生成 → 引用/拒答；无证据不调用模型。
- **v3 路径**：L2.4 / 核心（Gate；最小 RAG）
- **前置**：2.2（向量化与召回）。
- **时间盒**：6 小时（1h 读 + 4h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `minimal_rag.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.3-minimal-rag/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

“检索到了”不等于“回答有依据”。最小 RAG 最容易出这些事：

- 没检索到也调用模型，模型开始编；
- 上下文拼了来源，但回答的 `sources` 是模型编的；
- 检索/模型异常直接崩，用户看到 500；
- 上下文超预算，塞爆请求或截断关键事实；
- 拒答时仍附来源，制造“有证据”的假象。

这个 gate 用假检索/假模型，把 RAG 拆成 **上下文、来源、拒答、失败出口** 四件事。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `format_context` | 每段加 `[source]` 标记；按预算只放得下的片段；空列表返回 `""` |
| `answer_with_rag` | 检索 → 拼上下文 → 调模型 → 返回 answer/sources/refused/error |

关键口径：

- 空问题 -> `ValueError`。
- 无检索结果 -> `refused=True`，`answer="文档中没有提到。"`，**不调用** `chat_fn`。
- `sources` 来自实际进入上下文的片段，去重、按出现顺序。
- 检索异常 -> `error="retrieval_error"`；模型超时 -> `timeout`；其他异常 -> `model_error`；空回答 -> `empty_response`。
- `max_context_chars` 预算包含 `[source]\n` 前缀和块间分隔符；放不下的片段不进入上下文，也不进入 `sources`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 无检索结果 | 拒答，不调用模型 |
| 2 | 检索函数抛异常 | `retrieval_error`，不崩 |
| 3 | 模型超时 | `timeout`，不崩 |
| 4 | 模型返回空白 | `empty_response` |
| 5 | 上下文预算只够第一段 | `sources` 只有第一段 |
| 6 | 两段同来源 | `sources` 去重 |
| 7 | 空问题 | `ValueError` |
| 8 | 片段缺 text/source | `ValueError` |

## 验收标准

`gate_check.py` 的 10 项全部 PASS：

- 上下文格式/非法输入；有证据、无证据、空问题。
- 检索异常、模型超时、空回答、预算、来源去重。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么无证据时要“不调用模型”，而不是让模型自己判断？
2. `sources` 应该由谁生成：模型还是程序？为什么？
3. 上下文预算应该包含来源标记吗？不计入会怎样？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（10/10）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 2.3 minimal_rag.py
python tools/run_chapter.py 2.3 minimal_rag_langchain.py
```

对照时只回答：

1. 原生实现显式串联检索、预算裁剪与模型调用；LCEL 版本是如何通过管道符 `|` 实现类似逻辑的？
2. 原生实现严格核对引用 `source#index` 与拒答；LCEL 对照版依赖提示词让模型自报来源，存在什么缺陷？
3. 原生实现在无检索证据时完全跳过模型调用，节约了哪些开销？

## 框架对照

本章提供了两种实现方式供对比学习：
- 原生实现：`minimal_rag.py`（推荐生产基线，原生 Python + OpenAI SDK）
- LCEL 对照：`minimal_rag_langchain.py`（LangChain 经典声明式链路）

### 1. 代码形态对比

在 LCEL 对照版中，调用链通过操作符重载拼接：

```python
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
```

而在原生实现中，执行流程为显式控制流：

```python
docs = retrieve_fn(question)
if not docs:
    return {"refused": True, "answer": "文档中没有提到。", "sources": []}
context = format_context(docs, max_context_chars)
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"上下文：\n{context}\n\n问题：{question}"},
]
answer = chat_fn(messages)
```

### 2. 调试与可观测性代价

- **调用栈深度**：LCEL 链在执行单次调用时，底层穿透 `RunnableSequence`、`RunnableParallel`、`RunnableAssign`、序列化转换器等十余层内部包装类。一旦网络抖动、返回格式畸变或超时，排查日志往往包含数页非业务栈帧。
- **异常拦截与降级**：原生代码对检索异常（`retrieval_error`）、超时（`timeout`）、空响应（`empty_response`）可以直接使用标准的 `try-except` 分级捕获并返回确定性结果；LCEL 链则需挂载回调处理器（Callbacks）或复杂的 Fallback 结构。
- **无证据短路**：原生实现能在检索结果不足时直接短路返回，零 LLM Token 损耗且无证据时不调用模型；LCEL 基础管道如果不引入复杂的条件分支，通常仍会执行完整的模型推理。

## 概念地图

- **RAG 四层**：召回、上下文、生成、拒答/引用；答错时先定位层。
- **上下文预算**：片段、来源标记、分隔符都占 token；超预算要裁剪。
- **程序生成来源**：`sources` 应来自进入上下文的片段，不应让模型自由编。
- **无证据拒答**：没有候选就不调用模型，省钱且避免幻觉。
- **可读失败**：检索/模型异常转成 `error`，让上层降级。

## 边界

- gate 用假检索/假模型，不验证真实 RAG 质量。
- 通过 gate 只证明上下文/引用/拒答结构正确。
- 进阶混合检索与重排见 2.8 与 2.11；完整真实评测见 2.15。
