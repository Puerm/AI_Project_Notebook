# Plan: v0.4 渐进式披露分析引擎

## 1. 变更范围

### 需要新建的文件

| 文件 (完整路径) | 改动意图 |
| ---- | ---- |
| `app/analyzer/guiding_files.py` | 引导文件收集模块：扫描目标项目的关键文件（README、依赖清单、Docker/CI 配置、框架配置），生成目录结构摘要（≤30 行，折叠 UUID/编译产物目录） |
| `app/analyzer/domain_analyzer.py` | LLM 业务板块识别模块：将引导文件 + 目录结构输入 LLM，产出板块列表（名称、描述、路径、置信度、证据来源）、板块关系、下一步建议 |

### 需要修改的文件

| 文件 (完整路径) | 改动意图 |
| ---- | ---- |
| `app/analyzer/__init__.py` | 版本号 0.3.2 -> 0.4.0 |
| `app/analyzer/llm_assistant.py` | 砍掉 5 个全量分析旧函数（`enhance_module_descriptions_batch`、`enhance_data_flow_llm`、`enhance_tech_stack_llm`、`detect_entry_functions`、`enhance_dir_description`、`enhance_module_description`、`enhance_project_description`、`enhance_description`），保留 `_load_dotenv`、`_get_llm_config`、`_call_llm`、`check_api_key_available` 四个基础设施函数 |
| `app/analyzer/map_writer.py` | 砍掉 4 文件输出函数（`generate_overview`、`generate_directory_map`、`generate_module_map`、`generate_data_flow`、`generate_all`）和模块分组辅助函数（`_group_modules_by_directory`、`_compute_module_dependencies`、`_infer_module_description` 等），新增 `generate_progressive_overview()` 输出单一 `project-overview.md`；保留 `_atomic_write`、`_merge_sections`、`_split_by_sections` 底层工具 |
| `harness/scripts/analyze_project.py` | 完全重写：砍掉全量分析流程（Step 2-4 及 `_module_snippet`），砍掉 `--depth` 和 `--source-root` 参数。新流程：引导文件收集 → 目录摘要 → LLM 板块识别 → 输出概览 |
| `harness/scripts/help.py` | 版本号 v0.3.1 -> v0.4，analyze_project.py 命令描述更新 |
| `README.md` | 版本号 v0.3.1 -> v0.4，快速开始更新为新分析示例 |
| `harness/project-map/command-map.md` | `analyze_project.py` 行描述更新 |
| `harness/project-map/module-map.md` | 新增 `guiding_files.py` 和 `domain_analyzer.py` 登记；移除 `scanner.py`、`parser.py`、`overview.py` 已砍模块 |
| `harness/project-map/directory-map.md` | `app/analyzer/` 更新文件列表 |

### 不修改但受影响的文件（代码不变，仅依赖关系变化）

| 文件 | 说明 |
| ---- | ---- |
| `app/analyzer/scanner.py` | 保留 `EXCLUDE_DIRS` 常量（被 `guiding_files.py` 引用），其余函数（`scan_directory`、`detect_source_root`、`detect_source_roots`）不再被调用 |
| `app/analyzer/parser.py` | 整个文件不再被导入或调用 |
| `app/analyzer/overview.py` | 整个文件不再被导入或调用 |

### 不修改的文件

`app/analyzer/scanner.py`、`app/analyzer/parser.py`、`app/analyzer/overview.py` 文件保留在磁盘上但不再被 `analyze_project.py` 导入。完整移除留待后续版本清理。

## 2. 任务列表

### 实现任务 (-> Generator)

---

**IMP-1: 版本号更新**

- 文件: `app/analyzer/__init__.py`
- 内容: `__version__ = "0.4.0"`
- 完成标准: `python -c "from app.analyzer import __version__; print(__version__)"` 输出 `0.4.0`

---

**IMP-2: 引导文件收集模块 (guiding_files.py)**

- 文件: `app/analyzer/guiding_files.py` (新建)
- 内容:
  1. 定义 `GUIDING_FILE_PATTERNS` 字典（文件名/路径模式 -> 用途说明）：
     - 文档类: `README.md`, `README.rst`, `README`, `CHANGELOG.md`, `CONTRIBUTING.md`
     - 依赖清单: `package.json`, `pyproject.toml`, `setup.py`, `requirements.txt`, `Pipfile`, `Gemfile`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`
     - 容器/部署: `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`
     - CI/CD: `.github/workflows/` 下所有 `.yml`/`.yaml`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml`
     - 构建/任务: `Makefile`, `GNUmakefile`
     - 框架配置: `tsconfig.json`, `next.config.js`, `next.config.ts`, `next.config.mjs`, `nest-cli.json`, `vite.config.js`, `vite.config.ts`, `webpack.config.js`, `angular.json`
     - 环境提示: `.env.example`, `.env.template`, `.gitignore`, `.dockerignore`
  2. `collect_guiding_files(target_path)` 函数：
     - 在目标项目根目录及一级子目录搜索上述模式文件
     - README 取前 80 行，配置文件取完整内容或前 100 行
     - 返回 `{"found": [{file_path, content, label}], "missing": [label]}`
     - 总数控制在 5-15 个，超过优先保留根目录级别
     - 单个文件读取失败不崩溃
  3. `generate_directory_summary(target_path)` 函数：
     - 一级+二级目录名（仅目录，不展开文件）
     - 过滤 `EXCLUDE_DIRS`
     - UUID 格式目录折叠为 `... UUID 目录 (N 个)`
     - 编译产物目录（`dist/`, `build/`, `.next/`）折叠
     - 输出 ≤30 行纯文本
- 依赖: 从 `app.analyzer.scanner` import `EXCLUDE_DIRS`
- 完成标准: 对 Notebook 自身运行，收集到 README.md 等；目录摘要排除 `.git`、`__pycache__`

---

**IMP-3: LLM 业务板块识别模块 (domain_analyzer.py)**

- 文件: `app/analyzer/domain_analyzer.py` (新建)
- 内容:
  1. `analyze_business_domains(guiding_files_result, dir_summary, project_name, enable_dotenv=True)` 函数：
     - 调用 `llm_assistant._get_llm_config()` 获取配置
     - 无 API Key → 返回降级结果（`source="degraded"`，置信度全部标"低"）
     - 有 Key → 调用 `_call_llm()` 分析业务板块
     - 返回 `{one_liner, tech_stack, domains: [{name, description, evidence, paths, confidence}], relationships: [{from, to, type, evidence}], next_steps: [str, str, str], source: "llm"|"degraded"}`
  2. `_build_domain_analysis_prompt()` 构造 LLM prompt：
     - 约束：业务板块是用户视角的功能领域，不是代码目录名；必须注明信息来源；禁止凭空编造；板块数量 5-20；不确定时标低置信度
     - 输入：项目名 + 引导文件内容 + 目录摘要
     - 输出格式：JSON（one_liner, tech_stack, domains, relationships, next_steps）
  3. `_parse_domain_response()` 提取 JSON（处理 ```json 包裹、畸形 JSON 降级）
  4. `_degraded_domain_result()` 无 LLM 时的模板降级
- 依赖: `llm_assistant._get_llm_config`, `llm_assistant._call_llm`
- `max_tokens=2048`, `timeout=60`
- 完成标准: 无 Key 降级不崩溃；有 Key 返回 LLM 推断结果

---

**IMP-4: 清理 llm_assistant.py 旧函数**

- 文件: `app/analyzer/llm_assistant.py`
- 内容: 删除以下不再需要的函数：
  - `enhance_dir_description()` (行 163-170)
  - `enhance_module_description()` (行 173-182)
  - `enhance_project_description()` (行 185-192)
  - `enhance_description()` (行 195-201)
  - `enhance_module_descriptions_batch()` 及 `_batch_individual()`、`_batch_single_call()` (行 228-333)
  - `enhance_data_flow_llm()` (行 337-388)
  - `enhance_tech_stack_llm()` (行 391-424)
  - `detect_entry_functions()` 及 `_extract_func_name()`、`_get_module_dir()`、`_find_source_root_for_file()` (行 428-602)
  - `_template_dir_description()` 及 `_template_module_description()`、`_template_project_description()` (行 110-161)
  - `_STDLIB_NAMES` 常量 (行 264-281，仅被 `_compute_module_dependencies` 使用)
- 保留: `_load_dotenv()`, `_get_llm_config()`, `_call_llm()`, `check_api_key_available()`
- 完成标准: 旧函数全部删除，`python -c "from app.analyzer.llm_assistant import _get_llm_config, _call_llm, check_api_key_available"` 成功

---

**IMP-5: map_writer.py 瘦身 + 新增渐进式概览函数**

- 文件: `app/analyzer/map_writer.py`
- 内容:
  A. 删除以下不再需要的函数和常量：
     - `_format_tree()`, `_build_directory_tree_lines()` (目录树格式化)
     - `_parse_module_table_rows()`, `_line_has_manual()` (模块表格增量)
     - `_group_modules_by_directory()`, `_infer_module_description()`, `_compute_module_dependencies()` (模块分组)
     - `_STDLIB_NAMES` 常量
     - `_build_table_section()`, `_build_dir_table_section()`, `_build_file_table_section()` (表格构建)
     - `generate_overview()`, `generate_directory_map()`, `generate_module_map()`, `generate_data_flow()`, `_generate_data_flow_template()`, `generate_all()` (4 文件生成)
  B. 新增 `generate_progressive_overview(domain_result, output_dir)` 函数：
     - 输出 `{output_dir}/project-overview.md`
     - 结构：定位 → 技术栈 → 业务板块表格（名称/描述/路径/置信度）→ 板块关系 → 下一步建议 → 页脚
     - 置信度用纯文本符号（✓ 高 / — 中 / ? 低）
     - 使用已有的 `_atomic_write()` 和 `_merge_sections()`
  C. 保留: `_atomic_write()`, `_read_existing()`, `_split_by_sections()`, `_merge_sections()`, `MANUAL_MARKER`
- 完成标准: 函数生成 `project-overview.md`，内容包含全部 6 个部分

---

**IMP-6: CLI 入口重写 (analyze_project.py)**

- 文件: `harness/scripts/analyze_project.py`
- 内容: 完全重写主流程：
  - 砍掉 `--depth`、`--source-root` 参数
  - 保留 `--llm`、`--quiet`、`--output-dir`、`target_path`
  - 砍掉全量分析代码（Step 2-4、source_roots 检测、文件解析循环、模块分组、4 文件生成）
  - 砍掉 `_module_snippet()` 函数
  - 新流程：
    Step 1: 引导文件收集 + 目录摘要
    Step 2: LLM 板块识别（有 `--llm` 时）或降级
    Step 3: 调用 `generate_progressive_overview()` 输出
  - 移除旧导入：`scan_directory`、`detect_source_roots`、`parse_file`、`analyze_overview`、`generate_all`
  - 新导入：`collect_guiding_files`、`generate_directory_summary`、`analyze_business_domains`、`generate_progressive_overview`
- 完成标准:
  - `python harness/scripts/analyze_project.py .` 生成 `project-overview.md`
  - `python harness/scripts/analyze_project.py . --llm` 启用 LLM
  - `python harness/scripts/analyze_project.py --help` 显示新用法

---

**IMP-7: help.py 版本更新**

- 文件: `harness/scripts/help.py`
- 内容:
  - 版本号 `v0.3.1` -> `v0.4`
  - `analyze_project.py` 描述：`"智能项目分析引擎 (v0.4 渐进式披露 / --llm LLM增强)"`
- 完成标准: `python harness/scripts/help.py` 输出版本号 v0.4

---

**IMP-8: 文档更新**

- 文件: `README.md`, `harness/project-map/command-map.md`, `harness/project-map/module-map.md`, `harness/project-map/directory-map.md`
- 内容:
  - **README.md**: 版本号 -> v0.4，描述更新，快速开始更新示例
  - **command-map.md**: `analyze_project.py` -> `"智能项目分析引擎 (v0.4: 渐进式披露 / --llm LLM增强)"`
  - **module-map.md**: 新增 `guiding_files.py`、`domain_analyzer.py`；移除 `scanner.py`、`parser.py`、`overview.py`
  - **directory-map.md**: `app/analyzer/` 下文件列表同步
- 完成标准: `python harness/scripts/check_structure.py` 通过

---

### 测试任务 (-> Tester)

---

**TST-1: 引导文件收集测试**

- 文件: `tests/test_guiding_files.py` (新建)
- 覆盖: 标准项目收集、空项目返回 empty、README 截断、超 15 个优先级排序、CI 配置收集、排除目录跳过、单文件读取失败不崩溃
- 验证: `python -m pytest tests/test_guiding_files.py -v`

---

**TST-2: 目录摘要生成测试**

- 文件: `tests/test_guiding_files.py` (追加)
- 覆盖: 标准输出含一二级目录、UUID 折叠、编译产物折叠、排除目录不出现、≤30 行、空目录提示
- 验证: `python -m pytest tests/test_guiding_files.py -v -k "directory_summary"`

---

**TST-3: 业务板块识别测试**

- 文件: `tests/test_domain_analyzer.py` (新建)
- 覆盖: 无 Key 降级 mode、降级结果包含所有字段、降级置信度为"低"、prompt 构建含引导文件内容、JSON 解析正常/```json 包裹/畸形降级
- 验证: `python -m pytest tests/test_domain_analyzer.py -v`

---

**TST-4: 渐进式概览输出测试**

- 文件: `tests/test_analyze_project.py` (追加)
- 覆盖: `generate_progressive_overview()` 生成文件含 6 个必需部分、置信度符号正确、空板块不崩溃、原子写入无 .tmp 残留
- 验证: `python -m pytest tests/test_analyze_project.py -v -k "progressive_overview"`

---

**TST-5: CLI 端到端测试**

- 文件: `tests/test_analyze_project.py` (追加)
- 覆盖: 默认模式生成 `project-overview.md`、`--llm` 组合、`--quiet` 退出码 0、`--help` 含新参数说明
- 验证: `python -m pytest tests/test_analyze_project.py -v -k "CLI"`

---

**TST-6: 全量回归测试**

- 文件: `tests/` (全部已有测试)
- 覆盖: 所有已有测试保持通过（`test_export_report.py`、`test_help.py`、`test_init_project.py`、`test_search_notes.py`）
- 验证: `python -m pytest tests/ -v`

---

## 3. 依赖关系

```
IMP-1 (版本号) — 无依赖，可最先执行

IMP-2 (guiding_files.py) — 无依赖

IMP-4 (清理 llm_assistant.py) — 无依赖

IMP-3 (domain_analyzer.py) — 依赖 IMP-2 (数据结构) + IMP-4 (需要保留的 _get_llm_config/_call_llm)
    |
    v
IMP-5 (map_writer 瘦身+新增) — 依赖 IMP-3 (domain_result 数据结构)
    |
    v
IMP-6 (analyze_project.py 重写) — 依赖 IMP-2, IMP-3, IMP-5
    |
    v
IMP-7 (help.py) — 依赖 IMP-6（确认命令描述）
IMP-8 (文档更新) — 依赖 IMP-6
```

### 并行化建议

- **第一波 (并行)**: IMP-1, IMP-2, IMP-4
- **第二波**: IMP-3（依赖 IMP-2 + IMP-4）
- **第三波**: IMP-5（依赖 IMP-3）
- **第四波**: IMP-6（依赖 IMP-2, IMP-3, IMP-5）
- **第五波 (并行)**: IMP-7, IMP-8
- **第六波 (并行)**: TST-1, TST-2, TST-3, TST-4
- **第七波**: TST-5
- **第八波**: TST-6

## 4. 风险点

1. **旧代码删除范围**：删除 llm_assistant.py 和 map_writer.py 中大量函数时，需确保保留的函数不引用已删除函数。先用 grep 检查内部调用关系。
2. **引导文件读取的编码和权限**：`collect_guiding_files()` 需 try/except 包裹每个文件读取，单文件失败不影响整体。
3. **LLM JSON 解析容错**：`_parse_domain_response()` 需多重尝试——直接 `json.loads()` → 从 ```json 块提取 → 降级。所有路径不抛异常。
4. **无 LLM 场景的降级质量**：输出文件顶部明确标注"未启用 LLM"避免误认。
5. **EXCLUDE_DIRS 交叉引用**：`guiding_files.py` 从 `scanner.py` import `EXCLUDE_DIRS`，单向无循环。
6. **已有测试兼容**：`test_analyze_project.py` 中的旧测试依赖 `--depth=full` 模式和 4 文件输出，需 Tester 同步更新。
