"""L2.9 静态上下文与 Skills · 离线 gate 验收。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES_DIR = HERE / "fixtures" / "skills"


def load_module(path: Path):
    if not path.exists():
        raise SystemExit(f"找不到实现文件：{path}")
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("candidate_l29_skills", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_l29_skills"] = module
    spec.loader.exec_module(module)
    return module


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class Gate:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, module_path: Path) -> int:
        passed = sum(row["ok"] for row in self.rows)
        total = len(self.rows)
        for row in self.rows:
            mark = "PASS" if row["ok"] else "FAIL"
            print(f"[{mark}] {row['name']}" + ("" if row["ok"] else f"  <- {row['error']}"))
        print(f"\n{passed}/{total} passed")
        if passed != total:
            print("gate 未通过：先修 FAIL 项，不要打开参考实现。")
        out = {
            "gate": "L2.9-static-context-skills",
            "module": str(module_path),
            "passed": passed,
            "total": total,
            "ok": passed == total,
            "checks": self.rows,
        }
        (HERE / "gate_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if passed == total else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default=str(HERE / "starter.py"))
    args = parser.parse_args()
    module_path = Path(args.module).resolve()
    core = load_module(module_path)
    gate = Gate()

    def test_parse_valid():
        for skill_dir in ["pdf-reader", "data-cleaner", "security-audit"]:
            p = FIXTURES_DIR / skill_dir / "SKILL.md"
            text = p.read_text(encoding="utf-8")
            skill = core.parse_skill_md(text, str(p))
            expect(skill.meta.name == skill_dir, f"name 不对：{skill.meta.name}")
            expect(len(skill.meta.description) > 0, f"description 为空：{skill_dir}")
            expect(len(skill.body) > 0, f"body 缺少正文：{skill_dir}")
            expect("---" not in skill.body, "body 不应包含 frontmatter 分界线")

    def test_parse_missing_frontmatter():
        p = FIXTURES_DIR / "missing-frontmatter" / "SKILL.md"
        text = p.read_text(encoding="utf-8")
        try:
            core.parse_skill_md(text, str(p))
        except core.SkillFormatError:
            return
        raise AssertionError("缺少 frontmatter 应抛 SkillFormatError")

    def test_parse_missing_name():
        bad_text = "---\ndescription: Only description without name\n---\nBody here."
        try:
            core.parse_skill_md(bad_text, str(FIXTURES_DIR / "dummy" / "SKILL.md"))
        except core.SkillFormatError:
            return
        raise AssertionError("缺少 name 应抛 SkillFormatError")

    def test_parse_invalid_name():
        # 1. 大写与特殊字符
        p = FIXTURES_DIR / "invalid-name" / "SKILL.md"
        text = p.read_text(encoding="utf-8")
        try:
            core.parse_skill_md(text, str(p))
            raise AssertionError("非法 name (大写/特殊字符) 应抛 SkillFormatError")
        except core.SkillFormatError:
            pass

        # 2. 以连字符结尾 (如 pdf-)
        bad_trailing = "---\nname: pdf-\ndescription: trailing hyphen test\n---\nBody"
        try:
            core.parse_skill_md(bad_trailing, str(FIXTURES_DIR / "pdf-" / "SKILL.md"))
            raise AssertionError("以连字符结尾的 name 应抛 SkillFormatError")
        except core.SkillFormatError:
            pass

        # 3. 包含连续连字符 (如 pdf--reader)
        bad_consecutive = "---\nname: pdf--reader\ndescription: consecutive hyphen test\n---\nBody"
        try:
            core.parse_skill_md(bad_consecutive, str(FIXTURES_DIR / "pdf--reader" / "SKILL.md"))
            raise AssertionError("含连续连字符的 name 应抛 SkillFormatError")
        except core.SkillFormatError:
            pass

        # 4. name 与所在目录名不一致
        mismatch_path = FIXTURES_DIR / "data-cleaner" / "SKILL.md"
        valid_yaml_wrong_dir = "---\nname: pdf-reader\ndescription: valid name but wrong dir\n---\nBody"
        try:
            core.parse_skill_md(valid_yaml_wrong_dir, str(mismatch_path))
            raise AssertionError("name 与目录名不符应抛 SkillFormatError")
        except core.SkillFormatError:
            pass

    def test_build_index_basic():
        skills = [
            core.Skill(core.SkillMeta("pdf-reader", "Extract text from PDF", "p1"), "body1"),
            core.Skill(core.SkillMeta("data-cleaner", "Clean CSV tables", "p2"), "body2"),
        ]
        idx = core.build_index(skills, budget_tokens=500, count_tokens=lambda s: len(s.split()))
        expect("- pdf-reader: Extract text from PDF" in idx, f"索引格式不对：{idx}")
        expect("- data-cleaner: Clean CSV tables" in idx, f"缺少第二个技能：{idx}")
        expect("body1" not in idx and "body2" not in idx, "索引绝不能泄露正文 body")

    def test_build_index_truncation():
        skills = [
            core.Skill(core.SkillMeta("s1", "description one", "p1"), "b1"),
            core.Skill(core.SkillMeta("s2", "description two", "p2"), "b2"),
            core.Skill(core.SkillMeta("s3", "description three", "p3"), "b3"),
        ]
        # budget 限制为仅能容纳第一条加截断提示
        idx = core.build_index(skills, budget_tokens=10, count_tokens=lambda s: len(s.split()))
        expect("（另有" in idx and "未列出）" in idx, f"超出预算应有截断提示：{idx}")
        expect("- s1:" in idx, "第一条应保留")
        expect("- s3:" not in idx, "超出预算的条目应被截断")

    def test_select_skills_ranking():
        skills = [
            core.Skill(core.SkillMeta("pdf-tool", "extract and parse pdf document files", "p1"), "b1"),
            core.Skill(core.SkillMeta("csv-tool", "clean and filter csv tabular data", "p2"), "b2"),
            core.Skill(core.SkillMeta("audit-tool", "audit security credentials", "p3"), "b3"),
        ]
        task = "I need to parse and extract text from this document and data"
        selected = core.select_skills(task, skills, limit=2)
        expect(len(selected) == 2, f"应按重合度命中 2 个技能：{selected}")
        expect(selected[0] == "pdf-tool", f"重合度最高的应排第1：{selected}")
        expect(selected[1] == "csv-tool", f"重合度次高的应排第2：{selected}")

    def test_select_skills_no_overlap():
        skills = [
            core.Skill(core.SkillMeta("s1", "alpha beta gamma", "p1"), "b1"),
        ]
        task = "quantum physics entanglement"
        selected = core.select_skills(task, skills, limit=2)
        expect(selected == [], f"无重合词应返回空列表：{selected}")

    def test_load_skill_progressive():
        skills_map = {
            "pdf-reader": core.Skill(core.SkillMeta("pdf-reader", "desc", "p"), "Full body instructions"),
        }
        loaded = set()
        # 首次加载
        body1 = core.load_skill("pdf-reader", skills_map, loaded)
        expect(body1 == "Full body instructions", f"首次加载应返回正文：{body1}")
        expect("pdf-reader" in loaded, "加载后应加入 loaded 集合")

        # 重复加载
        body2 = core.load_skill("pdf-reader", skills_map, loaded)
        expect(body2 == "", f"再次加载应返回空串：{body2}")

    def test_load_skill_missing():
        try:
            core.load_skill("unknown-tool", {}, set())
        except core.SkillNotFound:
            return
        raise AssertionError("未知 skill 应抛 SkillNotFound")

    def test_lint_instructions_checks():
        # 1. 超过 max_lines
        long_text = "\n".join([f"line {i}" for i in range(10)])
        warnings_long = core.lint_instructions(long_text, max_lines=5)
        expect("too_long" in warnings_long, f"行数超限未报警：{warnings_long}")

        # 2. 重复行与疑似密钥
        sample = (
            "Rule 1: Always verify.\n"
            "Rule 2: Don't bypass.\n"
            "Rule 1: Always verify.\n"
            "api_key = 'sk-proj-1234567890abcdef1234'\n"
        )
        warnings = core.lint_instructions(sample, max_lines=20)
        expect("duplicate_line:3" in warnings, f"重复行未检出：{warnings}")
        expect("secret_like:4" in warnings, f"疑似密钥未检出：{warnings}")

    gate.check("01 合法 SKILL.md 解析", test_parse_valid)
    gate.check("02 缺少 frontmatter", test_parse_missing_frontmatter)
    gate.check("03 缺少 name 字段", test_parse_missing_name)
    gate.check("04 字段不符合约束", test_parse_invalid_name)
    gate.check("05 索引仅含 name 与 description", test_build_index_basic)
    gate.check("06 超预算截断提示", test_build_index_truncation)
    gate.check("07 选择初筛排序与截断", test_select_skills_ranking)
    gate.check("08 无重合词返回空列表", test_select_skills_no_overlap)
    gate.check("09 首次加载与重复加载防重", test_load_skill_progressive)
    gate.check("10 未知技能抛 SkillNotFound", test_load_skill_missing)
    gate.check("11 指令文件三重 Lint 告警", test_lint_instructions_checks)
    return gate.report(module_path)


if __name__ == "__main__":
    raise SystemExit(main())
