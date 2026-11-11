# 1.6 MCP 入门：先连通一项工具

[全书目录](../../README.md) · [上一章 1.5](../1.5-tool-calling/README.md) · [下一章 1.7](../1.7-llm-internals/README.md)

- **目标**：用真实的 MCP 协议连通一个本机工具，分清客户端、服务端和模型三者的职责。
- **v3 路径**：选修 / 选修（被 L4.14 取代）
- **前置**：1.5。
- **环境**：最小示例离线运行，不需要模型和密钥，需要 `mcp` 包（见 `requirements-course.txt`）；完整示例 `mcp_agent.py` 另需 `langchain` 包（`create_agent`）和模型密钥。
- **命令**：`python tools/run_chapter.py 1.6 minimal_client.py`

## 问题

工具越来越多时，每个应用都重复写连接方式、工具列表和调用协议，难以维护。MCP 把这些交互约定统一起来。本章先用一个加法工具看懂连接过程，综合示例放到最后。

## 概念

- **三个角色**：服务端提供工具（名称、描述、参数 schema、执行入口）；客户端发现并调用工具；模型决定是否调用、调用哪个。模型的选择是另一层决策，MCP 只是工具连接协议。
- **传输**：stdio 由客户端把服务端脚本当子进程拉起，通过标准输入输出传递协议消息，只适合本机练习；streamable-http 用于常驻的远程服务。
- **三种原语**：Tools（可调用的函数，有些只读，有些有副作用）、Resources（只读资料）、Prompts（可复用的提示模板）。
- MCP 不解决租户授权、工具安全和业务审批，这些在第 10 篇学习。

## 流程

`minimal_client.py` 的一次运行：

```text
启动 minimal_server.py 子进程（stdio）
  → initialize：协议握手
  → list_tools：发现 add 及其参数 schema
  → call_tool(add, a=2, b=3)：服务返回 5
  → call_tool(add, a="不是整数")：参数校验失败，返回错误
  → 退出 async with：关闭会话和子进程
```

stdio 的 stdout 留给协议消息，服务端的诊断日志要写到 stderr，不能随意 `print`。

## 代码导读

先读最小示例，再读综合示例：

| 文件 | 内容 | 需要模型或服务 |
|---|---|---|
| [minimal_server.py](minimal_server.py) | 只有 `add` 一个工具，先读它的类型标注和 docstring | 否 |
| [minimal_client.py](minimal_client.py) | 启动子进程，做 `initialize`、`list_tools`、`call_tool` 三次协议调用 | 否 |
| [mcp_server.py](mcp_server.py) | 完整服务端：Tools、Resources、Prompts 各一组示例 | 否，由客户端拉起 |
| [mcp_server_http.py](mcp_server_http.py) | 同类工具改为 HTTP 常驻服务，需在单独终端运行 | 否 |
| [mcp_agent.py](mcp_agent.py) | 客户端全景 demo1–6：把 MCP 工具交给 Agent，含多服务与流式输出 | 是，需要 `DEEPSEEK_API_KEY`；涉及 Agent，学完第 4 篇再回看更容易理解 |

## 练习

1. 运行最小客户端：工具列表含 `add`，调用返回 5，非法参数被拒绝。
2. 改成 `a=7, b=8`，确认结果为 15；传入非整数，确认校验失败。
3. 写出客户端、服务端、模型三者的职责，说明这次离线实验实际用到了哪些角色。
4. 完成前三步后，再阅读 `mcp_agent.py` 的 demo1，看模型如何选择 MCP 工具。

在 [学习记录](workbook.md) 记录成功、非法参数和退出结果。

## 运行与边界

- 最小示例验证的是本机协议往返，没有验证模型选工具、HTTP 鉴权、部署或跨团队接入。
- 客户端使用 `sys.executable` 和服务端脚本的绝对路径，换工作目录后仍能找到服务端。
- 初始化失败或服务进程异常会使练习失败，先看终端报错，不要自动重试或改用远端服务。
- 参考：[MCP 服务端教程](https://modelcontextprotocol.io/docs/develop/build-server)。
