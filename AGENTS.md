# AGENTS.md

本仓库是面向测试工程师转向 AI 应用开发的中文章节练习与累积项目。课程范围、当前进度和运行说明以 `README.md` 和 `chapters/README.md` 为准；个人背景与目标见 `memory/`，任务状态见 `TASKS.md`。

## 代码边界

- `chapters/part1-foundations/` 起的章节目录保存可独立理解的练习；不要把历史练习无故改成统一框架。
- `flagship-project/` 已于 2026-10-27 冻结为基于 LangChain 1.x 的历史教学快照，不再修改；业务行为以 `capstone/` 为准，修改 capstone 时不再同步旗舰项目的验收证据。快照仍可用 `tools/materialize.py` 还原运行。
- `common.py` 保存共享模型和嵌入配置。模型密钥只从环境变量或本机 `.env` 读取，不写入代码、测试或提交文件。
- RAG 改动要分别检查数据来源、切分、召回、重排、上下文、生成和引用；多租户改动要验证权限边界。

## 常用入口

```text
python -m capstone.milestones --strict-evidence
python -m capstone.project_baseline --json
pytest capstone/test_regression.py -v
python tools/materialize.py flagship m8-evidence-final-frontend/step2
```

其他章节练习、服务、负载测试和微调命令见 `README.md` 与各目录说明。运行真实模型或外部服务前，确认依赖、密钥和数据范围；离线评估及回归测试优先使用可重复的测试替身。

## 修改与验证

- 先查看对应章节或里程碑的代码、现有测试和项目说明，再决定改动范围；保留历史练习的教学意图。
- 修改 `capstone/` 的主路径时，运行直接相关的回归测试；修改评估门槛时，同时核对评估集、指标口径与 CI 配置。
- 测试结果区分离线替身与真实模型运行；报告实际执行的命令及未验证的外部依赖。

## 文章与文档写作规范（随笔质感与图文排版）

- 撰写或审查任何中文文章、博客随笔、课程说明时，必须严格遵循 `tech-article-writing` 与 `de-ai-slop-review` skill 规范，以《调用大模型 API 时容易忽略的几个字段》为黄金标准范本。
- **文风标准**：平实、自然、素净的标准普通话随笔风格，不拿腔拿调，观点缓缓铺开，讲清事实。严禁大厂黑话（赋能/闭环/抓手/颗粒度等）、严禁做作假口语（玄乎/剥离/踩坑/随手处理等）、严禁机翻腔与立靶排比、严禁爹味说教与安慰剂总结。
- **代码规范**：代码必须包含清晰朴实的行内中文注释；代码下方必须有一小段文字务实解读“为什么这么写”、“返回值在下游怎么用”、“如何用来排查问题”。
- **配图规范**：克制配图，不为了增加图表而增加图表；卡片采用纯白底框（#ffffff）、极淡细边（#e2e8f0）与纯黑加粗标题（#0f172a），高对比度，局部点缀低饱和微色与朱砂红，杜绝外层深色笨重大底板，严格统一步调与字体栈。

## 本项目进度

实质性进展先写入 `TASKS.md` 和可定位的验证记录，再更新根目录 `PROJECT_STATUS.md`。课程目录存在和里程碑文件检查不代表本人学习完成或真实环境验收通过。项目只维护自己的任务与进度文件，不因状态变化写入其他项目。

## PROJECT_STATUS 同步契约（v1）

有实质进展时先更新项目内任务和验收记录，再更新根目录 `PROJECT_STATUS.md`；交付前校验以下格式。只维护本项目，不自动写入日常 vault，不把文件存在、格式通过或 Git 改动当作完成。

- 文件以 YAML frontmatter 开始，字段名不得重复；必填 `project_id`、`updated`、`status`、`overview`、`progress`、`next`、`evidence`。
- `project_id` 与登记的工作区相对路径一致，路径中的 `/` 替换为 `-`；本项目为 `ai-app-engineering`。
- `updated` 使用未加引号的真实 `YYYY-MM-DD` 日期，表示摘要维护日期；纯格式修订也可更新，但须在正文记录修订日期、原进展日期及未重新验收的边界。
- `status` 只允许 `active`（进行中）、`waiting`（等待输入）、`paused`（已延期）、`unknown`（待核实）；正在推进统一用 `active`，禁止 `in_progress`。它是项目跟进状态，不代表所有功能已经验收，也不使用 `done`。
- `overview`、`progress`、`next` 为非空字符串；复杂文字用 YAML 引号或块字符串。`progress` 区分实际通过、历史记录及尚未验收的事项。
- `evidence` 为非空字符串列表，只填项目内现存文件的相对路径，使用 `/`；禁止网址、描述文字、绝对路径、`.`/`..` 路径段、隐藏目录/文件、越界链接和 `PROJECT_STATUS.md` 自引用。不得读取或引用凭据、认证、运行目录；`runtime/`、`tmp/`、`temp/`、`logs/`、`storage/logs/` 下的文件不能作为 evidence 正本，核对过的结果应写入稳定任务/验收文档。
- URL、测试命令、结果、部署编号和说明写入项目内任务或验收文件，再由 `evidence` 引用该文件；注明实际验证日期、环境、结果及未验证项。迁移旧摘要文字时标为历史记录搬迁，不能冒充本次复测。
- 同步契约说明和模板位于日常库 `output/项目进展同步/README.md`、`PROJECT_STATUS.template.md`；本节保留完整字段规则，项目离开共同工作区后仍适用。跨项目访问须遵守既有项目边界；仅在用户本次明确授权访问日常同步工具且工具可用时，从共同工作区执行 `py -3.14 -B notebook_obsidian/日常/output/项目进展同步/sync_project_status.py --check --project ai-app-engineering`，只检查格式和证据路径，不读取或写入待办。

- 未使用同步工具时，仍须在本项目内逐项自检字段、状态与证据路径，并报告未通过项；不能跳过摘要维护。新建独立项目时先补齐本节约束和 PROJECT_STATUS.md，未知业务进度用 unknown，不因目录存在而推断完成。
