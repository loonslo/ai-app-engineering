# 真实语料库来源清单 (Corpus Sources)

本清单记录用于 L2.12 真实资料知识库评测与消融实验的公开文档集合（共 24 份，以中文资料为主）。

> **版权与许可说明**：
> 1. 所有收录文档均为官方或知名开源社区发布的开放许可证材料（MIT, Apache 2.0, CC BY 3.0, CC BY-SA 4.0, PSF, MPL 2.0 等），允许公开下载、技术学习与衍生教学。
> 2. 特殊许可证限制声明：
>    - `MPL 2.0`（如扫描页样例）：弱写本开源许可，仅对修改后的原文件具有传染性，独立流水线与训练集使用不受影响；
>    - `CC BY 3.0` / `CC BY-SA 4.0` / `PSF`：必须保留署名（Attribution），衍生再分发须遵从对应条款；
>    - 本仓库仅收录合规文档，无任何闭源或商业限制（NC）冲突内容。
> 3. 为避免仓库体积冗余，**原始文档（特别是大文件与 PDF）不提交入 Git 仓库**，由 `fetch_corpus.py` 脚本依据固定 Tag / Commit 校验 SHA256 哈希后按需下载。
> 4. 读取、校验与哈希核对基准日期：2026-10-28。

## 语料清单 (共 24 份)

| 序号 | 标识名 | 文档名称 | 许可证 | 格式 / 特征 | 来源链接 / 出处 | 许可证链接 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | `python-tutorial-zh` | Python 3.11 官方中文教程（基础与数据结构） | PSF License | PO/文本（中文） | https://raw.githubusercontent.com/python/python-docs-zh-cn/3.11/tutorial/introduction.po | https://docs.python.org/3/license.html |
| 02 | `semver-spec-zh` | 语义化版本 2.0.0 中文规范全文 | CC BY 3.0 | Markdown（中文） | https://raw.githubusercontent.com/semver/semver.org/gh-pages/lang/zh-CN/spec/v2.0.0.md | https://creativecommons.org/licenses/by/3.0/ |
| 03 | `table-pdf-background-checks` | 员工背景审查标准表格样例 | MIT | 表格密集 PDF | https://raw.githubusercontent.com/jsvine/pdfplumber/v0.11.4/examples/pdfs/background-checks.pdf | https://github.com/jsvine/pdfplumber/blob/v0.11.4/LICENSE.txt |
| 04 | `scanned-fax-ccitt` | 传真扫描图像页样例（无文本层，用于失败测试） | MPL 2.0 | 图像扫描 PDF | https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/v16.0.4/tests/resources/ccitt.pdf | https://www.mozilla.org/MPL/2.0/ |
| 05 | `linux-cmd-find` | Linux find 查找指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/find.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 06 | `linux-cmd-tar` | Linux tar 归档压缩指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/tar.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 07 | `linux-cmd-grep` | Linux grep 正则检索指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/grep.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 08 | `linux-cmd-awk` | Linux awk 文本报表分析指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/awk.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 09 | `linux-cmd-sed` | Linux sed 流式编辑指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/sed.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 10 | `linux-cmd-curl` | Linux curl 网络传输指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/curl.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 11 | `linux-cmd-chmod` | Linux chmod 权限控制指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/chmod.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 12 | `linux-cmd-chown` | Linux chown 所有者管理指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/chown.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 13 | `linux-cmd-ps` | Linux ps 进程快照指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/ps.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 14 | `linux-cmd-top` | Linux top 实时进程监控指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/top.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 15 | `linux-cmd-kill` | Linux kill 信号发送指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/kill.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 16 | `linux-cmd-ping` | Linux ping ICMP 检测指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/ping.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 17 | `linux-cmd-crontab` | Linux crontab 定时调度指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/crontab.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 18 | `linux-cmd-df` | Linux df 磁盘空间查询指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/df.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 19 | `linux-cmd-du` | Linux du 目录使用量估算指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/du.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 20 | `linux-cmd-cat` | Linux cat 文件连接与打印手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/cat.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 21 | `linux-cmd-diff` | Linux diff 文本差异比对手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/diff.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 22 | `linux-cmd-ssh` | Linux ssh 远程安全连接手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/ssh.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 23 | `linux-cmd-git` | Linux git 版本控制命令速查手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/git.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
| 24 | `linux-cmd-docker` | Linux docker 容器运维指令手册 | MIT | Markdown（中文） | https://raw.githubusercontent.com/jaywcjlove/linux-command/f588698da9303c3a932c81694d7bee3371f33342/command/docker.md | https://github.com/jaywcjlove/linux-command/blob/master/LICENSE |
