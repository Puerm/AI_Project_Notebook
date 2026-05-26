# Module Map

各模块的职责、接口和依赖关系。


## 自动分析模块

| 文件路径 | 模块描述 | 主要函数 | 主要类 |
| ---- | ---- | ---- | ---- |
| app\analyzer\__init__.py | analyzer 包入口，v0.5.1 | - | - | <!-- MANUAL -->
| app\analyzer\prompts\__init__.py | prompt 库加载器 | load_prompt | - |
| app\analyzer\guiding_files.py | 引导文件收集与目录摘要 | collect_guiding_files, generate_directory_summary | - |
| app\analyzer\domain_analyzer.py | LLM 业务板块识别（两级：主板块+子板块） | analyze_business_domains, _build_domain_analysis_prompt, _parse_domain_response, _degraded_domain_result | - |
| app\analyzer\llm_assistant.py | LLM API 基础设施（调用/配置/Key检测） | _load_dotenv, _get_llm_config, _call_llm, check_api_key_available | - |
| app\analyzer\digest_collector.py | codebase-digest 集成与维度文件筛选 | is_cdigest_available, collect_digest, preprocess_digest, format_digest_for_llm, format_files_for_llm, filter_for_architecture, filter_for_user_stories, filter_for_risk | - |
| app\analyzer\dimension_analyzer.py | 聚焦三维度分析引擎（架构/用户故事/风险），使用官方 prompt + 筛选文件子集 | analyze_architecture, analyze_user_stories, analyze_risk | - |
| app\analyzer\map_writer.py | 项目地图文件生成（v0.4 渐进式概览） | _atomic_write, _merge_sections, generate_progressive_overview | - |
| app\analyzer\scanner.py | EXCLUDE_DIRS 常量（目录排除规则） | _infer_dir_label, scan_directory, detect_source_root, detect_source_roots | - |
| app\analyzer\parser.py | ~~已移除~~ — 不再被导入 | parse_python, check_nodejs, _parse_js_regex | - |
| app\analyzer\overview.py | ~~已移除~~ — 不再被导入 | analyze_overview, _detect_tech_stack, _detect_entry_files | - |
| app\analyze_project.py | 智能项目分析引擎入口 v0.5.1 — 渐进式披露 + digest 聚焦三维度分析 | main | - |
| harness\state\feedback_signal.py | 反馈信号数据模型 | to_dict, from_dict, to_json_schema | FeedbackSignal |
| harness\state\feedback_engine.py | 反馈信号引擎（读写/去重/模式检测） | load_signals, add_signal, save_signals, detect_patterns | FeedbackEngine |
| harness\state\workflow_state.py | 工作流状态管理器（偏差趋势/回环决策） | init, record_stage, get_deviation_trend, should_continue_loop, to_feedback_signal | WorkflowState |
| harness\scripts\generate_rule_evolution.py | 规则演化建议生成脚本 | - | - |
| harness\scripts\diagnose_and_fix.py | 自我升级引擎 — 反馈信号驱动的自动诊断与修复 | main, _load_config, _check_dedup, _apply_safety_boundary, _call_llm_diagnosis, _sandbox_verify, _write_upgrade_history | - |
| harness\config\project.yaml | 项目模板变量定义 — 所有占位符 {{...}} 的单一数据源 | - | - |
| tests\test_export_report.py | 导出报告测试 | test_export_report_runs_and_returns_zero, test_export_report_contains_expected_sections, test_export_report_sections_have_numbered_source_labels | - |
| tests\test_help.py | help 命令测试 | test_help_runs_and_returns_zero, test_help_lists_all_commands | - |
| tests\test_init_project.py | 初始化项目测试 | test_init_project_creates_harness_dir, test_init_project_generates_directory_map_with_tree, test_init_project_refuses_existing_harness, test_init_project_refuses_nonexistent_path, test_init_project_missing_argument_exits_one | - |
| tests\test_search_notes.py | 搜索笔记测试 | test_search_finds_matches, test_search_no_match_shows_nothing, test_search_missing_argument_exits_one, test_search_output_format_contains_filename_colon_lineno | - |





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
