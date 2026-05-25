# Command Map

所有可执行命令索引。

## CLI 命令

| 命令 | 用途 | 来源文件 |
| ---- | ---- | ---- |
| `python harness/scripts/help.py` | 打印所有可用命令 | `harness/scripts/help.py` |
| `python harness/scripts/init_project.py <目标路径>` | 初始化新项目地图 | `harness/scripts/init_project.py` |
| `python harness/scripts/check_structure.py` | 检查项目结构完整性 | `harness/scripts/check_structure.py` |
| `python harness/scripts/search_notes.py <关键词>` | 搜索笔记 | `harness/scripts/search_notes.py` |
| `python harness/scripts/export_report.py` | 导出项目理解报告 | `harness/scripts/export_report.py` |
| `python harness/scripts/analyze_project.py <目标路径>` | 智能项目分析引擎 (v0.5.1: 渐进式披露 / --digest 聚焦三维度分析) [--digest] [--max-size N] | `harness/scripts/analyze_project.py` |
| `python harness/scripts/generate_rule_evolution.py` | 扫描反馈信号，生成规则演化建议 | `harness/scripts/generate_rule_evolution.py` |

## Claude Code 命令

| 命令 | 用途 | 定义位置 |
| ---- | ---- | ---- |
| `/opsx:propose <name>` | 创建变更提案 | `.claude/commands/opsx/propose.md` |
| `/opsx:explore` | 进入探索模式 | `.claude/commands/opsx/explore.md` |
| `/opsx:apply` | 执行变更任务 | `.claude/commands/opsx/apply.md` |
| `/opsx:archive` | 归档已完成变更 | `.claude/commands/opsx/archive.md` |
| `/pm:discuss <topic>` | 启动 PM 讨论，产出 spec 文档 | `.claude/commands/pm/discuss.md` |
| `/workflow:full-cycle <topic>` | 完整开发周期 (PM→Planner→Explorer→Generator→Reviewer→Tester) | `.claude/commands/workflow/full-cycle.md` |
| `/workflow:implement` | 执行已有计划 (Explorer→Generator→Reviewer→Tester) | `.claude/commands/workflow/implement.md` |
| `/workflow:quick-fix <描述>` | 快速修复 (Explorer→Generator→Tester) | `.claude/commands/workflow/quick-fix.md` |
| `/workflow:review-fix` | 审查反馈修复 (三类问题自动路由) | `.claude/commands/workflow/review-fix.md` |

## 搜索命令

| 命令 | 用途 |
| ---- | ---- |
| `grep -r "关键词" harness/project-map/` | 搜索项目地图 |
| `grep -r "关键词" harness/feedback/` | 搜索反馈日志 |
| `grep -r "关键词" harness/rules/` | 搜索规则 |

## 变更规则

- 新增命令后必须在本文档中登记
- 修改命令参数后必须更新对应行
- 删除命令后标记为 `~~已移除~~`
