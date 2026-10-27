"""章节 1.3 · 结构化输出的三种方式与防御性校验

知识点：
1. 方式一：JSON Object 模式（response_format={"type": "json_object"}）+ Pydantic 校验 + 失败修复重试
2. 方式二：工具即输出（Tool Calling），通过参数提取结构化数据
3. 方式三：严格模式（Structured Outputs / JSON Schema），及其上游厂商兼容性判定
4. 思考模型（Reasoning Models）与结构化提取的冲突与关闭策略

运行方式：
    python chapters/part1-foundations/1.3-structured-output/structured_output.py
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

# 导入共享配置与客户端工厂
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from common import chat_model_name, get_openai_client, provider_capabilities
except ImportError:
    chat_model_name = None  # type: ignore
    get_openai_client = None  # type: ignore
    provider_capabilities = None  # type: ignore


class SchemaError(ValueError):
    """模型输出不符合约定结构。"""


class CodeReviewModel(BaseModel):
    """代码审查领域数据模型。"""

    summary: str = Field(min_length=1)
    issues: list[str]
    score: int = Field(ge=1, le=10)


def _extract_json_str(text: str) -> str:
    """从可能包含 Markdown 围栏或前后闲聊文字的文本中提取 JSON 片段。"""
    # 优先匹配 ```json ... ``` 围栏
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    # 尝试提取首个 { 到末尾 }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()

    return text.strip()


def _check_schema_fields(data: Any, schema: dict[str, type]) -> None:
    if not isinstance(data, dict):
        raise SchemaError("解析结果非字典对象")

    for field, expected_type in schema.items():
        if field not in data:
            raise SchemaError(f"缺少必需字段: {field}")
        val = data[field]
        # Python 中 bool 是 int 的子类，需显式防御
        if expected_type is int and isinstance(val, bool):
            raise SchemaError(f"字段 {field} 类型应为 int，不能为 bool")
        if not isinstance(val, expected_type):
            raise SchemaError(f"字段 {field} 类型错误: 期望 {expected_type}，实际 {type(val)}")


def parse_model_json(
    text: str,
    schema: dict[str, type],
    repair_fn: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """解析并校验模型输出的 JSON。

    要求：
    - 接受纯 JSON、```json ... ``` 围栏、前后带闲聊说明的文字；
    - 按 schema 校验必需字段和类型；int 不接受 bool；
    - 解析或校验失败时，若提供 repair_fn，只调用一次修复；
    - 修复后仍失败抛 SchemaError；
    - 成功返回原始 dict。
    """

    def try_parse_and_validate(raw_str: str) -> dict[str, Any]:
        json_candidate = _extract_json_str(raw_str)
        try:
            parsed = json.loads(json_candidate)
        except Exception as exc:
            raise SchemaError(f"JSON 反序列化失败: {exc}") from exc
        _check_schema_fields(parsed, schema)
        return parsed

    try:
        return try_parse_and_validate(text)
    except SchemaError:
        if repair_fn is not None:
            repaired_text = repair_fn(text)
            return try_parse_and_validate(repaired_text)
        raise


def validate_code_review(data: dict[str, Any]) -> dict[str, Any]:
    """业务级代码审查结果校验与规范化。"""
    if not isinstance(data, dict):
        raise SchemaError("入参必须是 dict")

    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise SchemaError("summary 必须为非空字符串")

    issues = data.get("issues")
    if not isinstance(issues, list):
        raise SchemaError("issues 必须为列表")
    for issue in issues:
        if not isinstance(issue, str):
            raise SchemaError("issues 的元素必须全为字符串")

    score = data.get("score")
    if isinstance(score, bool) or not isinstance(score, int):
        raise SchemaError("score 必须为整数且不能为布尔值")
    if score < 1 or score > 10:
        raise SchemaError(f"score 必须在 1–10 之间，实际: {score}")

    return {
        "summary": summary.strip(),
        "issues": list(issues),
        "score": score,
    }


def demonstrate_three_approaches() -> None:
    print("=== 结构化输出三种实现对比 ===")
    print(
        """
| 方式 | 原理 | 厂商兼容性 | 失败特征与重试成本 | 典型适用场景 |
|---|---|---|---|---|
| **1. JSON Object 模式** | prompt 约定 + response_format={"type": "json_object"} | 几乎所有主流模型支持 | 格式必定是 JSON，但字段名可能拼错或漏字段；需 Pydantic 校验并重试 | 兼容绝大多数厂商的通用方案 |
| **2. 工具即输出 (Tool Calling)** | 绑定带有 JSON Schema 的工具函数，强制 tool_choice | 支持 Function Calling 的模型 | 字段契约约束强；但部分模型在思考模式下无法强制选择工具 | 需稳定 Schema 且支持工具调用的场景 |
| **3. 严格 JSON Schema** | response_format={"type": "json_schema", ...} 严格模式 | OpenAI gpt-4o 等，部分国内厂商暂不支持 | 服务端按有限状态机（CFG）约束生成，零字段漂移；但启动编译开销稍高 | OpenAI 生态下的首选方案 |
"""
    )

    if get_openai_client is None or chat_model_name is None:
        print("[提示] 无法导入 common 模块，跳过真实调用演示。")
        return

    try:
        client = get_openai_client()
    except Exception as exc:
        print(f"[提示] 未能初始化客户端（{exc}）。演示跳过真实网络请求。")
        return

    model = chat_model_name()
    sample_code = """
def add_user(user_id, name):
    sql = "INSERT INTO users VALUES ('" + user_id + "', '" + name + "')"
    db.execute(sql)
"""
    # 方式一：JSON Object 模式演示
    print(f"\n--- 1. 演示 JSON Object 模式（模型: {model}）---")
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个代码审查助手。请以严格的 JSON 对象返回，包含字段："
                "summary (str), issues (list[str]), score (int 1-10)。"
            ),
        },
        {"role": "user", "content": f"请审查以下代码片段：\n{sample_code}"},
    ]

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw_content = resp.choices[0].message.content or ""
        print(f"原始响应: {raw_content}")

        # 使用 Pydantic 校验
        validated = CodeReviewModel.model_validate_json(raw_content)
        print(f"Pydantic 校验通过: summary={validated.summary!r}, score={validated.score}")
    except ValidationError as val_err:
        print(f"[Pydantic 校验失败]: {val_err.errors()} -> 触发修复提示重试")
    except Exception as exc:
        print(f"[调用失败]: {type(exc).__name__}: {exc}")

    # 方式二：工具即输出 (Tool as Output)
    print("\n--- 2. 演示工具即输出 (Tool Calling) 模式 ---")
    tool_schema = {
        "type": "function",
        "function": {
            "name": "submit_code_review",
            "description": "提交代码审查结果报告",
            "parameters": CodeReviewModel.model_json_schema(),
        },
    }

    try:
        resp_tool = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个代码审查助手，必须调用 submit_code_review 提交审查结果。"},
                {"role": "user", "content": f"请审查以下代码片段：\n{sample_code}"},
            ],
            tools=[tool_schema],
            tool_choice={"type": "function", "function": {"name": "submit_code_review"}},
            temperature=0.0,
        )
        tool_calls = resp_tool.choices[0].message.tool_calls
        if tool_calls:
            call_args = tool_calls[0].function.arguments
            print(f"工具入参提取: {call_args}")
            review_obj = CodeReviewModel.model_validate_json(call_args)
            print(f"校验成功: issues={review_obj.issues}")
        else:
            print("模型未触发预期工具调用。")
    except Exception as exc:
        print(f"[工具调用异常]: {type(exc).__name__}: {exc} (注意：部分模型或开启思考模式时可能不支持强制 tool_choice)")

    # 方式三：严格 JSON Schema 能力判断
    print("\n--- 3. 严格 JSON Schema 模式兼容性判定 ---")
    caps = provider_capabilities() if provider_capabilities else None
    supports_strict = getattr(caps, "supports_json_schema", False)

    print(f"当前 Provider 能力声明 supports_json_schema: {supports_strict}")
    if supports_strict:
        print("环境支持严格 Schema，可安全使用 response_format={'type': 'json_schema', ...}。")
    else:
        print(
            "【能力降级】当前服务商未声明支持严格 JSON Schema（例如 DeepSeek 官方 Chat Completions 端点）；"
            "生产环境应降级采用方式一（JSON Object + 运行时校验）或方式二。"
        )


if __name__ == "__main__":
    demonstrate_three_approaches()
