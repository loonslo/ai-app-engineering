# L5.4 认证、授权与多租户 · 清单 + 产物

[全书目录](../../README.md) · [上一章 L5.3](../5.4-sqlite-persistence/README.md) · [下一章 L5.5](../5.7-security-guardrails/README.md)

- **目标**：说清认证与授权的区别；在检索层实现租户隔离（预过滤）；读懂 Postgres 行级安全（RLS）；写出多租户威胁模型；用 capstone 的权限测试证明隔离。
- **v3 路径**：L5.4 / 核心（清单验收）
- **岗位任务 / 面试题型**：T2、T5 / F3
- **前置**：L5.1（服务）、L5.3（持久化）、L2.8（检索）；核心阅读 [9.5 Postgres RLS](../../part9-enterprise-infra-optional/9.5-postgres-rls/README.md)。
- **环境**：只需要本仓库和 `.venv`；运行 `capstone` 的离线测试，不调用真实模型，不需要数据库服务。
- **时间盒**：5 小时（2h 读 + 2h 读测试与画图 + 1h 威胁模型）。

## 问题

多租户系统最危险的一类事故是“A 租户的用户看到了 B 租户的数据”。在 RAG 里它更隐蔽：越权的内容不是被直接展示，而是被检索出来塞进 prompt，模型再把它“复述”给用户。你要能回答三件事：这个请求是谁（认证）？他能看哪些数据（授权）？这条规则被哪个测试守着？

## 概念

1. **认证（authentication）与授权（authorization）**：认证回答“你是谁”，授权回答“你能做什么”。登录成功不等于能读所有文档。常见错误是只做了认证，数据层完全信任“已登录”这个事实。
2. **JWT 的常见坑**：[RFC 8725《JSON Web Token Best Current Practices》](https://www.rfc-editor.org/rfc/rfc8725)（2020-02，读取于 2026-10-31）列出了典型问题与对策：
   - **`alg=none` 与算法混淆**：攻击者把头里的算法改成 `none`，或把 RS256 改成 HS256；服务端必须自己指定允许的算法，不能信任令牌头里的 `alg`（RFC 8725 §2.1、§3.1）；
   - **audience（`aud`）与签发者（`iss`）校验**：不校验就可能把发给别的服务的令牌拿来用（§2.7、§3.8、§3.9）；
   - **过期时间（`exp`）**：令牌必须有有效期并在服务端校验；
   - **弱密钥**：用人类能记住的口令当 HS256 密钥会被离线暴力破解（§2.2、§3.5）；
   - **密钥轮换**：用 `kid` 标识当前密钥，支持新旧密钥并存一段时间再淘汰旧的。这条是通行做法，RFC 8725 没有逐条规定，具体做法以你使用的库和身份提供方的文档为准。
   - **不要信任令牌里的任何声明去做查找**：声明可能被用作注入或 SSRF 的入口（§2.9、§3.10）。
3. **检索层的租户隔离：预过滤 vs 后过滤**：
   - **预过滤**：检索时就把搜索范围限制在当前用户有权限的文档里（向量库的元数据过滤）。越权文档根本不会被召回。
   - **后过滤**：先检索 top-k，再把无权限的结果丢掉。越权文档已经被检索出来、进了流程，只是在最后一步被挡住；而且过滤后可能一条不剩或数量不足。若某个环节（缓存、日志、重排、上下文拼装）出现在过滤之前，就出现“授权空窗”——数据已经越界，只是没展示。
   - Thoughtworks 技术雷达第 34 期（2026-04）把 **Role-based contextual isolation in RAG** 列为 Assess：在索引时给每个分块打上基于角色的权限标签，查询时按已认证的身份限制检索范围，使模型拿不到未授权的上下文（来源：[Thoughtworks 技术雷达条目](https://www.thoughtworks.com/en-us/radar/techniques/role-based-contextual-isolation-in-rag)，读取于 2026-10-31）。Assess 的意思是“值得探索、了解它会如何影响你”，不是已被普遍采用的默认做法。
4. **Postgres RLS（行级安全）**：让数据库自己按策略过滤每一行，应用即使忘了写 `WHERE tenant_id = …` 也读不到别人的行。概念与演示见核心阅读 [9.5](../../part9-enterprise-infra-optional/9.5-postgres-rls/README.md)。RLS 是防线之一，不替代应用层的授权。
5. **缺省拒绝**：没有明确允许的权限规则就是拒绝；新文档默认不可见，新角色默认没有任何权限。
6. **审计日志**：谁、何时、对什么、做了什么、结果如何；记元数据，不记原文（见 [5.7](../5.7-security-guardrails/README.md) 的 `audit_record`）。

## 流程

按 [CHECKLIST](gate/CHECKLIST.md) 逐项完成；证据写在 [workbook.md](workbook.md)。

## 练习

1. 阅读核心阅读 9.5 与 [`capstone/permissions.py`](../../../capstone/permissions.py)，画出一个请求从认证到检索过滤的数据流（用 Mermaid 或手绘照片均可），标出每一步“身份”这个信息保存在哪里、在哪一步被用来过滤。
2. 运行：

```bash
python -m pytest capstone/test_production.py -q
```

   在输出里找到验证租户隔离与权限的测试（例如 `test_acl_defaults_to_deny`、`test_vector_acl_filter_is_applied_before_search`、`test_cross_tenant_retrieval_is_rejected`、`test_cache_key_isolation`、`test_jwt_round_trip_and_tamper_rejected`），读测试代码，逐条写出：它构造了什么场景、断言什么、如果被测代码有哪种缺陷这条测试会失败。
3. 按 [模板](templates/threat-model.md) 写多租户威胁模型：资产、入口、威胁、缓解措施、对应测试。
4. 写出一个当前没有被测试覆盖的越权场景，以及你会怎样补测试（不要求真的补，要求写清楚：输入、预期、断言）。

## 产物与验收

- 数据流图（练习 1）。
- 逐条测试解读（练习 2）。
- 威胁模型：`templates/threat-model.md` 的填写版（练习 3）。
- 一个未覆盖场景与补测试方案（练习 4）。
- 验收看三点：能说出认证与授权的区别；能指出预过滤与后过滤的差别，并找到 capstone 里对应的测试；威胁模型里每条“缓解措施”都对应一个具体的测试或明确写“无测试”。

## 边界

- 本章是阅读与分析清单，没有可执行 gate；不能证明你能写出安全的认证系统。
- capstone 的离线测试用的是测试替身，不是真实的身份提供方、数据库 RLS 或多节点部署；“测试通过”只说明这些场景在测试里被覆盖，不等于生产隔离已被验证。
- 不覆盖 OAuth/OIDC 流程、会话管理、SSO、密钥托管；这些在真实系统里要用成熟的身份提供方和库，不要自己实现。
- JWT 的密钥轮换做法本章没有逐条核对到官方文档，按你的库与平台文档为准。
