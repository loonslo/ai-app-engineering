# P6 项目叙事与证据索引 · 项目章

[全书目录](../../README.md) · [上一章 P5](../11.5-demo-web-ui/README.md) · [篇首](../README.md) · [下一篇 J](../../part12-job-track/README.md)

- **目标**：把项目整理成招聘方看得懂、验证得了的作品叙事：作品 README、证据索引、决策索引、10 分钟演示稿、简历条目。
- **v3 路径**：P6 / 项目（清单验收）
- **岗位任务 / 面试题型**：T6 / F6
- **节奏**：4 小时，第 15–16 周；项目继续运行，不要为写叙事而停服务。
- **前置**：[11.1–11.5](../README.md)；证据类型见 [L0.2](../../part0-setup/0.2-learning-workflow/README.md)。

## 为什么

做完一个项目不等于别人知道你做了什么。招聘方没有时间读你的全部代码，他们要在几分钟内判断：这个人**真的做过、做到了什么程度、能不能讲清取舍**。叙事的任务是把可验证的证据摆在显眼的位置，而不是修辞。

## 招聘方看什么（行业经验，不是研究结论）

下面是内容创作者和招聘相关文章的观点，样本与方法都不清楚，只能当作经验参考，不要当成统计结论。读取日期 2026-10-31。

- 有文章主张，AI 作品集不需要十个项目，一个“已部署、有评测框架、并如实写出哪里坏过又怎样修好”的系统，胜过一堆教程克隆（[How to Build an Engineering Portfolio for AI Roles](https://zalt.me/blog/engineer-portfolio-for-ai-roles)，博客）；
- 同一作者的另一篇文章说，“聊天机器人封装”只能证明读过文档，带评测、护栏与成本上限的项目才证明工程能力（[AI Portfolio Projects That Actually Prove You Can Engineer](https://zalt.me/blog/2026/07/ai-portfolio-projects-that-prove-skill)，博客）；
- 另有招聘清单类文章强调团队想找的是能把 AI 系统从想法做到生产的人（[AI Engineer Skills in 2026](https://www.scaler.com/topics/ai-engineer-skills-2026-checklist-hiring-teams-want)，教育机构的内容页，带营销性质）。

把它们归纳成可检查的几项：真实上线、用量数字、事故、评测证据、取舍理由。

## 常见减分项

- 只有 notebook，没有可访问的服务；
- 没有用量数字，或数字对不上证据；
- 评测靠目测，没有 golden set、没有指标定义；
- 说不出出过什么事故、怎么处理的；
- “什么都用 LangChain”：说不出为什么需要它、它替你做了什么、不用会怎样。

## 每一个声明都要能对上代码或证据

- 作品 README 里的每个数字、每个能力描述，都在[证据索引](templates/evidence-index.md)里有一行：**声明 → 证据文件或命令 → 日期 → 类型**（离线 gate / 真实运行 / 部署）；
- 证据能打开、能复现；复现不了就降级成“历史记录”，或者删掉；
- 简历中不写代码不支持的说法。例如主链路仍有框架胶水时，不写“完全去框架”。

## 步骤

1. 先写[证据索引](templates/evidence-index.md)，再写作品 README——顺序不能反；
2. 按[作品 README 模板](templates/portfolio-readme.md)写：问题 → 架构 → 评测 → 事故 → 数字 → 下次会怎么改；
3. 汇总[决策索引](templates/decisions-index.md)，指向 `DECISIONS.md` 里的关键条目；
4. 写[10 分钟演示稿](templates/demo-script-10min.md)，并演练 2 次；
5. 按三类目标岗位写[简历条目](templates/resume-bullets.md)，数字只取自证据索引；
6. 自查：随机抽 5 条声明，按证据索引能否在 2 分钟内打开或复现。

## 模板

- [`templates/portfolio-readme.md`](templates/portfolio-readme.md)
- [`templates/decisions-index.md`](templates/decisions-index.md)
- [`templates/demo-script-10min.md`](templates/demo-script-10min.md)
- [`templates/evidence-index.md`](templates/evidence-index.md)
- [`templates/resume-bullets.md`](templates/resume-bullets.md)

## 产物与验收

见 [CHECKLIST](gate/CHECKLIST.md)。

## 常见失败

- 先写好听的 README，再回头找证据，找不到的就“合理推测”；
- 把离线 gate 的结果当成线上用量；
- 简历里的数字比证据索引里的大；
- 演示时才第一次打开页面，现场出错。

## 边界

- 这些模板不保证你拿到面试；招聘结果取决于大量不在本课程控制范围内的因素。
- 上面的“招聘方看什么”是公开文章里的观点，不同公司和岗位差异很大。
