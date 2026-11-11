# v2 路线移除收尾验证 · 2026-11-09

v2 路线移除的改动正文记的是 2026-11-08，上一会话落盘后中断（会话异常），本页记录收尾：删掉 v2 时代的文档与标签工具、清掉 ACL 异常目录和残留缓存，并在当前工作区复跑标签、断链、静态检查与测试。

## 范围

### 删除（30 个文件）

| 类别 | 文件 |
|---|---|
| v2 课程文档（9） | `docs/curriculum-v2.md`、`docs/course-v2-map.json`、`docs/course-v2-structure-validation.md`、`docs/course-book-validation.md`、`docs/course-book-v1-validation.md`、`docs/course-review-validation.md`、`docs/course-restructure-validation.md`、`docs/gate-rollout-plan.md`、`docs/gate-samples-validation.md` |
| v2 时代验证记录（20） | `docs/gate-b1-validation.md` 到 `docs/gate-b6i-validation.md` 共 20 个：b1、b2a、b2b、b3a、b3b、b4a、b4b、b4c、b4d、b5a、b5b、b6a–b6i |
| v2 标签工具（1） | `tools/apply_v2_map.py` |

### v2 改动涉及的文件（121 个）

下表只统计 v2 路线移除本身改的文件；`TASKS.md` 与 `PROJECT_STATUS.md` 的同步改动另计，所以 `git status` 里显示 123 个修改。

| 类别 | 数量 | 改动 |
|---|---|---|
| `chapters/**/README.md` | 83 | 删除 `- **v2 路径**：…` 行，其余头部字段不动 |
| `flagship-project/**/README.md` | 29 | 只删该行；冻结快照的其他内容不改 |
| `tools/apply_v3_map.py`、`tools/test_apply_v3_map.py` | 2 | 去掉“插到 v2 行下方”的分支，改为在第一个头部字段行之后插入；测试同步 |
| `README.md`、`chapters/README.md` | 2 | 去掉 v2 路线说明与“v2 路径速查”小节，运行环境说明改写 |
| `docs/curriculum-v3.md`、`docs/v3/README.md`、`docs/v3/conventions.md`、`docs/v3/review-checklist.md`、`docs/v3/specs/index-labels.md` | 5 | 命令表去掉 `apply_v2_map`，标注 v2 路线已移除 |
| `.github/workflows/eval-gate.yml` | 1 | 去掉 `apply_v2_map.py --check` 步骤 |

### 本次收尾额外处理

| 对象 | 处理 |
|---|---|
| `.pytest-tmp`、`.acl-recovery` | 上一会话删除被 ACL 拒绝；本次直接删除成功。`.pytest-tmp` 是空目录，`.acl-recovery` 里只有一份 ACL 诊断 jsonl |
| `pytest.ini` | 恢复 `addopts = --basetemp=.tmp/pytest`，重建 `.tmp/` |
| `chapters/part1-foundations/1.1-first-call/README.md` | 头部改为“标题、空行、`v3 路径` 行、空行、正文” |
| 29 个 `flagship-project/**/README.md` | 删掉 v2 行后留下的连续空行收敛成一行 |
| 14 个根目录 `pytest-cache-files-*` | 空目录，上一会话 pytest 在 basetemp 不可用时生成；本次删除 |
| `chapters/.wtest_backend`、根目录 `.cleanup_v2.py` | 空目录与一次性清理脚本，删除 |

### 一次性脚本的其余动作（脚本已删除）

- 清理 `__pycache__`、`.pyc`、章节内 `gate_report.json` 与 `chroma_db/`。
- 删除 `capstone/data/` 下被 `.gitignore` 忽略的运行产物：`failures.json`、`eval_report.md`、`metrics.db`、`memory.db`、`tenants/`。
- 删除 `.pytest_cache`、`.build`、`.tmp` 等缓存目录；`.pytest-tmp` 当时被 ACL 挡住没删掉，本次处理。

## 实际执行

环境：Windows，`.venv` 的 Python 3.14.4，`PYTHONUTF8=1`，工作区 `D:\workspace\ai-app-engineering`。

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python tools/apply_v3_map.py --check` | 119 个章节；inserted=0 updated=0 unchanged=119 待建=0 | 0 |
| `python tools/check_course_links.py` | 检查 462 个 Markdown 文件（含本页）；断链 0 | 0 |
| `python -m ruff check --target-version py311 capstone tools chapters/test_v3_lessons.py` | All checks passed | 0 |
| `python -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q` | 106 passed，1 warning（chromadb 的 `asyncio.iscoroutinefunction` DeprecationWarning），5.93s | 0 |
| `python -m capstone.project_baseline --json` | 全部条目 passed | 0 |
| `python -m capstone.milestones --strict-evidence` | 报 `MISSING capstone/data/failures.json` | 1 |

后两项不在本次要求里，但它们直接检查证据文件是否存在，删了文件要确认，所以一并跑了。

## 未验证与遗留

- `capstone.milestones --strict-evidence` 缺 `capstone/data/failures.json`。这个文件由 `python -m capstone.main eval` 生成、被 `.gitignore` 忽略，随本次清理一并删除；干净克隆里本来也没有。要恢复得跑一次真实评测，本次没有为此调用真实模型，也没有用占位文件冒充。
- 未在 CI 的 Python 3.11 上复跑。本机 `.venv` 是 3.14.4，执行的命令与 CI 一致。
- 未运行 gate 骨架与临时参考解。本次没有改 gate 逻辑。
- 未调用真实模型，未部署，未提交。
- 历史验证记录（`docs/gate-v3-*.md`、`docs/v3/reviews/*.md`、`docs/v3/specs/V3-0-infra.md`）里仍有 `apply_v2_map.py` 的命令行。那是当时的执行记录，不是现在能跑的命令；没有改写这些历史记录。
- 没有用日常库的同步工具校验 `PROJECT_STATUS.md`（本次未授权访问），只在本项目内逐项自检字段与证据路径。

## 复现方式

```powershell
cd D:\workspace\ai-app-engineering
$env:PYTHONUTF8 = '1'
.venv\Scripts\python.exe tools\apply_v3_map.py --check
.venv\Scripts\python.exe tools\check_course_links.py
.venv\Scripts\python.exe -m ruff check --target-version py311 capstone tools chapters/test_v3_lessons.py
.venv\Scripts\python.exe -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q
```

## 边界

- 30 个删除的文件仍在 git 历史里，未提交前可以用 `git restore` 取回。
- `.pytest-tmp` 与 `.acl-recovery` 是上一会话的沙箱 ACL 产物，不是课程资产；`.acl-recovery` 的诊断记录随目录删除，没有另存。
- 删除的是 v2 路线文档与标签，v3 的章节结构、正文和 gate 没有改动；README 里不再有 `v2 路径` 行。
- `flagship-project/` 仍是冻结快照，本次只删了 29 个 README 的 `v2 路径` 行和随之多出的空行。
- 本次只做离线检查与测试，不代表真实学习者完成、真实模型运行或生产环境验收通过。
