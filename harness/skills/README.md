# Skills

此目录存放 Agent 工作流技能定义（Markdown 格式）。

每个技能文件定义了一个可供 AI Agent 调用的工作流，包含：
- 触发条件（何时使用）
- 执行步骤
- 输出格式
- 约束和边界

## 当前技能

暂无自定义技能。技能将在实际开发过程中根据需求逐步添加。

## 技能命名规范

- 文件名: `kebab-case.md`
- 必须包含 YAML frontmatter（name, description, 触发条件）
- 技能必须定义明确的输入和输出格式
