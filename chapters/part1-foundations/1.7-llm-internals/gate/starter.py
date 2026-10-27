"""1.7 (L1.2) LLM 工作原理 · 闭卷接口定义与骨架。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriceTable:
    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float


def softmax(logits: list[float], temperature: float = 1.0) -> list[float]:
    """数值稳定的 softmax 计算。

    temperature <= 0 抛 ValueError；数值稳定（先减最大值）；输出概率之和为 1.0。
    """
    raise NotImplementedError


def top_p_filter(probs: list[float], p: float) -> list[float]:
    """Nucleus (Top-p) 采样过滤。

    保留累计概率首次 >= p 的最小集合（按概率降序，同概率按下标升序），其余置 0 后重新归一化；
    p 不在 (0, 1] 时抛 ValueError。
    """
    raise NotImplementedError


def top_k_filter(probs: list[float], k: int) -> list[float]:
    """Top-k 采样过滤。

    保留概率最大的 k 个（同概率按下标升序）并重新归一化；
    k <= 0 抛 ValueError；k 大于长度时全部保留。
    """
    raise NotImplementedError


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
    任一参数 <= 0 抛 ValueError。
    """
    raise NotImplementedError


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。

    长度不同或任一为全零向量时抛 ValueError。
    """
    raise NotImplementedError


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int,
    price: PriceTable,
) -> float:
    """根据 Token 用量与价格表计算单次调用成本。

    缓存命中部分按 cached 单价，其余未命中输入按 input 单价，输出按 output 单价；
    cached_input_tokens > input_tokens 或任一 token 数为负时抛 ValueError。
    返回成本值（单位与单价一致，通常为每百万 token 单价折算后的实际金额）。
    """
    raise NotImplementedError


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """计算 Precision、Recall、F1 分数。

    分母为 0 时对应指标记 0.0；任一参数为负数时抛 ValueError。
    返回 (precision, recall, f1)。
    """
    raise NotImplementedError
