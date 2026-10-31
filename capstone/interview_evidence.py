"""只保留能指向仓库证据、并主动说明边界的面试速查。"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class CheatCard:
    group: str
    question: str
    answer: str
    evidence: tuple[str, ...]


CARDS = (
    CheatCard(
        "RAG",
        "RAG 答错时怎么区分检索错误和生成错误？",
        "先检查标准答案所需证据是否进入召回上下文；没有就查切分、查询和排序，"
        "已有但回答不忠实再查生成。当前失败库用关键词做粗分类，仍需扩大人工标注。",
        ("capstone/evaluation.py", "capstone/knowledge_base.py"),
    ),
    CheatCard(
        "RAG",
        "chunk size 怎么选？",
        "项目默认 300、重叠 50 只是起点；用固定数据集对比召回、答案质量、"
        "token 和延迟，结构化文档还要按标题、表格或代码边界切。",
        ("capstone/config.py", "capstone/knowledge_base.py"),
    ),
    CheatCard(
        "RAG",
        "混合检索一定更好吗？",
        "向量与 BM25 能互补，但是否更好必须做同一评测集上的单路/混合消融。"
        "当前代码实现了两路融合，尚未保存完整消融报告。",
        ("capstone/knowledge_base.py", "capstone/data/eval_set.json"),
    ),
    CheatCard(
        "评测",
        "当前项目的评测结果能证明什么？",
        "当前只有 6 条基础用例：4 条关键词、2 条拒答。最近真实运行 6/6 通过，"
        "只证明这些回归未退化，不代表总体准确率。",
        ("capstone/data/eval_set.json", "capstone/data/eval_report.md"),
    ),
    CheatCard(
        "评测",
        "LLM-as-judge 为什么需要校准？",
        "judge 也有位置、长度和同源模型偏差；上线前要与人工标签比较一致性，"
        "并为不确定样本保留人工复核。",
        (
            "chapters/part3-evals/3.3-llm-judge/llm_judge.py",
            "chapters/part3-evals/3.8-prompt-ab-judge/prompt_ab_judge.py",
        ),
    ),
    CheatCard(
        "CI",
        "CI 失败是否自动等于不能合并？",
        "工作流会返回失败并上传报告；只有在仓库分支保护中把检查设为 required，"
        "才真正阻止合并。当前仓库代码不能证明远端设置已经开启。",
        (".github/workflows/eval-gate.yml", "capstone/ci_gate.py"),
    ),
    CheatCard(
        "Agent",
        "状态和长期记忆有什么区别？",
        "checkpointer 保存线程状态和中断恢复；Store 保存跨线程用户记忆。"
        "当前主路径用持久化审批状态机保护副作用，并用显式同意的租户隔离偏好库；"
        "LangGraph InMemorySaver 只保留为框架对照。",
        ("capstone/approval.py", "capstone/memory.py"),
    ),
    CheatCard(
        "Agent",
        "HITL 演示距离生产还差什么？",
        "主 API 已要求主管/admin、租户匹配、过期和一次性决策；当前仍需真实外部"
        "副作用执行器、撤销/取消和加密状态。",
        ("capstone/approval.py", "capstone/api_enterprise.py"),
    ),
    CheatCard(
        "安全",
        "Text2SQL 如何降低注入和越权风险？",
        "更保守的路径是让模型选择查询 ID，而不是输出可执行 SQL；SQL 模板、"
        "租户身份和 LIMIT 由应用提供，再叠只读角色、超时和审计。",
        ("capstone/query_catalog.py", "capstone/service.py"),
    ),
    CheatCard(
        "工程",
        "模型供应商是否可以无缝替换？",
        "统一工厂减少业务改动，但工具调用、结构化输出、上下文、认证和重试语义"
        "不同；切换后仍要跑契约与质量回归。",
        ("common.py", "capstone/provider_contract.py"),
    ),
    CheatCard(
        "工程",
        "怎么在不掉质量的前提下降本？",
        "先记录价格、token、缓存命中和质量基线，再逐项实验缓存、路由和上下文裁剪。"
        "当前没有受控成本节省百分比，因此不报 X%。",
        ("capstone/cache.py", "capstone/monitoring.py"),
    ),
    CheatCard(
        "性能",
        "本地 fake 压测能证明多少并发？",
        "它证明认证 API 和压测统计链路可运行，不是生产容量。定容需要固定环境、"
        "更长稳态、逐级加压，并记录 worker、缓存和上游限额。",
        ("capstone/load_test.py",),
    ),
)


def evidence_status(card: CheatCard) -> dict[str, bool]:
    return {path: (ROOT / path).is_file() for path in card.evidence}


def matching_cards(topic: str) -> list[CheatCard]:
    needle = topic.strip().casefold()
    if not needle:
        return list(CARDS)
    return [
        card
        for card in CARDS
        if needle in f"{card.group} {card.question} {card.answer}".casefold()
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic", nargs="?", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--strict-evidence",
        action="store_true",
        help="任何引用文件缺失时返回非零退出码",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cards = matching_cards(args.topic)
    if not cards:
        print(f"没有匹配：{args.topic}")
        return 2
    payload = [
        {**asdict(card), "evidence_status": evidence_status(card)} for card in cards
    ]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for card, item in zip(cards, payload):
            print(f"\n[{card.group}] {card.question}")
            print(f"回答：{card.answer}")
            statuses = item["evidence_status"]
            assert isinstance(statuses, dict)
            print(
                "证据："
                + "；".join(
                    f"{path}={'OK' if exists else 'MISSING'}"
                    for path, exists in statuses.items()
                )
            )
    missing = [
        path
        for item in payload
        for path, exists in item["evidence_status"].items()
        if not exists
    ]
    return 1 if args.strict_evidence and missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
