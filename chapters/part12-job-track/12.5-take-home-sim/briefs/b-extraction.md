# 任务 B：结构化抽取分类器（附评测脚本）

- **限时**：3 小时（计时开始后不要看参考实现；超时就在时限点提交当时的版本，并在自评里写明未完成项）
- **离线检查器**：见下方“接口约定”；检查器用假模型运行固定用例，**通过检查器只说明接口与基本行为正确，不代表质量好**。

## 需求

实现 `extract_ticket`：把一条用户消息交给模型，抽取出结构化工单；再实现 `evaluate`：对一组带标准答案的用例打印准确率。

1. 模型输出可能是裸 JSON、被 ``` 代码块包裹的 JSON，或根本不是 JSON，要能处理；
2. 校验：`category` 必须是 `billing`、`bug`、`feature`、`other` 之一；`priority` 必须是 1–3 的整数（`true` 不算）；`summary` 必须是 1–80 字的非空字符串；
3. 校验失败时，**带着失败原因**再请求一次模型，次数有上限；
4. 模型调用抛异常算一次失败；永远不要把异常抛给调用方；
5. `evaluate` 要给出类别准确率、优先级准确率、完全匹配率和失败用例列表；抽取失败的用例算错。

## 提供的数据

`fixtures/cases_b.json`：8 条虚构用户消息，带标准答案（`category`、`priority`），你可以拿它们做自己的开发集。检查器用脚本化的假模型，不依赖这些文本。

## 接口约定（供离线检查器调用）

```python
def extract_ticket(text: str, chat_fn, *, max_attempts: int = 2) -> dict:
    """chat_fn(messages) -> str。返回 {"ok": bool, "data": {"category","priority","summary"} | None,
    "attempts": int, "error": str | None}；max_attempts < 1 抛 ValueError；其他情况不抛异常。"""

def evaluate(cases: list[dict], extract_fn) -> dict:
    """cases: [{"id", "text", "expected": {"category", "priority"}}]；extract_fn(text) -> extract_ticket 的返回值。
    返回 {"n", "category_accuracy", "priority_accuracy", "exact_match", "failures": [用例 id]}；空用例集不崩溃。"""
```

运行检查器：

```bash
python chapters/part12-job-track/12.5-take-home-sim/checkers/check_b.py --module path/to/solution_b.py
```

起点文件：`starters/solution_b.py`（空实现）。

## 交付物

- 你的实现文件；
- 一个 **README**：做了什么、怎么运行、提示词怎么写的、取舍与限制；
- 一个能**打印分数**的小评测脚本（用 `evaluate` 和 `cases_b.json`；真实模型的结果要标明模型 ID 与日期，离线假模型的结果要标明是离线）；
- 自评表。

## 评分表（自评用，见 `../templates/self-review.md`）

| 维度 | 看什么 |
|---|---|
| 可运行 | 检查器 6 项全部通过 |
| 坏输出 | 各种不合格输出的处理与重试 |
| 测试 | 你自己补的边界用例 |
| 评测脚本 | 指标定义、失败用例可定位 |
| README | 写明取舍与限制，诚实 |
