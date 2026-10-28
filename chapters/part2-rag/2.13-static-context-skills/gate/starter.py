"""L2.9 静态上下文与 Skills · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
skills_loader.py。实现下面五个函数/接口，然后运行：

    python chapters/part2-rag/2.13-static-context-skills/gate/gate_check.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


class SkillFormatError(ValueError):
    """SKILL.md 格式不合规异常。"""


class SkillNotFound(KeyError):
    """请求未注册或不存在的 Skill 异常。"""


@dataclass(frozen=True)
class SkillMeta:
    name: str
    description: str
    path: str


@dataclass(frozen=True)
class Skill:
    meta: SkillMeta
    body: str


def parse_skill_md(text: str, path: str) -> Skill:
    """解析单个 SKILL.md 文件。

    规范约束（引用 agentskills.io 开放标准，读取日期：2026-10-28）：
    - 文件必须以 '---' 开头的 frontmatter 起始，以随后的 '---' 结束；
    - 仅使用标准库单行解析 'key: value'，不依赖 PyYAML；
    - name: 必填，1~64 字符，仅限小写英文字母、数字和连字符 '-'，且不能以连字符开头；
    - description: 必填，1~1024 字符的非空描述；
    - 格式不合法抛出 SkillFormatError，并在异常消息中说明具体原因；
    - frontmatter 结束行之后的剩余内容作为 Markdown 正文 (body)。
    """
    raise NotImplementedError("实现 SKILL.md 解析")


def build_index(
    skills: list[Skill],
    budget_tokens: int,
    count_tokens: Callable[[str], int],
) -> str:
    """构造渐进披露的 Skill 索引列表。

    每个 Skill 输出一行 "- <name>: <description>"。
    各行之间换行连接。
    如果整体输出超出 budget_tokens，按传入顺序截断，并在末尾追加 "（另有 N 个 Skill 未列出）"。
    如果预算连一条都无法容纳或为空，按边界安全处理。
    """
    raise NotImplementedError("实现索引构建")


def select_skills(
    task: str,
    skills: list[Skill],
    limit: int = 2,
) -> list[str]:
    """根据任务描述与 Skill 描述的关键词重合度进行初筛。

    提取 task 与 description 中的单词/分词集合，计算交集词数。
    按重合度降序排序，重合数相同时保持原传入顺序。
    返回前 limit 个技能的 name 列表；若无任何词重合则返回 []。
    """
    raise NotImplementedError("实现技能初筛")


def load_skill(
    name: str,
    skills: dict[str, Skill],
    loaded: set[str],
) -> str:
    """渐进加载技能正文。

    首次加载返回 Skill.body，并把 name 加入 loaded 集合；
    再次加载相同 name 返回空字符串 ""（避免重复占用上下文 Token）；
    如果 name 不在 skills 中，抛出 SkillNotFound。
    """
    raise NotImplementedError("实现技能渐进加载")


def lint_instructions(text: str, max_lines: int = 200) -> list[str]:
    """对 Agent 说明与指令文件进行静态安全与质量巡检。

    告警项（行号从 1 开始）：
    - 行数超过 max_lines 时记 "too_long"；
    - 完全相同的非空行重复出现时，在第二次及后续出现处记 "duplicate_line:<行号>"；
    - 发现形似密钥的字符串（如以 'sk-'、'AKIA' 开头且长度 >= 16 的 Token）记 "secret_like:<行号>"。
    """
    raise NotImplementedError("实现说明文件巡检")
