# V3-8 篇 12 就业轨道（J）验证 · 2026-10-31

本批次改了什么：新建篇 12（`chapters/part12-job-track/`）：篇首 README 与 7 个章节 12.1–12.7（README、`gate/CHECKLIST.md`、模板）；12.3 含带 3 个预埋 bug 的演练小服务与断言式检查脚本；12.5 含 3 份任务书、固定数据、3 个离线检查器与空实现起点。没改旧章节与 capstone。

实施线程额度用完，由审核者亲自实施并复跑，没有实施与审核的分离。

## 范围

| 编号 | 目录 | 文件 |
|---|---|---|
| 篇首 | `part12-job-track/` | `README.md`：7 章节奏、与 L0.5 的衔接、证据登记、信息会过期的说明 |
| J1 | `12.1-positioning-resume` | README、CHECKLIST、`positioning`、三版简历模板 |
| J2 | `12.2-public-portfolio-cadence` | README、CHECKLIST（14 周打卡表）、`weekly-update`、`eval-article-outline` |
| J3 | `12.3-coding-interview` | README、CHECKLIST、`dsa-tracker`、`ai-verification-log`、`drill/`（4 个模块 + `check_drill.py`） |
| J4 | `12.4-llm-system-design-mock` | README、`prompts.md`（5 题与追问）、CHECKLIST、`mock-record` |
| J5 | `12.5-take-home-sim` | README、`briefs/`（A、B、C）、`fixtures/`、`starters/`、`checkers/check_a|b|c.py`、`self-review`、CHECKLIST |
| J6 | `12.6-behavioral-stories` | README、CHECKLIST、`star-story`、`incident-story` |
| J7 | `12.7-applications-funnel` | README、CHECKLIST、6 个模板 |

另改 `tools/course_catalog.py`（登记 12.1–12.7）、`chapters/test_v3_lessons.py`（新增 4 项离线测试）。

临时参考解（不入库）：`.tmp/gate_solutions/v3/12.3-drill/`（修复版）、`12.5-a.py`、`12.5-b.py`、`12.5-c.py`。

## 外部出处核对（2026-10-31 读取）

| 内容 | 实际读到的 | 与细则的差异 |
|---|---|---|
| Meta AI-enabled coding | Hello Interview（辅导机构）：2025-10 起推出；可使用 AI 助手；多文件代码库、找 bug / 实现 / 优化三阶段；与一道不用 AI 的算法题并存；评价四项：问题解决、代码质量、验证、沟通 | 引文来自该文转述的 Meta 内部消息，未核对官方原文；已标注性质 |
| Google | Business Insider（2026-05）：据内部文件试点允许使用 AI 助手；2026-10 的后续报道只读到搜索摘要 | 细则写“在试点”，一致；后者标注“未读全文” |
| Amazon | Business Insider（2025-02）：内部指引称除非明确允许不得使用生成式 AI，否则可能被取消资格；发言人称在适用时候选人须确认不使用“未经授权的工具” | 细则写“要求书面承诺”；原文是“候选人须确认”，README 照原文 |
| 面试时长、算法轮难度、“AI 公司现场用 API 构建”、take-home 常见时长（4–8 小时、60–90 分钟） | **没有找到权威来源**（PracHub 指南明确说时长以任务书为准） | README 标“未核实”，没有写数字 |
| 评测讨论是否“多数候选人没准备” | 只找到一篇博客提出评测轮的观点，没有统计依据 | README 写成博客观点，不当结论 |
| 招聘市场数据（J1） | 沿用 L0.5 已核对的 365 Data Science、Axial Search（读取 2026-10-27） | 标注沿用与读取日期 |

## 实际执行

| # | 命令 | 结果 |
|---|---|---|
| 1 | `drill/check_drill.py`（原始代码） | 退出 1，失败 3 项（分页、时区、幂等），对照项通过 |
| 2 | `drill/check_drill.py --root .tmp/gate_solutions/v3/12.3-drill`（修复版） | 4/4 通过，退出 0 |
| 3 | `check_a|b|c.py`（`starters/` 空实现） | 均退出 1，0 项通过（6、6、7 项） |
| 4 | `check_a|b|c.py --module .tmp/gate_solutions/v3/12.5-<x>.py` | 6/6、6/6、7/7 通过，退出 0 |
| 5 | `tools/check_course_links.py` | 0 断链 |
| 6 | `apply_v3_map.py --check` | 12.1–12.7 均 unchanged；至此 v3 映射“待建”为 0 |
| 7 | `ruff check --target-version py311 chapters/part11-project-sprint chapters/part12-job-track tools chapters/test_v3_lessons.py` | 通过 |
| 8 | `pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py capstone/test_regression.py -q` | 114 passed（含新增的演练与空实现拒绝测试） |
| 9 | LangChain 导入检查 | part12 无命中 |

## 细则偏离

- J3 的演练修复版与 J5 的参考解放在 `.tmp/gate_solutions/v3/`，没有入库；因此 CI 里的测试只验证“预埋 bug 的演练在原始代码上失败（恰好 3 项）”和“空实现被三个检查器全部拒绝”，没有在 CI 里验证“修复后通过”（那一步只在本机用 `.tmp` 的修复版跑过）。
- J5 的 3 个检查器各自重复了一份很小的 Checker 骨架，没有抽成共享模块，目的是让学习者拿到单文件就能读懂。
- 细则 J3 要求“修复版放在 `.tmp/gate_solutions/v3/12.3-drill/`”：已照做。

## 未验证

- 没有任何真实学习者完成过这些演练或任务书；检查器的难度与区分度没有经过真实提交验证。
- 3 个检查器只覆盖固定用例；一份“通过检查器但质量很差”的实现是可能的，README 已说明。
- 面试形态、市场信息会过期；没有逐条核对 Google 的 2026-10 报道全文。
- 所有模板都没有被填写过；没有示例经历、示例公司名单或示例故事（刻意不提供）。
