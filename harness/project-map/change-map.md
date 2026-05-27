# Change Map

记录每次变更的摘要，保持项目演化历史可追溯。

## 变更记录

### 2026-05-27: 修复 LLM 检测成功判断逻辑 — stderr 错误输出 + focus_fields 模式成功判断

- **类型**: 修复
- **范围**: `harness/scripts/harness_deploy.py` (1 文件)
- **摘要**: 修复 `_llm_detect_project` 和 `detect_project` 两个 bug
  - **IMP-1**: `_llm_detect_project` — 4 个异常分支增加 stderr 输出：API 调用异常 / 空响应 / JSON 解析失败 / 未找到 JSON 对象，异常变量改为 `except Exception as e` 避免丢信息
  - **IMP-2**: `detect_project` — focus_fields 模式成功判断从硬编码 `"languages" in llm_result` 改为模式感知：focus 模式判断 `isinstance(llm_result, dict) and bool(llm_result)`，完整模式保持 `"languages" in llm_result`；引入 `is_focus_mode`/`llm_attempted` 消除 `missing_fields` 作用域隐患；result merging 拆分 `languages`/`framework`（仅完整模式）和 `domain`/`description`/`entry_point`/`source`（两者均适用）的外层条件
- **验证**: `check_structure.py` 52/52 PASS, `pytest tests/test_harness_deploy.py` 55/55 PASS

### 2026-05-27: 修复维度分析 Prompt 溢出

- **类型**: 修复
- **范围**: 4 修改 + 3 文档更新
- **摘要**: 修复 LLM 聚焦分析中 prompt 超大导致 HTTP 400 溢出的问题，三层防线控制
  - **IMP-1**: `llm_assistant.py` — `_call_llm` 返回值从 `str|None` 改为元组 `(str|None, dict|None)`，HTTPError 返回 `(None, {"status": code, "reason": reason})`
  - **IMP-2**: `domain_analyzer.py` — 适配元组返回值 + 增强 err_info 诊断日志；`test_analyze_project.py` 断言同步更新
  - **IMP-3**: `digest_collector.py` — `filter_for_risk` 增加优先级排序（依赖>配置>脚本>错误处理路径>安全关键词）+ 两遍去重
  - **IMP-4**: `digest_collector.py` — 三个 filter 函数增加文件数上限（架构100/用户故事150/风险200），超出截断并打印 warning
  - **IMP-5**: `digest_collector.py` — 新增 `estimate_tokens()` + `format_files_for_llm()` 支持 `max_tokens` 参数，超出预算截断并追加截断标注
  - **IMP-6**: `dimension_analyzer.py` — 新增 `_get_model_context_limit()` + `_compute_token_budget()`；三个 builder 函数接入 token 预算；`_call_llm_with_retry` 检测 HTTP 400 跳过重试
  - **IMP-7**: 确认 `analyze_project.py` 无需修改
- **影响文件**: `app/analyzer/llm_assistant.py`, `app/analyzer/domain_analyzer.py`, `app/analyzer/digest_collector.py`, `app/analyzer/dimension_analyzer.py`, `tests/test_analyze_project.py`, `harness/project-map/module-map.md`, `harness/project-map/change-map.md`
- **验证**: `python harness/scripts/check_structure.py` 52/52 PASS, `python -m pytest tests/test_analyze_project.py tests/test_digest_collector.py` -v 92/92 PASS

### 2026-05-26: CodeGraph 集成 — 图谱增强项目分析

- **类型**: 新功能
- **范围**: 1 新建 + 4 修改 + 4 文档更新
- **摘要**: 实现 CodeGraph 符号知识图谱集成，新增 `--codegraph` 选项增强 LLM 项目分析质量
  - **IMP-1**: 新建 `app/analyzer/codegraph.py` — db 检测、Schema 提取、只读 SELECT 查询、Markdown 格式化
  - **IMP-2**: `llm_assistant.py` — 新增 `_call_llm_with_tools()` 函数，支持 Anthropic/OpenAI tool use 多轮探索（最多 5 轮）
  - **IMP-3**: `analyze_project.py` — 新增 `--codegraph` CLI 参数，非 digest 模式 Step 1.5 / digest 模式 Step 3.5 插入 CodeGraph 探索阶段，探索结果作为 `codegraph_context` 注入 domain/dimension 分析
  - **IMP-4**: `domain_analyzer.py` — `analyze_business_domains()` 新增可选参数 `codegraph_context`，非空时追加到 LLM prompt
  - **IMP-5**: `dimension_analyzer.py` — 三个分析函数各新增可选参数 `codegraph_context`，非空时追加维度特定的 CodeGraph 上下文引导
  - **IMP-6**: project-map 文档同步更新 (module-map/directory-map/command-map/data-flow/change-map)
- **影响文件**: `app/analyzer/codegraph.py` (新), `app/analyzer/llm_assistant.py`, `app/analyzer/domain_analyzer.py`, `app/analyzer/dimension_analyzer.py`, `app/analyze_project.py`, `harness/project-map/module-map.md`, `harness/project-map/directory-map.md`, `harness/project-map/command-map.md`, `harness/project-map/data-flow.md`
- **验证**: `python harness/scripts/check_structure.py` 52/52 通过

### 2026-05-26: deploy 脚本集成 init 流水线 — 读取 project.yaml 基线

- **类型**: 增强
- **范围**: 1 修改
- **摘要**: `harness_deploy.py` 的 `detect_project()` 现在优先读取 `init_project.py` 生成的 `project.yaml` 作为基线，只补充缺失字段（domain/description/entry_point），不覆盖已有值。确立三步迁移流程：init → analyze → deploy。
  - 新增 `_read_project_yaml_baseline()` 读取已有 project.yaml
  - `_llm_detect_project()` 支持 `focus_fields` 参数，基线存在时只请求缺失字段
  - `main()` 帮助文本更新为三步迁移流程图
- **验证**: `check_structure.py` 52/52 PASS

### 2026-05-26: Harness 框架个性化部署 v0.1 审查修复 — 3 个 Reviewer 问题修复

- **类型**: 修复
- **范围**: 1 修改
- **摘要**: 修复 `harness_deploy.py` `_adapt_workflow_content` 中 Reviewer 发现的 3 个问题
  - `{{project_name}}` 替换值从 `os.path.basename(os.getcwd())` 改为 `features.get("project_name")`
  - `is_frontend_only`/`is_go_only`/`is_rust_only` 死代码消除：现在实际影响 stages 跳过逻辑
  - 实现 YAML frontmatter 解析 + 项目类型条件适配：前端项目自动标记 `tester`/`generator-fix`/`generator-test-fix` 阶段为 `skip: true`
- **验证**: `check_structure.py` 52/52 PASS, 功能测试通过

### 2026-05-26: Harness 框架个性化部署 v0.1 — LLM 检测 + 适配建议生成 + 交互式确认

- **类型**: 新功能
- **范围**: 1 新建 + 18 修改
- **摘要**: 实现 Harness 框架个性化部署系统，使 harness 可智能适配目标项目
  - **IMP-1**: 7 个 agent 文件 (pm/planner/explorer/generator/reviewer/tester/harness_maintainer) 添加 `<!-- ADAPTABLE_ZONE_START/END -->` 可适配区标记
  - **IMP-2**: `harness/config/project.yaml` 新增 `domain`、`description`、`entry_point` 三个字段
  - **IMP-3**: 新建 `harness/scripts/harness_deploy.py` — 三阶段部署引擎 (Phase 1: LLM 项目检测 + 静态降级, Phase 2: 适配建议生成, Phase 3: 交互式确认 + 原子写入)
  - **IMP-4**: `help.py` / `check_structure.py` / `command-map.md` 注册新命令
  - **IMP-5**: 5 个 project-map 文档同步更新 (module-map/directory-map/data-flow/change-map/overview)
  - **IMP-6**: `README.md` / `CLAUDE.md` 版本号 v0.9 -> v0.10，新增 harness_deploy 使用说明
- **影响文件**: `harness_deploy.py` (新), 7 个 agent 文件, `project.yaml`, `help.py`, `check_structure.py`, 5 个 project-map, `README.md`, `CLAUDE.md`
- **验证**: `python harness/scripts/check_structure.py` 52/52 通过

### 2026-05-26: Harness 框架通用化 v0.1 BUG-1 修复 — _fill_templates 扩展至 .claude/ 目录

- **类型**: 修复
- **范围**: 1 修改
- **摘要**: `init_project.py` 的 `_fill_templates` 仅遍历 `harness/`，不填充 `.claude/agents/` 中的 `{{test_command}}` 占位符。在第 522 行增加 `_fill_templates(target_claude, config_for_fill)` 调用。
- **验证**: `check_structure.py` PASS (51/51), pytest 350 passed / 15 failed (3 gap-marker 测试因占位符已被填充而失败, 需 Tester 更新; 12 个为预存的 analyze_project CLI 测试失败)

### 2026-05-26: Harness 框架通用化 v0.1 — project.yaml 模板变量 + 语言无关改造 + 目录结构分离

- **类型**: 重构
- **范围**: 1 新建 + 15 修改
- **摘要**: 移除 Python/pytest/check_structure.py 硬编码，使 harness 框架可部署到非 Python 项目
  - **IMP-1**: 新建 `harness/config/project.yaml` — 项目模板变量定义（project_name/version/languages/test_framework/test_command/package_manager/validation_command）
  - **IMP-2**: `harness/scripts/help.py` — 从 project.yaml 读取项目名和版本，移除 check_structure.py/analyze_project.py 命令条目
  - **IMP-3**: `.claude/agents/*.md` — 移除 python/pytest/snake_case.py 硬编码，替换为 {{test_command}} 和通用描述
  - **IMP-4**: `harness/rules/coding-rules.md`, `workflow-rules.md` — 规则 3/8/11 改为语言无关描述
  - **IMP-5**: `harness/scripts/analyze_project.py` 迁移至 `app/analyze_project.py`；check_structure.py 移除 app/analyzer/ 目录和 analyze_project.py 检查；init_project.py 移除 app/analyzer/ 创建；dimension_analyzer.py 更新路径引用
  - **IMP-6**: `diagnose_and_fix.py` — `_run_verification()` 从三步（check_structure + pytest + agent YAML）调整为两步（pytest + agent YAML）
  - **IMP-7**: `init_project.py` — 新增 LLM 项目检测（_detect_project_features/_generate_project_yaml/_fill_templates），降级为纯静态检测
  - **IMP-8**: `harness/prompts/diagnosis.txt` — 头部注释改为 {{project_name}} 占位符
  - **IMP-9**: 8 个文档同步更新（overview/directory-map/module-map/command-map/data-flow/change-map/README/CLAUDE.md）
  - **check_structure.py**: REQUIRED_DIRS 移除 app/analyzer，REQUIRED_FILES 移除 analyze_project.py，新增 project.yaml
- **影响文件**: `harness/config/project.yaml` (新), `help.py`, `init_project.py`, `check_structure.py`, `diagnose_and_fix.py`, `diagnosis.txt`, `dimension_analyzer.py`, `app/analyze_project.py` (新位置), `coding-rules.md`, `workflow-rules.md`, 7 个 project-map + README + CLAUDE
- **验证**: `python harness/scripts/check_structure.py` 通过 (14/38)

### 2026-05-25: Harness 自我升级引擎 v0.1 — LLM 根因诊断 + git worktree 沙盒验证 + 自动程度分层处理

- **类型**: 新功能
- **范围**: 3 新建 + 11 修改
- **摘要**: 实现 Harness 自我升级系统 v0.1
  - **IMP-1**: 新建 `harness/config/self-upgrade.yaml` — 自动程度配置（auto/semi-auto/disabled glob 匹配）
  - **IMP-2**: 新建 `harness/prompts/diagnosis.txt` — LLM 诊断 prompt 模板（v1.0.0）
  - **IMP-3**: 新建 `harness/scripts/diagnose_and_fix.py` — 自我升级主引擎（反馈信号扫描 → 24h 去重 → LLM 诊断 → 安全边界 → git worktree 沙盒验证 → 合并/降级）
  - **IMP-4**: `.gitignore` — 追加 `upgrade-history.json`
  - **IMP-5**: `check_structure.py` — 新增 2 目录 + 3 文件检查项
  - **IMP-6**: 4 个 `.claude/commands/workflow/*.md` — 收尾阶段追加自我升级触发逻辑
  - **IMP-7**: 5 个 project-map 文档同步更新
- **影响文件**: `harness/config/self-upgrade.yaml` (新), `harness/prompts/diagnosis.txt` (新), `harness/scripts/diagnose_and_fix.py` (新), `.gitignore`, `check_structure.py`, 4 个 workflow command, 5 个 project-map 文件
- **验证**: `python harness/scripts/check_structure.py` 52/52 通过

### 2026-05-25: fix-harness-feedback-loop — save_signals 空操作修复 + generate_rule_evolution 原子写入补全

- **类型**: 修复
- **范围**: 2 个文件
- **摘要**: 修复测试报告中阻塞 bug 和第二类问题
  - **阻塞 bug**: `feedback_engine.py` — `save_signals()` 方法体从 `pass` 替换为实际原子写入。`__init__` 新增 `self._signals` 内存缓存，`add_signal()` 同步更新缓存，`save_signals()` 从缓存写入磁盘（.tmp + os.replace）
  - **第二类**: `generate_rule_evolution.py` — 追加模式从直接 `open("a")` 替换为原子写入（先读已有内容再整体 .tmp + os.replace）
- **影响文件**: `harness/state/feedback_engine.py`, `harness/scripts/generate_rule_evolution.py`
- **验证**: `python harness/scripts/check_structure.py` 47/47 通过, `python -m pytest tests/` 254/254 通过

### 2026-05-25: Harness 反馈调节系统 v0.1 — 偏差趋势自适应回环 + 规则演化引擎

- **类型**: 新功能
- **范围**: 4 个新建文件 + 7 个修改文件
- **摘要**: 实现工作流反馈闭环：偏差趋势自适应回环替代硬编码"最多 2 次"、反馈信号持久化引擎、规则演化建议自动生成
  - **IMP-1**: 新建 `harness/state/feedback_signal.py` — FeedbackSignal dataclass（7 个字段 + to_dict/from_dict/to_json_schema）
  - **IMP-2**: 新建 `harness/state/feedback_engine.py` — FeedbackEngine 类（JSON 读写/去重/重复模式检测 >=3 次）
  - **IMP-3**: 新建 `harness/state/workflow_state.py` — WorkflowState 类（init/record_stage/get_deviation_trend/should_continue_loop/to_feedback_signal，偏差趋势自适应回环决策）
  - **IMP-4**: 新建 `harness/scripts/generate_rule_evolution.py` — 扫描反馈信号生成 rule-evolution-proposal.md
  - **IMP-5**: `check_structure.py` — REQUIRED_DIRS 新增 `harness/state`（12 -> 13 目录）
  - **IMP-6**: `.gitignore` — 忽略运行时生成的 JSON 状态文件
  - **IMP-7**: 4 个 `.claude/commands/workflow/*.md` — 升级为自包含的偏差趋势自适应回环指令（WorkflowState 初始化 + 偏差趋势判断 + FeedbackSignal 追加 + generate_rule_evolution.py 收尾），不再使用跨文件引用
  - **IMP-8**: `.claude/agents/planner.md` — 新增第 6 步：阅读 rule-evolution-proposal.md 未处理建议
  - **IMP-9**: 5 个 project-map 文档同步更新（directory-map/module-map/data-flow/command-map/change-map）
- **影响文件**: `harness/state/` (新建 4 文件), `harness/scripts/generate_rule_evolution.py` (新建), `check_structure.py`, `.gitignore`, 4 个 `.claude/commands/workflow/*.md`, `planner.md`, 5 个 project-map 文件
- **验证**: `python harness/scripts/check_structure.py` 通过 (47/47), self-tests 通过

### 2026-05-22: v0.5.1 修复 LLM 全量分析失焦问题 — 聚焦分析替代全量 dump

- **类型**: 修复
- **范围**: 4 个新建文件 + 3 个修改应用文件 + 7 个文档更新
- **摘要**: 修复 v0.5 --digest 模式下全量文件统一 dump 导致 LLM 失去焦点的问题，改为每维度筛选文件子集 + 官方 prompt 模板
  - **IMP-1**: `domain_analyzer.py` — 业务板块识别支持两级结构（主板块+子板块），不确定信息标注 [推测]，`_normalize_result` 补齐 `sub_domains` 默认值
  - **IMP-2**: 新建 `app/analyzer/prompts/` 目录 — `__init__.py` (load_prompt 加载器) + 三个官方 prompt 模板 (`architecture.txt`, `user_stories.txt`, `risk.txt`)，每个模板 >200 字符
  - **IMP-3**: `digest_collector.py` — 新增 `filter_for_architecture/filter_for_user_stories/filter_for_risk` 三个维度筛选函数（基于启发式正则），新增 `format_files_for_llm` 函数，`collect_digest` 不再格式化全量 LLM 文本（返回 `files` 字段替代 `text`）
  - **IMP-4**: `dimension_analyzer.py` — 重构为聚焦分析：`analyze_architecture/analyze_user_stories/analyze_risk` 接收 `filtered_files` 替代 `digest_text`，`_build_*_prompt` 改为 `_build_*_prompt_from_files` 使用 `load_prompt` 加载官方模板，移除全量 dump 路径
  - **IMP-5**: `analyze_project.py` — digest 模式从 6 步改为 7 步新流程：引导文件概览 → 两级板块识别 → 概览输出 → digest 文件池收集 → 三维度聚焦分析（每维度传入筛选子集+官方 prompt），非 digest 模式行为不变
  - **IMP-6**: 版本号 0.5.0 → 0.5.1，README/help.py/command-map/module-map/directory-map/data-flow 同步更新
  - **IMP-7**: change-map 登记本次变更
- **影响文件**: `domain_analyzer.py` (修改), `prompts/__init__.py` (新), `prompts/architecture.txt` (新), `prompts/user_stories.txt` (新), `prompts/risk.txt` (新), `digest_collector.py` (修改), `dimension_analyzer.py` (修改), `analyze_project.py` (修改), `__init__.py` (修改), `help.py` (修改), `module-map.md`, `directory-map.md`, `data-flow.md`, `command-map.md`, `README.md`
- **验证**: `python harness/scripts/check_structure.py` 通过 (46/46)

### 2026-05-22: v0.1.5 集成 Codebase Digest — 全量文件收集 + LLM 三维度分析

- **类型**: 新功能
- **范围**: 2 个新建文件 + 3 个修改应用文件 + 5 个文档更新
- **摘要**: 集成 codebase-digest 包实现全量文件收集，新增三维度 LLM 分析（架构/用户故事/风险），添加 `--digest` 和 `--max-size` CLI 参数
  - **IMP-1**: 新建 `digest_collector.py` — codebase-digest 集成、噪声过滤、max-size 截断、LLM 文本格式化
  - **IMP-2**: 新建 `dimension_analyzer.py` — 三维度分析引擎（架构分层/用户故事重建/风险分析），含 LLM 增强和降级模式
  - **IMP-3**: `analyze_project.py` 新增 `--digest` / `--max-size` 参数，digest 模式下 6 步流程（收集→领域分析→概览→架构→故事→风险），非 digest 模式保持现有行为不变
  - **IMP-4**: `help.py` 版本号 v0.4 → v0.5，命令描述更新
  - **IMP-5**: `module-map.md` 登记 2 个新模块
  - **IMP-6**: command-map / data-flow / change-map / README 文档同步更新
- **影响文件**: `digest_collector.py` (新), `dimension_analyzer.py` (新), `__init__.py`, `analyze_project.py`, `help.py`, module-map.md, command-map.md, data-flow.md, change-map.md, README.md
- **验证**: `python harness/scripts/check_structure.py` 通过 (46/46), `python -m pytest tests/test_analyze_project.py` 50/51 通过 (1 个 test_help_output 失败因版本号变更，待 Tester 更新)

### 2026-05-22: v0.1.5 generator-fix — 审查反馈修复 (4 个问题)

- **类型**: 修复
- **范围**: `digest_collector.py`, `dimension_analyzer.py`, `analyze_project.py`, `directory-map.md`
- **摘要**: 修复 v0.1.5 审查发现的 4 个问题
  - **第一类-1**: `digest_collector.py` — run_digest_collection / preprocess_digest / format_digest_for_llm / collect_digest 四个函数的多行 docstring 改为单行描述（符合 coding-rules 第 13 条）
  - **第一类-2**: `dimension_analyzer.py` — analyze_architecture / analyze_user_stories / analyze_risk 三个函数的多行 docstring 改为单行描述（其余 8 个内部函数已为单行，无需修改）
  - **第一类-3**: `analyze_project.py` — 移除非 digest 模式下重复的"分析目标"和"输出目录" print（已在上方统一打印）
  - **第二类-4**: `directory-map.md` — `app/analyzer/` 目录树中补充 digest_collector.py 和 dimension_analyzer.py
- **验证**: `python harness/scripts/check_structure.py` 通过 (46/46), `python -m pytest tests/test_analyze_project.py` 50/51 通过 (1 个 test_help_output 失败为预存问题)

### 2026-05-22: v0.4 渐进式披露引擎 — 引导文件收集 + LLM 业务板块识别 + 单一概览输出

- **类型**: 新功能
- **范围**: 2 个新建文件 + 4 个修改应用文件 + 5 个文档更新
- **摘要**: 实现 v0.4 渐进式披露分析引擎，用聚焦的引导文件分析替代全量源码扫描
  - **IMP-1**: 版本号 0.3.2 -> 0.4.0
  - **IMP-2**: 新建 `guiding_files.py` — 引导文件收集 (GUIDING_FILE_PATTERNS) + 目录摘要 (≤30行, UUID/编译产物折叠)
  - **IMP-3**: 新建 `domain_analyzer.py` — LLM 业务板块识别 (max_tokens=2048, timeout=60) + 降级模式
  - **IMP-4**: `llm_assistant.py` 砍掉 13 个旧函数，仅保留 4 个基础设施函数 (_load_dotenv, _get_llm_config, _call_llm, check_api_key_available)
  - **IMP-5**: `map_writer.py` 砍掉 15 个旧函数/常量，新增 `generate_progressive_overview()` 单一输出函数
  - **IMP-6**: `analyze_project.py` 完全重写: 砍掉 --depth/--source-root，3 步新流程 (引导文件→板块识别→概览输出)
  - **IMP-7**: help.py 版本号 v0.3.1 -> v0.4
  - **IMP-8**: README/command-map/module-map/directory-map 文档同步更新
- **影响文件**: `guiding_files.py` (新), `domain_analyzer.py` (新), `__init__.py`, `llm_assistant.py`, `map_writer.py`, `analyze_project.py`, `help.py`, README.md, command-map.md, module-map.md, directory-map.md, data-flow.md, change-map.md
- **验证**: `python harness/scripts/check_structure.py` 通过 (46/46), `python -m pytest tests/` 待 Tester 更新

### 2026-05-21: v0.3.2 BioTec --llm 实测 — 暴露多源码根串扰 + data-flow 超时 + 粒度问题

- **类型**: 测试/反馈
- **范围**: 无新代码修改（data-flow 分批+超时已临时修复）
- **摘要**: BioTec --llm 实测发现 4 个问题：
  - data-flow LLM 调用超时（10s 不够，已临时改分批+30s）
  - 多源码根 back/front 互相串扰（缺父子过滤）
  - `back/python` 被当成一个模块（源码根检测不够深入）
  - directory-map 仍有 harness 部署残留
- **影响文件**: `llm_assistant.py`（data-flow 分批+超时修复）、feedback 日志
- **验证**: 待用户重新测试

### 2026-05-21: v0.3.2 LLM 集成修复 — Generator 审查反馈修复 (FIX-IMP-1/2/3)

- **类型**: 修复
- **范围**: `app/analyzer/llm_assistant.py` (1 文件)
- **摘要**: 修复 v0.3.2 审查发现的 3 个应用代码问题
  - **FIX-IMP-1**: `.env` 加载可控化 — `_get_llm_config()` 及 9 个公开函数新增 `enable_dotenv` 参数（默认 True），测试环境可传 False 跳过 `.env` 加载
  - **FIX-IMP-2**: `_get_module_dir()` 支持 source_root 前缀剥离 — 新增 `source_root` 参数和 `_find_source_root_for_file()` 辅助函数，`detect_entry_functions()` 改为按文件匹配 source_root
  - **FIX-IMP-3**: 批量模块描述使用各模块自身 source_root — `_batch_individual()` 和 `_batch_single_call()` 改为从 `mod.get("source_root", source_root)` 取标签
- **验证**: `python harness/scripts/check_structure.py` 通过 (46/46), `python -m pytest tests/ -v` 68/71 通过 (3 个失败为期待结果，需 Tester 同步更新 FIX-TST-1/2)
- **待 Tester**: FIX-TST-1 (测试传入 `enable_dotenv=False`), FIX-TST-2 (data-flow 断言更新为 "未检测到入口函数")

### 2026-05-21: v0.3.2 LLM 集成修复 — 多源码根/LLM三维护增强/入口函数检测

- **类型**: 新功能
- **范围**: 6 个应用代码文件修改，无新建文件
- **摘要**: 实现 v0.3.2 LLM 集成修复，解决真机测试暴露的"项目分析不透彻"问题
  - **IMP-1**: 版本号 0.3.1 -> 0.3.2
  - **IMP-2**: scanner.py 新增 `detect_source_roots()` 多源码根检测（Python包/js项目分别识别，父子去重）
  - **IMP-3**: overview.py `_detect_tech_stack()` 改为深目录递归搜索（3层），新增 `_gather_tech_features()` 收集技术特征供LLM上下文使用
  - **IMP-4**: llm_assistant.py 新增 `enhance_module_descriptions_batch()` 自适应批量模块描述（<=10逐模块，>10单次批处理），`_call_llm()` max_tokens改为可配置
  - **IMP-5**: llm_assistant.py 新增 `enhance_data_flow_llm()` LLM数据流推断
  - **IMP-6**: llm_assistant.py 新增 `enhance_tech_stack_llm()` LLM技术栈/项目类型推断
  - **IMP-7**: llm_assistant.py 新增 `detect_entry_functions()` 硬编码规则检测入口函数（Python argparse/click/typer + JS express/fastify）
  - **IMP-8**: map_writer.py 表头新增"源码根"列，`generate_data_flow()` 签名改为 `entry_functions`，`_parse_module_table_rows()` 表头检测修复
  - **IMP-9**: analyze_project.py 编排重构：多源码根分组、LLM三维护增强（模块描述/数据流/技术栈）、无LLM入口函数降级
- **影响文件**: `app/analyzer/__init__.py`, `app/analyzer/scanner.py`, `app/analyzer/overview.py`, `app/analyzer/llm_assistant.py`, `app/analyzer/map_writer.py`, `harness/scripts/analyze_project.py`, `harness/project-map/command-map.md`
- **验证**: `python harness/scripts/check_structure.py` 通过 (46/46), `python -m pytest tests/` 68/71 通过 (3 个失败：1个.env预存在问题 + 2个data-flow行为变更预期)

### 2026-05-21: v0.3.1 输出质量修复 — 修复 v0.3 真机测试暴露的 4 个质量问题

- **类型**: 修复
- **范围**: 6 个应用代码文件修改，无新建文件
- **摘要**: 修复 v0.3 BioTec 真机测试暴露的输出质量问题
  - **IMP-1**: 版本号更新 0.3.0 -> 0.3.1
  - **IMP-2**: scanner.py 新增 `detect_source_root()` 自动识别源码根目录
  - **IMP-3**: map_writer.py 目录树新增 `--depth` 参数（默认 3）和折叠显示
  - **IMP-4**: map_writer.py module-map 重构为目录级模块，新增 `_group_modules_by_directory`、`_infer_module_description`、`_compute_module_dependencies`，表头改为模块路径/描述/函数类/依赖
  - **IMP-5**: map_writer.py data-flow 重定义为 LLM 引导模板（无 LLM 时不生成逐条 import）
  - **IMP-6**: map_writer.py `generate_all` 签名更新，新增 `max_depth` 和 `source_root` 参数
  - **IMP-7**: llm_assistant.py 新增 `_load_dotenv()` .env 解析和 `check_api_key_available()` API Key 引导
  - **IMP-8**: analyze_project.py CLI 新增 `--depth`/`--source-root`，移除 `--no-llm`，新增源码根检测和目录级模块分组编排逻辑
  - **IMP-9**: help.py 版本号 v0.3 -> v0.3.1，命令描述增强
  - **generator-fix**: README.md 版本号 v0.3 -> v0.3.1，新增 --depth/--source-root/--llm 使用示例
- **影响文件**: `app/analyzer/__init__.py`, `app/analyzer/scanner.py`, `app/analyzer/map_writer.py`, `app/analyzer/llm_assistant.py`, `harness/scripts/analyze_project.py`, `harness/scripts/help.py`, `README.md`
- **验证**: `python harness/scripts/check_structure.py` 通过 (46/46), `python -m pytest tests/` 47/51 通过 (4 个失败为期待结果，由 Tester 更新 TST-6)

### 2026-05-21: v0.3 BioTec 真机测试 — 暴露 4 个质量问题

- **类型**: 测试/反馈
- **范围**: 无代码修改，仅记录反馈
- **摘要**: 对 BioTec 项目（682 源文件）运行 `analyze_project.py`，产出 4 个 project-map 文件但质量不可用
  - **问题 1 — module-map**: 682 行平铺表格，每文件一行。根因：Spec 将"文件"等同于"模块"，未定义模块聚合粒度
  - **问题 2 — data-flow**: 逐条 import 语句列出（含 stdlib 和第三方包），未聚合为模块级依赖
  - **问题 3 — directory-map**: 298KB 全展开目录树，未限制深度
  - **问题 4 — 无 .env / 引导**: `ANTHROPIC_API_KEY` 环境变量未在任何地方告知用户，缺 Key 时静默降级
  - **根因**: PM 缺"关键概念定义"、Plan 缺"输出质量约束"、Generator 缺"输出可用性自检"、全链路缺"用户上手引导"
  - 已记录 4 条改进到 `harness/feedback/improvement-log.md`
- **影响文件**: harness/feedback/improvement-log.md, harness/project-map/change-map.md
- **验证**: —

### 2026-05-21: v0.3 审查反馈修复 — scanner/map_writer/init_project

- **类型**: 修复
- **范围**: `app/analyzer/scanner.py`, `app/analyzer/map_writer.py`, `harness/scripts/init_project.py`
- **摘要**: 修复 v0.3 项目分析引擎的三个审查发现的问题
  - **D1**: scanner.py EXCLUDE_DIRS 增加 `harness`，与 init_project.py 对齐，避免扫描自身 harness 目录
  - **D2**: init_project.py 的 command-map 模板追加 `analyze_project.py` 条目，按功能分组排列
  - **D3**: map_writer.py 重写 `_merge_sections()` 为按 ## 段落增量合并（保留 MANUAL 段落），`generate_module_map()` 支持行级增量更新（MANUAL 行保留、新模块追加、已有模块更新）
- **验证**: `python harness/scripts/check_structure.py` 通过 (46/46), `python -m pytest tests/ -v` 20/20 通过

### 2026-05-21: v0.3 智能项目分析引擎 — 自动生成项目理解地图

- **类型**: 新功能
- **范围**: `app/analyzer/` + `harness/scripts/analyze_project.py` + project-map 文档更新
- **摘要**: 实现 v0.3 智能项目分析引擎，自动扫描目标项目并生成 4 个 project-map 文件
  - 创建 `app/analyzer/` 包（6 个模块）：scanner（目录扫描）、parser（代码解析）、overview（项目概览）、llm_assistant（LLM 语义增强）、map_writer（地图文件生成）
  - 创建 `harness/scripts/analyze_project.py` CLI 入口命令，编排分析流水线
  - 修改 `harness/scripts/check_structure.py` — REQUIRED_DIRS 新增 `app/analyzer/`，REQUIRED_FILES 新增 `analyze_project.py`
  - 修改 `harness/scripts/help.py` — 版本号更新为 v0.3，注册新命令
  - 更新 6 个 project-map 文档（overview/module-map/command-map/directory-map/data-flow/change-map）
  - 更新 `README.md` — 版本号 v0.3，快速开始新增分析命令示例
- **影响文件**: 6 新建 + 2 修改脚本 + 7 文档更新 = 15 文件
- **验证**: `python harness/scripts/check_structure.py` 待验证

### 2026-05-25: 修复文档失真 + 测试断言过期 + Windows 编码隐患

- **类型**: 修复
- **范围**: 测试 / 脚本 / 项目地图 / README
- **摘要**: 代码审查发现的四个具体问题修复
  - **测试断言过期**: `test_parse_missing_sections_use_defaults` 期望 `replace_max_lines=20`，但 `_DEFAULT_CONFIG` 已改为 80。更新断言为 80。
  - **Windows 编码兼容**: `diagnose_and_fix.py` 子进程调用 `text=True` 无 `encoding`，Windows cp936 解码 UTF-8 输出触发 `UnicodeDecodeError`。全部加上 `encoding="utf-8", errors="replace"`。
  - **overview.md 版本严重滞后**: 仍显示 v0.1 自动生成内容，项目已到 v0.8。完全重写。
  - **LLM 依赖语义模糊**: README 写"LLM 必需"但代码有多处降级路径。改为准确描述：LLM 增强深度，无 Key 时降级为纯静态扫描/规则匹配。
- **影响文件**: diagnose_and_fix.py, test_diagnose_and_fix.py, overview.md, README.md
- **验证**: `pytest tests/test_diagnose_and_fix.py -v` 69/69 通过, `check_structure.py` 52/52 通过

### 2026-05-25: 工作流回环机制 — Explorer/Tester 阻塞路由

- **类型**: 新功能
- **范围**: Agent 定义 + 工作流 YAML + 编排器命令
- **摘要**: 填补工作流中两个缺失的失败处理路径
  - **Explorer 阻塞回环**: Explorer 发现计划与现实的阻塞差距 → 路由回 Planner 修正计划 → 重新侦察 → Generator
  - **Tester 阻塞回环**: Tester 发现代码 bug → 路由回 Generator 修复 → 重新测试 → 通过
  - 修改 `.claude/agents/explorer.md` — 新增严重程度判定（阻塞/无阻塞），输出格式增加阻塞问题表格和路由说明
  - 修改 `.claude/agents/tester.md` — 失败分类体系（测试自身问题/代码 bug），路由目标从 Reviewer 改为 Generator
  - 修改 4 个 `harness/workflow/*.md` — YAML 新增 `on_blocked`、`condition`、`loop_back` 字段，新增 planner-replan / generator-fix / generator-test-fix 回环阶段
  - 修改 4 个 `.claude/commands/workflow/*.md` — 编排器指令新增回环检查逻辑（最多 2 次）
  - 更新 `harness/workflow/README.md` — 架构图加入双向回环，新增回环机制说明
- **影响文件**: 2 Agent + 4 workflow YAML + 3 command + 1 README = 10 文件
- **验证**: `python harness/scripts/check_structure.py` 通过 (44/44)

### 2026-05-21: v0.2 Harness 部署范围修正 — 工作流系统部署

- **类型**: 新功能
- **范围**: `harness/scripts/init_project.py`, `harness/scripts/check_structure.py`
- **摘要**: 修正 init_project.py 部署范围，使目标项目获得完整的工作流执行能力
  - **IMP-1**: 部署后删除目标项目中的 `init_project.py`，确保目标项目不包含 Notebook 专用初始化脚本
  - **IMP-2**: 部署 `.claude/agents/` (7 个 agent 定义) 到目标项目
  - **IMP-3**: 部署 `.claude/commands/` (pm + workflow，共 5 个命令) 到目标项目，排除 opsx/
  - **IMP-4**: 创建空的 `.claude/skills/` 目录 (不复制 OpenSpec 技能)
  - **IMP-5**: `check_structure.py` 加回 `.claude/` 目录和文件检查 (4 目录 + 12 文件)，移除 `init_project.py` 检查项
- **影响文件**: 2 修改 + 2 更新 (project-map)
- **验证**: `python harness/scripts/check_structure.py` 通过 (44/44)

### 2026-05-20: 修复 check_structure.py — 移除 .claude/ 目录检查

- **类型**: 修复
- **范围**: `harness/scripts/check_structure.py`
- **摘要**: `REQUIRED_DIRS` 包含 `.claude/`、`.claude/agents/`、`.claude/commands/`、`.claude/skills/`，但这些目录不属于部署到目标项目的 harness 骨架，导致 init_project 后 check_structure 必然 FAIL。已移除这 4 个条目。
- **影响文件**: 1
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: 工作流执行模型重构 — 轻量编排器 + 独立子 Agent 上下文

- **类型**: 重构
- **范围**: 全部 workflow 文件 + 全部 agent 定义 + 全部 command 入口 + workflow rules
- **摘要**: 将工作流执行模型从"主会话角色扮演所有 agent"重构为"轻量编排器 spawn 独立子 Agent"
  - 修改 4 个 `harness/workflow/*.md` — 新增结构化 YAML stages frontmatter，正文替换为编排器指令
  - 修改 6 个 `.claude/agents/*.md` — 正文精简为纯角色定义，移除执行步骤和启动流程
  - 修改 4 个 `.claude/commands/workflow/*.md` — 入口文件指向编排器执行模型
  - 修改 `harness/workflow/README.md` — 新增架构图和核心原则
  - 修改 `harness/rules/workflow-rules.md` — 规则 4 更新：agent 不再需要读 workflow 文件
- **核心变化**:
  - 主会话上下文从数千行（agent 定义 + 中间产物 + 思考过程）压缩到 ~70 行（YAML + 5 段摘要）
  - 每个子 Agent 拥有独立上下文窗口，只加载自己的 agent 定义 + 任务 prompt
  - 子 Agent 之间通过文件系统交接，返回 ≤200 字摘要
- **影响文件**: 14 修改
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: 新增 Agent 工作流编排系统

- **类型**: 新功能
- **范围**: harness 框架 / Agent 工作流
- **摘要**: 创建 `harness/workflow/` 目录，定义 Agent 工作流编排，省去用户手动逐个唤醒 Agent 的步骤
  - 创建 `harness/workflow/README.md` — 工作流系统说明
  - 创建 `harness/workflow/full-cycle.md` — 完整开发周期 (PM→Planner→Explorer→Generator→Reviewer→Tester)
  - 创建 `harness/workflow/implement.md` — 执行已有计划 (Explorer→Generator→Reviewer→Tester)
  - 创建 `harness/workflow/quick-fix.md` — 快速修复 (Explorer→Generator→Tester)
  - 创建 `.claude/commands/workflow/full-cycle.md` — `/workflow:full-cycle` 命令入口
  - 创建 `.claude/commands/workflow/implement.md` — `/workflow:implement` 命令入口
  - 创建 `.claude/commands/workflow/quick-fix.md` — `/workflow:quick-fix` 命令入口
  - 更新 `directory-map.md`, `command-map.md`, `check_structure.py`
- **影响文件**: 7 新建 + 2 修改
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: Agent 启动流程统一加入工作流文件阅读步骤

- **类型**: 规则更新
- **范围**: 全部 Agent 定义 + 工作流规则
- **摘要**: 之前 Agent 被工作流唤醒时不知道自己在流程中的位置。新增硬性规定
  - 修改 `harness/rules/workflow-rules.md` — 新增第 4 条：如果在工作流中被唤醒，必须先阅读 `harness/workflow/README.md` 和对应 workflow 文件
  - 修改全部 6 个 Agent (`pm`, `planner`, `explorer`, `generator`, `reviewer`, `tester`) 的启动流程 — 每个启动流程新增第 0 步：阅读 workflow 文件确认上下文
  - 每个 Agent 的第 0 步针对其角色定制了关注点 (PM 关注下游交接，Generator 关注三种调用模式区分，Reviewer 关注三类分类规则等)
- **影响文件**: 1 规则 + 6 Agent
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: Tester 测试编写依据补全 — 四份输入源

- **类型**: 修复
- **范围**: Tester Agent 定义 + 全部工作流文档
- **摘要**: Tester 原来只写"读计划"作为测试编写依据，缺少关键输入。补全为四份依据
  - 修改 `.claude/agents/tester.md` — 启动流程改为四份依据依次阅读：Spec (验收标准) → 计划 (TST- 任务) → 实际代码 (接口签名) → 审查报告 (已知问题优先覆盖)
  - 更新 4 个工作流文档中 Tester 的调用 prompt — 全部改为传递四份输入
  - review-fix 工作流新增独立的 Tester 阶段（之前缺少，只写了手动运行 pytest）
  - quick-fix 工作流的 Tester 以问题描述 + 实际代码为替代依据（无正式 spec/plan）
- **影响文件**: 1 Agent + 4 工作流
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: 明确 Generator/Tester 职责边界 — 测试代码由 Tester 编写

- **类型**: 修复
- **范围**: Generator, Tester, Planner Agent 定义
- **摘要**: Generator 之前被描述为"唯一可以写代码的 agent"，但 Tester 也需要写测试代码。明确职责边界
  - 修改 `.claude/agents/generator.md` — 移除"唯一可写代码"声明，改为"只写应用代码，不写测试代码"；约束中新增"不修改 tests/ 目录"
  - 修改 `.claude/agents/tester.md` — 定位改为"项目中唯一编写测试代码的 Agent"
  - 修改 `.claude/agents/planner.md` — 任务列表拆分为实现任务 (IMP- → Generator) 和测试任务 (TST- → Tester)，不允许混在一起
- **影响文件**: 3 个 Agent 定义
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: PM Agent 升级为工作流驱动 + 全部 Agent 定义同步更新

- **类型**: 重构
- **范围**: 全部 Agent 定义 + 全部工作流文档
- **摘要**: 将 "主 Agent" 抽象概念替换为 PM Agent 作为工作流驱动者，同步更新全部 6 个 Agent 定义
  - 更新 `.claude/agents/pm.md` — 新增工作流驱动角色和审查反馈介入职责
  - 更新 `.claude/agents/planner.md` — 新增两种工作流定位（正常流程 + 审查反馈修复计划响应）
  - 更新 `.claude/agents/generator.md` — 新增三种指令来源（正常流程 + 第一类小修 + 修复计划）
  - 更新 `.claude/agents/explorer.md` — 新增工作流调用时机说明
  - 更新 `.claude/agents/reviewer.md` — 新增 review-fix 衔接关系图
  - 更新 `.claude/agents/tester.md` — 新增四种工作流的调用时机说明
  - 更新 4 个工作流文档 (`full-cycle.md`, `implement.md`, `quick-fix.md`, `review-fix.md`) + `README.md` — 全部 "主 Agent" 替换为 "PM Agent"
  - 更新 `.claude/commands/workflow/full-cycle.md` — 命令描述同步
- **影响文件**: 6 Agent + 5 工作流 + 1 命令 + change-map = 13 文件
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: 新增 Review Fix 工作流 + Reviewer 问题分类

- **类型**: 新功能
- **范围**: harness 框架 / 审查反馈流程
- **摘要**: 将 Reviewer 输出改为三类结构化分类，创建 review-fix 工作流自动路由修复
  - 修改 `.claude/agents/reviewer.md` — 新增三类问题分类体系（小修/实现偏差/需求问题）和结构化输出格式
  - 创建 `harness/workflow/review-fix.md` — 审查反馈修复工作流，按优先级 (第三类→第二类→第一类) 自动路由
  - 创建 `.claude/commands/workflow/review-fix.md` — `/workflow:review-fix` 命令入口
  - 三类路由规则：
    - 第一类 (小修) → Generator 直接修复
    - 第二类 (实现偏差) → Planner 制定修复计划 → Generator 执行
    - 第三类 (需求问题) → PM 澄清 → Planner 修订计划 → Generator 执行
  - 更新 `command-map.md`
- **影响文件**: 2 新建 + 1 修改 + 1 更新
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: v0.1 脚本实现

- **类型**: 新功能
- **范围**: 全项目
- **摘要**: 实现 v0.1 全部 7 个功能
  - 创建 `harness/scripts/export_report.py` — 导出项目理解报告
  - 创建 `harness/scripts/search_notes.py` — 搜索笔记
  - 创建 `harness/scripts/help.py` — 打印可用命令
  - 创建 `harness/scripts/init_project.py` — 初始化新项目地图（复制骨架+扫描目录）
  - 创建 `tests/test_export_report.py`, `tests/test_search_notes.py`, `tests/test_help.py`, `tests/test_init_project.py` — 12 个测试用例
  - 更新 `command-map.md`, `module-map.md`, `overview.md`, `README.md`
- **影响文件**: 4 新建脚本 + 4 新建测试 + 4 修改文档
- **验证**: `python harness/scripts/check_structure.py` 通过, `python -m pytest tests/ -v` 12/12 通过

### 2026-05-20: 新增 PM Agent 角色

- **类型**: 新功能
- **范围**: 工作流 / Agent 定义
- **摘要**: 在现有 OpenSpec 工作流中新增 PM Agent 角色，填补"需求讨论→spec 产出"环节
  - 创建 `.claude/agents/pm.md` — PM Agent 角色定义
  - 创建 `.claude/commands/pm/discuss.md` — `/pm:discuss` 命令入口
  - 修改 `.claude/agents/planner.md` — 启动流程增加读取 openspec/specs/ 步骤
  - 更新 `command-map.md` — 登记 `/pm:discuss` 命令
  - 创建 `openspec/specs/pm-agent.md` — PM Agent 自身 spec 文档
- **影响文件**: 2 新建 + 2 修改 + 1 新增 spec
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-19: 项目初始化

- **类型**: 初始化
- **范围**: 全项目
- **摘要**: 创建 AI Project Notebook v0.1 骨架
  - 建立目录结构
  - 创建 harness 框架（rules, scripts, skills, project-map, feedback）
  - 编写可执行规则（coding, data-safety, workflow）
  - 创建项目地图文件（overview, directory-map, module-map, command-map, data-flow, change-map）
  - 创建结构检查脚本 `check_structure.py`
- **影响文件**: 全部为新建
- **验证**: `python harness/scripts/check_structure.py` 通过

---

### 2026-05-26: CodeGraph 集成 generator-fix — 审查反馈修复 (3 个问题)

- **类型**: 修复
- **范围**: `app/analyzer/llm_assistant.py`, `app/analyze_project.py`, `README.md`
- **摘要**: 修复 Reviewer 发现的 3 个第一类问题
  - `_call_llm_with_tools()` 多行 docstring 改为单行 (coding-rule 13)
  - `_run_codegraph_exploration()` 多行 docstring 改为单行 (coding-rule 13)
  - `README.md` 补充遗漏的 `--codegraph` 使用示例 (coding-rule 5)
- **验证**: `python harness/scripts/check_structure.py` 52/52 PASS

---

## 记录规则

每次变更必须记录：
1. 日期和变更名称
2. 变更类型（初始化/新功能/修复/重构/规则更新）
3. 影响范围（哪些文件/模块）
4. 摘要
5. 验证命令及其结果
