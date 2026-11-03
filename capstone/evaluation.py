"""
capstone/evaluation.py · 自动化评测：指标 + 报告 + 失败用例库
==========================================================
整合第 2–3 篇的评测做法：读评测集 → 跑 RAG → 算拒答率/关键词命中 → 出 markdown 报告
+ 归档失败用例。这是项目的评测核心模块。
==========================================================
"""

import json
from datetime import UTC, datetime

from . import config as C
from .cache import AnswerCache
from .contracts import AssistRequest
from .knowledge_base import KnowledgeBase, is_refusal
from .permissions import User
from .service import AssistantService


def _refused(ans: str) -> bool:
    """评测只把知识库的规范拒答句式判作拒答。"""
    return is_refusal(ans)


def load_eval_set() -> list[dict]:
    if not C.EVAL_SET.exists():
        raise FileNotFoundError(
            f"先准备评测集 {C.EVAL_SET}（见 data/eval_set.json 示例）"
        )
    payload = json.loads(C.EVAL_SET.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("评测集必须是非空数组")
    ids: set[str] = set()
    for index, case in enumerate(payload, 1):
        if not isinstance(case, dict):
            raise ValueError(f"第 {index} 条评测用例必须是对象")
        case_id = case.get("id")
        question = case.get("question")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"第 {index} 条评测用例缺少稳定 id")
        if case_id in ids:
            raise ValueError(f"评测用例 id 重复：{case_id}")
        ids.add(case_id)
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"评测用例 {case_id} 的 question 无效")
        for field in ("keywords", "expected_sources", "roles"):
            if field in case and (
                not isinstance(case[field], list)
                or not all(isinstance(value, str) for value in case[field])
            ):
                raise ValueError(f"评测用例 {case_id} 的 {field} 必须是字符串数组")
    return payload


class _EvaluationRegistry:
    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    def get(self, tenant_id: str) -> KnowledgeBase:
        if tenant_id != self.kb.tenant_id:
            raise PermissionError("评测身份与知识库租户不一致")
        return self.kb


def run(kb: KnowledgeBase) -> dict:
    """通过与 HTTP API 相同的 AssistantService 执行版本化评测。"""
    service = AssistantService(
        _EvaluationRegistry(kb),
        cache=AnswerCache(max_entries=1024, ttl_seconds=60),
    )
    rows, failures = [], []
    refuse_total = refuse_ok = ans_total = kw_ok = 0
    citation_total = citation_ok = 0

    for case in load_eval_set():
        q = case["question"]
        identity = User(
            case.get("user_id", "eval-reader"),
            tenant_id=case.get("tenant_id", kb.tenant_id),
            dept=case.get("dept", ""),
            roles=frozenset(case.get("roles", ["public"])),
        )
        result = service.assist(
            AssistRequest(
                question=q,
                request_id=f"eval-{case.get('id', len(rows) + 1)}",
                mode=case.get("mode", "knowledge"),
                query_id=case.get("query_id"),
            ),
            identity,
        )
        ans = result.answer
        refused = _refused(ans)
        expected_sources = set(case.get("expected_sources", []))
        actual_sources = {citation.source_id for citation in result.citations}
        citation_passed = not expected_sources or expected_sources.issubset(
            actual_sources
        )
        if expected_sources:
            citation_total += 1
            citation_ok += citation_passed

        if case.get("should_refuse"):
            refuse_total += 1
            passed = refused and not actual_sources
            refuse_ok += passed
        else:
            kws = case.get("keywords", [])
            keyword_passed = all(k in ans for k in kws) if kws else True
            passed = keyword_passed and citation_passed
            if kws:
                ans_total += 1
                kw_ok += keyword_passed
        rows.append(
            {
                "id": case.get("id", ""),
                "q": q,
                "passed": passed,
                "ans": ans,
                "mode": result.mode,
                "sources": sorted(actual_sources),
            }
        )

        if not passed:
            ctx = [d.page_content for d in kb.retrieve(q, user=identity)]
            kws = case.get("keywords", [])
            retrieved_ok = any(any(k in c for k in kws) for c in ctx) if kws else None
            cause = (
                "召回了但生成错"
                if retrieved_ok
                else "引用与期望来源不一致"
                if not citation_passed
                else "应拒答却乱答"
                if case.get("should_refuse")
                else "检索没召回"
            )
            failures.append(
                {
                    "id": case.get("id", ""),
                    "q": q,
                    "ans": ans,
                    "cause": cause,
                    "actual_sources": sorted(actual_sources),
                    "expected_sources": sorted(expected_sources),
                }
            )

    metrics = {
        "拒答正确率": f"{refuse_ok}/{refuse_total}" if refuse_total else "n/a",
        "关键词命中率": f"{kw_ok}/{ans_total}" if ans_total else "n/a",
        "引用正确率": (f"{citation_ok}/{citation_total}" if citation_total else "n/a"),
        "失败数": len(failures),
        "拒答样本数": refuse_total,
        "事实样本数": ans_total,
        "引用样本数": citation_total,
    }
    C.REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_report(rows, failures, metrics)
    C.FAILURES_PATH.write_text(
        json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metrics


def _write_report(rows, failures, metrics):
    lines = [
        "# RAG 评测报告",
        f"\n生成时间：{datetime.now(UTC).isoformat(timespec='seconds')}",
        "\n## 指标\n",
    ]
    for k, v in metrics.items():
        lines.append(f"- {k}：{v}")
    lines += [
        "\n## 逐条\n",
        "| ID | 模式 | 问题 | 来源 | 通过 |",
        "|----|------|------|------|------|",
    ]
    for r in rows:
        question = str(r["q"]).replace("|", "\\|").replace("\n", " ")
        sources = "；".join(r.get("sources", [])) or "-"
        lines.append(
            f"| {r.get('id', '')} | {r.get('mode', '')} | {question} | "
            f"{sources} | {'✓' if r['passed'] else '✗'} |"
        )
    if failures:
        lines.append("\n## 失败用例\n")
        for f in failures:
            lines.append(f"- **{f['q']}** — {f['cause']}")
    C.REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"报告已写入 {C.REPORT_PATH}")


if __name__ == "__main__":
    kb = KnowledgeBase().build()
    print("评测结果：", run(kb))
