#!/usr/bin/env python3
"""工单筛选与分页任务检查脚本。

非 pytest 测试文件，由学习者或 Agent 独立执行：
    python check_task.py
通过退出码为 0，失败退出码为 1。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# 将当前目录加入导包路径
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from models import TicketStatus  # noqa: E402
except ImportError as exc:
    print(f"[FAIL] 导入基础模型失败: {exc}", file=sys.stderr)
    sys.exit(1)


def load_service_class() -> type:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        target_path = Path(sys.argv[1]).resolve()
        if not target_path.exists():
            print(f"[FAIL] 指定的实现文件不存在: {target_path}", file=sys.stderr)
            sys.exit(1)
        spec = importlib.util.spec_from_file_location("custom_service", target_path)
        if spec is None or spec.loader is None:
            print(f"[FAIL] 无法解析模块: {target_path}", file=sys.stderr)
            sys.exit(1)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "TicketService"):
            print(f"[FAIL] 模块中未找到 TicketService: {target_path}", file=sys.stderr)
            sys.exit(1)
        return mod.TicketService
    else:
        try:
            from service import TicketService
            return TicketService
        except ImportError as exc:
            print(f"[FAIL] 导入 service 模块失败: {exc}", file=sys.stderr)
            sys.exit(1)


def check_assertions() -> bool:
    passed = True
    TicketService = load_service_class()
    service = TicketService()

    # 1. 默认无筛选与第一页检查
    res = service.list_tickets(page=1, page_size=3)
    expected_keys = {"total", "page", "page_size", "total_pages", "items"}
    if not isinstance(res, dict) or not expected_keys.issubset(res.keys()):
        print(f"[FAIL] 返回值应包含字段 {expected_keys}，实际返回: {res}", file=sys.stderr)
        return False

    if res["total"] != 8:
        print(f"[FAIL] 期望 total=8，实际: {res.get('total')}", file=sys.stderr)
        passed = False
    if res["total_pages"] != 3:
        print(f"[FAIL] 期望 total_pages=3，实际: {res.get('total_pages')}", file=sys.stderr)
        passed = False
    if len(res.get("items", [])) != 3:
        print(f"[FAIL] 期望 page=1 返回 3 条数据，实际: {len(res.get('items', []))}", file=sys.stderr)
        passed = False

    # 2. 最后一页检查（第 3 页，每页 3 条，总计 8 条，最后一页应有 2 条）
    res_last = service.list_tickets(page=3, page_size=3)
    if len(res_last.get("items", [])) != 2:
        print(f"[FAIL] 期望最后一页返回 2 条数据，实际: {len(res_last.get('items', []))}", file=sys.stderr)
        passed = False

    # 3. 越界页检查（第 4 页，越界应返回空列表 []，不报错）
    res_overflow = service.list_tickets(page=4, page_size=3)
    if res_overflow.get("items") != []:
        print(f"[FAIL] 期望越界页返回空列表 []，实际: {res_overflow.get('items')}", file=sys.stderr)
        passed = False

    # 4. 状态筛选（open 状态有 3 条）
    res_open = service.list_tickets(status="open", page=1, page_size=10)
    if res_open.get("total") != 3:
        print(f"[FAIL] 期望 open 状态 total=3，实际: {res_open.get('total')}", file=sys.stderr)
        passed = False
    for item in res_open.get("items", []):
        if item.status != TicketStatus.OPEN:
            print(f"[FAIL] 返回了非 open 状态工单: {item}", file=sys.stderr)
            passed = False

    # 5. 状态大小写不敏感（"OPEN" 应同样匹配）
    res_open_upper = service.list_tickets(status="OPEN", page=1, page_size=10)
    if res_open_upper.get("total") != 3:
        print(f"[FAIL] 期望大小写不敏感匹配 total=3，实际: {res_open_upper.get('total')}", file=sys.stderr)
        passed = False

    # 6. 非法状态抛 ValueError
    try:
        service.list_tickets(status="non_existent_status")
        print("[FAIL] 传入非法 status 应该抛出 ValueError，但没有抛出", file=sys.stderr)
        passed = False
    except ValueError:
        pass
    except Exception as exc:
        print(f"[FAIL] 传入非法 status 应抛出 ValueError，实际抛出: {type(exc)}", file=sys.stderr)
        passed = False

    # 7. 参数合法性：page_size <= 0 抛 ValueError
    for invalid_size in (0, -1):
        try:
            service.list_tickets(page_size=invalid_size)
            print(f"[FAIL] page_size={invalid_size} 应该抛出 ValueError", file=sys.stderr)
            passed = False
        except ValueError:
            pass

    # 8. 参数合法性：page < 1 抛 ValueError
    for invalid_page in (0, -2):
        try:
            service.list_tickets(page=invalid_page)
            print(f"[FAIL] page={invalid_page} 应该抛出 ValueError", file=sys.stderr)
            passed = False
        except ValueError:
            pass

    # 9. 0 数据时的 total_pages == 0 边界
    empty_service = TicketService(tickets=[])
    res_empty = empty_service.list_tickets(page=1, page_size=5)
    if res_empty.get("total") != 0 or res_empty.get("total_pages") != 0 or res_empty.get("items") != []:
        print(f"[FAIL] 空数据时期望 total=0, total_pages=0, items=[]，实际: {res_empty}", file=sys.stderr)
        passed = False

    return passed


def main() -> int:
    if check_assertions():
        print("[PASS] 工单列表筛选与分页功能检查全部通过！")
        return 0
    else:
        print("[FAIL] 存在未通过的检查项，请根据上述提示修正实现。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
