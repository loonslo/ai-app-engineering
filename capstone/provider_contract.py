"""验证统一模型工厂与 provider 能力边界。"""

from __future__ import annotations

import argparse
from dataclasses import asdict

from common import (
    provider_capabilities,
    validate_provider_configuration,
)

from .llm import get_chat


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--invoke",
        action="store_true",
        help="执行一次真实模型调用；默认只检查配置，避免意外消耗额度",
    )
    parser.add_argument("--prompt", default="只回复：provider-ok")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_provider_configuration()
    if errors:
        for error in errors:
            print(f"配置错误：{error}")
        return 2
    capabilities = provider_capabilities()
    print("当前模型配置：")
    for key, value in asdict(capabilities).items():
        print(f"  {key}: {value}")
    print("配置检查：PASS")
    if not args.invoke:
        print("未调用模型；加 --invoke 才会产生真实网络请求和可能的费用。")
        return 0

    content = get_chat().complete([{"role": "user", "content": args.prompt}]).text
    if not content.strip():
        raise RuntimeError("provider 返回了空或非文本响应")
    print(f"真实调用：PASS（{content.strip()[:120]}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
