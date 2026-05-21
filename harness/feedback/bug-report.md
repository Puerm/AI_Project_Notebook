# Bug Report

记录用户手工测试中发现的应用层 bug。

## 格式

```
### YYYY-MM-DD — bug 简述

- **现象**: 发生了什么
- **期望**: 预期行为
- **复现步骤**: 如何触发
- **涉及文件**: 初步判断哪些文件有问题
- **状态**: 待修复 / 已修复 / 拒绝
```

## 记录

### 2026-05-20 — check_structure.py 在目标项目上报 FAIL

- **现象**: 对 BioTec 项目运行 `python harness/scripts/check_structure.py`，报告 13 项缺失（`.claude/agents/`、`.claude/commands/`、`.claude/skills/`），必然 FAIL
- **期望**: `check_structure.py` 应只检查 `harness/` 骨架完整性，不检查 `.claude/` 子目录（`.claude/` 不属于被部署到目标项目的 harness 骨架）
- **复现步骤**: 
  1. `python harness/scripts/init_project.py C:\Users\21093\Desktop\BioTec`
  2. `python C:\Users\21093\Desktop\BioTec\harness\scripts\check_structure.py`
- **涉及文件**: `harness/scripts/check_structure.py` — `REQUIRED_DIRS` 列表包含了 `.claude/`、`.claude/agents/`、`.claude/commands/`、`.claude/skills/`
- **状态**: 已修复
