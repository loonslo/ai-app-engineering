"""L2.10 记忆与上下文压缩 · 离线 gate 验收。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(path: Path):
    if not path.exists():
        raise SystemExit(f"找不到实现文件：{path}")
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    spec = importlib.util.spec_from_file_location("candidate_l210_mem", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_l210_mem"] = module
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
            "gate": "L2.10-memory-compaction",
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

    def build_test_history():
        msgs = [
            {"role": "system", "content": "System prompt: You are a customer support agent."},
            {"role": "user", "content": "我的订单号是 ORD-1001"},
            {"role": "assistant", "content": "收到，请问有什么可以帮您？"},
            {"role": "user", "content": "我想把收货地址改成北京市海淀区", "pinned": True},
            {"role": "assistant", "content": "已为您记录地址变更申请"},
            {"role": "user", "content": "运费是多少钱？"},
            {"role": "assistant", "content": "满99包邮，不满收取8元"},
            {"role": "user", "content": "发什么快递？"},
            {"role": "assistant", "content": "默认顺丰速运"},
        ]
        return msgs

    def test_within_budget():
        msgs = build_test_history()
        res = core.compact_history(msgs, budget=2000, summarize_fn=lambda x: "summary")
        expect(res.messages == msgs, "未超预算应原样返回")
        expect(res.prefix_changed is False, "未超预算 prefix_changed 应为 False")
        expect(res.summarized_count == 0, "未超预算 summarized_count 应为 0")

    def test_preserve_system():
        msgs = build_test_history()
        res = core.compact_history(msgs, budget=100, summarize_fn=lambda x: "已讨论订单与运费", keep_last=2)
        expect(res.messages[0]["role"] == "system", "首条消息必须是 system")
        expect("System prompt" in res.messages[0]["content"], f"首条 system 未原样保留：{res.messages[0]}")

    def test_preserve_tail():
        msgs = build_test_history()
        res = core.compact_history(msgs, budget=100, summarize_fn=lambda x: "summary", keep_last=2)
        expect(res.messages[-2]["content"] == "发什么快递？", "倒数第2条未保留")
        expect(res.messages[-1]["content"] == "默认顺丰速运", "最后一条未保留")

    def test_preserve_pinned():
        msgs = build_test_history()
        res = core.compact_history(msgs, budget=100, summarize_fn=lambda x: "summary", keep_last=2)
        pinned = [m for m in res.messages if m.get("pinned")]
        expect(len(pinned) == 1, "固定 pinned 消息应保留")
        expect("北京市海淀区" in pinned[0]["content"], "pinned 内容不对")

    def test_summary_placement():
        msgs = build_test_history()
        res = core.compact_history(msgs, budget=100, summarize_fn=lambda x: "已确认订单及修改地址", keep_last=2)
        expect(res.messages[1]["role"] == "system", "摘要消息必须为 system role")
        expect(res.messages[1]["content"].startswith("[摘要]"), f"摘要必须以 [摘要] 开头：{res.messages[1]}")

    def test_summarize_error_fallback():
        def broken_summary(x):
            raise RuntimeError("LLM rate limited")

        msgs = build_test_history()
        res = core.compact_history(msgs, budget=100, summarize_fn=broken_summary, keep_last=2)
        expect("[摘要不可用，已截断" in res.messages[1]["content"], f"摘要失败应降级为截断提示：{res.messages[1]}")

    def test_post_compact_within_budget():
        msgs = build_test_history()
        # 1. 预算设为 160，摘要提供极长文本，验证压缩后总 Token 严格不超预算
        res = core.compact_history(msgs, budget=160, summarize_fn=lambda x: "超长冗余会话历史摘要说明内容" * 15, keep_last=2)
        total_tokens = sum(len(m.get("content", "")) for m in res.messages)
        expect(total_tokens <= 160, f"压缩后总 Token ({total_tokens}) 仍超出预算 (160)：{res.messages}")

        # 2. 必须保留的消息本身已超预算时，必须抛出 ValueError
        err_raised = False
        try:
            core.compact_history(msgs, budget=10, summarize_fn=lambda x: "summary", keep_last=2)
        except ValueError:
            err_raised = True
        expect(err_raised, "必须保留的消息总预算超出 budget 时应抛出 ValueError")

    def test_prefix_changed():
        msgs = build_test_history()
        res = core.compact_history(msgs, budget=100, summarize_fn=lambda x: "summary", keep_last=2)
        expect(res.prefix_changed is True, "发生压缩修改历史时 prefix_changed 应为 True")
        # 测试无需压缩时 prefix_changed 为 False
        res_no_comp = core.compact_history(msgs, budget=5000, summarize_fn=lambda x: "summary")
        expect(res_no_comp.prefix_changed is False, "未修改消息内容时 prefix_changed 必须为 False")

    def test_memory_isolation():
        store = core.MemoryStore()
        store.remember("tenant_1", "user_a", "theme", "dark", source="user", confirmed=True)
        # 本租户本用户可读
        expect(store.recall("tenant_1", "user_a", "theme") == "dark", "记忆读取失败")
        # 跨租户隔离
        expect(store.recall("tenant_2", "user_a", "theme") is None, "跨租户泄露！")
        # 跨用户隔离
        expect(store.recall("tenant_1", "user_b", "theme") is None, "跨用户泄露！")

    def test_model_unconfirmed_rejected():
        store = core.MemoryStore()
        # 1. 未确认的模型写入必须被拒绝
        ok = store.remember("tenant_1", "user_a", "city", "Beijing", source="model", confirmed=False)
        expect(ok is False, "未确认的模型写入必须被拒绝")
        expect(store.recall("tenant_1", "user_a", "city") is None, "拒绝项不应写入存储")
        # 2. 经确认的模型写入允许通过
        ok_confirmed = store.remember("tenant_1", "user_a", "city", "Beijing", source="model", confirmed=True)
        expect(ok_confirmed is True, "已确认的模型写入应当允许写入")
        expect(store.recall("tenant_1", "user_a", "city") == "Beijing", "已确认模型写入应可召回")
        # 3. 用户直接写入允许通过
        ok_user = store.remember("tenant_1", "user_a", "theme", "dark", source="user", confirmed=True)
        expect(ok_user is True, "用户写入应当允许写入")
        expect(store.recall("tenant_1", "user_a", "theme") == "dark", "用户写入应可召回")

    def test_forget_and_export():
        store = core.MemoryStore()
        store.remember("t1", "u1", "k1", "v1", source="user", confirmed=True)
        store.remember("t1", "u1", "k2", "v2", source="user", confirmed=True)

        exp = store.export("t1", "u1")
        expect(exp == {"k1": "v1", "k2": "v2"}, f"export 不对：{exp}")
        exp["k1"] = "tampered"
        expect(store.recall("t1", "u1", "k1") == "v1", "export 必须返回副本，不能污染内部存储")

        expect(store.forget("t1", "u1", "k1") is True, "删除已存在的 key 应返回 True")
        expect(store.recall("t1", "u1", "k1") is None, "已删除 key 应读不出")
        expect(store.forget("t1", "u1", "k1") is False, "删除不存在的 key 应返回 False")

    gate.check("01 预算内原样返回", test_within_budget)
    gate.check("02 首条 system 消息保留", test_preserve_system)
    gate.check("03 末尾 keep_last 条消息保留", test_preserve_tail)
    gate.check("04 固定 pinned 消息原样保留", test_preserve_pinned)
    gate.check("05 摘要消息插入位置与前缀正确", test_summary_placement)
    gate.check("06 摘要失败降级为截断说明", test_summarize_error_fallback)
    gate.check("07 压缩后总 token 不超预算", test_post_compact_within_budget)
    gate.check("08 压缩时 prefix_changed 判断正确", test_prefix_changed)
    gate.check("09 多租户与跨用户严格隔离", test_memory_isolation)
    gate.check("10 策略管控：未确认模型写入拦截、确认模型与用户写入通过", test_model_unconfirmed_rejected)
    gate.check("11 记忆遗忘与安全副本导出", test_forget_and_export)
    return gate.report(module_path)


if __name__ == "__main__":
    raise SystemExit(main())
