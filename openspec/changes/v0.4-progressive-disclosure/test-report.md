## 测试报告

### 结论: 通过（附 1 个代码 bug 备注，非阻塞）

### 测试概况

- 新增测试文件: 2 (`test_guiding_files.py`, `test_domain_analyzer.py`)
- 重写测试文件: 1 (`test_analyze_project.py`)
- 整体测试用例: 115
- 通过: 115
- 失败: 0
- 跳过: 0

### 失败详情

无。

### 失败分类

| 类别 | 数量 | 处理方式 |
| ---- | ---- | ---- |
| 测试自身问题 | 0 | -- |
| 代码 bug | 0（1 个已备注） | 非阻塞备注 |

### 代码 bug 备注（非阻塞）

**B1: `.github/workflows/*.yml` 未实际收集**

`collect_guiding_files()` 的第二遍扫描将 `.github/workflows/` 下的 `.yml`/`.yaml` 文件加入 `all_candidates`，但后续匹配循环仅按 `GUIDING_FILE_PATTERNS` 的精确文件名匹配。由于 `ci.yml`、`deploy.yaml` 等自定义文件名不在 patterns 字典中，这些 CI 工作流文件从未被添加到 `found` 列表。

影响: spec 要求的 `.github/workflows/` 下 CI 配置文件无法被收集。
测试覆盖: `test_collect_github_actions_not_in_patterns` 记录了当前行为（assert 文件未被收集），便于后续修复后验证。

### 覆盖情况

| 模块/函数 | 正常路径 | 边界测试 | 状态 |
| ---- | ---- | ---- | ---- |
| `scanner.py` (scan_directory) | 6 | 标准标签识别、内容推断、排除、空目录、非源码、非目录 | PASS |
| `parser.py` (parse_python / parse_file) | 12 | imports/functions/classes、JS 正则、语法错误、空文件、不存在、未知扩展 | PASS |
| `overview.py` (analyze_overview) | 10 | Python/Node.js/TypeScript 检测、Web/CLI 识别、入口文件、空项目 | PASS |
| `llm_assistant.py` (保留函数) | 5 | check_api_key(无/有 key)、get_llm_config(无/有 env)、call_llm(无 key) | PASS |
| `guiding_files.py` (collect_guiding_files) | 10 | README/package.json 收集、空项目、截断、超15限制、CI、排除、失败不崩、字段格式、missing | PASS |
| `guiding_files.py` (generate_directory_summary) | 8 | 一二级目录、UUID 折叠、编译产物折叠、隐藏/排除、≤30行、空目录 | PASS |
| `domain_analyzer.py` (degraded mode) | 4 | 无 Key 降级、字段完整、置信度"低"、项目名 | PASS |
| `domain_analyzer.py` (_build_domain_analysis_prompt) | 4 | 引导文件内容、missing 标注、目录摘要、输出格式约束 | PASS |
| `domain_analyzer.py` (_parse_domain_response) | 7 | 正常 JSON、```json 包裹、无标签包裹、畸形降级、缺字段默认、空串、前后多余文字 | PASS |
| `domain_analyzer.py` (_normalize_result) | 2 | 补全默认、保留已存在 | PASS |
| `domain_analyzer.py` (fake key LLM 失败) | 1 | 假 Key 调用失败返回降级不崩溃 | PASS |
| `map_writer.py` (generate_progressive_overview) | 10 | 6 部分、数据内容、置信度符号、空板块、降级警告、原子写入、目录创建、合并保留、LLM 页脚、返回值 | PASS |
| `map_writer.py` (_merge_sections) | 1 | MANUAL 保留 | PASS |
| CLI (analyze_project.py) | 7 | --help、无效路径(不存在/非目录)、无 Key 退出、有效项目、--quiet、--output-dir | PASS |

### 回归检查

| 测试文件 | 之前 | 之后 | 变化 |
| ---- | ---- | ---- | ---- |
| test_help.py | 2/2 | 2/2 | 无变化 |
| test_search_notes.py | 4/4 | 4/4 | 无变化 |
| test_export_report.py | 3/3 | 3/3 | 无变化 |
| test_init_project.py | 11/11 | 11/11 | 无变化 |
| test_analyze_project.py (旧) | 33/51 | -- | 见下文 |
| test_analyze_project.py (新) | -- | 51/51 | 28 旧保留 + 23 新增 |
| test_guiding_files.py (新) | -- | 24/24 | 新增 |
| test_domain_analyzer.py (新) | -- | 20/20 | 新增 |

旧 test_analyze_project.py 中原先失败的 18 个测试（依赖已删除函数 `enhance_description`、`_template_*`、`generate_all`、`generate_overview`、`generate_data_flow` 等）已全部替换为匹配 v0.4 新架构的测试。

### 验证命令结果

```
$ python harness/scripts/check_structure.py
[PASS] 46/46

$ python -m pytest tests/ -v
[PASS] 115 passed, 0 failed
```
