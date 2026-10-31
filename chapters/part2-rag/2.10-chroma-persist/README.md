# L2.7 向量库持久化 · Gate（原 2.10）

[全书目录](../../README.md) · [上一章 L2.7](../2.9-query-rewrite/README.md) · [下一章 L2.9](../2.13-static-context-skills/README.md)

- **能力**：把向量记录写入 JSON、落盘、重新加载；校验重复 ID/维度/坏文件。
- **v2 路径**：L2.7 / 核心（Gate；持久化）
- **v3 路径**：L2.8 / 核心（Gate；持久化与增量）
- **前置**：2.2（向量与索引）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `chroma_persist.py`。
- **验收命令**：

```bash
python chapters/part2-rag/2.10-chroma-persist/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

持久化不是“把内存对象 dump 成 JSON”这么简单：

- 文件不存在/损坏时，服务要能明确报错；
- ID 重复会覆盖旧记录；
- 维度不一致会让查询崩；
- 加载后 metadata 丢失，引用就断了；
- 写入时持有外部列表引用，后续修改污染索引。

这个 gate 用临时 JSON 文件做落盘/加载往返，不依赖 Chroma。

## 任务

实现 `gate/starter.py` 的 `PersistentVectorStore`：

| 方法 | 你要交付的行为 |
|---|---|
| `add` | 校验长度/ID/维度/metadata；保存副本 |
| `search` | 余弦排序 top-k；空库 `[]`；维度/k 错误报 `StoreError` |
| `save` | 写 UTF-8 JSON；失败报 `StoreError` |
| `load` | 读 JSON；缺文件/坏 JSON/缺字段/重复 ID 报 `StoreError` |

关键口径：

- `metadata` 缺省为等长空 dict；长度必须一致。
- ID 非空且不重复；向量维度一致。
- `k < 1`、查询维度不一致 -> `StoreError`。
- 内部保存 `vector`/`metadata` 副本，不持有外部引用。
- JSON 至少包含 `id/vector/metadata`。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 保存后重新加载 | 排序与 metadata 一致 |
| 2 | 文件不存在 | `StoreError` |
| 3 | 坏 JSON | `StoreError` |
| 4 | 重复 ID | `StoreError` |
| 5 | 维度不一致 | `StoreError` |
| 6 | metadata 长度不一致 | `StoreError` |
| 7 | `k=0` | `StoreError` |
| 8 | 外部修改传入向量/metadata | 索引不变 |

## 验收标准

`gate_check.py` 的 9 项全部 PASS：

- 写入/检索、保存/加载往返、缺文件、坏 JSON、重复 ID、维度/metadata、空库/k、查询维度、外部引用。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么加载时要重新校验 ID/维度，而不是直接信任文件？
2. 文档更新后，旧库怎么失效？确定性 ID 和源文件删除如何协同？
3. JSON 持久化和生产级 Chroma 持久化的差别是什么？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（9/9）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python tools/run_chapter.py 2.10
```

对照时只回答：

1. 原生参考实现用 `chromadb.PersistentClient` 结合确定性 sha256 ID；重复写入相同文档时为什么不会增加记录总数？
2. 当源文档内容发生修改时，参考实现是如何实现“清理旧版本片段并写入新版本”的？
3. 原生 Chroma 的 `collection.query` 是如何利用元数据过滤（`where={"category": "refund"}`）缩小检索范围的？

## 概念地图

- **持久化**：把向量、ID、metadata 落盘；下次加载不再重新 embedding。
- **加载校验**：文件可能损坏/过期；ID/维度/字段必须重新校验。
- **失效**：文档/切分参数变化后，旧库不能自动更新；需要版本或重建。
- **副本**：内部保存副本，避免外部引用污染。
- **选型**：JSON 适合教学/小规模；Chroma/FAISS/pgvector 各有适用边界。
- **确定性 ID 与幂等同步**：使用 `sha256(source + index + text)`，重复写入自动幂等，防止脏数据累积。
- **增量同步与失效**：源文件更新时通过元数据删除历史片段，再做 upsert。
- **元数据过滤**：在向量检索前/时附加标量条件过滤（Pre-filtering），提升检索准确率与安全性。

## 边界

- gate 用临时 JSON 文件验证持久化契约，不引入第三方向量数据库依赖；不验证真实向量库性能/并发。
- 通过 gate 只证明落盘/加载/校验结构正确。
- 生产级持久化客户端、确定性哈希 ID 生成与元数据过滤演示见参考实现。
- 增量更新、版本失效、并发写入在 gate 中未做完整验证。
