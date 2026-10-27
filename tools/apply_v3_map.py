"""把 v3 路径标签写入章节 README。

映射源：docs/course-v3-map.json
用法：
    python tools/apply_v3_map.py --check
    python tools/apply_v3_map.py --apply

只做一件事：在每章 README 的头部插入或更新：
`- **v3 路径**：<stage> / <role>（<note>）`。
插入规则：
- 已有 v3 路径行时原地替换；
- 否则若有 v2 路径行，插在它的上一行；
- 两者都没有时，插在第一个头部字段行（- **能力** 或 - **目标**）之后。
永远保留 v2 路径行；不处理 flagship-project/（已冻结）；
映射中存在但尚未创建目录的章节输出为“待建”，不视为错误。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = ROOT / "docs" / "course-v3-map.json"


def load_map(map_path: Path = MAP_PATH) -> dict[str, dict]:
    return json.loads(map_path.read_text(encoding="utf-8"))


def render(meta: dict) -> str:
    stage = meta["stage"]
    role = meta["role"]
    note = meta.get("note", "").strip()
    tail = f"（{note}）" if note else ""
    return f"- **v3 路径**：{stage} / {role}{tail}"


def chapter_readme(chapter_id: str, root: Path = ROOT) -> Path | None:
    matches = list((root / "chapters").glob(f"part*/{chapter_id}-*/README.md"))
    return matches[0] if len(matches) == 1 else None


def upsert(path: Path, line: str, apply: bool) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    v3_idx = next(
        (i for i, line_text in enumerate(lines) if "**v3 路径**" in line_text),
        None,
    )
    if v3_idx is not None:
        if lines[v3_idx] == line:
            return "unchanged"
        updated = list(lines)
        updated[v3_idx] = line
        status = "updated"
    else:
        v2_idx = next(
            (i for i, line_text in enumerate(lines) if "**v2 路径**" in line_text),
            None,
        )
        if v2_idx is not None:
            updated = lines[:v2_idx] + [line] + lines[v2_idx:]
        else:
            header_idx = next(
                (
                    i
                    for i, line_text in enumerate(lines)
                    if line_text.startswith(("- **能力**", "- **目标**"))
                ),
                None,
            )
            if header_idx is not None:
                updated = (
                    lines[: header_idx + 1] + [line] + lines[header_idx + 1 :]
                )
            else:
                bullet_at = next(
                    (
                        i
                        for i, line_text in enumerate(lines)
                        if line_text.startswith("- **")
                    ),
                    None,
                )
                if bullet_at is not None:
                    updated = (
                        lines[: bullet_at + 1] + [line] + lines[bullet_at + 1 :]
                    )
                else:
                    nav_at = next(
                        (
                            i
                            for i, line_text in enumerate(lines)
                            if line_text.startswith(
                                ("[全书目录]", "[项目目录]", "[返回")
                            )
                        ),
                        None,
                    )
                    if nav_at is not None:
                        updated = (
                            lines[: nav_at + 1] + ["", line] + lines[nav_at + 1 :]
                        )
                    else:
                        updated = lines[:2] + ["", line] + lines[2:]
        status = "inserted"

    new_text = "\n".join(updated) + "\n"
    if new_text == text:
        return "unchanged"
    if apply:
        path.write_text(new_text, encoding="utf-8")
    return status


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    map_path = root / "docs" / "course-v3-map.json"
    if not map_path.exists():
        print(f"映射文件不存在：{map_path}", file=sys.stderr)
        return 1

    mapping = load_map(map_path)
    apply = args.apply
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "待建": 0}
    problems: list[str] = []

    for chapter_id, meta in mapping.items():
        readme = chapter_readme(chapter_id, root)
        rendered_line = render(meta)
        if readme is None:
            counts["待建"] += 1
            print(f"[{'待建':9}] {chapter_id:6}  {rendered_line}")
            continue

        status = upsert(readme, rendered_line, apply)
        counts[status] += 1
        print(f"[{status:9}] {readme.relative_to(root)}  {rendered_line}")

    total = sum(counts.values())
    print(
        f"\n合计：{total} 个章节；"
        f"inserted={counts['inserted']} updated={counts['updated']} "
        f"unchanged={counts['unchanged']} 待建={counts['待建']}"
    )

    if problems:
        print("问题：", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    if not apply and (counts["inserted"] > 0 or counts["updated"] > 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
