# Change Summary: Harness 框架通用化 v0.1

**日期**: 2026-05-26
**类型**: 重构
**状态**: BUG-1 已修复

## 修复记录

**BUG-1: `_fill_templates` 作用域不足 — `.claude/agents/` 模板未被填充** (2026-05-26)

- 文件: `harness/scripts/init_project.py`
- 问题: `init_project()` 中 `_fill_templates(target_harness, config)` 仅遍历 `harness/` 目录，部署到目标项目的 `.claude/agents/` 文件（含 `{{test_command}}` 占位符）未被填充。
- 修复: 在 `_fill_templates(target_harness, ...)` 后增加 `_fill_templates(target_claude, config_for_fill)` (第 522 行)，使用同一 config dict 填充 `.claude/` 下的模板占位符。
- 影响文件: `generator.md` (第 65 行 `{{test_command}}`), `tester.md` (第 82 行 `{{test_command}}`)
- 验证: `check_structure.py` PASS (51/51), pytest 350 passed / 15 failed (12 个为预存的 analyze_project CLI 测试失败, 3 个 gap-marker 测试因占位符已被正确填充而失败, 需 Tester 更新断言)

## 完成的任务

| 任务 | 文件 | 状态 |
| ---- | ---- | ---- |
| IMP-1 | `harness/config/project.yaml` (新建) | 完成 |
| IMP-2 | `harness/scripts/help.py` | 完成 |
| IMP-3 | `.claude/agents/*.md` (4 文件) | 完成 |
| IMP-4 | `harness/rules/coding-rules.md`, `workflow-rules.md` | 完成 |
| IMP-5a | `app/analyze_project.py` (新路径) | 完成 |
| IMP-5b | `harness/scripts/check_structure.py` | 完成 |
| IMP-5c | `harness/scripts/init_project.py` | 完成 |
| IMP-5d | `app/analyzer/dimension_analyzer.py` | 完成 |
| IMP-6 | `harness/scripts/diagnose_and_fix.py` | 完成 |
| IMP-7 | `harness/scripts/init_project.py` (LLM 增强 + BUG-1 修复) | 完成 |
| IMP-8 | `harness/prompts/diagnosis.txt` | 完成 |
| IMP-9 | 8 个文档 | 完成 |
