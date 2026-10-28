"""章节 2.13 · 静态上下文与 Agent Skills 渐进加载（原生实现）

==========================================================
为什么需要 Agent Skills 渐进披露？
1. 静态上下文（System Prompt、项目说明、工具说明、规则集）是所有请求的前置依赖；
2. 如果把所有工具的完整使用文档与代码说明全量塞入 System Prompt，将导致严重的“指令膨胀（Instruction Bloat）”：
   - 极度消耗上下文预算与首 Token 延迟；
   - 规则互相冲突，模型注意力稀释，指令遵循度下降；
3. 渐进披露（Progressive Disclosure）标准：
   - 启动时：仅在上下文加载 Skill 的元数据索引（name 与简短 description）；
   - 执行中：模型根据任务初筛或自主意图决定加载具体 Skill 时，才将对应 body 注入会话；
   - 本文基于 agentskills.io 开放标准构建，实现轻量解析、初筛、渐进加载与安全 Lint。

运行：python tools/run_chapter.py 2.13
==========================================================
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
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
    """按 agentskills.io 规范解析 SKILL.md。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillFormatError("SKILL.md 必须以 '---' 开头的 frontmatter 起始")

    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        raise SkillFormatError("SKILL.md frontmatter 缺少闭合 '---'")

    fm_kv: dict[str, str] = {}
    for line in lines[1:end_idx]:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if ":" not in s:
            continue
        k, v = s.split(":", 1)
        fm_kv[k.strip()] = v.strip()

    if "name" not in fm_kv:
        raise SkillFormatError("frontmatter 缺少必填字段 'name'")
    if "description" not in fm_kv:
        raise SkillFormatError("frontmatter 缺少必填字段 'description'")

    name = fm_kv["name"]
    description = fm_kv["description"]

    # 规范校验（agentskills.io 读取日期：2026-10-28）：1~64 字符，仅限小写字母、数字和连字符，不得以连字符起止，不得含连续连字符
    if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", name) or "--" in name or len(name) > 64:
        raise SkillFormatError(
            f"name 字段不符合规范（必须为 1~64 字符小写字母、数字或连字符，且不得以连字符起止、不得含连续连字符）：{name!r}"
        )

    # name 必须与所在目录名一致
    dir_name = Path(path).resolve().parent.name
    if dir_name != name:
        raise SkillFormatError(
            f"Skill name ({name!r}) 与所在目录名 ({dir_name!r}) 不一致"
        )

    if not (1 <= len(description) <= 1024):
        raise SkillFormatError("description 字段必须为 1~1024 字符的非空描述")

    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    return Skill(
        meta=SkillMeta(name=name, description=description, path=path),
        body=body,
    )


def build_index(
    skills: list[Skill],
    budget_tokens: int,
    count_tokens: Callable[[str], int],
) -> str:
    """构造渐进披露的 Skill 摘要索引。"""
    if not skills:
        return ""

    lines = [f"- {s.meta.name}: {s.meta.description}" for s in skills]
    full_text = "\n".join(lines)
    if count_tokens(full_text) <= budget_tokens:
        return full_text

    included: list[str] = []
    for i, line in enumerate(lines):
        cand = list(included) + [line]
        remain = len(lines) - len(cand)
        notice = f"\n（另有 {remain} 个 Skill 未列出）" if remain > 0 else ""
        cand_str = "\n".join(cand) + notice
        if count_tokens(cand_str) <= budget_tokens:
            included.append(line)
        else:
            break

    remain = len(lines) - len(included)
    notice = f"\n（另有 {remain} 个 Skill 未列出）" if remain > 0 else ""
    return "\n".join(included) + notice


def select_skills(
    task: str,
    skills: list[Skill],
    limit: int = 2,
) -> list[str]:
    """根据任务关键词匹配度进行初筛。"""
    task_tokens = set(
        re.findall(r"[a-zA-Z0-9_\-]+|[\u4e00-\u9fa5]", task.lower())
    )
    scored: list[tuple[int, int, str]] = []
    for idx, s in enumerate(skills):
        desc_tokens = set(
            re.findall(r"[a-zA-Z0-9_\-]+|[\u4e00-\u9fa5]", s.meta.description.lower())
        )
        overlap = len(task_tokens & desc_tokens)
        if overlap > 0:
            scored.append((-overlap, idx, s.meta.name))

    if not scored:
        return []
    scored.sort(key=lambda x: (x[0], x[1]))
    return [item[2] for item in scored[:limit]]


def load_skill(
    name: str,
    skills: dict[str, Skill],
    loaded: set[str],
) -> str:
    """渐进式单次加载 Skill 正文。"""
    if name not in skills:
        raise SkillNotFound(f"未找到 Skill: {name}")
    if name in loaded:
        return ""
    loaded.add(name)
    return skills[name].body


def lint_instructions(text: str, max_lines: int = 200) -> list[str]:
    """指令文件三重安全与质量 Lint 检查。"""
    lines = text.splitlines()
    warnings: list[str] = []
    if len(lines) > max_lines:
        warnings.append("too_long")

    seen_lines: set[str] = set()
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped:
            if stripped in seen_lines:
                warnings.append(f"duplicate_line:{idx}")
            else:
                seen_lines.add(stripped)
        if re.search(r"\b(sk-[a-zA-Z0-9_\-]{16,}|AKIA[0-9A-Z]{16,})\b", line):
            warnings.append(f"secret_like:{idx}")

    return warnings


def simple_token_counter(text: str) -> int:
    """简易确定性 token 估算：CJK 字符计 1，非 CJK 单词计 1。"""
    cjk = len(re.findall(r"[\u4e00-\u9fa5]", text))
    non_cjk = len(re.findall(r"[a-zA-Z0-9_\-]+", text))
    return cjk + non_cjk


if __name__ == "__main__":
    print("=== 2.13 静态上下文与 Agent Skills 渐进披露演示 ===")
    fixtures_dir = Path(__file__).resolve().parent / "gate" / "fixtures" / "skills"

    loaded_skills: list[Skill] = []
    for skill_name in ["pdf-reader", "data-cleaner", "security-audit"]:
        p = fixtures_dir / skill_name / "SKILL.md"
        if p.is_file():
            loaded_skills.append(parse_skill_md(p.read_text(encoding="utf-8"), str(p)))

    skills_dict = {s.meta.name: s for s in loaded_skills}
    print(f"成功加载并验证 {len(loaded_skills)} 个合规 Skill 模块。\n")

    # 1. 构建初始元数据索引
    index_str = build_index(loaded_skills, budget_tokens=500, count_tokens=simple_token_counter)
    print("【初始注入上下文：Skill 元数据索引】")
    print(index_str)

    # 2. Token 开销对比
    full_load_text = "\n\n".join(
        [f"=== Skill: {s.meta.name} ===\n{s.meta.description}\n{s.body}" for s in loaded_skills]
    )
    full_tokens = simple_token_counter(full_load_text)
    index_tokens = simple_token_counter(index_str)
    print(f"\n[Token 对比] 全量加载开销: ~{full_tokens} tokens vs 渐进索引开销: ~{index_tokens} tokens")
    print(f"首轮上下文节省比例：~{(1 - index_tokens / full_tokens) * 100:.1f}%\n")

    # 3. 按任务触发加载
    task = "Please parse this PDF and extract its text content."
    selected = select_skills(task, loaded_skills, limit=1)
    print(f"收到用户任务：'{task}'")
    print(f"初筛命中 Skill：{selected}")

    loaded_cache: set[str] = set()
    if selected:
        target = selected[0]
        body = load_skill(target, skills_dict, loaded_cache)
        print(f"渐进加载 [{target}] 正文（{simple_token_counter(body)} tokens）：")
        print(body.strip()[:100] + "...")

    # 4. 指令安全巡检演示
    dirty_instructions = (
        "# Project Instructions\n"
        "- Rule 1: Always check inputs.\n"
        "- Rule 2: Fail closed.\n"
        "- Rule 1: Always check inputs.\n"
        "BACKEND_API_KEY = 'sk-proj-99998888777766665555444433332222'\n"
    )
    warnings = lint_instructions(dirty_instructions, max_lines=100)
    print(f"\n巡检说明文件告警列表：{warnings}")
