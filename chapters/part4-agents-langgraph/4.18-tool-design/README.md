# L4.3 工具设计 · Gate

[全书目录](../../README.md) · [上一章 L4.2](../4.5-react-agent/README.md) · [下一章 L4.4（4.7）](../4.7-structured-routing/README.md)

- **能力**：为订单客服设计有 schema、权限、幂等、分页与可读错误的工具。
- **v3 路径**：L4.3 / 核心（Gate；工具设计）
- **岗位任务 / 面试题型**：T3 / F3、F4
- **前置**：L4.2 有界循环、L1 工具调用。
- **时间盒**：6 小时（2h 读 + 3h 实现 + 1h 记录）。
- **闭卷规则**：只读本页、`gate/starter.py` 和标准库官方文档；通过前不要打开 `tool_design.py`。
- **验收命令**：

```bash
python chapters/part4-agents-langgraph/4.18-tool-design/gate/gate_check.py
```

全部 PASS 才算通过；脚本写 `gate/gate_report.json`，不允许修改 gate_check.py 绕过检查。

## 为什么做这个 gate

工具是给“不确定的调用方”使用的契约：模型可能选错工具、遗漏参数，或重复提交一次写请求。函数能执行，不等于模型知道何时该调用、输入什么、失败后怎么办。

Anthropic《[Writing effective tools for agents](https://www.anthropic.com/research/writing-tools-for-agents)》（2025-09，读取于 2026-10-31）讨论了明确工具边界、命名空间、可读输出、截断和描述优化。本章把这些建议缩成可离线验收的订单客服工具，而不是把原文建议当作安全保证。

## 概念

| 设计点 | 订单客服中的具体做法 |
|---|---|
| 命名与命名空间 | `get_order` 比 `do_action` 清楚；多个业务域可用 `orders_get_order`、`billing_get_invoice`，不要混用含糊名字 |
| 描述写给模型 | 说清何时用、返回什么、不做什么；例如“创建退款申请，不代表已退款” |
| 参数 schema | `required` 定义必填项，`enum` 限定状态，`description` 解释含义；编号格式在 handler 中检查，不能只写说明 |
| 错误即上下文 | “缺少 order_id；建议补编号”能指导修正；堆栈既费 token，也可能泄露内部信息 |
| 幂等键 | 同一次写请求重试复用同一键，避免重复退款；这不同于“所有退款都用一个键” |
| 权限与确认 | 读权限不包含写权限；人工确认是意图边界，权限是身份边界，都在执行前检查 |
| 分页、筛选、截断 | 先按状态筛选，再用 page 取一页；截断告诉调用方原长度和如何继续，不把残缺 JSON 当完整对象 |
| 工具筛选 | 先按任务检索相关工具，再延迟加载描述，减少上下文里的无关选择；本章仅用关键词基线 |

工具多并不必然更好：描述重叠会增加选择歧义。`select_tools` 用英文词、数字、下划线和中文单字做集合交集；同分保留输入顺序，不冒充语义检索质量评测。

**代码化工具调用（programmatic tool calling）**：让受限程序编排多个工具，只把需要的中间结果交还模型，区别于每次工具调用都由模型往返决策。[OpenAI changelog](https://developers.openai.com/api/docs/changelog) 的 2026-07-09 条目列出了这一功能（读取于 2026-10-31）。这里只解释概念，不实现执行生成代码的沙箱；也不把 Responses 专属能力假定为所有 Chat Completions 服务都支持。

## 任务

实现 starter 的 `ToolSpec`、`ToolResult` 所配套的五个函数：

| 函数 | 输入 → 输出 / 失败行为 |
|---|---|
| `validate_tool_spec` | 工具契约 → 问题列表，合格 `[]` |
| `validate_args` | 契约 + 参数 → 必填、类型、枚举、多余字段问题列表 |
| `format_tool_error` | 错误种类、原因、建议 → 固定中文格式 |
| `execute_tool` | 参数校验 → 权限 → 幂等缓存 → 执行 → 截断 → 成功缓存 |
| `select_tools` | 任务 + 工具列表 + limit → 按重合关键词排序的名称 |

## 关键约定

- 名称为 3–64 字符，匹配 `^[a-z][a-z0-9_]{2,63}$`；描述 20–1024 字符；每个参数有非空 description。
- 本章支持平面 object schema；属性类型为 string/integer/number/boolean，可有 enum。integer、number 都不接受 bool，不做隐式类型转换。
- write 工具必须有必填的 string `idempotency_key`；读工具不缓存。每个租户、每个工具使用独立缓存，失败不缓存。生产系统还要对同键不同参数做冲突检测，本接口未实现该协议。
- 超长结果保留前 `max_result_chars` 个字符，再追加 `（已截断，共 N 字，可用 page 参数翻页）`。上限是正文上限，不包含提示。
- `ToolResult.error_kind` 为 `invalid_args`、`permission_denied`、`tool_error` 或 `None`。参数校验先于权限，权限先于缓存。
- `limit <= 0` 返回 `[]`；没有相关词时仍按原顺序取前 limit 个。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 / 对应检查 |
|---|---|---|
| 1 | 大写/连字符名、短描述、参数没描述 | 契约问题，02–04 |
| 2 | write 缺幂等键 | 契约问题，05 |
| 3 | 缺必填、bool 当页码、枚举外值、多余 tenant_id | invalid_args，06–09、16 |
| 4 | 无读权限 | 拒绝且不执行，10 |
| 5 | 同一写键调用两次，再撤销权限重试 | 仅执行一次，撤权后不读缓存，11 |
| 6 | handler 抛异常 | tool_error + 修正建议，12、15 |
| 7 | 返回十字、正文上限四字 | 截断并提示翻页，13 |
| 8 | 相关工具并列、limit=0 | 稳定排序与数量上限，14 |

## 验收标准

16 项：合法契约 1 项、契约故障 4 项、参数故障 4 项、权限与幂等 2 项、异常与截断 2 项、筛选 1 项、错误格式 1 项、执行顺序与合法参数 1 项。

## 提交物

实现后的 starter、16/16 gate_report、[workbook](workbook.md) 的预测、故障分析与解释题。

## 通过后对照参考实现

```bash
python tools/run_chapter.py 4.18 tool_design.py
python tools/run_chapter.py 4.18 tool_design.py --live
```

默认复用 L4.2 原生循环，演示查订单、分页、退款待确认；另用明确标注的独立“已确认调用”演示幂等，不自动替当前用户审批。`--live` 通过 L4.2 的 common 工厂调用模型；缺钥或不可达以 1 退出，无未捕获堆栈。
该 live 适配器对 DeepSeek 显式关闭思考模式；真实服务是否支持这些工具参数仍需单独实测。订单仍是本地合成数据，不查询真实客户。

对照：① schema 校验与业务格式校验分别在哪里？② 为什么缓存命中仍需权限？③ 只筛选不分页，为什么仍可能浪费 token？

## 概念地图

工具契约 → 参数校验 → 身份权限 → 写入确认 → 幂等执行 → 精简结果 → 有界循环。

## 边界

内存订单、单进程缓存和关键词筛选只证明控制流，不证明真实模型会选对工具。缓存没有持久化、并发原子性或同键异参冲突检查；工具异常文本在真实服务中应进一步脱敏。租户身份由宿主注入，不能相信模型传入的身份。包装不可信结果不能单独消除提示注入；写权限与审批必须独立于模型判断。
