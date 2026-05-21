# Error Log

记录开发和使用过程中遇到的错误，供后续分析和规则改进。

## 格式

```
### YYYY-MM-DD HH:MM — 错误简述

- **现象**: 发生了什么
- **触发**: 执行了什么操作
- **根因**: 为什么会发生（如果已知）
- **解决**: 如何修复的
- **关联规则**: 涉及 `harness/rules/` 下哪条规则
```

## 记录

### 2026-05-20 16:22 — check_structure.py 用 Notebook 自身结构标准检查目标项目

- **现象**: 对 BioTec（NestJS+React 项目）运行 `check_structure.py`，报告 13 项缺失（`app/`、`data/`、`tests/`、`openspec/`、`.claude/agents/`、`CLAUDE.md` 等），必然 FAIL
- **触发**: `python harness/scripts/check_structure.py` 在目标项目 BioTec 下执行
- **根因**: `check_structure.py` 的检查清单硬编码了 AI_Project_Notebook 自身结构。它检查的是"运行它的项目有没有长成 Notebook 的样子"，而不是检查 harness 骨架自身是否完整
- **解决**: 暂未修复。应改为检查 harness 内部结构完整性（`project-map/` 6 个文件、`rules/`、`scripts/` 等），或支持按项目类型配置检查规则
- **关联规则**: `harness/rules/workflow-rules.md` 第 7 条

---

> 每当遇到错误，在此文件顶部（标题下方）添加一条记录。
