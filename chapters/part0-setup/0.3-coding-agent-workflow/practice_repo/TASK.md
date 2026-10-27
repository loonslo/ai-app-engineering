# 任务需求：实现工单列表筛选与分页

请为 `TicketService.list_tickets` 方法实现按状态筛选和分页功能。

## 接口规范

```python
def list_tickets(
    self,
    status: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
```

### 1. 状态筛选 (`status`)
- 当 `status=None` 时，不按状态过滤，返回所有工单。
- 当 `status` 为字符串时，只返回对应状态的工单，大小写不敏感（如 `"OPEN"`、`"open"` 均匹配 `TicketStatus.OPEN`）。
- 若 `status` 传入了非法的状态名（不在 `open`、`in_progress`、`resolved`、`closed` 中），必须抛出 `ValueError(f"无效的工单状态: {status}")`。

### 2. 参数合法性校验
- `page_size` 必须大于 0；若 `page_size <= 0`，必须抛出 `ValueError("page_size 必须大于 0")`。
- `page` 必须大于等于 1；若 `page < 1`，必须抛出 `ValueError("page 必须大于等于 1")`。

### 3. 返回字典契约
返回值必须为字典，包含以下字段：
- `"total"`: int，满足筛选条件的工单总条数。
- `"page"`: int，当前页码（从 1 开始）。
- `"page_size"`: int，每页容量。
- `"total_pages"`: int，总页数。
  - 当 `total == 0` 时，`total_pages = 0`。
  - 否则 `total_pages = (total + page_size - 1) // page_size`。
- `"items"`: list[Ticket]，当前页包含的工单列表。
  - 第 1 页从索引 `0` 到 `page_size`。
  - 若 `page` 超过 `total_pages`（即越界页），`items` 应返回空列表 `[]`，不应报错。

## 验收检查
修改完成后运行：
```bash
python check_task.py
```
全部断言通过时脚本退出码为 0，有任何失败时退出码为 1。
