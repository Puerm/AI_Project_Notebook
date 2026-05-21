# Module Map

各模块的职责、接口和依赖关系。


## 自动分析模块

| 文件路径 | 模块描述 | 主要函数 | 主要类 |
| ---- | ---- | ---- | ---- |
| app\analyzer\__init__.py | 无函数/类 | - | - | <!-- MANUAL -->
| app\analyzer\llm_assistant.py | 模块职责描述、数据流推断、技术栈推断、入口函数检测 | _load_dotenv, _get_llm_config, _call_llm, enhance_module_descriptions_batch, enhance_data_flow_llm, enhance_tech_stack_llm, detect_entry_functions, check_api_key_available | - |
| app\analyzer\map_writer.py | 20 个函数，1 个导入 | _format_tree, _group_modules_by_directory, _infer_module_description, _compute_module_dependencies, generate_all | - |
| app\analyzer\overview.py | 项目概览：技术栈检测、项目类型推断、入口文件检测 | _detect_tech_stack, _gather_tech_features, _infer_project_type, _detect_entry_files, analyze_overview | - |
| app\analyzer\parser.py | 6 个函数，6 个导入 | parse_python, check_nodejs, check_js_parser, _parse_js_with_acorn, _parse_js_regex | - |
| app\analyzer\scanner.py | 目录扫描、源码根检测（单/多） | _infer_dir_label, scan_directory, detect_source_root, detect_source_roots, _common_ancestor | - |
| tests\test_export_report.py | 3 个函数，3 个导入 | test_export_report_runs_and_returns_zero, test_export_report_contains_expected_sections, test_export_report_sections_have_numbered_source_labels | - |
| tests\test_help.py | 2 个函数，3 个导入 | test_help_runs_and_returns_zero, test_help_lists_all_commands | - |
| tests\test_init_project.py | 11 个函数，5 个导入 | test_init_project_creates_harness_dir, test_init_project_generates_directory_map_with_tree, test_init_project_refuses_existing_harness, test_init_project_refuses_nonexistent_path, test_init_project_missing_argument_exits_one | - |
| tests\test_search_notes.py | 4 个函数，3 个导入 | test_search_finds_matches, test_search_no_match_shows_nothing, test_search_missing_argument_exits_one, test_search_output_format_contains_filename_colon_lineno | - |





## 登记规则

新模块登记时必须填写：
1. 模块名称（与文件名对应）
2. 文件路径
3. 一句话职责描述
4. 依赖列表（依赖哪些模块/库）


## 变更规则

- 新增模块后在此文件中新增一行
- 修改模块职责后更新对应描述
- 模块被移除后标记为 `~~已移除~~` 并在 `change-map.md` 中记录
