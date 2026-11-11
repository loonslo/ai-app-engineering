# L1.4 上下文与记忆 · Gate（原 1.4）

[全书目录](../../README.md) · [上一章 L1.4](../1.3-structured-output/README.md) · [下一章 L1.6](../1.5-tool-calling/README.md)

- **能力**：按会话隔离历史；在字符预算内保留最近上下文；system 消息永不被裁掉。
- **v3 路径**：L1.5 / 核心（Gate；上下文与记忆）
- **前置**：1.1（一次调用）。
- **时间盒**：5 小时（1h 读 + 3h 实现 + 1h 故障分析）。
- **闭卷规则**：只读本页和 `gate/starter.py`；**通过 gate 之前不要打开** `context_memory.py`。
- **验收命令**：

```bash
python chapters/part1-foundations/1.4-context-memory/gate/gate_check.py
```

全部 PASS 才算通过；脚本会写 `gate/gate_report.json`。不允许改 `gate_check.py` 绕过检查。

## 为什么做这个 gate

多轮对话最容易被忽略的是“历史越来越长”：

- 不同用户/会话串台；
- 历史无限增长，token 成本和延迟失控；
- 裁剪时把 system 规则裁掉，模型开始不守约束；
- 裁剪后顺序乱了，模型看到错乱的对话；
- 返回历史列表的引用，外部一改就污染内部状态。

这个 gate 把记忆拆成 **会话隔离 + 历史副本 + 预算裁剪**，用固定字符预算做确定性验收。

## 任务

实现 `gate/starter.py` 的两个部分：

| 部分 | 你要交付的行为 |
|---|---|
| `SessionMemory` | `add` 校验 session/role/content；`get` 返回副本；`clear` 幂等 |
| `trim_history` | system 永远保留；非 system 从最新往前选，遇到放不下就停；不改输入、不乱序 |

关键口径：

- `role` 只允许 `system` / `user` / `assistant`；不合法抛 `MemoryError`。
- `get` 返回副本；调用方修改返回值不能影响内部历史。
- `max_chars < 0` 抛 `ValueError`；空列表返回 `[]`。
- 字符预算按 `len(content)` 计算；不截断单条消息。
- system 消息可以超预算，但必须保留并放在最前。
- 非 system 消息从最新往前选；第一条放不下就停止（不跳过去选更旧的）。

## 故障注入（必须亲手触发）

| # | 注入 | 期望 |
|---|---|---|
| 1 | 两个 session 各写一条 | 互不串台 |
| 2 | 修改 `get()` 返回的列表 | 内部历史不变 |
| 3 | `role="tool"` / 空 session / content 非字符串 | `MemoryError` |
| 4 | 预算为 0 | 只保留 system |
| 5 | system 本身超预算 | 仍然保留 |
| 6 | 最近一条放不下 | 停止，不选更旧的小消息 |
| 7 | 负预算 | `ValueError` |
| 8 | 消息缺 role/content | `ValueError` |
| 9 | 裁剪后检查原输入 | 不被修改 |

## 验收标准

`gate_check.py` 的 12 项全部 PASS：

- 会话：追加/读取、隔离、副本、清空、非法输入。
- 裁剪：预算足够、超预算保留最近、system 保留、顺序/不修改、空历史、负预算、非法消息。

通过后，在 [workbook.md](workbook.md) 写：

1. 为什么 `get` 要返回副本？返回内部列表会出什么问题？
2. system 超预算时为什么仍保留？如果业务要求硬预算，怎么处理？
3. 真实 token 预算和 `len(content)` 有什么区别？生产里应怎么估？

## 提交物

- `gate/starter.py`（实现后的版本）。
- `gate/gate_report.json`（12/12）。
- workbook 里的失败分析与三个问题的回答。

## 通过后对照参考实现

不要提前看。通过后再运行并对照：

```bash
python chapters/part1-foundations/1.4-context-memory/context_memory.py
```

参考实现改用原生的 `messages` 列表管理多轮会话，并演示了基于滑动窗口的预算裁剪与对话摘要压缩。

> [!NOTE]
> **章节边界与进阶指引**：
> 本章只聚焦于**单会话内的滑动窗口预算管理与基础隔离**。关于复杂长上下文的结构化工程设计（Context Engineering）详见 [L2.1](../../part2-rag/2.1-load-split/README.md)；跨会话长期记忆、实体抽取与分层压缩机制详见 [L2.10](../../part2-rag/2.10-chroma-persist/README.md)。

对照时思考并回答：

1. 为什么在多轮对话中盲目将全部历史发给模型不仅成本飙升，还会因为“Lost in the Middle”效应导致模型指令遵循能力下降？
2. 为什么在裁剪历史时，System Prompt 必须永远无条件保留在最前面？
3. 在生产环境中，若会话达到数万 Token，阶段性摘要（Summarization）与直接丢弃旧消息相比各有什么优缺点？

## 概念地图

- **模型无状态**：记忆是程序每次把历史重新放进 prompt。
- **会话隔离**：session_id 相同的才共享历史；不隔离会串台。
- **历史副本**：对外返回副本，避免外部修改内部状态。
- **预算裁剪**：保留最近上下文，system 规则优先；裁剪策略要可解释。
- **持久化**：内存历史程序退出即丢；生产用 checkpoint/数据库。

## 边界

- gate 用字符预算做确定性验收，不是真实 token 计数。
- 通过 gate 只证明会话/裁剪结构正确，不验证真实多轮回答质量。
- 摘要、长期记忆、跨会话偏好见 L4.6。
