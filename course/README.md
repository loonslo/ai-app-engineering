# 报销实战课程

从一张模拟发票开始，逐步做出能查询报销制度、提交申请和处理审批的应用。

## 第一课

[0.1 发票校验与异步请求](lesson_01/README.md)已经可以跟练。准备 Python 3.11 或更高版本，在仓库根目录运行以下命令。Windows 可以直接使用虚拟环境里的 Python。

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install pydantic==2.13.4 httpx==0.28.1 pytest==9.0.3
.venv/Scripts/python.exe -m pytest course/lesson_01/test_0_1.py -v
```

macOS 和 Linux 把 `.venv/Scripts/python.exe` 换成 `.venv/bin/python`。预期看到 `5 passed`。测试使用模拟接口，无需 API 密钥。

如果刚开始学 Python，可以先打开首课的测试文件，读懂负数金额的例子。把断言里的预期改错一次，看看失败信息指向哪一行，再改回来。读到异步请求时，可以对照测试看模拟接口如何返回数据。

## 后续章节

[22 篇课程大纲](../docs/course-outline-22-articles-v3.0.md#三22-篇实战文章总览)列出了完整学习顺序。报销系列的其余篇目仍在规划中。想继续动手，可以在[配套练习](../chapters/README.md)里选一个主题。
