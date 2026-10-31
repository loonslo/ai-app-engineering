# 任务 A：带引用与拒答的文档问答

- **限时**：4 小时（计时开始后不要看参考实现；超时就在时限点提交当时的版本，并在自评里写明未完成项）
- **离线检查器**：见下方“接口约定”；检查器用假模型运行固定用例，**通过检查器只说明接口与基本行为正确，不代表质量好**。

## 需求

给定一个小型资料库（几条产品文档），实现 `answer_question`：

1. 根据问题**自己检索**相关资料（关键词重叠、字符二元组、向量都行，不要求高级方法）；
2. 把检索到的资料作为**数据**放进提示里，让模型回答；
3. 回答要带**来源**（资料 id），并且来源必须是真正放进了提示的那几条；
4. 资料库里没有相关信息时**拒答**，并且**不要调用模型**（调用模型就可能编造）；
5. 模型调用失败时不要抛异常，返回一个可读的错误；
6. 资料里如果夹带“忽略以上指令”之类的内容，它只是数据，不能被当成指令。

## 提供的数据

`fixtures/docs_a.json`：6 条虚构产品“Pebble 云备份”的文档（本课程自写，可再分发），每条有 `id`、`title`、`text`；`fixtures/cases_a.json`：7 个用例（5 个范围内、2 个范围外），你可以拿它们做自己的开发集；检查器还会加入其他情形。

## 接口约定（供离线检查器调用）

```python
def answer_question(question: str, docs: list[dict], chat_fn) -> dict:
    """docs: [{"id", "title", "text"}]；chat_fn(messages: list[dict]) -> str，由调用方注入，可能抛异常。
    返回 {"answer": str, "sources": list[str], "refused": bool, "error": str | None}；本函数不抛异常。"""
```

- 范围内：`refused=False`，`sources` 为放进提示的资料 id（最多 3 条），`chat_fn` 恰好调用一次；
- 范围外：`refused=True`、`sources=[]`、`answer` 是可读的拒答说明、`chat_fn` **不被调用**；
- `chat_fn` 抛异常：`{"answer": "", "sources": [], "refused": False, "error": "<异常类名>"}`；
- 不修改传入的 `docs`。

运行检查器（把 `solution_a.py` 换成你的文件）：

```bash
python chapters/part12-job-track/12.5-take-home-sim/checkers/check_a.py --module path/to/solution_a.py
```

起点文件：`starters/solution_a.py`（空实现，检查器应全部失败）。

## 交付物

- 你的实现文件；
- 一个 **README**（写在文件头或单独文件）：做了什么、怎么运行、检索方法的取舍、已知限制；
- 你自己写的**评测脚本**：用 `cases_a.json` 打印“来源是否命中、拒答是否正确”的小结（打印出分数）；
- 自评表。

## 评分表（自评用，见 `../templates/self-review.md`）

| 维度 | 看什么 |
|---|---|
| 可运行 | 检查器 6 项全部通过；评测脚本能直接运行 |
| 坏输出与异常 | 模型失败、检索不到、资料带指令时的处理 |
| 测试 | 除检查器外，你自己补了哪些用例 |
| 评测脚本 | 能打印分数，指标定义清楚 |
| README | 写明取舍与限制，诚实 |
