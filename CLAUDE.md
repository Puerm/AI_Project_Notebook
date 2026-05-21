# CLAUDE.md

## 项目定位

AI Project Notebook — 项目理解与知识沉淀工作台。v0.1 命令行版本。

## 工作原则

- 所有变更必须先读 `harness/project-map/overview.md` 了解项目全貌
- 修改文件后检查 `harness/rules/` 下的相关规则是否命中
- 代码修改后运行 `python harness/scripts/check_structure.py` 确认结构完整
- 遇到错误记录到 `harness/feedback/error-log.md`
- 发现可改进的规则记录到 `harness/feedback/improvement-log.md`
- 每次任务完成后更新 `harness/project-map/change-map.md`

## 项目地图入口

| 文档 | 用途 |
| ---- | ---- |
| `harness/project-map/overview.md` | 项目总览 |
| `harness/project-map/directory-map.md` | 目录结构 |
| `harness/project-map/module-map.md` | 模块职责 |
| `harness/project-map/command-map.md` | 命令索引 |
| `harness/project-map/data-flow.md` | 数据流 |
| `harness/project-map/change-map.md` | 变更记录 |

## 规则入口

| 文档 | 用途 |
| ---- | ---- |
| `harness/rules/coding-rules.md` | 编码规则 |
| `harness/rules/data-safety-rules.md` | 数据安全规则 |
| `harness/rules/workflow-rules.md` | 工作流规则 |
