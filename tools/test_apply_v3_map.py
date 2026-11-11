"""tools/apply_v3_map.py 单元测试。

验证插入位置、幂等性与“待建”目录不影响退出码。
"""

import json
from pathlib import Path

from tools import apply_v3_map


def test_upsert_replace_v3_in_place(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# 测试章\n\n- **能力**：测试\n- **v3 路径**：L1.1 / 核心（旧备注）\n",
        encoding="utf-8",
    )
    new_line = "- **v3 路径**：L1.1 / 核心（新备注）"

    status = apply_v3_map.upsert(readme, new_line, apply=True)
    assert status == "updated"

    lines = readme.read_text(encoding="utf-8").splitlines()
    assert lines[3] == new_line

    # 再次运行应为 unchanged
    status_second = apply_v3_map.upsert(readme, new_line, apply=True)
    assert status_second == "unchanged"


def test_upsert_insert_after_first_header(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# 新章\n\n- **目标**：掌握新原语\n- **岗位任务**：T1\n",
        encoding="utf-8",
    )
    new_line = "- **v3 路径**：L0.3 / 核心（清单验收）"

    status = apply_v3_map.upsert(readme, new_line, apply=True)
    assert status == "inserted"

    lines = readme.read_text(encoding="utf-8").splitlines()
    assert lines[2] == "- **目标**：掌握新原语"
    assert lines[3] == new_line
    assert lines[4] == "- **岗位任务**：T1"


def test_idempotence_and_check_exit_code(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    map_file = docs_dir / "course-v3-map.json"
    mapping = {
        "0.1": {"stage": "L0.1", "role": "核心", "note": "清单验收"},
        "0.3": {"stage": "L0.3", "role": "核心", "note": "清单验收"},  # 待建目录
    }
    map_file.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

    chap_dir = tmp_path / "chapters" / "part0-setup" / "0.1-env"
    chap_dir.mkdir(parents=True)
    readme = chap_dir / "README.md"
    readme.write_text("# 0.1\n\n- **目标**：环境检查\n", encoding="utf-8")

    # 1. 存在未写入的 README 时，--check 退出码应为 1
    code_check_1 = apply_v3_map.main(["--check"], root=tmp_path)
    assert code_check_1 == 1

    # 2. 运行 --apply 写入
    code_apply_1 = apply_v3_map.main(["--apply"], root=tmp_path)
    assert code_apply_1 == 0

    content_after_first_apply = readme.read_text(encoding="utf-8")
    assert "- **v3 路径**：L0.1 / 核心（清单验收）" in content_after_first_apply

    # 3. 再次运行 --apply，无任何改动（幂等）
    code_apply_2 = apply_v3_map.main(["--apply"], root=tmp_path)
    assert code_apply_2 == 0
    assert readme.read_text(encoding="utf-8") == content_after_first_apply

    # 4. 再次运行 --check，待建目录不算错误，退出码应为 0
    code_check_2 = apply_v3_map.main(["--check"], root=tmp_path)
    assert code_check_2 == 0


def test_multiple_directory_match_records_problem(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    map_file = docs_dir / "course-v3-map.json"
    mapping = {
        "0.1": {"stage": "L0.1", "role": "核心", "note": "清单验收"},
    }
    map_file.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

    # 创建两个同名 0.1 章节目录
    p1 = tmp_path / "chapters" / "part0-setup" / "0.1-env-a"
    p2 = tmp_path / "chapters" / "part0-setup" / "0.1-env-b"
    p1.mkdir(parents=True)
    p2.mkdir(parents=True)
    (p1 / "README.md").write_text("# 0.1a\n", encoding="utf-8")
    (p2 / "README.md").write_text("# 0.1b\n", encoding="utf-8")

    code = apply_v3_map.main(["--check"], root=tmp_path)
    assert code == 1
