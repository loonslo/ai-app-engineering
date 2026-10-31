# J3 编码面试与 AI 辅助编码 · 就业章（含演练）

[全书目录](../../README.md) · [上一章 J2](../12.2-public-portfolio-cadence/README.md) · [篇首](../README.md) · [下一章 J4](../12.4-llm-system-design-mock/README.md)

- **目标**：了解 2026 年编码面试的几种形态；练习“用 AI 助手完成任务，并证明你验证过它”；目标含大厂时按计划练算法。
- **v3 路径**：J3 / 就业（演练测试）
- **岗位任务 / 面试题型**：T7 / F1、F2
- **节奏**：14 小时，第 3–14 周，每周 1–2 小时。
- **前置**：[L0.3 编码 Agent 工作流与审查](../../part0-setup/0.3-coding-agent-workflow/README.md)、L0.4 Python 工程底座。

## 编码面试的几种形态（2026-10-31 读取；以招聘方当次通知为准）

下面的信息来自媒体报道和面试辅导机构，**不是各公司的官方文件**，也不代表所有岗位；形态变化很快。

| 公司 / 情形 | 报道的内容 | 来源与性质 |
|---|---|---|
| Meta | 自 2025 年 10 月起推出“AI-enabled coding”面试：候选人可以使用 AI 助手，在一个多文件代码库里经历找 bug、实现、优化三个阶段；该轮与一道传统的（不用 AI 的）算法题并存。报道称其评价维度与传统编码面试相同的四项：问题解决、代码质量、验证、沟通 | Hello Interview（面试辅导机构）的整理，内含候选人转述（[链接](https://www.hellointerview.com/blog/meta-ai-enabled-coding)）；Meta 内部通知引文来自该文，我们没有核对官方原文 |
| Google | 据 Business Insider 对内部文件的报道，Google 在试点允许使用 AI 助手的软件工程师面试；10 月的后续报道称其中一轮是“代码理解”（阅读、调试、改进现有代码库） | 媒体报道，试点范围不明（[2026-05](https://www.businessinsider.com/google-job-interview-software-engineers-ai-assistant-coding-2026-5)、[2026-10](https://www.businessinsider.com/google-interview-process-ai-gemini-coding-comprehension-software-engineer-2026-10)；后者我们只读到搜索摘要，未读全文） |
| Amazon | 2025-02 的内部招聘指引：面试中除非明确允许，不得使用生成式 AI 工具，否则可能被取消资格；Amazon 发言人称在适用时，候选人须确认不会使用“未经授权的工具，如 GenAI” | Business Insider 对内部指引的报道（[链接](https://www.businessinsider.com/amazon-stop-people-using-ai-cheat-job-interviews-2025-2)，读取于 2026-10-31） |
| 大厂的传统算法轮 | 仍然存在；常见难度为 LeetCode 中等左右（这是行业常见说法，我们没有统计来源） | 未核实 |
| 其他公司 | 有的会让你现场用模型 API 构建一个小功能；这一说法我们没有找到统计来源 | 未核实 |

**怎么用这张表**：不要押注某一种形态。收到面试通知后，向招聘方确认三件事：这一轮能不能用 AI、能用哪些工具、评价标准是什么，然后按那一轮准备。

## 允许用 AI 的编码轮怎么评分

用上面 Meta 的例子，评价看的是四件事：

1. **解题**：能不能把问题拆开、选对方法、想到边界情况；
2. **代码质量**：代码是否清晰；更重要的是你是否**理解 AI 生成的内容**（该文提到有候选人因“明显依赖 AI、影响了方案质量”得到负面反馈）；
3. **验证**：是否频繁运行、检查 AI 的输出、测试边界；
4. **沟通**：是否边做边讲，解释你的决定和 AI 给的东西。

**测试背景的优势在“验证”。**你习惯问“怎么证明它是对的”：先复现、再改、再用用例证明。这一章的演练就练这个。

## 演练：带预埋 bug 的小服务

`drill/` 是一个多文件的小服务（工单路由，4 个模块），预埋了 **3 个 bug**：

- 分页的“差一”；
- 时区比较；
- 幂等判断写反。

`drill/check_drill.py` 是断言式检查脚本（不是 pytest 用例，不命名为 `test_*.py`）：**修复前失败 3 项，修复后全部通过。**

```bash
python chapters/part12-job-track/12.3-coding-interview/drill/check_drill.py
```

步骤：

1. 先**自己读一遍代码**（5 分钟），再跑检查脚本，看失败信息；
2. 用 AI 助手帮你定位和修复，**但每一条建议都要验证**：它说的 bug 是不是真的？改法会不会引入新问题？
3. 在[验证记录](templates/ai-verification-log.md)里写：AI 给了什么建议、哪里不对、怎样验证、最终改法；
4. 修复后检查脚本全部通过；再想想还有没有检查脚本没覆盖的边界。

不要把 `drill/` 的修复版当答案去找；预埋 bug 的位置也不会写在本页，因为演练的价值就是自己发现。

## 算法练习计划（只在目标含大厂时重点投入）

主题：数组与哈希、双指针、栈与队列、二分、树与图的 BFS / DFS、堆、区间、基础动态规划；用 Python。

- 每个主题先独立做 3–5 题，再用 AI 做一次对照复盘；
- 用[追踪表](templates/dsa-tracker.md)记录：题目、类型、用时、是否独立完成、复盘；
- 如果目标不含大厂，这一部分只保持手感，不要挤占 J4、J5 的时间。

## 模板

- [`templates/dsa-tracker.md`](templates/dsa-tracker.md)
- [`templates/ai-verification-log.md`](templates/ai-verification-log.md)

## 产物与验收

见 [CHECKLIST](gate/CHECKLIST.md)。

## 常见失败

- 先让 AI 找 bug，自己没读代码，结果被 AI 的错误诊断带偏；
- 把 AI 的修改整段粘贴进去，说不出每一行为什么这样改；
- 只修让检查脚本通过的那一处，不想想同类问题；
- 算法只刷不复盘，同一类错误反复出。

## 边界

- 本章只训练“读代码、定位、验证”，不能替代真实面试环境（计时、沟通、陌生平台）。
- 面试形态的信息来自媒体与辅导机构，可能已经变化；请以招聘方通知为准。
- 演练检查脚本只覆盖 3 个预埋 bug 与一项对照检查，不证明你的修复在所有输入上正确。
