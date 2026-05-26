# Plan: Harness 框架通用化 v0.1

## 1. 变更范围

### 新增文件

| 文件 | 意图 |
| ---- | ---- |
| `harness/config/project.yaml` | 所有模板变量的单一数据源。定义 `project_name`、`languages`、`test_framework`、`test_command`、`package_manager`。在 Notebook 仓库中填入 Notebook 自身值；部署到目标项目时由 init_project.py 根据 LLM 检测结果生成新值。 |

### 修改文件

| 文件 | 改动意图 |
| ---- | ---- |
| **Agent 定义 — 移除 Python/pytest/check_structure.py 硬编码** | |
| `.claude/agents/generator.md` | 移除 `check_structure.py` 引用（第 37/56/65 行），移除 `snake_case.py` 命名约束（第 58 行），将 `python harness/scripts/check_structure.py` 替换为语言无关的"运行项目配置的验证命令"描述 |
| `.claude/agents/tester.md` | 移除 `python -m pytest tests/ -v` 硬编码（第 82 行），替换为 `{{test_command}}` 占位符 |
| `.claude/agents/reviewer.md` | 移除 `check_structure.py` 检查项（第 51 行） |
| `.claude/agents/harness_maintainer.md` | 移除 `check_structure.py` 检查项更新引用（第 33/56/83/90 行），替换为通用的"项目结构检查配置"描述 |
| **规则文件 — 移除语言特定约束** | |
| `harness/rules/coding-rules.md` | 规则 3：`Python 用 snake_case.py` 改为 `文件命名遵循项目约定的命名规范`；规则 8：`python harness/scripts/check_structure.py` 改为 `运行项目配置的结构验证命令`；规则 11：`python -m pytest tests/ -v` 改为 `运行项目配置的测试命令 {{test_command}}` |
| `harness/rules/workflow-rules.md` | 规则 8：`python harness/scripts/check_structure.py` 改为 `运行项目配置的验证命令`；规则 9：`python -m pytest tests/ -v` 改为 `运行项目配置的测试命令` |
| **目录结构分离** | |
| `harness/scripts/analyze_project.py` | 移出 `harness/scripts/`，移动至 `app/analyze_project.py`；调整 `import` 路径（原 `from app.analyzer.xxx` 改为相对导入或更新 sys.path）；更新内部注释中自我引用的路径 |
| `harness/scripts/check_structure.py` | REQUIRED_DIRS 移除 `app/analyzer`（不再是 harness 框架范围）；REQUIRED_FILES 移除 `harness/scripts/analyze_project.py`；总数从 15+39 变为 14+38 |
| `harness/scripts/init_project.py` | 移除 `app/analyzer/` 目录骨架创建代码（第 260-261 行）；移除 command-map 模板中的 `analyze_project.py` 条目；加入新功能（见功能 6） |
| `harness/scripts/help.py` | 移除 `analyze_project.py` 命令条目；移除 `check_structure.py` 命令条目；将硬编码的 `AI Project Notebook v0.5.1` 替换为 `{{project_name}} {{version}}`，从 `project.yaml` 读取 |
| `app/analyze_project.py`（新路径） | 更新内部注释和字符串中自引路径从 `harness/scripts/analyze_project.py` 到 `app/analyze_project.py` |
| `app/analyzer/dimension_analyzer.py` | 第 135 行样本入口文件列表中移除 `check_structure.py` 条目，更新 `analyze_project.py` 路径引用 |
| **check_structure.py 引用清理** | |
| `harness/scripts/diagnose_and_fix.py` | `_run_verification()` 函数从三步验证（check_structure.py + pytest + agent YAML）调整为两步（pytest + agent YAML）；移除 check_structure.py 调用代码块；更新函数文档字符串 |
| **init_project.py LLM 增强** | |
| `harness/scripts/init_project.py` | 新增 LLM 项目检测函数 `_detect_project_features(target_path)`：文件后缀统计 -> 语言列表、配置文件检测（package.json/pyproject.toml/go.mod/Cargo.toml 等）-> 包管理器/测试框架/入口文件；新增 `_generate_project_yaml(features, project_name)` 生成 `project.yaml`；新增 `_fill_template_placeholders(content, config)` 对含 `{{...}}` 占位符的文件执行替换；在 `init_project()` 主流程中插入：LLM 检测 -> 生成 project.yaml -> 复制骨架 -> 填充模板；LLM 不可用时降级为纯静态检测（CLI 参数 + 文件后缀扫描） |
| **文档同步** | |
| `harness/project-map/overview.md` | 更新版本号 v0.8 -> v0.9；更新"下一步计划"移除 check_structure.py 提及；新增 harness 通用化描述 |
| `harness/project-map/directory-map.md` | 更新 `harness/scripts/` 目录树移除 `analyze_project.py`；新增 `harness/config/project.yaml` 条目 |
| `harness/project-map/module-map.md` | 移除 `analyze_project.py` 条目（已不在 harness/scripts/）；新增 `harness/config/project.yaml` 条目 |
| `harness/project-map/command-map.md` | CLI 命令表移除 `check_structure.py` 和 `analyze_project.py`；更新 `help.py` 命令描述 |
| `harness/project-map/data-flow.md` | 自我升级数据流图中移除 check_structure.py 节点；新增 project.yaml 模板填充的数据流说明 |
| `harness/project-map/change-map.md` | 登记本次变更 |
| `README.md` | 更新版本号；更新命令列表 |
| `CLAUDE.md` | 移除 check_structure.py 的运行指令 |

---

## 2. 任务列表

### 实现任务 (→ Generator)

**IMP-1: 创建 project.yaml 模板变量定义文件**
- 文件：`harness/config/project.yaml`
- 完成标准：文件包含 `project_name`、`version`、`languages`（列表）、`test_framework`、`test_command`、`package_manager` 字段，值填入 AI Project Notebook 的当前真实值；schema 清晰无冗余字段
- 验证：`python -c "import yaml; yaml.safe_load(open('harness/config/project.yaml')); print('OK')"`（若无 PyYAML 则手动检查格式）

**IMP-2: help.py 通用化 — 移除项目名/版本/check_structure/analyze 硬编码**
- 文件：`harness/scripts/help.py`
- 完成标准：打印消息从 `project.yaml` 读取 `project_name` 和 `version`；COMMANDS 列表中移除 `analyze_project.py` 和 `check_structure.py` 条目；无 AI Project Notebook 硬编码文本
- 验证：`python harness/scripts/help.py` 输出不再包含 "AI Project Notebook"、"check_structure.py"、"analyze_project.py"，版本号从 yaml 读取

**IMP-3: Agent 定义通用化 — 移除 generator/reviewer/harness_maintainer/tester 中的语言/工具硬编码**
- 文件：`.claude/agents/generator.md`、`.claude/agents/tester.md`、`.claude/agents/reviewer.md`、`.claude/agents/harness_maintainer.md`
- 完成标准：
  - generator.md：不再出现 `python harness/scripts/check_structure.py`、`snake_case.py`、`pytest`；约束改为引用 `{{test_command}}` 和通用的"项目配置的验证命令"
  - tester.md：`python -m pytest tests/ -v` 替换为 `{{test_command}}`
  - reviewer.md："检查项列表"移除 `check_structure.py` 是否通过这一条
  - harness_maintainer.md：所有 `check_structure.py` 引用替换为通用的"项目结构检查配置"
- 验证：`grep -n "check_structure.py\|snake_case.py\|python -m pytest"` 在四个 agent 文件中无匹配

**IMP-4: 规则文件通用化 — 移除 coding-rules 和 workflow-rules 中的语言特定约束**
- 文件：`harness/rules/coding-rules.md`、`harness/rules/workflow-rules.md`
- 完成标准：
  - coding-rules.md：规则 3（文件命名）移除 "Python 用 snake_case.py"，改为语言无关描述；规则 8（check_structure.py）改为引用 `{{validation_command}}`；规则 11（pytest）改为 `{{test_command}}`
  - workflow-rules.md：规则 8（check_structure.py）和规则 9（pytest）改为语言无关描述
- 验证：`grep -n "python\|snake_case\|pytest\|check_structure"` 在两个规则文件中（除占位符行外）无 Python 特定匹配

**IMP-5: 目录结构分离 — analyze_project.py 迁移 + check_structure.py/init_project.py/help.py 同步调整**
- 文件：`app/analyze_project.py`（新路径）、`harness/scripts/check_structure.py`、`harness/scripts/init_project.py`、`app/analyzer/dimension_analyzer.py`
- 子任务：
  - 5a: 将 `harness/scripts/analyze_project.py` 移动到 `app/analyze_project.py`；更新文件头注释和内部引用路径
  - 5b: `check_structure.py` 的 REQUIRED_DIRS 移除 `app/analyzer`；REQUIRED_FILES 移除 `harness/scripts/analyze_project.py`
  - 5c: `init_project.py` 移除 `app/analyzer/` 目录创建代码（第 260-261 行）；移除 command-map 模板中的 `analyze_project.py` 条目
  - 5d: `dimension_analyzer.py` 第 135 行移除 check_structure.py 条目，更新 analyze_project.py 路径
- 完成标准：`harness/scripts/` 下无 analyze_project.py；`check_structure.py` 不检查 app/analyzer/ 和 analyze_project.py；init_project.py 部署到目标项目时不创建 app/analyzer/
- 验证：`ls harness/scripts/analyze_project.py` 返回文件不存在；`ls app/analyze_project.py` 返回文件存在；`python harness/scripts/check_structure.py` 通过（14/38 或调整后总数）

**IMP-6: diagnose_and_fix.py 沙盒验证从三步调整为两步**
- 文件：`harness/scripts/diagnose_and_fix.py`
- 完成标准：`_run_verification()` 函数中移除 check_structure.py 验证步骤（第 611-627 行）；函数文档字符串更新为"两步（pytest + agent YAML）"；流程中不再出现 `check_structure.py` 字符串
- 验证：`grep -n "check_structure" harness/scripts/diagnose_and_fix.py` 无匹配；`python -c "from harness.scripts.diagnose_and_fix import _run_verification; print(_run_verification.__doc__)"` 包含"两步"描述

**IMP-7: init_project.py LLM 增强 — 项目检测 + project.yaml 生成 + 模板填充**
- 文件：`harness/scripts/init_project.py`
- 完成标准：
  - 新增 `_detect_project_features(target_path)` — 扫描文件后缀统计语言、检测配置文件（package.json/pyproject.toml/go.mod/Cargo.toml 等）推断包管理器/测试框架；返回 dict 含 languages/test_framework/test_command/package_manager
  - 新增 `_generate_project_yaml(features, project_name)` — 输出符合 IMP-1 格式的 yaml 文本
  - 新增 `_fill_templates(target_harness, config)` — 遍历 harness 下所有 .md/.yaml/.txt 文件，将 `{{project_name}}`/`{{test_command}}`/`{{version}}`/`{{validation_command}}` 等占位符替换为 config 中的实际值
  - 主流程 `init_project()` 在 `shutil.copytree()` 后调用 LLM 检测；LLM 不可用（API Key 未配）时降级为纯静态检测
  - LLM 增强使用已有的 `app.analyzer.llm_assistant`（只在 Notebook 项目自身运行 init_project.py 时可用）
- 验证：在 Notebook 自身目录运行 `python harness/scripts/init_project.py <临时测试目录>`，检查目标目录的 `harness/config/project.yaml` 是否正确生成，agent 文件中的 `{{test_command}}` 是否被替换为实际命令

**IMP-8: help.py / init_project.py / diagnosis.txt 中的项目名硬编码替换**
- 文件：`harness/scripts/help.py`、`harness/prompts/diagnosis.txt`
- 完成标准：
  - help.py：第 22 行 "AI Project Notebook v0.5.1" 替换为从 `project.yaml` 读取
  - diagnosis.txt：第 1-2 行注释中的 "Harness 自我升级系统" 改为 "{{project_name}} 自我升级系统"
- 验证：`python harness/scripts/help.py` 输出不含 "AI Project Notebook"；`grep "AI Project Notebook" harness/prompts/diagnosis.txt` 无匹配

**IMP-9: 文档同步 — 更新全部 7 个文档**
- 文件：`harness/project-map/overview.md`、`directory-map.md`、`module-map.md`、`command-map.md`、`data-flow.md`、`change-map.md`、`README.md`、`CLAUDE.md`
- 完成标准：所有 project-map 文档反映新的目录结构（analyze_project.py 在 app/ 下、project.yaml 在 harness/config/ 下）；command-map 移除 check_structure.py 和 analyze_project.py；overview 版本号更新；change-map 登记本次变更；README 更新命令列表和版本号；CLAUDE.md 移除 check_structure.py 运行指令
- 验证：`grep -rn "analyze_project.py" harness/project-map/` 仅在新路径 `app/analyze_project.py` 出现；`grep -rn "check_structure.py" harness/project-map/` 仅在 change-map 历史条目和 command-map 移除标记（如有）中出现

---

### 测试任务 (→ Tester)

**TST-1: 更新 help.py 相关测试**
- 文件：`tests/test_help.py`
- 覆盖：help.py 不再输出 "AI Project Notebook"、不再列出 check_structure.py 和 analyze_project.py、版本号从 project.yaml 读取后的输出格式
- 验证：`python -m pytest tests/test_help.py -v` 全部通过

**TST-2: 更新 init_project.py 相关测试**
- 文件：`tests/test_init_project.py`
- 覆盖：部署后目标项目包含 `harness/config/project.yaml`；模板占位符被正确填充；`app/analyzer/` 目录不再创建；command-map 模板不含 check_structure.py/analyze_project.py
- 验证：`python -m pytest tests/test_init_project.py -v` 全部通过

**TST-3: 更新 diagnose_and_fix.py 相关测试**
- 文件：`tests/test_diagnose_and_fix.py`
- 覆盖：`_run_verification` 从三步变两步后沙盒验证逻辑仍正确；不再检查 check_structure.py 步骤；pytest + agent YAML 两步验证结果正确
- 验证：`python -m pytest tests/test_diagnose_and_fix.py -v` 全部通过

**TST-4: 新增 project.yaml schema 验证和模板填充测试**
- 文件：`tests/test_project_yaml.py`（新建）
- 覆盖：project.yaml 字段完整性；版本号为合法 semver；languages 为非空列表；test_command 为合法 shell 命令；模板填充函数 `_fill_templates` 对各种占位符的正确替换
- 验证：`python -m pytest tests/test_project_yaml.py -v` 全部通过

---

## 3. 依赖关系

```
IMP-1 (project.yaml)
 ├── IMP-2 (help.py 通用化，需读取 project.yaml)
 ├── IMP-3 (agent 定义通用化)
 ├── IMP-4 (规则文件通用化)
 ├── IMP-6 (diagnose_and_fix.py 调整)
 ├── IMP-8 (help.py/diagnosis.txt 硬编码替换)
 │
 IMP-5 (目录结构分离，独立可并行)
 │
 IMP-7 (init_project.py LLM 增强，依赖 IMP-1 + IMP-5)
 │
 IMP-9 (文档同步，依赖全部 IMP-1~8 完成后执行)
```

**并行执行组**：
- 组 A（可并行）：IMP-2, IMP-3, IMP-4, IMP-5, IMP-6, IMP-8
- IMP-1 必须先完成（作为模板变量基础）
- IMP-7 依赖 IMP-1（project.yaml schema）和 IMP-5（analyze_project.py 位置确定）
- IMP-9 在所有 IMP- 完成后执行

**测试任务依赖**：
- TST-1 依赖 IMP-2 完成
- TST-2 依赖 IMP-7 完成
- TST-3 依赖 IMP-6 完成
- TST-4 依赖 IMP-1 + IMP-7 完成
- TST-1~4 之间无依赖，可并行

---

## 4. 风险点

1. **占位符语法冲突** — `{{}}` 在 YAML 中可能与 Jinja2 模板语法混淆。project.yaml 自身不应使用 `{{}}`（它是值的来源，不是模板）。只在 agent 定义和规则文件等"被填充方"使用占位符。验证时用 `grep -rn '\{\{' harness/config/project.yaml` 确保无冲突。

2. **analyze_project.py 迁移后 import 路径** — 从 `harness/scripts/` 移到 `app/` 后，对 `app.analyzer.*` 的 import 需要调整。当前使用 `sys.path.insert(0, PROJECT_ROOT)` 方式导入，移动后需确认 PROJECT_ROOT 计算仍然正确（`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` 会从 `app/analyze_project.py` 往上两级到项目根，与原来一致）。

3. **help.py 读取 project.yaml** — help.py 需要读取 `harness/config/project.yaml`，涉及 YAML 解析。当前项目无 PyYAML 依赖，需判断是否用最小化 YAML 解析器（类似 diagnose_and_fix.py 中的 `_parse_minimal_yaml`）。如果 project.yaml 结构简单（纯键值对 + 列表），用现有最小解析器即可。

4. **init_project.py LLM 检测准确率** — 多语言混合项目可能导致语言检测失真（如 Python + JS 混合）。缓解措施：LLM 不可用时降级为纯静态检测（统计文件后缀 → 取占比最高的作为主语言，扫描已知配置文件推断包管理器）。该降级逻辑必须在 init_project.py 中显式实现。

5. **init_project.py 部署后自我删除问题** — init_project.py 在部署完成后从目标项目中删除自身（现有行为）。本次修改需确认 LLM 检测和模板填充在 self-delete 之前完成。当前流程：copy -> delete init_project.py -> generate templates，顺序正确不影响。

6. **diagnose_and_fix.py 移除 check_structure.py 后验证强度下降** — 沙盒验证从三步变为两步，少了一层结构完整性检查。风险可控，因为 pytest 测试覆盖率和 agent YAML frontmatter 有效性检查仍保留了核心验证能力。后续版本（LLM 深度适配）可补充语言特定的验证步骤。

7. **coding-rules.md 编号跳跃** — 删除规则 8（check_structure.py）后将产生编号缺口。处理方式：删除后不重新编号（其他规则编号不变，保留缺口），避免下游引用规则编号时出现偏移。coding-rules.md 和 workflow-rules.md 处理方式相同。

8. **模板填充后文件的"可逆性"** — 部署到目标项目后 agent 定义中的 `{{test_command}}` 被替换为实际值（如 `npm test`），但如果在目标项目中运行 `diagnose_and_fix.py` 的自我升级，诊断 prompt 模板 `diagnosis.txt` 可能因已填充而丧失通用性。缓解：diagnosis.txt 本身不使用项目特定占位符（它使用自己的 `{{TARGET_FILE_CONTENT}}` 占位符），仅将文件头部注释中的项目名改为从 project.yaml 读取后填充。

9. **不修改 harness/state/ 下的自测代码** — spec 明确标记为"暂不实现"，feedback_engine.py 和 workflow_state.py 中对 agent 名称（`explorer-blocked`、`tester-failed` 等）的引用保持不变。这些名称在部署到新项目时可能产生噪音，但不会造成功能阻塞。本版本不处理。
