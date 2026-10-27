"""1.7 (L1.2) LLM 工作原理 · 原生实现与演示。

涵盖：
1. Logits 到概率的数值稳定 Softmax 与 Temperature 缩放
2. Top-p (Nucleus) 与 Top-k 采样截断算法
3. Transformer 架构下 KV Cache 显存容量推导
4. 向量余弦相似度计算（语义检索数学基础）
5. Token 计费模型（按前缀缓存与未命中分别核算）
6. 分类与抽取质量评估指标（Precision, Recall, F1）
7. 可选 --live 模式：对比不同 temperature 下的真实输出与 usage
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

# 导入共享配置
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from common import chat_model_name, get_openai_client
except ImportError:
    chat_model_name = None  # type: ignore
    get_openai_client = None  # type: ignore


@dataclass(frozen=True)
class PriceTable:
    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float


def softmax(logits: list[float], temperature: float = 1.0) -> list[float]:
    """数值稳定的 softmax 计算。

    temperature <= 0 抛 ValueError；数值稳定（先减最大值）；输出概率之和为 1.0。
    """
    if temperature <= 0.0:
        raise ValueError("temperature 必须大于 0")
    if not logits:
        return []

    # 减去最大值防止浮点数指数溢出 (exp overflow)
    max_logit = max(logits)
    scaled_exps = [math.exp((x - max_logit) / temperature) for x in logits]
    sum_exps = sum(scaled_exps)
    if sum_exps == 0.0:
        raise ValueError("Softmax 指数和为 0")
    return [exp_val / sum_exps for exp_val in scaled_exps]


def top_p_filter(probs: list[float], p: float) -> list[float]:
    """Nucleus (Top-p) 采样过滤。

    保留累计概率首次 >= p 的最小集合（按概率降序，同概率按下标升序），其余置 0 后重新归一化；
    p 不在 (0, 1] 时抛 ValueError。
    """
    if p <= 0.0 or p > 1.0:
        raise ValueError("p 必须在 (0, 1] 区间内")
    if not probs:
        return []

    if math.isclose(p, 1.0, abs_tol=1e-9):
        # 重新归一化确保和为 1.0
        total = sum(probs)
        return [x / total for x in probs]

    # 按概率降序排序，相同概率保持下标升序
    indexed = sorted(enumerate(probs), key=lambda x: (-x[1], x[0]))

    cumulative = 0.0
    kept_indices: set[int] = set()
    for idx, prob in indexed:
        kept_indices.add(idx)
        cumulative += prob
        if cumulative >= p:
            break

    result = [prob if idx in kept_indices else 0.0 for idx, prob in enumerate(probs)]
    sum_kept = sum(result)
    if sum_kept == 0.0:
        raise ValueError("保留项概率和为 0")
    return [x / sum_kept for x in result]


def top_k_filter(probs: list[float], k: int) -> list[float]:
    """Top-k 采样过滤。

    保留概率最大的 k 个（同概率按下标升序）并重新归一化；
    k <= 0 抛 ValueError；k 大于长度时全部保留。
    """
    if k <= 0:
        raise ValueError("k 必须大于 0")
    if not probs:
        return []

    if k >= len(probs):
        total = sum(probs)
        return [x / total for x in probs]

    indexed = sorted(enumerate(probs), key=lambda x: (-x[1], x[0]))
    kept_indices = {idx for idx, _ in indexed[:k]}

    result = [prob if idx in kept_indices else 0.0 for idx, prob in enumerate(probs)]
    sum_kept = sum(result)
    if sum_kept == 0.0:
        raise ValueError("保留项概率和为 0")
    return [x / sum_kept for x in result]


def kv_cache_bytes(
    layers: int,
    kv_heads: int,
    head_dim: int,
    seq_len: int,
    batch: int = 1,
    bytes_per_value: int = 2,
) -> int:
    """计算 KV Cache 占用的显存字节数。

    公式: 2 * layers * kv_heads * head_dim * seq_len * batch * bytes_per_value
    （系数 2 代表 Key 与 Value 两个张量；FP16/BF16 通常为 2 字节）
    任一参数 <= 0 抛 ValueError。
    """
    params = (layers, kv_heads, head_dim, seq_len, batch, bytes_per_value)
    if any(p <= 0 for p in params):
        raise ValueError("所有维度参数必须大于 0")

    return 2 * layers * kv_heads * head_dim * seq_len * batch * bytes_per_value


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。

    长度不同或任一为全零向量时抛 ValueError。
    """
    if len(a) != len(b):
        raise ValueError(f"向量维度不匹配: {len(a)} != {len(b)}")

    dot_product = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        raise ValueError("不能计算全零向量的余弦相似度")

    sim = dot_product / (norm_a * norm_b)
    # 浮点数截断修正
    return max(-1.0, min(1.0, sim))


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int,
    price: PriceTable,
) -> float:
    """根据 Token 用量与价格表计算单次调用成本。

    缓存命中部分按 cached 单价，其余未命中输入按 input 单价，输出按 output 单价；
    cached_input_tokens > input_tokens 或任一 token 数为负时抛 ValueError。
    """
    if cached_input_tokens > input_tokens:
        raise ValueError("缓存命中 token 数不能大于总输入 token 数")
    if input_tokens < 0 or output_tokens < 0 or cached_input_tokens < 0:
        raise ValueError("Token 数量不能为负数")

    uncached_input = input_tokens - cached_input_tokens
    cost = (
        cached_input_tokens * price.cached_input_per_mtok
        + uncached_input * price.input_per_mtok
        + output_tokens * price.output_per_mtok
    ) / 1_000_000.0
    return cost


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """计算 Precision、Recall、F1 分数。

    分母为 0 时对应指标记 0.0；任一参数为负数时抛 ValueError。
    返回 (precision, recall, f1)。
    """
    if tp < 0 or fp < 0 or fn < 0:
        raise ValueError("混淆矩阵计数不能为负数")

    precision = float(tp) / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = float(tp) / (tp + fn) if (tp + fn) > 0 else 0.0

    if precision + recall > 0.0:
        f1 = 2.0 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return (precision, recall, f1)


def demo_offline() -> None:
    print("=== 1. Softmax 温度缩放演示 ===")
    logits = [3.0, 1.0, 0.2]
    print(f"原始 Logits: {logits}")
    print(f"  - T=2.0 (平滑/发散): {[round(x, 4) for x in softmax(logits, 2.0)]}")
    print(f"  - T=1.0 (标准):     {[round(x, 4) for x in softmax(logits, 1.0)]}")
    print(f"  - T=0.2 (尖锐/确定): {[round(x, 4) for x in softmax(logits, 0.2)]}")

    print("\n=== 2. Top-p 与 Top-k 采样过滤 ===")
    probs = [0.05, 0.60, 0.20, 0.15]
    print(f"原始概率分布: {probs}")
    print(f"  - Top-p (p=0.8): {[round(x, 4) for x in top_p_filter(probs, 0.8)]}")
    print(f"  - Top-k (k=2):   {[round(x, 4) for x in top_k_filter(probs, 2)]}")

    print("\n=== 3. 7B 模型 KV Cache 显存占用 ===")
    bytes_7b = kv_cache_bytes(layers=32, kv_heads=32, head_dim=128, seq_len=4096, batch=1)
    print(f"7B 模型在 4k 上下文、Batch=1 下单次请求 KV Cache: {bytes_7b / (1024**3):.2f} GB")

    print("\n=== 4. 向量余弦相似度 ===")
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, 2.0, 3.1]
    v_orth = [-2.0, 1.0, 0.0]
    print(f"相似向量余弦值: {cosine_similarity(v1, v2):.4f}")
    print(f"正交向量余弦值: {cosine_similarity(v1, v_orth):.4f}")

    print("\n=== 5. Prompt Caching 计费对比 ===")
    # 参考 DeepSeek 官方定价（单位：元/百万 token）
    deepseek_price = PriceTable(
        input_per_mtok=2.0, output_per_mtok=8.0, cached_input_per_mtok=0.5
    )
    cost_no_cache = estimate_cost(100_000, 2_000, 0, deepseek_price)
    cost_cached_80 = estimate_cost(100_000, 2_000, 80_000, deepseek_price)
    print(f"100k 输入未命中缓存成本: {cost_no_cache:.4f} 元")
    print(f"100k 输入命中 80% 缓存成本: {cost_cached_80:.4f} 元 (节省 {(1 - cost_cached_80/cost_no_cache)*100:.1f}%)")

    print("\n=== 6. 分类与抽取指标 ===")
    p, r, f1 = precision_recall_f1(tp=18, fp=2, fn=5)
    print(f"TP=18, FP=2, FN=5 -> Precision: {p:.4f}, Recall: {r:.4f}, F1: {f1:.4f}")


def demo_live() -> None:
    if get_openai_client is None or chat_model_name is None:
        print("[提示] 无法导入 common 模块，跳过真实调用。")
        return

    try:
        client = get_openai_client()
    except Exception as exc:
        print(f"[提示] 未能初始化客户端（{exc}）。演示跳过真实网络请求。")
        return

    model = chat_model_name()
    prompt = "请用严谨的 20 字以内回答：什么是大模型的 KV Cache？"
    print(f"=== 真实模型调用对比（模型: {model}）===")

    for temp in (0.0, 1.0):
        print(f"\n--- Temperature = {temp} ---")
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
            )
            choice = resp.choices[0]
            print(f"输出: {choice.message.content}")
            if resp.usage:
                print(f"Usage: prompt={resp.usage.prompt_tokens}, completion={resp.usage.completion_tokens}")
        except Exception as exc:
            print(f"调用失败: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    if "--live" in sys.argv:
        demo_live()
    else:
        demo_offline()
