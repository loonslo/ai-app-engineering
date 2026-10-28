# L2.12 真实资料知识库 v1 · 验收检查清单

## 检查项对应表

| 编号 | 检查项 | 验证内容 | 评分点 |
| :--- | :--- | :--- | :--- |
| 01 | 扫描页记失败 (reason=no_text_layer) | page 为 None 时记录 (source, page, "no_text_layer") | 1 |
| 02 | 空白页记失败 (reason=empty_page) | 去空白后为空串的页面记录 (source, page, "empty_page") | 1 |
| 03 | 表格行按行保留且不跨行合并 | 包含 \| 的表格行独立生成单个 Chunk，不被合并 | 1 |
| 04 | Chunk 字段完整性与页内索引起始规范 | Chunk 包含 source、page(>=1)、index(页内>=1)、text | 1 |
| 05 | 无足够支持证据时安全拒答且引用为空 | 检索分低于 min_score 时 refused=True 且 citations=[] | 1 |
| 06 | 引用格式严格遵循 source#p<page>#<index> | 作答时生成的引用格式匹配正则表达式 | 1 |
| 07 | 拦截引用未传给模型的幻觉片段 | 模型编造的不在检索传入集合中的引用被过滤剔除 | 1 |
| 08 | 资料装配在 user 消息分隔符内且声明为数据 | Prompt 包含明确分隔符（如 ---）并将资料标识为数据 | 1 |
| 09 | 固定替身下单项指标精确计算 | evaluate 精确输出 citation_accuracy, refusal_accuracy, hit_at_5 | 1 |
| 10 | 消融表按配置逐行输出包含延迟与指标 | ablation 生成包含各配置三项指标与 avg_latency_ms 的列表 | 1 |
| 11 | 门禁阈值拦截器判断全部未达标项 | 当指标低于 0.9/0.9/0.8 时准确列出未达标项 | 1 |
| 12 | cases.json 结构与用例完整性校验 | 用例数 >= 30，含拒答题与对抗注入题，ID 唯一 | 1 |
