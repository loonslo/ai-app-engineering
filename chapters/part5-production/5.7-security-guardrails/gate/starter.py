"""L5.4 安全护栏 · 闭卷骨架

规则：只读本文件和本章 README 的 gate 任务书；通过 gate 之前不要打开
security_guardrails.py。实现下面三个函数，然后运行：

    python chapters/part5-production/5.7-security-guardrails/gate/gate_check.py
"""

from __future__ import annotations


def scan_input(text: str) -> dict:
    """检测提示词注入，返回 {"action": "block"|"flag"|"pass", "hits": list[str]}。

    要求：
    - 归一化全角/大小写/零宽字符/空白后再匹配；
    - 明确的改写指令（忽略以上…指令、ignore previous instructions、索要系统提示词）
      -> block；
    - 只出现 system prompt/API key 等可疑词 -> flag；
    - 正常问题 -> pass；
    - 非字符串 -> ValueError。
    """
    raise NotImplementedError("实现注入检测")


def mask_pii(text: str) -> tuple[str, dict[str, str]]:
    """脱敏邮箱/身份证/银行卡/手机号，返回 (脱敏文本, 还原表)。

    要求：
    - 先长后短匹配，避免手机号从身份证中间咬走；
    - 同一原值复用同一占位符；
    - 占位符形如 [邮箱_1]/[手机号_1]；
    - 非字符串 -> ValueError。
    """
    raise NotImplementedError("实现 PII 脱敏")


def scrub_secrets(text: str) -> str:
    """把 sk-... / bearer ... / api_key=... 替换为 [已脱敏密钥]。"""
    raise NotImplementedError("实现密钥脱敏")


def audit_record(event: dict, *, hash_fn) -> dict:
    """生成审计记录，只输出这些字段：ts、tenant_id、actor_ref、action、decision、model、prompt_version。

    - actor_ref = hash_fn(event["actor_id"]) 的前 12 位；
    - event 缺少 ts、tenant_id、actor_id、action、decision、model、prompt_version 任一字段（缺失或为空）-> ValueError；
    - event 里的 prompt、completion、email、phone 等其他字段，原文不得出现在输出中。
    """
    raise NotImplementedError("实现审计记录")


def label_ai_content(text: str, policy: dict) -> str:
    """policy = {"disclose": bool, "label": str}。

    - disclose 为假 -> 原样返回 text；
    - disclose 为真且 text 尚未包含 label -> 返回 f"{text}\\n{label}"（正文、换行、标识）；
    - 已包含 label -> 原样返回，不重复追加；
    - disclose 为真但 label 为空 -> ValueError。
    """
    raise NotImplementedError("实现 AI 内容标识")
