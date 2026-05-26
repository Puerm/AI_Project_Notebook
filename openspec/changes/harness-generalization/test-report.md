## 测试报告

### 结论: 阻塞

发现 1 个代码 bug — `init_project.py` 的 `_fill_templates` 仅遍历 `harness/` 目录，不填充 `.claude/agents/` 中的模板文件。编排器将路由回 Generator 修复。

### 测试概况

- 新增用例: 40
- 通过: 124
- 失败: 0
- 跳过: 0

### 失败详情

无。

### 失败分类

| 类别 | 数量 | 处理方式 |
| ---- | ---- | ---- |
| 测试自身问题 | 0 | — |
| 代码 bug | 1 | 路由回 Generator |

### 代码 bug 详情

**BUG-1: `_fill_templates` 作用域不足 — `.claude/agents/` 模板未被填充**

- 影响文件: `harness/scripts/init_project.py`
- 问题描述: IMP-3 在 agent 定义文件 (tester.md, generator.md) 中加入 `{{test_command}}` 占位符，但 IMP-7 的 `_fill_templates(target_harness, config)` 仅遍历 `harness/` 目录，不处理 `.claude/agents/` 文件。部署到目标项目后，agent 文件中的 `{{test_command}}` 占位符未被替换为实际命令。
- 修复建议: 在 `init_project()` 中于 `_fill_templates(target_harness, ...)` 之后,增加对 `.claude/` 目录的模板填充调用: `_fill_templates(target_claude, config_for_fill)`。
- 检测测试: `test_init_deployed_claude_agents_not_filled_gap`, `test_init_deployed_generator_not_filled_gap`, `test_init_deployed_tester_not_filled_gap` — 这三个测试当前断言占位符**未被填充**以标记此 gap。修复后需更新断言为 `assert "{{test_command}}" not in content`。
- 阻塞级别: 阻塞 — agent 定义文件中的 `{{test_command}}` 未填充会导致 Tester Agent 无法获知正确的测试命令。

### 覆盖情况

| 函数/模块 | 正常路径 | 边界测试 | 状态 |
| ---- | ---- | ---- | ---- |
| help.py (IMP-2) | 运行返回0, 列出正确命令 | 不含 check_structure/analyze_project, 不含硬编码名称, 版本从 yaml 读取 | 通过 |
| init_project.py project.yaml 部署 (IMP-7) | project.yaml 创建完整性 | 字段完整性 | 通过 |
| init_project.py 模板填充 (IMP-7) | harness/rules 模板正确填充 | — | 通过 |
| init_project.py .claude 模板填充 (IMP-7) | — | — | **阻塞 (bug)** |
| init_project.py 目录分离 (IMP-5c) | app/ 不创建, command-map 不含旧条目 | — | 通过 |
| diagnose_and_fix.py _run_verification (IMP-6) | docstring 提及两步, 源码不含 check_structure | 无 tests 无 agents 也通过 | 通过 |
| project.yaml schema (IMP-1) | 所有字段存在, version semver, languages 非空, test_command 非空 | — | 通过 |
| _generate_project_yaml (IMP-7) | 单/多语言项目格式正确 | 未知语言 | 通过 |
| _detect_project_features (IMP-7) | python 项目检测正确 | 空项目返回 unknown | 通过 |
| _fill_template_placeholders (IMP-7) | 所有6个占位符替换正确 | 未知占位符保持, 缺字段用默认值 | 通过 |

### 回归检查

原始 82 个测试全部保持通过（其中 `test_help_lists_all_commands` 已更新为 `test_help_lists_all_expected_commands` 以匹配新的命令列表）。
