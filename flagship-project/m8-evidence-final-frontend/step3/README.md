# 里程碑 7.8 / step3 · 前端工作台对接 里程碑 7.8 / step2 API

[项目目录](../../README.md) · [上一步](../step2/README.md)

## 问题：网页怎样真正接上后端？

最后把用户输入、接口调用和结果展示接起来，处理认证、错误和反馈。页面好看还不够，要知道显示的来源、状态和事件来自哪个响应字段。

## 概念

前端管理交互和展示，API 客户端管理请求，后端执行权限与业务。浏览器中的令牌存储和错误提示需要与接口契约对应。

## 动手与观察

对接还原出的后端，分别观察正常回答、认证失败和网络失败；源码检查不能替代真实浏览器联调。

结果记入 [workbook.md](workbook.md)。

## 项目实现参考

里程碑 7.8 / step3 不再新增一套客服后端，而是把 里程碑 7.8 / step2 已经完成的能力接到一个独立的浏览器前端：

```text
浏览器页面（里程碑 7.8 / step3 / Vite）
  → /api 代理
  → 里程碑 7.8 / step2 FastAPI
  → JWT 身份校验
  → 统一业务应用
  → RAG / 会话 / 订单工具 / 工单 / 反馈
```

## 页面能演示什么

- JWT token 连接与本地保存
- 多轮客服问答和新会话切换
- 里程碑 7.8 / step2 返回的知识来源展示
- 订单号进入只读订单工具分支
- 人工工单编号展示
- 正负反馈进入 里程碑 7.8 / step2 `/feedback`
- API 在线状态和错误提示

前端不会自报 `user_id`，身份仍由 里程碑 7.8 / step2 的签名 token 决定；页面上的 token 输入框是为了让 里程碑 7.4 / step3 的可信身份能力可以在演示中被看见。

## 运行 里程碑 7.8 / step2 后端

先在仓库根目录还原最终后端：

```bash
python tools/materialize.py flagship m8-evidence-final-frontend/step2
cd .build/flagship/m8-evidence-final-frontend/step2/customer-support
uv sync
```

设置 里程碑 7.8 / step2 所需环境变量：

```bash
export JWT_SECRET="里程碑 7.8 / step3-local-secret-at-least-32-characters"
export LLM_API_KEY="你的 DeepSeek Key"
uv run uvicorn customer_support.runtime:create_runtime_api --factory --reload --port 8000
```

PowerShell 对应写法：

```powershell
$env:JWT_SECRET = "里程碑 7.8 / step3-local-secret-at-least-32-characters"
$env:LLM_API_KEY = "你的 DeepSeek Key"
uv run uvicorn customer_support.runtime:create_runtime_api --factory --reload --port 8000
```

## 生成本地演示 token

保持后端虚拟环境可用，在仓库根目录另开一个终端运行：

```bash
export JWT_SECRET="里程碑 7.8 / step3-local-secret-at-least-32-characters"
uv run --project .build/flagship/m8-evidence-final-frontend/step2/customer-support python \
  flagship-project/m8-evidence-final-frontend/step3/scripts/issue_demo_token.py
```

把终端输出的 token 粘贴到 里程碑 7.8 / step3 页面右侧“连接后端”卡片中。

## 启动 里程碑 7.8 / step3 前端

```bash
cd flagship-project/m8-evidence-final-frontend/step3
npm install
npm run dev
```

打开 <http://127.0.0.1:5173>。`vite.config.js` 会把 `/api/*` 代理到 `127.0.0.1:8000`，因此本地开发不需要额外配置 CORS。

生产部署时可以设置 `VITE_API_BASE` 指向反向代理后的 里程碑 7.8 / step2 API；生产环境不应开放演示 token 生成脚本，也不应把 JWT 写入 URL。

## 验收

1. 未连接 token 时发送问题，页面应提示先连接身份。
2. 连接有效 token 后，发送“退款多久到账？”，页面应显示答案和 `refund.md` 来源。
3. 发送“那发票呢？”，验证会话上下文仍由 里程碑 7.8 / step2 保存。
4. 填写订单号后发送查询，验证请求包含 `order_id`。
5. 点击反馈按钮，验证 里程碑 7.8 / step2 `/feedback` 返回 202。
6. 输入错误 token，验证页面显示 401 并清除本地 token。
