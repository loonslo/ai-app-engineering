# V3-10 标签与索引细则

> 2026-11-08 说明：v2 路线与 v2 标签已整体移除；本细则记录 V3-10 当时的做法，涉及 `tools/apply_v2_map.py` 与 `v2 路径` 的步骤不再适用。

目标：所有内容批次合并后，统一添加 v3 标签、更新章节总地图与根目录 README，使学习者从入口就能按 v3 路线学习。

前置：V3-0 至 V3-9 全部合并。用户的决定见 [README 第 7 节](../README.md#7-用户决定2026-10-27)：保留 v2 行并新增 v3 行；flagship-project 冻结。

## 任务 1：打标签

- 运行 `python tools/apply_v3_map.py --check`，确认只剩旧章节缺少 v3 行，且没有“待建”目录。
- 执行 `python tools/apply_v3_map.py --apply`：v3 行插在 v2 行下方，v2 行保持原样。不实现替换选项。
- 冻结的 `flagship-project/` 各步骤不加 v3 标签；它的 README 顶部已有冻结说明。
- 再次运行 `--check`，应无改动（幂等）；`python tools/apply_v2_map.py --check` 仍应无变化。

## 任务 2：导航链接

- 按 v3 顺序重写各章 README 的“上一章 / 下一章”链接，包括旧章节。
- 可以写一次性脚本放在 `.tmp/` 中生成；只提交结果。
- 改动的 README 数量多时，分两次提交（L0–L3、L4 及以后），每次都跑断链检查。

## 任务 3：章节总地图 `chapters/README.md`

- 在最前面新增“v3 路线速查”：按 L0–L5、P、J 列出 v3 编号、标题、目录链接、验收方式、课时，内容与 [outline.md](../outline.md) 第 4 节一致。
- 新增篇 11、篇 12 的章节表。
- 原有“v2 路径速查”保留，改标题为“v2 路径速查（历史）”，并说明各章 README 中两种标签并存。
- 第 7 篇（旗舰项目）的条目标注“已冻结，历史快照”。
- “怎样运行”一节补充 `tools/run_chapter.py` 对 11.x、12.x 章节的说明（这两篇的章节多数没有脚本）。

## 任务 4：根目录 `README.md`

- 标题改为“AI 应用与 Agent 开发学习手册”（仓库目录名与 project_id 不变）。
- “课程结构”表改为 v3：L0–L5、P、J，以及选修；指向 `docs/v3/outline.md` 与 `chapters/README.md`。第 7 篇旗舰项目移到表外，单列一行“历史教学快照（已冻结）”。
- 删除“本仓库基于 langchain 1.x”的定位表述，改为“默认使用原生 SDK + Pydantic；LangGraph 用于状态图，LangChain 作为框架对照”。
- 环境准备补充 Pydantic AI 与 OpenTelemetry 的依赖说明。

## 任务 5：提案状态

- `docs/curriculum-v3.md` 顶部状态改为“已采纳（日期）”，并写明执行情况与未完成项。
- `docs/curriculum-v2.md` 顶部注明“已被 v3 取代（日期）”。

## 验收

```bash
python tools/apply_v3_map.py --check        # 无改动
python tools/apply_v2_map.py --check        # 仍无变化（v2 行保留）
python tools/check_course_links.py          # 全仓库断链 0
python -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
```

- 人工抽查：从根目录 README 出发，能按 v3 顺序走完 L0.1 → J7 的导航链接。
- 验证记录：`docs/gate-v3-10-validation.md`。

## 审核重点

- 总地图与 outline.md 逐条一致。
- 导航链接没有断点或循环。
- 措辞与“已采纳”状态一致，没有夸大完成度（例如真实学习与真实部署仍未验证时，要如实写明）。
