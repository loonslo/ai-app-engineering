# L2.3 扩展：PDF 与来源溯源 · Gate（原 2.6）

[全书目录](../../README.md) · [上一章 L2.2（2.1）](../2.1-load-split/README.md) · [下一章 L2.3](../2.2-embed-retrieve/README.md)

- **能力**：按页加载 PDF 文本；把 source/page 带进上下文；核对答案引用是否真实存在。
- **v3 路径**：L2.2 / 核心（Gate；PDF 与来源）
- **前置**：2.3（最小 RAG）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `pdf_sources.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.6-pdf-sources/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

“带来源”在 demo 里只是拼一个字符串，在生产里要能核对：

- 扫描件页面没有文字层，不能当空片段入库；
- 页码丢失，回答只能标到文件、标不到页；
- 模型编造 `【来源：xxx 第9页】`，用户无法验证；
- 拒答/回答没有引用，或引用了不存在的文件。

这个 gate 用固定页文本和固定答案，验证“加载 → 标注 → 核对引用”这条链。

## 任务

实现 `gate/starter.py` 的三个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `load_pages` | `(页码, 文本)` → 带 source/page 的片段；空白页跳过；非法页/来源报错 |
| `format_context` | 有页码用 `[来源：file 第N页]`，无页码用 `[来源：file]`；段间空行 |
| `verify_citations` | 解析答案里的 `【来源：...】`，返回 `ok/cited/unknown` |

关键口径：

- 页码必须是 `>=1` 的整数；`source` 非空。
- 规范化引用：有页码 `"source#pN"`，无页码 `"source"`。
- `ok = 至少一个引用 且 unknown 为空`。
- 无引用 -> `ok=False`；伪造来源/未知页码 -> 进 `unknown`。
- 不修改输入。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 空白页 | 跳过，不生成片段 |
| 2 | 页码 0 / 字符串 | `ValueError` |
| 3 | source 为空 | `ValueError` |
| 4 | 答案引用真实页码 | `ok=True`，`cited` 正确 |
| 5 | 答案引用不存在的页码 | `ok=False`，进 `unknown` |
| 6 | 答案引用伪造文件 | `ok=False`，进 `unknown` |
| 7 | 答案没有引用 | `ok=False` |
| 8 | 片段缺 text/source | `ValueError` |

## 验收标准

`gate_check.py` 的 9 项全部 PASS：

- 按页加载、空白页、非法页/来源。
- 带页码上下文、非法片段。
- 引用全命中、未知页码、伪造来源、无引用、非法输入。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么空白页不能当片段入库？
2. 引用核对应该由程序做还是模型做？为什么？
3. 扫描件没有文字层时，最小可行方案是什么？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（9/9）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 2.6
```

对照时只回答：

1. 参考实现用 `pypdf` 逐页 `extract_text`；它怎么处理空页？
2. 参考实现的 `format_context` 怎么把页码拼进上下文？你的实现格式与规范差在哪？
3. 参考实现让模型自己写【来源】；它有没有核对引用？本 gate 的 `verify_citations` 补了什么？

## 概念地图

- **页级来源**：source + page；PDF 的页码是引用最小单位。
- **空页**：扫描件无文字层；跳过并记录，不能当空片段。
- **引用核对**：程序解析引用，与已知 source/page 比对；模型自报不算证据。
- **可追溯**：回答能回到具体文件的具体页。
- **过度拒答**：有部分证据也应尽量答并标来源，但引用必须真实。

## 边界

- gate 不读真实 PDF/pypdf，只处理页文本；扫描件 OCR 不在本章。
- 通过 gate 只证明来源/引用结构正确，不证明回答质量。
- 引用核对不等于事实正确；事实仍要靠人工抽查和评测。
