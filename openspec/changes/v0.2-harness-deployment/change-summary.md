# Change Summary: v0.2 Harness 部署范围修正

## 完成情况

5/5 实现任务全部完成。

## 修改的文件

| 文件 | 改动 |
| ---- | ---- |
| `harness/scripts/init_project.py` | 新增 .claude/ 部署逻辑 (agents/commands/skills) + 部署后删除自身 |
| `harness/scripts/check_structure.py` | REQUIRED_DIRS 新增 4 个 .claude/ 条目；REQUIRED_FILES 新增 12 个 .claude/ 条目、移除 1 个 init_project.py 条目 |
| `harness/project-map/module-map.md` | 更新 init_project 模块职责描述 |
| `harness/project-map/change-map.md` | 新增本次变更记录 |

## 验证结果

- `python harness/scripts/check_structure.py` — PASS (44/44)
- `python -m pytest tests/ -v` — 15/15 passed (无回归)
