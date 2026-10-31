"""旗舰项目各步骤（FLAGSHIP_STEPS）的任务契约：声明目标、实现、失败测试和验收证据，并检查证据文件是否存在。"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from tools.course_catalog import FLAGSHIP_STEPS, step_label

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ProjectTask:
    step: str
    title: str
    user_story: str
    principle: str
    implementation: tuple[str, ...]
    failure_tests: tuple[str, ...]
    evidence: tuple[str, ...]
    acceptance: tuple[str, ...]
    boundary: str
    prerequisites: tuple[str, ...] = ()
    concepts: tuple[str, ...] = ()
    code_walkthrough: tuple[str, ...] = ()
    lab_steps: tuple[str, ...] = ()
    expected_results: tuple[str, ...] = ()
    common_mistakes: tuple[str, ...] = ()
    review_questions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.step not in FLAGSHIP_STEPS:
            raise ValueError("请选择 FLAGSHIP_STEPS 中的项目步骤")
        for name in (
            "implementation",
            "failure_tests",
            "evidence",
            "acceptance",
            "prerequisites",
            "concepts",
            "code_walkthrough",
            "lab_steps",
            "expected_results",
            "common_mistakes",
            "review_questions",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} 不能为空")


def task_status(task: ProjectTask) -> dict[str, object]:
    evidence_status = {
        path: (ROOT / path.rstrip("/")).exists() for path in task.evidence
    }
    return {**asdict(task), "evidence_status": evidence_status}


def render_markdown(task: ProjectTask) -> str:
    """生成可直接浏览的各步骤教程；路径均相对仓库根目录。"""

    def section(title: str, items: tuple[str, ...], *, ordered: bool = False):
        lines = [f"## {title}", ""]
        for index, item in enumerate(items, 1):
            prefix = f"{index}." if ordered else "-"
            lines.append(f"{prefix} {item}")
        lines.append("")
        return lines

    target = task.step
    lines = [
        f"# {step_label(task.step)} · {task.title}",
        "",
        f"> 用户故事：{task.user_story}",
        ">",
        f"> 第一性原则：{task.principle}",
        "",
        "## 从哪里开始",
        "",
        "所有路径都相对于仓库根目录，所有命令都从这里运行：",
        "",
        "```powershell",
        r"cd D:\workspace\ai-app-engineering",
        f"python tools/materialize.py flagship {target} --diff",
        "```",
        "",
        "先运行上面的命令看完整任务，再按照下文给出的文件和函数顺序操作。",
        "当前仓库保存完成版实现；学习时先根据步骤自己解释或重写目标函数、补失败测试，",
        "卡住后再把现有实现当参考答案，不要只把文件从头读到尾。",
        "",
    ]
    lines += section("开始前你要知道", task.prerequisites)
    lines += section("本节学完你能做到", task.implementation, ordered=True)
    lines += section("概念先翻译成人话", task.concepts)
    lines += [
        "## 本节代码到底在哪里",
        "",
        "下面不是泛泛的“阅读文档”，而是本节的代码导航顺序。用 IDE 按路径打开，",
        "搜索给出的类、函数或字段；读完一项再进入下一项。",
        "",
    ]
    for index, item in enumerate(task.code_walkthrough, 1):
        lines.append(f"{index}. {item}")
    lines.append("")
    lines += section("跟着做", task.lab_steps, ordered=True)
    lines += section("做对后应该看到", task.expected_results)
    lines += section("必须理解的失败测试", task.failure_tests, ordered=True)
    lines += ["## 本步骤产物在哪里", ""]
    for path in task.evidence:
        link = path.replace("\\", "/")
        lines.append(f"- [`{path}`](../{link})")
    lines += ["", "## 完成验收", ""]
    for command in task.acceptance:
        lines += ["```powershell", command, "```", ""]
    lines += [
        "最后检查本步骤依赖的证据文件：",
        "",
        "```powershell",
        f"python -m capstone.milestones {target} --strict-evidence",
        "```",
        "",
    ]
    lines += section("初学者最容易踩的坑", task.common_mistakes)
    lines += section("完成后请自己回答", task.review_questions, ordered=True)
    lines += ["## 本节不能夸大的边界", "", task.boundary, ""]
    return "\n".join(lines)


def run_task(task: ProjectTask, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=f"{step_label(task.step)} {task.title}"
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="本步骤证据缺失时返回非零退出码",
    )
    args = parser.parse_args(argv)
    payload = task_status(task)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{step_label(task.step)} · {task.title}")
        print(f"\n用户故事：{task.user_story}")
        print(f"第一性原则：{task.principle}")
        print("\n开始前你要知道：")
        for item in task.prerequisites:
            print(f"  - {item}")
        print("\n本节学完你能做到：")
        for index, item in enumerate(task.implementation, 1):
            print(f"  {index}. {item}")
        print("\n概念先翻译成人话：")
        for item in task.concepts:
            print(f"  - {item}")
        print("\n按这个顺序读代码：")
        for index, item in enumerate(task.code_walkthrough, 1):
            print(f"  {index}. {item}")
        print("\n跟着做：")
        for index, item in enumerate(task.lab_steps, 1):
            print(f"  {index}. {item}")
        print("\n做对后应该看到：")
        for item in task.expected_results:
            print(f"  - {item}")
        print("\n必须写的失败测试：")
        for index, item in enumerate(task.failure_tests, 1):
            print(f"  {index}. {item}")
        print("\n证据：")
        evidence_status = payload["evidence_status"]
        assert isinstance(evidence_status, dict)
        for path, exists in evidence_status.items():
            print(f"  {'OK' if exists else 'MISSING'} {path}")
        print("\n完成验收：")
        for command in task.acceptance:
            print(f"  {command}")
        print("\n初学者最容易踩的坑：")
        for item in task.common_mistakes:
            print(f"  - {item}")
        print("\n完成后请自己回答：")
        for index, item in enumerate(task.review_questions, 1):
            print(f"  {index}. {item}")
        print(f"\n本节不能夸大的边界：{task.boundary}")
    missing = [
        path for path, exists in payload["evidence_status"].items() if not exists
    ]
    return 1 if args.strict and missing else 0
