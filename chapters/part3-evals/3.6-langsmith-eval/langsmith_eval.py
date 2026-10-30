"""章节 3.6 · LangSmith：trace 可视化与在线评估（平台示例）
==========================================================
3.2–3.5 的评测是"本地算指标"。但 RAG 答错时，你还想知道错在检索的哪一步、召回了什么、
prompt 收到的上下文是什么样。LangSmith 把每次调用的"检索 → 拼上下文 → 生成"记成一条
trace，出问题时点开就能看，不用塞一堆 print。这就是可观测性。

两件事：
1. 开 trace：设几个环境变量，之后所有 LangChain / LangGraph 调用自动上报，不用改业务代码。
2. 在线评估：把评测集传成 LangSmith dataset，用评分函数批量运行，在网页里看结果对比。

注：本脚本为专有平台 SDK 示例。在现代标准化生产架构中，推荐使用基于 OpenTelemetry 开放
标准的 `otel_tracing_eval.py`。

运行模式：
  默认离线演示（无需 key，不上报数据）：
    python tools/run_chapter.py 3.6 langsmith_eval.py
  显式在线真实运行与上报（需配置 LANGSMITH_API_KEY 与模型密钥）：
    python tools/run_chapter.py 3.6 langsmith_eval.py --live
==========================================================
"""

from __future__ import annotations

import argparse
import json  # noqa: E402
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 兼容导入
try:
    from common import SAMPLE_DOC, SHARED_DATA_DIR, chat_model_name, get_openai_client  # noqa: E402
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from common import SAMPLE_DOC, SHARED_DATA_DIR, chat_model_name, get_openai_client  # noqa: E402


def trace_demo(has_key: bool):
    """跑一次带 trace 的 RAG 调用。配置了 key 时上报至 LangSmith。"""
    try:
        from pdf_sources import build_retriever, build_rag_chain
    except ImportError:
        # 若未导入 pdf_sources，提供基础说明
        print("（未找到 pdf_sources 模块，跳过旧版 LangChain RAG 链）")
        return

    try:
        retriever = build_retriever(SAMPLE_DOC)
        chain = build_rag_chain(retriever)
        ans = chain.invoke("RAG 是什么")
        print("回答：", ans[:80], "...")
        if has_key:
            print("→ 打开 https://smith.langchain.com，进 rag-evaluation 项目看这次的 trace：")
            print("  能看到 retriever 召回了哪些块、prompt 实际收到的上下文、LLM 输入输出。")
        else:
            print("（未配 LANGSMITH_API_KEY，跳过 trace 上报。配好后重跑即可在网页看每一步。）")
    except Exception as exc:
        raise RuntimeError(f"RAG 链路执行异常：{exc}") from exc


def langsmith_eval():
    """进阶：把评测集传成 dataset，定义评分函数，用 LangSmith 批量评估。
    依赖 eval_set_full.json（先运行 3.4、3.5 生成）。"""
    from langsmith import Client, evaluate
    from pdf_sources import build_retriever, build_rag_chain

    data_file = SHARED_DATA_DIR / "eval_set_full.json"
    if not data_file.exists():
        print(f"提示：未找到 {data_file}，请先运行 3.4、3.5 生成评测集")
        return

    cases = [c for c in json.loads(data_file.read_text(encoding="utf-8"))
             if not c.get("should_refuse")]   # 在线评估先只跑有答案的题

    client = Client()
    ds_name = "rag-evaluation"
    if not client.has_dataset(dataset_name=ds_name):
        ds = client.create_dataset(ds_name)
        client.create_examples(
            dataset_id=ds.id,
            inputs=[{"question": c["question"]} for c in cases],
            outputs=[{"reference": c["reference"]} for c in cases],
        )

    retriever = build_retriever(SAMPLE_DOC)
    chain = build_rag_chain(retriever)

    # target：被评系统。LangSmith 会把 dataset 每条 input 喂进来
    def target(inputs: dict) -> dict:
        return {"answer": chain.invoke(inputs["question"])}

    # 评分函数（现代签名）：拿到模型输出 + 参考答案，返回打分
    def keyword_ok(outputs: dict, reference_outputs: dict) -> dict:
        ref = reference_outputs["reference"]
        ans = outputs["answer"]
        hit = any(w and w in ans for w in ref.replace("、", " ").split())
        return {"key": "keyword_hit", "score": int(hit)}

    results = evaluate(target, data=ds_name, evaluators=[keyword_ok],
                       experiment_prefix="rag-evaluation")
    print("在线评估已提交，去 LangSmith 看结果对比：", results)


def main() -> int:
    parser = argparse.ArgumentParser(description="3.6 LangSmith 追踪与在线评估（平台示例）")
    parser.add_argument("--live", action="store_true", help="显式开启真实网络调用与 LangSmith 上报")
    args = parser.parse_args()

    print("==========================================================")
    print("  3.6 LangSmith 平台示例（专用 SDK 接入与在线评测）")
    print("==========================================================")

    if not args.live:
        print("[模式说明] 当前为默认【离线演示模式】（未加 --live 开关）。")
        print("本脚本保留为商业平台专有 SDK 的接入示范，说明：")
        print("1. 调用第三方平台会将 Query、检索分块与回答内容上传至云端；")
        print("2. 需配置 LANGSMITH_API_KEY 与模型密钥，附加 --live 显式开启；")
        print("3. v3 课程标准推荐使用标准化、可自托管的 otel_tracing_eval.py。\n")
        print("离线模式执行完成 (exit 0)。")
        return 0

    has_langsmith_key = bool(os.getenv("LANGSMITH_API_KEY"))
    if not has_langsmith_key:
        print("[配置提示] 未配置 LANGSMITH_API_KEY，无法连接 LangSmith 平台进行 Trace 上报与在线评估。", file=sys.stderr)
        return 1

    # 校验模型客户端可用性
    try:
        _ = get_openai_client(timeout=10.0, max_retries=1)
        _ = chat_model_name()
    except Exception as exc:
        print(f"[配置错误] 无法初始化模型客户端：{exc}", file=sys.stderr)
        return 1

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "rag-evaluation")

    print("===== 1) trace 演示 =====")
    try:
        trace_demo(has_key=has_langsmith_key)
    except Exception as exc:
        print(f"[运行失败] Trace 演示过程中发生错误：{exc}", file=sys.stderr)
        return 1

    print("\n===== 2) LangSmith 在线评估 =====")
    try:
        langsmith_eval()
    except Exception as exc:
        print(f"(在线评估出错，多为 key/版本/网络问题，trace 部分不受影响) {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
