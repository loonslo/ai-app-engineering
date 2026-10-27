# v3 课程改造执行包

本目录把 [v3 提案](../curriculum-v3.md) 拆成可分工执行的任务：实施者按细则补内容，审核者按清单验收。章节、编号、目录、课时和批次以 [outline.md](outline.md) 为准。

## 1. 文件

| 文件 | 用途 | 读者 |
|---|---|---|
| [outline.md](outline.md) | 大纲：岗位任务、章节总表、就业出口标准、16 周排期 | 所有人 |
| [conventions.md](conventions.md) | 编写规范：目录、必备文件、README 模板、gate、依赖、验证命令、文风 | 实施者 |
| [review-checklist.md](review-checklist.md) | 审核清单与判定规则；实施者提交前先自检 | 实施者、审核者 |
| [specs/](specs/) | 章节细则，每个批次一份 | 实施者 |
| `reviews/` | 审核记录，由审核者创建 | 所有人 |

## 2. 角色

- **实施者**（其他 AI）：领取一个批次，按细则改写或新建章节，自检后提交。
- **审核者**（Claude）：按 [review-checklist.md](review-checklist.md) 逐项验收，结论写入 `reviews/<批次>.md`。
- **用户**：决定批次的合并顺序；已作出的决定记录在第 7 节。

## 3. 批次

| 批次 | 范围 | 细则 | 依赖 |
|---|---|---|---|
| V3-0 | 基础设施：原生模型工厂、依赖锁定、v3 映射与打标工具、v3 测试入口 | [specs/V3-0-infra.md](specs/V3-0-infra.md) | 无 |
| V3-1 | L0 + L1 | [specs/L0.md](specs/L0.md)、[specs/L1.md](specs/L1.md) | V3-0 |
| V3-2 | L2 | [specs/L2.md](specs/L2.md) | V3-0；L2.12 复用 V3-1 的 eval harness |
| V3-3 | L3 | [specs/L3.md](specs/L3.md) | V3-0 |
| V3-4 | L4-A | [specs/L4A.md](specs/L4A.md) | V3-1 |
| V3-5 | L4-B | [specs/L4B.md](specs/L4B.md) | V3-4 |
| V3-6 | L5 | [specs/L5.md](specs/L5.md) | V3-0；L5.7 参照 V3-5 的 L4.11 |
| V3-7 | P 项目主线（篇 11） | [specs/P.md](specs/P.md) | V3-0 |
| V3-8 | J 就业轨道（篇 12） | [specs/J.md](specs/J.md) | V3-0 |
| V3-9 | capstone：去掉 LCEL、接入 OTel、最小前端、简历措辞与代码对齐 | [specs/capstone.md](specs/capstone.md) | V3-2、V3-6 |
| V3-10 | v3 标签、章节索引、根目录 README | [specs/index-labels.md](specs/index-labels.md) | 其余批次 |

多个批次可以并行开发，但要逐个合并，避免 `TASKS.md`、`PROJECT_STATUS.md` 和 `tools/course_catalog.py` 冲突。

## 4. 每个批次的流程

1. 读本文件、[conventions.md](conventions.md)、对应细则，以及仓库根目录的 `AGENTS.md`。
2. 先读要改的现有章节（README、workbook、gate、参考实现），再动手；不凭空重写。
3. 按细则实现。gate 的临时参考解放在 `.tmp/gate_solutions/v3/<章节号>.py`，审核结束前不要删除。
4. 跑 [conventions.md 第 11 节](conventions.md#11-验证命令) 的全部命令，写验证记录 `docs/gate-v3-<批次号>-validation.md`（如 `docs/gate-v3-1-validation.md`）。
5. 按 `AGENTS.md` 更新 `TASKS.md` 与 `PROJECT_STATUS.md`。
6. 按第 5 节格式提交审核。结论分三种：通过 / 修改后通过 / 退回。

## 5. 提交审核的格式

```text
批次：V3-x
改动文件：新增 / 修改 / 删除，逐个列出
临时参考解：.tmp/gate_solutions/v3/……（每个 gate 一个）
命令与结果：conventions.md 第 11 节每条命令的输出摘要
细则偏离：没有写“无”；有则逐条写原因
未验证：真实模型、外部服务、部署等
```

## 6. 已定的默认决策

实施者不得自行更改。确需改动时，先在提交里写明理由，由审核者与用户决定。

1. **目录不改名**：新章节建新目录，编号见 outline.md；旧章节只改内容。
2. **默认实现**：`openai` SDK 走 OpenAI 兼容接口；模型 ID 从环境变量读取，不写死。
3. **核心 SDK**：Pydantic AI，版本在 V3-0 锁定。
4. **LangChain 边界**：只允许出现在 [conventions.md 第 7 节](conventions.md#7-langchain-使用边界) 列出的位置。
5. **标签**：内容批次不改任何 `v2 路径` 行；新章节直接写 `v3 路径` 行；旧章节的 v3 标签在 V3-10 统一添加，`v2 路径` 行保留（见第 7 节）。
6. **flagship-project 已冻结**：所有批次都不修改 `flagship-project/`（见第 7 节）。
7. **gate 与测试全部离线**：不调用真实模型，不联网。
8. **索引统一更新**：内容批次不改 `chapters/README.md` 与根目录 `README.md`，由 V3-10 统一更新。

## 7. 用户决定（2026-10-27）

1. **flagship-project 冻结**：作为基于 LangChain 1.x 的历史教学快照保留，不再更新。快照仍可还原运行，CI 继续跑 m1/step1 基线测试；项目实践以 capstone 与篇 11 为准。已同步：`flagship-project/README.md` 顶部的冻结说明、`AGENTS.md` 的代码边界约定、根目录 README 的课程表。
2. **新增 v3 路径行**：V3-10 打标签时，旧章节保留 `v2 路径` 行，在其下方新增 `v3 路径` 行；不实现替换。冻结的旗舰步骤不加 v3 标签。
   - 起初定的是“上方”。V3-0 复核时发现这与 `apply_v2_map.py` 冲突，改为“下方”，原因见 [reviews/V3-0.md](reviews/V3-0.md)。
