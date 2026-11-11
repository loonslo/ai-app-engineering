# 里程碑 7.1 / step1 · 可自由使用的客服 RAG 最小产品

[项目目录](../../README.md) · [下一步](../step2/README.md)

## 问题：客服第一次接入知识库，先要回答什么？

我们从一个最小场景开始：客户询问退款或配送政策，系统只依据现有文档回答。第一步先把加载、检索、生成和拒答接成可交互入口，不急着加入订单与前端。

## 概念

资料提供事实，检索器提供候选，Assistant 组织回答，应用入口处理交互。每一层都要能单独说清楚输入和输出。

## 动手与观察

用一个资料内问题和一个资料外问题比较行为，保存实际命中来源，再运行离线替身测试。真实模型输出需另记，不能把替身通过当成产品质量已达标。

结果记入 [workbook.md](workbook.md)。

## 项目实现参考

这是旗舰项目的第一个可运行版本。之后的 7 个里程碑在同一条产品链上逐步增加能力。

## 衔接基线

里程碑 7.1 / step1 没有需要继承的旧产品文件，本步先建立后面每一步都要沿用的最小主链：

| 文件 | 状态 | 主链职责 |
|---|---|---|
| `src/customer_support/settings.py` | 新建 | 提供单个知识文件和模型配置 |
| `src/customer_support/knowledge.py` | 新建 | 把 Markdown 转成 chunks 和 Retriever |
| `src/customer_support/bootstrap.py` | 新建 | 组装真实 embedding、Retriever、LLM |
| `src/customer_support/assistant.py` | 新建 | 执行检索、拒答、回答和来源返回 |
| `src/customer_support/app.py` | 新建 | 接收问题并展示结果 |

从 step2 起，各步在这个基线上标出“新增 / 修改旧文件 / 继承未改”。完整对照见 [首个里程碑衔接总览](../../docs/step-chain-overview.md)。

## 本步骤交付

- 用户可以连续输入任意问题，而不是只能运行写死示例。
- 程序先检索真实 FAQ，有证据才调用模型。
- 无证据时在模型调用前拒答。
- 回答来源只取自检索文档 metadata；模型按提示词拒答时不附来源。
- 运行主程序后直接输入问题，不需要记任何参数。

## 真实调用链

```text
用户输入
  → app.py
  → bootstrap.py 创建真实 embedding、Chroma Retriever、LLM
  → CustomerSupportAssistant.ask
  → 检索证据
  → 拒答或生成答案
  → 展示答案和来源
```

## 在 PyCharm 运行

先用 `tools/materialize.py flagship <里程碑/步骤>` 还原 里程碑 7.1 / step1，然后在 PyCharm 中：

1. 将 `.build/flagship/m1-rag-mvp/step1/customer-support/src` 标记为 Sources Root。
2. 新建 Python Module 运行配置，Module name 填 `customer_support.app`。
3. Working directory 选择 `.build/flagship/m1-rag-mvp/step1/customer-support`。
4. 点击运行按钮。

程序中可以连续输入自己的问题，输入 `exit` 或 `退出` 结束。

## 验收

人工验收必须至少尝试一个资料内问题和一个资料外问题。自动测试用于发布前回归，不是用户入口：

在 PyCharm 中右键 `tests` 目录运行全部测试。

里程碑 7.1 / step1 完成后，产品已经能真实问答；它暂时只读取一份 FAQ，里程碑 7.1 / step2 会在同一链路上扩展为多文档。
