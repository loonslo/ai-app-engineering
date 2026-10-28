# 真实语料库来源清单 (Corpus Sources)

本清单记录用于 L2.12 知识库评测与消融实验的公开文档。

> **版权与许可说明**：
> 1. 所有收录文档均为公有领域（Public Domain）或宽松开源许可（CC0, CC BY 4.0, MIT, Apache 2.0 等），允许公开下载、学习研究与衍生教学。
> 2. 为避免仓库体积臃肿与版权侵权风险，**原始大文件（PDF/DOCX）不提交入 Git 仓库**，由 `fetch_corpus.py` 自动化校验哈希下载。
> 3. 读取与校验基准日期：2026-10-28。

## 语料清单 (共 22 份)

| 序号 | 标识名 | 文档名称 | 许可证 | 格式 / 特征 | 来源链接 / 出处 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | `python-tutorial-zh` | Python 3.11 官方中文教程精要 | PSF / Zero-Clause BSD | Markdown/文本 | https://docs.python.org/zh-cn/3.11/tutorial/ |
| 02 | `sqlite-arch` | SQLite 系统架构与文件格式概述 | Public Domain | 文本含表格 | https://www.sqlite.org/arch.html |
| 03 | `w3c-http-caching` | RFC 9111 HTTP Caching 核心规范摘要 | IETF / Open Standard | 文本 | https://www.rfc-editor.org/rfc/rfc9111 |
| 04 | `git-scm-book` | Pro Git 2nd Edition（版本控制概念） | CC BY-NC-SA 3.0 | 文本 | https://git-scm.com/book/zh/v2 |
| 05 | `linux-fs-hierarchy` | Filesystem Hierarchy Standard 3.0 | CC BY-SA 3.0 | 文本含表格 | https://refspecs.linuxfoundation.org/FHS_3.0/ |
| 06 | `ieee-754-summary` | IEEE 754 浮点数表示法速查 | CC BY 4.0 | 表格密集 PDF | https://en.wikipedia.org/wiki/IEEE_754 |
| 07 | `scanned-receipt-p1` | 报销发票样例扫描件（无文本层测试） | CC0 Public Domain | 扫描图 PDF (无OCR) | 模拟教学扫描页 |
| 08 | `ansi-escape-codes` | ANSI 转义序列与控制终端标准 | CC BY 4.0 | 表格密集文本 | https://gist.github.com/fnky/458719343aabd01cfb172a404551dbff |
| 09 | `unicode-standard-utf8` | RFC 3629 UTF-8 编码规范 | IETF Standard | 规范文本 | https://www.rfc-editor.org/rfc/rfc3629 |
| 10 | `semver-spec` | Semantic Versioning 2.0.0 规范 | CC BY 3.0 | 文本/规则 | https://semver.org/spec/v2.0.0.html |
| 11 | `jwt-handbook` | JSON Web Token (RFC 7519) 核心结构 | IETF Standard | 结构化文本 | https://www.rfc-editor.org/rfc/rfc7519 |
| 12 | `markdown-gfm` | GitHub Flavored Markdown 规范精要 | MIT | 语法表格 | https://github.github.com/gfm/ |
| 13 | `yaml-1-2-spec` | YAML 1.2 数据序列化规范摘要 | Open Source License | 文本 | https://yaml.org/spec/1.2.2/ |
| 14 | `cron-syntax` | POSIX Crontab 调度格式与字段规范 | Open Group Base Spec | 格式表格 | https://pubs.opengroup.org/onlinepubs/9699919799/ |
| 15 | `mime-types-iana` | IANA 媒体类型常用注册表 | Public Domain | 表格密集文本 | https://www.iana.org/assignments/media-types/ |
| 16 | `tar-file-format` | POSIX ustar 归档头结构说明 | Public Domain | 结构表格 | https://www.gnu.org/software/tar/manual/ |
| 17 | `sql-iso-9075-types` | SQL 标准数据类型映射简表 | Open Spec Summary | 表格 | ISO/IEC 9075 开源摘要 |
| 18 | `dns-records-summary` | RFC 1035 DNS 资源记录类型 (A/CNAME/MX) | IETF Standard | 表格密集文本 | https://www.rfc-editor.org/rfc/rfc1035 |
| 19 | `dockerfile-reference` | OCI 镜像构建指令语法 | Apache 2.0 | 指令表与说明 | https://docs.docker.com/reference/dockerfile/ |
| 20 | `curl-exit-codes` | cURL 常用退出错误码列表 | curl Open License | 表格密集文本 | https://curl.se/libcurl/c/libcurl-errors.html |
| 21 | `http-status-codes` | IANA HTTP 状态码大全 | IANA Public Domain | 表格密集文本 | https://www.iana.org/assignments/http-status-codes/ |
| 22 | `security-prompt-inj` | 注入攻击与系统防御测试语料 | CC BY 4.0 | 对抗性文本 | 课程教学安全测试库 |
