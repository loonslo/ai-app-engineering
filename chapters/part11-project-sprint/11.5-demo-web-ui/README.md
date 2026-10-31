# P5 可演示前端 · 项目章

[全书目录](../../README.md) · [上一章 P4](../11.4-execution-plane-launch/README.md) · [篇首](../README.md) · [下一章 P6](../11.6-project-narrative/README.md)

- **目标**：给项目配一个能点开就用的最小页面：提问、展示引用、展示降级与“需要人工”状态、反馈按钮、可读的错误提示。
- **v3 路径**：P5 / 项目（清单验收）
- **岗位任务 / 面试题型**：T6 / F4
- **节奏**：3 小时，第 11–12 周。
- **前置**：[11.2 最小上线](../11.2-walking-skeleton-deploy/README.md)（有一个可调用的 API）。

## 为什么

面试官和潜在用户更愿意点开一个能用的页面，而不是读一份 README。页面不需要漂亮，需要把系统的**可信度信号**展示出来：答案来自哪里、什么时候降级了、什么时候需要人工。

## 最小前端需要的 5 个功能

1. **提问**：输入框 + 提交，提交中有状态；
2. **展示引用**：每条答案下列出来源；
3. **展示降级与“需要人工”状态**：当系统降级（例如换了备用模型、检索失败）或建议转人工时，页面要明确提示，而不是假装一切正常；
4. **反馈按钮**：“有用 / 没用”，写回 API，用于积累 golden set；
5. **错误提示**：网络失败、鉴权失败、限流、服务异常各自给出可读信息，不显示堆栈。

## 实现方式

默认用**零依赖的静态 HTML 加原生 JS**，由 FastAPI 的静态文件服务提供；不引入前端框架。偏全栈方向的学习者可以另用 TypeScript 重写（选修，不计入验收）。

最小示例在 [`example_static/`](example_static/)（`index.html`、`app.js`）。它调用下面约定的 API；你的服务字段不同时，改 `app.js` 顶部的适配函数即可。

### 约定的 API

与 [5.1](../../part5-production/5.1-serve-fastapi/README.md) 的参考实现一致：

| 接口 | 请求 | 响应（必需字段） | 可选字段 |
|---|---|---|---|
| `POST /chat` | `{"question": str, "user_id"?: str}` | `answer`、`sources`（字符串数组）、`conversation_id`、`trace_id` | `degraded`（bool，已降级）、`needs_human`（bool，建议转人工） |
| `POST /feedback` | `{"conversation_id": int, "rating": 1 或 -1, "comment"?: str}` | `feedback_id` | — |

鉴权：若服务要求 API key，页面从输入框读取并放在请求头 `Authorization: Bearer <key>`，**不要把 key 写进页面源码**。

### 在 FastAPI 里提供静态文件

```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="example_static", html=True), name="ui")
```

把这行放在所有 API 路由之后，避免静态路由吞掉接口。

## 模板

- [`templates/ui-checklist.md`](templates/ui-checklist.md)

## 产物与验收

见 [CHECKLIST](gate/CHECKLIST.md)。录制 1 分钟演示视频或截图，登记到[证据索引](../11.6-project-narrative/templates/evidence-index.md)。

## 常见失败

- 引用只在后端有，页面没展示；
- 降级时页面照常显示“成功”的样子；
- 把 API key 写进 `app.js` 并提交到公开仓库；
- 直接把后端的异常文本显示给用户。

## 边界

- 示例页面在无头 Chromium 里对着一个**假 API** 手动验证过一次：提问、降级与“需要人工”徽标、引用、反馈写回、429 的可读错误、答案中的 HTML 不被解析；没有对接真实服务，也没有做自动化测试。
- 示例页面没有做无障碍、移动端适配、流式输出、历史会话。
- 本章没有自动化前端测试；验收靠你自己的手动检查与录屏。
