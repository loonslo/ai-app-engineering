"""语料库下载与校验工具 (Corpus Fetcher & Hash Verifier)

从 SOURCES.md 定义的开放许可证来源下载并严格校验语料 SHA256 哈希。
支持 --dry-run 离线清单校验。
若哈希不匹配或下载异常，立即清理受损文件并以非 0 状态码退出。
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
CORPUS_DIR = HERE / "corpus"
DOWNLOAD_DIR = CORPUS_DIR / "downloads"

# 24 份固定版本与校验哈希的公开语料清单
CORPUS_MANIFEST = [
    {
        "id": "python-tutorial-zh",
        "url": "https://raw.githubusercontent.com/python/python-docs-zh-cn/615a836a374685116e0742508bf4961b50b9c403/tutorial/introduction.po",
        "sha256": "008139317c1882d3a2bf83a51a06103dfff3a9626991f73cb49c01db7777cc80",
        "license": "PSF License",
        "ext": "po",
    },
    {
        "id": "semver-spec-zh",
        "url": "https://raw.githubusercontent.com/semver/semver.org/2cb4b39883d522b81ec42334730043dc541bfec9/lang/zh-CN/spec/v2.0.0.md",
        "sha256": "2fb860381902eaaf11fd75d10a037ce83a10c1e88742fe0933ad7ecb7c6a35b2",
        "license": "CC BY 3.0",
        "ext": "md",
    },
    {
        "id": "table-pdf-background-checks",
        "url": "https://raw.githubusercontent.com/jsvine/pdfplumber/v0.11.4/examples/pdfs/background-checks.pdf",
        "sha256": "4f0ae6e017b0e97de211da8fd97316e55bd927af5740d6ce95e1b7b1539f9407",
        "license": "Public Domain (U.S. Govt)",
        "ext": "pdf",
    },
    {
        "id": "scanned-fax-ccitt",
        "url": "https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/v16.0.4/tests/resources/ccitt.pdf",
        "sha256": "5f4b129bf0eb0d32358a917cd1754c6fd68cac589ad79076b6d0191ebe84f0f1",
        "license": "GFDL-1.2-or-later or CC-BY-SA-3.0",
        "ext": "pdf",
    },
    {
        "id": "linux-cmd-find",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/find.md",
        "sha256": "4952a88fdfab14cb1f01a88f5565f57af270d2cae12b77f2b76c099d37c98e03",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-tar",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/tar.md",
        "sha256": "19d0d51de187922465c50470596164f819279949902b5a5258e0b789914d1603",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-grep",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/grep.md",
        "sha256": "bbeb99dc3e6f0157331e680545f61602fc66390e99edc21777e2332c49249663",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-awk",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/awk.md",
        "sha256": "9c475c5210217752785f27656512d250b3cfce8b0c5cfb838cfabd18146344ae",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-sed",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/sed.md",
        "sha256": "e28669a08411f6a9198c0301ee0e0a52912105acc2dd5ecb5e2f549c8f4b1ff2",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-curl",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/curl.md",
        "sha256": "ac8ad9db83037507f37b17df755eece611f5d60f3ad0eeca4b0c1765d48ef14c",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-chmod",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/chmod.md",
        "sha256": "533230f9143c8955e83e5b5f028534e775dd7d605d7d46c27eaf66513f3b0e04",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-chown",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/chown.md",
        "sha256": "4df9e179cfa13f87a61a42ec177a3500b3dd2bae4f9803215be0235e2f1dccc9",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-ps",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/ps.md",
        "sha256": "c71487b72524b04de4d9357093b3f0ec381547757dbb67102bd6777ba55ef48f",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-top",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/top.md",
        "sha256": "02c05e17cbaec71a8500e0f942f58c5f485c9bd4f965526ecfc5bb9743c83769",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-kill",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/kill.md",
        "sha256": "9b28e0c5f0caa2bc115e436443e6d0a97dc69e8e7da2b8c5e212dac34382ee99",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-ping",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/ping.md",
        "sha256": "ec596e397ed0c0d24a3426f477771f9c0dfd32ad11ce8fb7181e3f9c340da3d3",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-crontab",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/crontab.md",
        "sha256": "e8033dbe6fdfe1d13ab640dcf177e5f36e001d6b3de08f7a9bb003863c0d2cc9",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-df",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/df.md",
        "sha256": "3b1708d0f30feb4b76ab58d692149f8466549d2f3fd1024e040b8c58860e58d8",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-du",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/du.md",
        "sha256": "c361ec1b7a9958bdc2f780cae7d61bbfdd42a8c692dde917ae36e1c332b9ab4a",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-cat",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/cat.md",
        "sha256": "542fdcad28787c2381684f96bf344417bea82bcea0aa9956e294dd2db4b2bd5f",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-diff",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/diff.md",
        "sha256": "3713620baa7c994055eda779833381d5c48b94ab9716bd07a5038ee07af06928",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-ssh",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/ssh.md",
        "sha256": "a93bf5c02d7d1fe7b08e2926a3459edc5450dd66b2ff21c903a1e70fabb058b1",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-git",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/git.md",
        "sha256": "05dc4acba874548da20abbffdd2971683ffd4a3e3a0b190a6a34ffe478dd29e4",
        "license": "MIT",
        "ext": "md",
    },
    {
        "id": "linux-cmd-docker",
        "url": "https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/docker.md",
        "sha256": "e6f02eb0659db1095acecbab1e78386c8f2a2da0c2cf1021d6e2db6313f916ff",
        "license": "MIT",
        "ext": "md",
    },
]


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_all(dry_run: bool = False) -> int:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"语料目标目录：{DOWNLOAD_DIR}")
    print(f"计划拉取/校验文档数：{len(CORPUS_MANIFEST)}")

    if dry_run:
        # 严格检查每份文档配置：URL 必须是固定 commit (40 位十六进制) 或 release tag (如 v0.11.4)
        for item in CORPUS_MANIFEST:
            url = item["url"]
            sha = item["sha256"]
            lic = item["license"]
            has_fixed_commit = any(len(seg) == 40 and all(c in "0123456789abcdefABCDEF" for c in seg) for seg in url.split("/"))
            has_fixed_tag = "/v" in url and any(seg.startswith("v") and "." in seg for seg in url.split("/"))
            if not (has_fixed_commit or has_fixed_tag):
                print(f"[DRY-RUN-FAIL] 语料 {item['id']} 的 URL 未指向固定 commit 或 tag：{url}")
                return 1
            if len(sha) != 64 or not all(c in "0123456789abcdef" for c in sha):
                print(f"[DRY-RUN-FAIL] 语料 {item['id']} 的 sha256 格式不合法：{sha}")
                return 1
            if not lic.strip():
                print(f"[DRY-RUN-FAIL] 语料 {item['id']} 缺少明确许可证")
                return 1

        print("[DRY-RUN] 清单配置校验通过：全部 24 份文档均配置固定 URL (commit/tag)、有效 SHA256 与明确许可证。")
        for item in CORPUS_MANIFEST:
            print(f"  - [{item['license']}] {item['id']}.{item['ext']} (sha256: {item['sha256'][:12]}...)")
        return 0

    success = 0
    for item in CORPUS_MANIFEST:
        dest = DOWNLOAD_DIR / f"{item['id']}.{item['ext']}"
        expected_hash = item["sha256"]

        if dest.exists():
            data = dest.read_bytes()
            h = compute_sha256(data)
            if h == expected_hash:
                print(f"[EXISTS-OK] {dest.name} 哈希匹配 (sha256: {h[:12]}...)")
                success += 1
                continue
            print(f"[MISMATCH] {dest.name} 本地文件哈希不匹配，已删除重新拉取...")
            dest.unlink(missing_ok=True)

        print(f"[FETCHING] {dest.name} 从 {item['url']} ...")
        try:
            req = Request(item["url"], headers={"User-Agent": "AntigravityCorpusFetcher/1.0"})
            with urlopen(req, timeout=15) as resp:
                data = resp.read()
            actual_hash = compute_sha256(data)
            if actual_hash != expected_hash:
                print(f"[FATAL-HASH-ERROR] {dest.name} 下载内容哈希与预期不符！")
                print(f"  预期: {expected_hash}")
                print(f"  实际: {actual_hash}")
                return 1
            dest.write_bytes(data)
            print(f"[OK] 已保存并校验 {dest.name} (sha256: {actual_hash[:12]}...)")
            success += 1
        except (URLError, TimeoutError, OSError) as exc:
            print(f"[NETWORK-ERROR] 下载失败 {item['id']}: {exc}")
            dest.unlink(missing_ok=True)
            return 1

    print(f"\n完成：全部 {success}/{len(CORPUS_MANIFEST)} 份语料下载并校验成功。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Corpus fetcher and SHA256 verifier")
    parser.add_argument("--dry-run", action="store_true", help="只校验清单，不发起网络请求")
    args = parser.parse_args()
    return fetch_all(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
