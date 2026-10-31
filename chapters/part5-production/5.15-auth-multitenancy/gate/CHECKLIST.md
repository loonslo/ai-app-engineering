# L5.4 认证、授权与多租户 · 验收清单

本章是清单章，没有可执行 gate。证据写到 [workbook](../workbook.md)；“未运行/未读懂”如实写，不当作通过。

- [ ] 阅读 9.5 与 `capstone/permissions.py`，画出请求从认证到检索过滤的数据流；
- [ ] 运行 `python -m pytest capstone/test_production.py -q`，找出其中验证租户隔离与权限的测试，逐条写出它们防住了什么；
- [ ] 按 `templates/threat-model.md` 写多租户威胁模型（资产、入口、威胁、缓解措施、对应测试）；
- [ ] 写出一个当前没有被测试覆盖的越权场景，以及你会怎样补测试；
- [ ] 能用两句话说清认证与授权的区别、预过滤与后过滤的区别。
