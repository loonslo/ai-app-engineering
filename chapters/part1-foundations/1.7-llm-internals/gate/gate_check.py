"""1.7 (L1.2) LLM 工作原理 · 离线自动化 Gate 检查。

覆盖：
1. softmax 温度效应（temperature 越低最大值概率越大）
2. softmax 非法温度报错（temperature <= 0）
3. top_p 过滤（保留首次 >= p 的最小概率集合并归一化）
4. top_p 边界（p=1 全部保留，非法 p 报错）
5. top_k 边界（k 大于数组长度全部保留，k <= 0 报错）
6. KV Cache 显存容量计算公式（7B 模型示例验证）
7. 余弦相似度：相同向量相似度为 1.0
8. 余弦相似度：正交向量为 0.0
9. 余弦相似度：零向量报错
10. 余弦相似度：长度不一致报错
11. 计费估算：带缓存命中的实际花费计算
12. 计费估算：cached > input 或负数报错
13. 评测指标：Precision / Recall / F1 及其除零保护与负数防御

运行方式：
    python gate_check.py
    或：python gate_check.py /path/to/impl.py
退出码：通过为 0，失败为 1。
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import math
import sys
from pathlib import Path
from typing import Any

import argparse
import json

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def load_module(path: Path):
    if not path.exists():
        raise SystemExit(f"找不到实现文件：{path}")
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("candidate_l12", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["candidate_l12"] = module
    spec.loader.exec_module(module)
    return module


class Gate:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def check(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            self.rows.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            self.rows.append({"name": name, "ok": True, "error": ""})

    def report(self, module_path: Path, gate_name: str) -> int:
        passed = sum(row["ok"] for row in self.rows)
        total = len(self.rows)
        for row in self.rows:
            mark = "PASS" if row["ok"] else "FAIL"
            print(f"[{mark}] {row['name']}" + ("" if row["ok"] else f"  <- {row['error']}"))
        print(f"\n{passed}/{total} passed")
        if passed != total:
            print("gate 未通过：先修 FAIL 项，不要打开参考实现。")
        out = {
            "gate": gate_name,
            "module": str(module_path),
            "passed": passed,
            "total": total,
            "ok": passed == total,
            "checks": self.rows,
        }
        (HERE / "gate_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if passed == total else 1


def test_1_softmax_temperature(mod: Any) -> None:
    logits = [2.0, 1.0, 0.0]
    p_high_temp = mod.softmax(logits, temperature=2.0)
    p_norm_temp = mod.softmax(logits, temperature=1.0)
    p_low_temp = mod.softmax(logits, temperature=0.5)

    assert math.isclose(sum(p_high_temp), 1.0, abs_tol=1e-5)
    assert math.isclose(sum(p_norm_temp), 1.0, abs_tol=1e-5)
    assert math.isclose(sum(p_low_temp), 1.0, abs_tol=1e-5)

    # temperature 越低，最大 logit 对应的概率越高，分布越尖锐
    assert p_low_temp[0] > p_norm_temp[0] > p_high_temp[0]


def test_2_softmax_invalid_temp(mod: Any) -> None:
    for invalid_t in (0.0, -0.5, -2.0):
        try:
            mod.softmax([1.0, 2.0], temperature=invalid_t)
        except ValueError:
            continue
        raise AssertionError(f"temperature={invalid_t} 应抛出 ValueError")


def test_3_top_p_filter(mod: Any) -> None:
    # 概率降序：[0.4, 0.3, 0.2, 0.1]
    # 当 p = 0.6 时，累计 0.4 + 0.3 = 0.7 >= 0.6，保留前两项 [0.4, 0.3]，重新归一化为 [4/7, 3/7, 0, 0]
    probs = [0.1, 0.4, 0.2, 0.3]
    filtered = mod.top_p_filter(probs, p=0.6)
    assert len(filtered) == 4
    assert math.isclose(sum(filtered), 1.0, abs_tol=1e-5)
    assert filtered[0] == 0.0
    assert filtered[2] == 0.0
    assert math.isclose(filtered[1], 4.0 / 7.0, abs_tol=1e-5)
    assert math.isclose(filtered[3], 3.0 / 7.0, abs_tol=1e-5)


def test_4_top_p_boundaries(mod: Any) -> None:
    probs = [0.5, 0.3, 0.2]
    # p=1.0 全部保留
    filtered_all = mod.top_p_filter(probs, p=1.0)
    for orig, new in zip(probs, filtered_all, strict=False):
        assert math.isclose(orig, new, abs_tol=1e-5)

    # 非法 p 报错
    for bad_p in (0.0, -0.1, 1.1, 2.0):
        try:
            mod.top_p_filter(probs, p=bad_p)
        except ValueError:
            continue
        raise AssertionError(f"p={bad_p} 应抛出 ValueError")


def test_5_top_k_filter(mod: Any) -> None:
    probs = [0.1, 0.5, 0.2, 0.2]
    # k=2 保留 0.5 与第一个 0.2（下标升序），重新归一化
    filtered = mod.top_k_filter(probs, k=2)
    assert len(filtered) == 4
    assert math.isclose(sum(filtered), 1.0, abs_tol=1e-5)
    assert filtered[0] == 0.0

    # k >= 长度时全部保留
    all_k = mod.top_k_filter(probs, k=10)
    for orig, new in zip(probs, all_k, strict=False):
        assert math.isclose(orig, new, abs_tol=1e-5)

    # k <= 0 报错
    for bad_k in (0, -1):
        try:
            mod.top_k_filter(probs, k=bad_k)
        except ValueError:
            continue
        raise AssertionError(f"k={bad_k} 应抛出 ValueError")


def test_6_kv_cache_formula(mod: Any) -> None:
    # 7B 典型参数：32 层、32 kv 头、head_dim 128、seq_len 2048、batch 1、fp16=2 字节
    # = 2 * 32 * 32 * 128 * 2048 * 1 * 2 = 1,073,741,824 字节 = 1 GB (1024^3 bytes)
    bytes_count = mod.kv_cache_bytes(
        layers=32,
        kv_heads=32,
        head_dim=128,
        seq_len=2048,
        batch=1,
        bytes_per_value=2,
    )
    assert bytes_count == 1073741824, f"7B KV Cache 计算不正确: {bytes_count}"

    # 非法参数 <= 0
    try:
        mod.kv_cache_bytes(layers=0, kv_heads=32, head_dim=128, seq_len=2048)
    except ValueError:
        return
    raise AssertionError("参数 <= 0 时应抛出 ValueError")


def test_7_cosine_same_vector(mod: Any) -> None:
    v = [0.3, 0.4, 0.5]
    sim = mod.cosine_similarity(v, v)
    assert math.isclose(sim, 1.0, abs_tol=1e-5), f"相同向量余弦相似度应为 1.0，实际: {sim}"


def test_8_cosine_orthogonal_vector(mod: Any) -> None:
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    sim = mod.cosine_similarity(v1, v2)
    assert math.isclose(sim, 0.0, abs_tol=1e-5), f"正交向量余弦相似度应为 0.0，实际: {sim}"


def test_9_cosine_zero_vector(mod: Any) -> None:
    v1 = [0.0, 0.0, 0.0]
    v2 = [1.0, 2.0, 3.0]
    try:
        mod.cosine_similarity(v1, v2)
    except ValueError:
        return
    raise AssertionError("全零向量计算余弦相似度应抛出 ValueError")


def test_10_cosine_different_lengths(mod: Any) -> None:
    try:
        mod.cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
    except ValueError:
        return
    raise AssertionError("长度不一致向量应抛出 ValueError")


def test_11_estimate_cost_with_cache(mod: Any) -> None:
    price = mod.PriceTable(
        input_per_mtok=2.0,       # 2 元/百万 token
        output_per_mtok=8.0,      # 8 元/百万 token
        cached_input_per_mtok=0.5 # 0.5 元/百万 token
    )
    # 输入 100 万 token（其中 60 万命中了缓存，40 万未命中）；输出 20 万 token
    # 成本 = 0.6 * 0.5 + 0.4 * 2.0 + 0.2 * 8.0 = 0.3 + 0.8 + 1.6 = 2.7 元
    cost = mod.estimate_cost(
        input_tokens=1_000_000,
        output_tokens=200_000,
        cached_input_tokens=600_000,
        price=price,
    )
    assert math.isclose(cost, 2.7, abs_tol=1e-6), f"计费不正确: 期望 2.7，实际 {cost}"


def test_12_estimate_cost_errors(mod: Any) -> None:
    price = mod.PriceTable(2.0, 8.0, 0.5)
    # cached > input 报错
    try:
        mod.estimate_cost(100, 50, 101, price)
    except ValueError:
        pass
    else:
        raise AssertionError("cached_input_tokens > input_tokens 应抛出 ValueError")

    # 负数报错
    for in_tok, out_tok, c_tok in [(-1, 10, 0), (10, -5, 0), (10, 10, -2)]:
        try:
            mod.estimate_cost(in_tok, out_tok, c_tok, price)
        except ValueError:
            continue
        raise AssertionError("负数 token 应抛出 ValueError")


def test_13_precision_recall_f1(mod: Any) -> None:
    # 正常计算：TP=8, FP=2, FN=2
    # Precision = 8 / (8 + 2) = 0.8
    # Recall = 8 / (8 + 2) = 0.8
    # F1 = 2 * 0.8 * 0.8 / (0.8 + 0.8) = 0.8
    p, r, f1 = mod.precision_recall_f1(tp=8, fp=2, fn=2)
    assert math.isclose(p, 0.8, abs_tol=1e-5)
    assert math.isclose(r, 0.8, abs_tol=1e-5)
    assert math.isclose(f1, 0.8, abs_tol=1e-5)

    # 除零安全：全为 0 时返回 (0.0, 0.0, 0.0)
    p0, r0, f1_0 = mod.precision_recall_f1(tp=0, fp=0, fn=0)
    assert (p0, r0, f1_0) == (0.0, 0.0, 0.0)

    # 负数防御
    try:
        mod.precision_recall_f1(tp=-1, fp=0, fn=0)
    except ValueError:
        return
    raise AssertionError("负数指标入参应抛出 ValueError")


ALL_CHECKS = [
    ("1. softmax 温度效应（低温更尖锐）", test_1_softmax_temperature),
    ("2. softmax 非法温度报错", test_2_softmax_invalid_temp),
    ("3. top_p 过滤（最小集合截断与归一化）", test_3_top_p_filter),
    ("4. top_p 边界（p=1 全部保留与非法范围报错）", test_4_top_p_boundaries),
    ("5. top_k 边界（k 大于长度全保留与 k<=0 报错）", test_5_top_k_filter),
    ("6. KV Cache 显存容量计算公式（7B 模型）", test_6_kv_cache_formula),
    ("7. 余弦相似度：相同向量等于 1.0", test_7_cosine_same_vector),
    ("8. 余弦相似度：正交向量等于 0.0", test_8_cosine_orthogonal_vector),
    ("9. 余弦相似度：全零向量报错", test_9_cosine_zero_vector),
    ("10. 余弦相似度：长度不一致报错", test_10_cosine_different_lengths),
    ("11. 计费估算：带缓存命中的实际花费计算", test_11_estimate_cost_with_cache),
    ("12. 计费估算：cached>input 与负数报错", test_12_estimate_cost_errors),
    ("13. 评测指标：Precision/Recall/F1 除零保护与负数防御", test_13_precision_recall_f1),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="1.7 (L1.2) LLM 工作原理 Gate 检查")
    parser.add_argument("--module", default=str(HERE / "starter.py"), help="待测试模块路径")
    parser.add_argument("positional", nargs="?", default=None, help="位置参数（兼容旧调用）")
    args = parser.parse_args()

    module_path = Path(args.positional or args.module).resolve()
    core = load_module(module_path)
    gate = Gate()

    for title, check_fn in ALL_CHECKS:
        gate.check(title, lambda fn=check_fn: fn(core))

    return gate.report(module_path, "L1.2-llm-internals")


if __name__ == "__main__":
    sys.exit(main())
