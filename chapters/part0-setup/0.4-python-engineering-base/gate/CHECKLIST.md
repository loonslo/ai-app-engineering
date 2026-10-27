# L0.4 验证清单：AI 应用的 Python 工程底座

本章为自动化 Gate。通过标准：实现 `starter.py` 中的接口并通过 `gate/gate_check.py` 的全部 12 项检查。

- [ ] 在 `starter.py` 中实现 `load_settings`：
  - [ ] 正确读取环境变量并构建 `Settings` 模型；
  - [ ] 校验失败时抛出 `SettingsError`，消息指出出错字段名；
  - [ ] 错误信息脱敏：不泄露任何输入内容或敏感密钥值。
- [ ] 在 `starter.py` 中实现 `retry_async`：
  - [ ] 支持指定 `attempts` 次数，小于 1 时抛出 `ValueError`；
  - [ ] 实现指数退避等待 `base_delay * 2**i`；
  - [ ] 通过依赖注入的 `sleep` 协程完成等待，不调用任何同步休眠；
  - [ ] 仅对 `retry_on` 元组中的异常进行重试，其他异常立即抛出；
  - [ ] 重试次数耗尽时抛出最后一次的异常。
- [ ] 在 `starter.py` 中实现 `gather_limited`：
  - [ ] 使用 `asyncio.Semaphore` 限制最大并发数；
  - [ ] 参数 `limit < 1` 时抛出 `ValueError`；
  - [ ] 返回结果列表严格与输入的工厂列表顺序一致。
- [ ] 在 `starter.py` 中实现 `fetch_json`：
  - [ ] 非 2xx HTTP 状态码抛出 `HttpError("status:<code>")`；
  - [ ] 响应体非 JSON 或非字典对象抛出 `HttpError("invalid_json")`；
  - [ ] 请求超时抛出 `HttpError("timeout")`。
- [ ] 执行离线验证命令：
  ```bash
  python gate/gate_check.py
  ```
  全部 12 项检查通过，退出码为 0。
- [ ] 结果记录到 `workbook.md`，离线测试不调用真实网络。
