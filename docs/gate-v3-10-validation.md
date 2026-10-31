# V3-10 标签、导航与总地图验证 · 2026-10-31

本批次改了什么：给旧章节补 v3 路径标签；按 v3 顺序重写主线章节的“上一章 / 下一章”；`chapters/README.md` 与根 `README.md` 改成 v3 入口；v3 提案标为已采纳，v2 提案标为已取代。没有改任何章节的代码或 gate。

实施线程额度用完，由审核者亲自实施，没有实施与审核的分离。

## 做了什么

| 任务 | 做法 | 结果 |
|---|---|---|
| 标签 | `python tools/apply_v3_map.py --apply` | 81 个旧章节 README 各插入一行 `v3 路径`；已有 38 个（新章节）不变；复查 `--check` 为 119 个全部 unchanged |
| 导航 | 一次性脚本（不提交）按 `docs/v3/outline.md` 第 4 节表格顺序，重写主线 88 个章节 README 的目录行；“阅读”行与选修章节不进顺序，保留原有的上一章/下一章 | 链接文字用 v3 编号（同一 v3 章节含多个目录时附章节号，如 `L2.2（2.1）`）；11.x、12.x 保留 `篇首` 链接；首章无“上一章”，12.7 无“下一章” |
| 总地图 | `chapters/README.md` 顶部新增“v3 路线速查”（由 outline.md 第 4 节表格生成，列：v3 编号、标题、章节、验收、课时）；旧速查改名“v2 路径速查（历史）”；各篇表格补入 37 个新章节，主线章节的标签换成 v3 编号，选修与阅读章节加 `v2` 前缀避免与 v3 编号混淆；新增第 11、12 篇；第 7 篇标注已冻结；“怎样运行”说明 11.x/12.x 多数没有脚本 | 见下 |
| 根 README | 标题改为“AI 应用与 Agent 开发学习手册”；课程结构表换成 v3（L0–L5、P、J、选修）；旧的“基于 langchain 1.x”定位换成“默认原生 SDK + Pydantic，LangGraph 用于状态图，LangChain 作为框架对照”，补 Pydantic AI 与 OpenTelemetry 依赖说明；旗舰项目单列为已冻结的历史快照 | 见下 |
| 提案状态 | `docs/curriculum-v3.md` 改为“已采纳（2026-10-31）”并写执行情况与未完成；`docs/curriculum-v2.md` 改为“已被 v3 取代” | 见下 |

没有触碰 `flagship-project/`。

## 验证（2026-10-31，Windows，`.venv`，离线）

| 命令 | 结果 |
|---|---|
| `python tools/apply_v3_map.py --check` | 119 个章节，inserted=0 updated=0 unchanged=119 待建=0 |
| `python tools/apply_v2_map.py --check` | 111 个 README，unchanged=111 |
| `python tools/check_course_links.py` | 484 个 Markdown 文件，断链 0 |
| `pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py capstone --deselect capstone/test_regression.py -q` | 151 passed |
| 限定范围 ruff（同 V3-9） | All checks passed |
| 导航链手动脚本检查：从 0.1 沿“下一章”走 | 88 步到 12.7，无重复、无环；每一对相邻章节的“上一章”与“下一章”互相指向对方 |

## 偏离与未验证

- 各篇表格里的“运行环境”列主要写于 v2 时期，没有逐章重核；已在“怎样运行”里加说明：v3 之后许多参考实现默认离线、`--live` 才调真实模型，以各章 README 为准。
- 选修与阅读章节保留旧的上一章/下一章，所以它们之间的相邻关系仍是 v2 顺序；这是有意的，选修不在主线顺序内。
- 链接文字的编号规则（v3 编号，必要时附章节号）是我定的，不来自 spec 原文。
- 未验证：真实学习者是否能按导航走完；`docs/v3/outline.md` 里的课时是建议值，不是实测。
- 一次性导航脚本没有提交；若今后调整 v3 顺序，需要重新生成导航并重跑上述检查。
