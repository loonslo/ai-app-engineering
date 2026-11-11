# 里程碑 7.1 / step3 · 用真实产品链执行离线评测

[项目目录](../../README.md) · [上一步](../step2/README.md) · [下一步](../step4/README.md)

## 问题：怎样保留第一次可用的质量起点？

试问几句得到正确回复，只能留下印象。现在把政策问题与拒答问题写成固定数据，通过正式产品入口执行，保存下一次改动可以比较的基线。

## 概念

评测集描述预期行为，替身隔离外部模型，评测器检查回答和引用。规则覆盖与真实模型语义质量仍需分开验收。

## 动手与观察

先改坏一条期望来源，确认评测能报警；再恢复并运行累计测试，记录哪些检查用了替身。

结果记入 [workbook.md](workbook.md)。

## 项目实现参考

固定评测题不是用户入口，而是版本升级前可以重复运行的质量基准。自由提问继续使用默认交互模式。

## 与 里程碑 7.1 / step2 的文件衔接

| 文件 | 本节的状态 | 为什么必须一起看 |
|---|---|---|
| `src/customer_support/evaluation.py` | 新增 | 读取固定用例并调用正式 `assistant.ask()` |
| `src/customer_support/settings.py` | 修改旧文件 | 在多文档配置上增加 `evaluation_path` |
| `data/eval_cases.json` | 新增 | 提供可重复的答案与来源验收输入 |
| `src/customer_support/knowledge.py` | 继承未改 | 评测仍使用 里程碑 7.1 / step2 的多文档摄取和检索 |
| `src/customer_support/assistant.py` | 继承未改 | 评测不复制问答逻辑，直接复用业务入口 |
| `src/customer_support/bootstrap.py` | 继承未改 | 两个入口都由同一个组合入口创建正式依赖 |

用 `python tools/materialize.py flagship m1-rag-mvp/step3 --diff` 核对实际变更。

## 本步骤交付

- `data/eval_cases.json` 保存问题、答案关键词、期望来源和拒答要求。
- `evaluation.py` 分别判断回答和引用，输出可定位结果。
- 评测作为独立开发验收程序，不进入用户问答界面。
- 评测程序创建真实 embedding、Retriever 和 LLM，再执行评测集。
- 任一用例失败时进程返回非零退出码，可供后续 CI 使用。

## PyCharm 中的两个运行配置

- 用户主程序：Module name 为 `customer_support.app`。
- 开发评测：Module name 为 `customer_support.evaluation`。

用户平时只运行第一个配置。

## 真实评测链

```text
eval_cases.json
  → load_cases
  → 真实 CustomerSupportAssistant.ask
  → 多文档检索 + LLM
  → answer_ok + citation_ok
  → 评测报告和退出码
```

## 在 PyCharm 运行

还原 里程碑 7.1 / step3 后，将 `.build/flagship/m1-rag-mvp/step3/customer-support/src` 标记为 Sources Root，Working directory 选择 `.build/flagship/m1-rag-mvp/step3/customer-support`，再选择对应模块运行配置。

真实评测需要模型环境可用。自动测试会替代昂贵外部依赖来验证评测规则，但本步骤完成标准还包括运行一次真实评测程序。

里程碑 7.1 / step4 将改进真实检索器，并用同一个评测程序比较结果。
