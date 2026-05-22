# Change Summary: v0.4 渐进式披露引擎

## 变更类型

新功能

## 变更日期

2026-05-22

## 变更动机

v0.3 全量扫描模式输出过重（682 行模块表、298KB 目录树），对陌生项目不友好。v0.4 采用渐进式披露策略：先收集引导文件（README、依赖清单、CI 配置等），让 LLM 从高层次识别业务板块，输出单一 `project-overview.md`，用户可按需深入。

## 变更范围

### 新建文件 (2)

| 文件 | 用途 |
| ---- | ---- |
| `app/analyzer/guiding_files.py` | 引导文件收集（35 种模式） + 目录摘要（≤30 行，UUID/编译产物折叠） |
| `app/analyzer/domain_analyzer.py` | LLM 业务板块识别（max_tokens=2048, timeout=60）+ 无 Key 降级模式 |

### 修改文件 (4)

| 文件 | 改动 |
| ---- | ---- |
| `app/analyzer/__init__.py` | 版本号 0.3.2 → 0.4.0 |
| `app/analyzer/llm_assistant.py` | 删除 13 个旧函数（模板描述、批量增强、数据流、技术栈、入口检测等），仅保留 4 个基础设施 |
| `app/analyzer/map_writer.py` | 删除 15 个旧函数/常量（4 文件生成、表格构建、模块分组等），新增 `generate_progressive_overview()` |
| `harness/scripts/analyze_project.py` | 完全重写：砍掉 `--depth`/`--source-root`，3 步新流程（引导文件→板块识别→概览） |

### 文档更新 (5)

| 文件 | 改动 |
| ---- | ---- |
| `README.md` | 版本号 v0.4，快速开始简化 |
| `harness/project-map/command-map.md` | analyze_project 命令描述更新 |
| `harness/project-map/module-map.md` | 新增 guiding_files/domain_analyzer，标记 parser/overview 已移除 |
| `harness/project-map/directory-map.md` | analyzer 目录新增两个文件 |
| `harness/project-map/data-flow.md` | 重写为 v0.4 数据流文档 |

### 不修改但受影响 (3)

| 文件 | 说明 |
| ---- | ---- |
| `app/analyzer/scanner.py` | 仅 EXCLUDE_DIRS 被 guiding_files.py 引用 |
| `app/analyzer/parser.py` | 不再被任何模块导入 |
| `app/analyzer/overview.py` | 不再被任何模块导入 |

## 验证结果

| 验证项 | 结果 |
| ---- | ---- |
| `python harness/scripts/check_structure.py` | PASS (46/46) |
| `python harness/scripts/analyze_project.py .` | 生成 `project-overview.md`，含 6 个必需部分 |
| `python harness/scripts/analyze_project.py --help` | 输出新用法，无 --depth/--source-root |
| `python harness/scripts/help.py` | 输出版本号 v0.4 |
| `pytest tests/ -k "not analyze" -v` | 20/20 通过（非分析测试无回归） |
| `python harness/scripts/analyze_project.py . --llm` | 待 Tester 在有 Key 环境测试 |

## 后续待办 (Tester)

- TST-1~TST-6: 更新 `test_analyze_project.py` 和新建 `test_guiding_files.py`、`test_domain_analyzer.py`
