# L2.9 静态上下文与 Skills 检查清单

在提交或通知审核前，确认以下 11 项检查在闭卷骨架实现后全部通过：

- [ ] **01 合法 SKILL.md 解析**：正确提取 frontmatter 中的 name 与 description，正文 body 不包含 `---` 边界符。
- [ ] **02 缺少 frontmatter**：无前置 YAML frontmatter 时明确抛出 `SkillFormatError`。
- [ ] **03 缺少 name 字段**：frontmatter 中未声明 name 时抛出 `SkillFormatError`。
- [ ] **04 字段不符合约束**：大写、特殊字符或超长 name 抛出 `SkillFormatError`。
- [ ] **05 索引仅含 name 与 description**：生成格式为 `- <name>: <description>`，不泄露任何正文 body。
- [ ] **06 超预算截断提示**：索引超出设定预算时正确截断并在末尾追加 `（另有 N 个 Skill 未列出）`。
- [ ] **07 选择初筛排序与截断**：按关键词重合度降序排列，并严格遵守 `limit` 数量截断。
- [ ] **08 无重合词返回空列表**：当任务与所有 Skill 描述均无词汇重合时，返回空列表 `[]`。
- [ ] **09 首次加载与重复加载防重**：首次加载返回正文并记录到 `loaded`；再次加载相同 name 返回空串 `""`。
- [ ] **10 未知技能抛 SkillNotFound**：请求未注册的技能名称时抛出 `SkillNotFound`。
- [ ] **11 指令文件三重 Lint 告警**：准确识别 `too_long`、`duplicate_line:<行号>` 与 `secret_like:<行号>`。
