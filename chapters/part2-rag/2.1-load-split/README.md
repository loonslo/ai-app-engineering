# L2.1 文档加载与切分 · Gate（原 2.1）

[全书目录](../../README.md) · [上一章 1.8](../../part1-foundations/1.8-cli-chatbot/README.md) · [下一章 2.2](../2.2-embed-retrieve/README.md)

- **能力**：把 UTF-8 文件读成可追溯文档；按大小/重叠切成非空片段，保留 source。
- **v2 路径**：L2.1 / 核心（Gate；加载与切分）
- **前置**：无（会读文件即可）。
- **时间盒**：4 小时（1h 读 + 2h 实现 + 1h 边界分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `load_split.py` / `load_split_formats.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.1-load-split/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

RAG 的第一步不是问模型，而是把资料变成**可追溯**的片段。常见事故：

- 文件读失败/编码错，整条建库静默为空；
- 空片段进入索引，召回一堆空内容；
- 片段超过预算，塞爆上下文；
- 重叠参数非法，切分死循环或重复过多；
- 片段丢了 `source`，回答无法引用。

这个 gate 用临时 UTF-8 文件和固定字符串，验证加载、校验、切分和重叠。

## 任务

实现 `gate/starter.py` 的两个函数：

| 函数 | 你要交付的行为 |
|---|---|
| `load_text` | 读 UTF-8；返回 `{"text","source"}`；不存在/读取失败抛 `ValueError` |
| `split_text` | 校验 doc/参数；空文本返回 `[]`；按 `chunk_size`/`overlap` 切；每段带 source/index |

关键口径：

- `source` 只取文件名（`Path.name`），不暴露绝对路径。
- `chunk_size` 必须 > 0；`overlap` 在 `[0, chunk_size)`。
- 片段非空、长度 ≤ `chunk_size`、index 从 1 连续编号。
- 相邻片段按字符重叠 `overlap` 个字符。
- 不修改传入的 `doc`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 不存在的文件 | `ValueError` |
| 2 | 空文本/纯空白 | `[]` |
| 3 | `chunk_size=0` | `ValueError` |
| 4 | `overlap=-1` / `overlap>=chunk_size` | `ValueError` |
| 5 | doc 缺 `text/source` 或类型错 | `ValueError` |
| 6 | 20 字符、10/2 切分 | 3 段，第二段以第一段末尾 2 字符开头 |

## 验收标准

`gate_check.py` 的 6 项全部 PASS：

- UTF-8 加载与 source、缺失文件。
- 空文本、切分/编号/重叠、非法参数、非法文档。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么片段要带 source，而不是只存正文？
2. `overlap` 太大/太小分别有什么代价？
3. 真实 PDF 无文字层时，`load_text` 会得到什么？该怎么提示用户？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（6/6）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 2.1 load_split.py
python tools/run_chapter.py 2.1 load_split_formats.py
```

对照时只回答：

1. 参考实现用原生递归字符切分 `split_text_recursive`，它比本 gate 的字符切分多做了什么？
2. 参考实现的 metadata 如何从文档复制到片段？你的实现在哪一步丢了 metadata？
3. 参考实现对 PDF/CSV 用不同 loader；本 gate 只做 txt，边界在哪里？

## 概念地图

- **Document**：正文 + metadata；metadata 要保留到引用。
- **加载**：按格式读取；编码/无文字层是常见失败。
- **切分**：chunk_size 控制成本与聚焦，overlap 缓解边界截断。
- **可追溯**：每个片段带 source/index，回答才能引用。
- **空片段**：不应进入索引；它会让召回和评测同时失真。

## 边界

- gate 只做 txt + 字符切分，不验证递归分隔符、PDF/Word/CSV。
- 通过 gate 不证明切分质量；切分好坏要用 2.7/2.9 的检索评测判断。
