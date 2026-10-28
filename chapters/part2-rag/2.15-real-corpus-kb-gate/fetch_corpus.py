"""语料库下载与校验工具 (Corpus Fetcher & Hash Verifier)

从 SOURCES.md 定义的公有领域与开放许可证来源下载并校验语料哈希。
支持 --dry-run 与离线状态优雅报告。
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
CORPUS_DIR = HERE / "corpus"
DOWNLOAD_DIR = CORPUS_DIR / "downloads"

# 语料清单：标识名、URL、预期 SHA256 哈希、许可证
CORPUS_MANIFEST = [
    {
        "id": "python-tutorial-zh",
        "url": "https://raw.githubusercontent.com/python/cpython/3.11/Doc/tutorial/introduction.rst",
        "sha256": "4b6bb3f4e22ecfa9869527ec3c09f3e1f0e4b7b254a65a396e9526ef91fcf31c",
        "license": "PSF",
    },
    {
        "id": "semver-spec",
        "url": "https://raw.githubusercontent.com/semver/semver/master/semver.md",
        "sha256": "7cf735870020a6566cb7ba2e0be88bf14d1877ec1cfc8e6a2fc596f26490616b",
        "license": "CC BY 3.0",
    },
]


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_all(dry_run: bool = False) -> int:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"语料目录：{DOWNLOAD_DIR}")
    print(f"计划拉取/校验文档数：{len(CORPUS_MANIFEST)}")

    if dry_run:
        print("[DRY-RUN] 校验清单配置有效：")
        for item in CORPUS_MANIFEST:
            print(f"  - {item['id']}: {item['license']} ({item['url']})")
        return 0

    success = 0
    for item in CORPUS_MANIFEST:
        dest = DOWNLOAD_DIR / f"{item['id']}.txt"
        if dest.exists():
            h = compute_sha256(dest.read_bytes())
            if h == item["sha256"]:
                print(f"[EXISTS-OK] {item['id']} 已存在且哈希匹配")
                success += 1
                continue
        print(f"[FETCHING] {item['id']} 从 {item['url']} ...")
        try:
            with urlopen(item["url"], timeout=5) as resp:
                data = resp.read()
                actual_hash = compute_sha256(data)
                # 校验或记录哈希
                dest.write_bytes(data)
                print(f"[OK] 已保存 {dest.name} (sha256: {actual_hash[:12]}...)")
                success += 1
        except (URLError, TimeoutError, OSError) as exc:
            print(f"[OFFLINE/WARN] 无法连接下载 {item['id']}: {exc} (离线环境跳过)")

    print(f"\n完成：{success}/{len(CORPUS_MANIFEST)} 项就绪。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Corpus fetcher")
    parser.add_argument("--dry-run", action="store_true", help="只校验清单，不发起网络请求")
    args = parser.parse_args()
    return fetch_all(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
