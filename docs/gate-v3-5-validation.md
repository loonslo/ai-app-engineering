# V3-5 L4-B 状态图、执行面、沙箱、MCP 与异步 Agent 验证 · 2026-10-31

本批次改了什么：按 `docs/v3/specs/L4B.md` 增补 4.2/4.3/4.4/4.6/4.10/4.11 的 LangGraph 内容，改写 4.12 的 Agent 安全，新增 4.19 执行面、4.20 沙箱、4.21 MCP 实战、4.22 复用 harness（清单）、4.23 异步 Agent Gate，改写 4.15 框架素养并新增 `create_agent_langchain.py`。没改 `flagship-project/`。

实施线程中途两次因额度中断，最后由审核者（我）补完并复跑：修了 4.20 在 Windows 上路径分隔符不一致导致符号链接检查失败、4.12 在 Windows 上 SQLite 连接未关闭导致临时目录删除 `PermissionError`、4.19 一处 ruff E731。

## 范围

| v3 编号 | 目录 | 类型 |
|---|---|---|
| L4.9 | `4.2`、`4.3`、`4.4`、`4.6` | 增补 |
| L4.10 | `4.10`、`4.11` | 增补 |
| L4.11 | `4.19-agent-execution-plane` | 新增 · gate |
| L4.12 | `4.20-sandbox-least-privilege` | 新增 · gate |
| L4.13 | `4.12-tool-safety-search` | 换实现 + 增补 · gate |
| L4.14 | `4.21-mcp-practice` | 新增 · gate |
| L4.15 | `4.22-reuse-harness` | 新增 · 清单（选做） |
| L4.16 | `4.15-framework-landscape` | 改写 · 清单 + 练习 |
| L4.17 | `4.23-async-agent-gate` | 新增 · gate + 产物 |

另改 `tools/course_catalog.py`、`requirements-course.txt`、`requirements-dev.txt`、`chapters/test_new_lessons.py`、`chapters/test_v3_lessons.py`。

## 实际执行

| 检查 | 结果 |
|---|---|
| gate 骨架（11 个） | 全部退出 1 |
| gate 参考解 `--module .tmp/gate_solutions/v3/<章>.py` | 4.2 4/4、4.3 4/4、4.4 5/5、4.6 7/7、4.10 6/6、4.11 4/4、4.12 5/5、4.19 16/16、4.20 24/24、4.21 18/18、4.23 13/13，共 106，退出 0 |
| 参考解连跑两次（4.19/4.20/4.21/4.23） | 输出一致 |
| `pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py capstone/test_regression.py` | 103 passed |
| `tools/check_course_links.py` | 387 篇，0 断链 |
| `ruff check --target-version py311 chapters/part3-evals chapters/part4-agents-langgraph common.py tools chapters/test_v3_lessons.py chapters/test_new_lessons.py` | 通过 |
| `apply_v2_map.py --check` | 111 unchanged |
| `apply_v3_map.py --check` | 4.19–4.23 均 unchanged；旧章节 inserted 属 V3-10 前的约定状态 |
| 新章节导入 LangChain/LangGraph | 新目录 4.19–4.23 无命中；`create_agent_langchain.py` 是保留的框架对照 |
| 离线运行（4.2、4.3 各脚本、4.4、4.6、4.12、4.19、4.20、4.21、4.23、4.15 对照） | 退出 0 |
| `--live`（DeepSeek `deepseek-flash`，单次） | 4.3、4.6、4.12 成功退出 0（`.env` 提供密钥） |
| `--live` 模型不可达（`127.0.0.1:9`） | 4.10、4.12、4.3、4.6 均退出 1，无堆栈 |

## 未验证 / 已知边界

- `--live` 缺密钥：`.env` 会补上密钥，这次没有构造无密钥环境，只测了不可达。
- 4.10 的 live：本机未装 `langmem`，只打印安装提示后退出 0，真实记忆路径未跑。
- 4.11 离线入口读 `input()`，非交互终端下 `EOFError`；这是原有行为，没有改。
- 4.20 只生成容器命令，不执行 Docker；容器隔离的真实效果、4.22 的实操部分、4.21 连接真实 MCP 服务、4.23 真实模型路径均未验证。
- 4.19–4.23 的 `--live` 成功路径未跑。
