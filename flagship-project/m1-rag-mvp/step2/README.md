# 里程碑 7.1 / step2 · 多文档知识库正式接入问答链

[项目目录](../../README.md) · [上一步](../step1/README.md) · [下一步](../step3/README.md)

## 问题：资料增多以后，最小实现哪里开始不足？

一份 FAQ 逐渐变成多份政策，若仍只读取一个文件，新增资料永远不会进入回答。我们先把文件摄取变成独立职责，再让原检索入口使用整个知识目录。

## 概念

摄取产生带来源和稳定标识的片段，知识层构建检索器，原问答层继续消费它。新增模块必须进入已有调用链才产生业务效果。

## 动手与观察

新增一份合成政策后问它独有的事实。对照 source、source_id 与 chunk_id，验证重复摄取是否稳定。

结果记入 [workbook.md](workbook.md)。

## 项目实现参考

里程碑 7.1 / step2 修改 里程碑 7.1 / step1 的真实运行路径，不新增孤立演示组件。

## 与 里程碑 7.1 / step1 的文件衔接

| 文件 | 本节的状态 | 为什么必须一起看 |
|---|---|---|
| `src/customer_support/ingestion.py` | 新增 | 遍历知识目录并生成带来源标识的 chunks |
| `src/customer_support/settings.py` | 修改旧文件 | `knowledge_path` 从单个 `customer_faq.md` 改为 `data/knowledge/` |
| `src/customer_support/knowledge.py` | 修改旧文件 | 从 `load_chunks` 切换为 `ingest_directory`，否则新摄取层不会生效 |
| `src/customer_support/bootstrap.py` | 继承未改 | 仍把 Settings 中的路径传入统一 `build_retriever` |
| `src/customer_support/assistant.py` | 继承未改 | 继续消费 Retriever，不需要知道知识库有几份文件 |

用 `python tools/materialize.py flagship m1-rag-mvp/step2 --diff` 可以核对这张表与实际文件差异。

## 本步骤交付

- 配置从单个 FAQ 文件升级为知识目录。
- 目录中的全部 Markdown 按稳定顺序摄取。
- 每个切块带有 `source`、`source_id` 和稳定 `chunk_id`。
- `build_retriever()` 使用全部文档构建真实 Chroma Retriever。
- 里程碑 7.1 / step1 的交互问答不变，但现在能检索退款和配送独立政策。

## 真实调用链

```text
data/knowledge/*.md
  → ingestion.ingest_directory
  → 全部 chunks
  → knowledge.build_retriever
  → Chroma
  → bootstrap.build_assistant
  → 主程序自由问答
```

`ingestion.py` 独立负责加载与切块，`knowledge.py` 负责构建检索器，二者不会互相导入。

## 在 PyCharm 运行与体验

还原 里程碑 7.1 / step2 后，将 `.build/flagship/m1-rag-mvp/step2/customer-support/src` 标记为 Sources Root；运行模块填写 `customer_support.app`，Working directory 选择 `.build/flagship/m1-rag-mvp/step2/customer-support`，然后点击运行。

请自由尝试退款、配送、发票和资料外问题，并检查来源是否来自实际命中文档。

## 完成标准

- 知识目录包含并加载 `customer_faq.md`、`refund.md`、`shipping.md`。
- 真实产品检索器由整个知识目录构建。
- 相同资料重复摄取产生相同 `chunk_id`。
- 里程碑 7.1 / step1 至 step2 的累计测试全部通过。

里程碑 7.1 / step3 将在这条真实问答链上运行固定业务回归集。
