# Plan: 集成 Codebase Digest (v0.1.5)

## 1. 变更范围

### 新增文件

| 文件 | 意图 |
| ---- | ---- |
| `app/analyzer/digest_collector.py` | 封装 `codebase_digest.app` Python API：调用 `analyze_directory()` 收集全量文本文件，合并为单一文本输出，执行预处理（噪声过滤、UUID 折叠、max-size 截断），检查包可用性并优雅降级 |
| `app/analyzer/dimension_analyzer.py` | 3 个分析维度函数（Architecture / User Stories / Risk），各自包含 LLM Prompt 模板、降级方案、文件输出逻辑。输出到 `analysis/` 目录 |

### 修改文件

| 文件 | 意图 |
| ---- | ---- |
| `app/analyzer/__init__.py` | 版本号 0.4.0 → 0.5.0 |
| `harness/scripts/analyze_project.py` | 新增 `--digest` 和 `--max-size` 参数；digest 模式下 4 步流程：digest 收集 → 架构分析 → 用户故事重建 → 风险分析；非 digest 模式保持现有流程不变 |
| `harness/scripts/help.py` | 版本号 v0.4 → v0.5，更新命令描述 |
| `harness/project-map/module-map.md` | 登记 `digest_collector.py` 和 `dimension_analyzer.py` 两个新模块 |
| `harness/project-map/command-map.md` | 更新 `analyze_project.py` 命令描述，反映 `--digest` / `--max-size` 新选项 |
| `harness/project-map/data-flow.md` | 新增 digest 分析流水线图（digest 收集 → 三维分析 → analysis/ 输出） |
| `harness/project-map/change-map.md` | 记录 v0.1.5 变更摘要 |
| `README.md` | 版本号 v0.4 → v0.5，快速开始新增 `--digest` 使用示例 |

### 不变更文件

- `app/analyzer/guiding_files.py` — 不需修改，digest 模式下原引导文件流程保持可用
- `app/analyzer/domain_analyzer.py` — 不需修改，digest 模式仍运行原有领域分析
- `app/analyzer/llm_assistant.py` — 不需修改，新模块通过 `_get_llm_config` / `_call_llm` 复用
- `app/analyzer/map_writer.py` — 不需修改
- `app/analyzer/scanner.py` — 不需修改
- `harness/scripts/check_structure.py` — 不需修改（新文件在已有 `app/analyzer/` 目录下，无需新增检查项）

---

## 2. 任务列表

### 实现任务 (→ Generator)

**IMP-1**: 新建 `app/analyzer/digest_collector.py`
- **内容**:
  - `is_cdigest_available()` — `try: import codebase_digest.app` 检查包可用性
  - `run_digest_collection(target_path, max_size_kb=10240)` — 调用 `codebase_digest.app.analyze_directory()` + `generate_content_string()`，返回 `{"files": [{path, content}], "total_tokens": int, "status": "ok"|"error"}`
  - `preprocess_digest(raw_result, max_size_kb)` — 后处理：去除 `[Non-text file]` 内容、折叠编译产物目录标注、截断超 max_size 内容
  - `format_digest_for_llm(preprocessed)` — 将文件列表格式化为 LLM 可消费的纯文本（`### File: path\n\`\`\`\ncontent\n\`\`\``格式）
  - `collect_digest(target_path, max_size_kb=10240)` — 编排函数：可用性检查 → 收集 → 预处理 → 格式化，返回 `{"text": str, "status": "ok"|"cdigest_unavailable"|"error", "stats": {files, total_tokens}}`
- **完成标准**: 导入 `codebase_digest.app` 成功时正确收集文件；未安装时返回 `cdigest_unavailable` 状态且不崩溃
- **验证命令**: `python -c "from app.analyzer.digest_collector import is_cdigest_available, collect_digest; print(is_cdigest_available()); result = collect_digest('.'); print(result['status'], len(result.get('text','')))"`

**IMP-2**: 新建 `app/analyzer/dimension_analyzer.py`
- **内容**:
  - `analyze_architecture(digest_text, project_name, output_dir, enable_dotenv=True)` → 调用 LLM 分析架构分层，写入 `analysis/architecture.md`
  - `analyze_user_stories(digest_text, arch_md_text, project_name, output_dir, enable_dotenv=True)` → 调用 LLM 反向重建用户故事，写入 `analysis/user-stories.md`（引用架构上下文）
  - `analyze_risk(digest_text, arch_md_text, stories_md_text, project_name, output_dir, enable_dotenv=True)` → 调用 LLM 分析错误与风险，写入 `analysis/risk-analysis.md`（引用架构+用户故事上下文）
  - 内部函数 `_build_architecture_prompt()` / `_build_stories_prompt()` / `_build_risk_prompt()` — 构造 LLM 系统 prompt + user prompt
  - 内部函数 `_degraded_architecture()` / `_degraded_user_stories()` / `_degraded_risk()` — 无 LLM Key 时的降级分析（目录结构描述 / 入口文件列表 / 基础静态检查）
  - 内部函数 `_write_analysis_file(output_dir, filename, content)` — 原子写入 `analysis/` 目录
  - `_check_llm_available(enable_dotenv)` — 复用 `llm_assistant._get_llm_config` 检查 Key
  - 每个分析函数返回 `{"file_path": str, "status": "llm"|"degraded"|"error", "content": str}`
- **完成标准**: 3 个分析文件独立可读；降级模式正确触发；交叉引用正确（用户故事文件引用 architecture.md，风险分析文件引用前两者）
- **验证命令**: `python -c "from app.analyzer.dimension_analyzer import _degraded_architecture, _degraded_user_stories, _degraded_risk; print(_degraded_architecture('test')); print(_degraded_user_stories('test')); print(_degraded_risk('test'))"`

**IMP-3**: 修改 `harness/scripts/analyze_project.py`
- **内容**:
  - 新增 `--digest` flag (action="store_true", default=False)
  - 新增 `--max-size` 参数 (type=int, default=10240, help="digest 最大输出大小(KB)")
  - digest 模式流程（`args.digest == True`）：
    1. 调用 `collect_digest()` 收集全量文件 → 不可用时降级回引导文件模式
    2. 运行现有 `analyze_business_domains()` → 生成 `project-overview.md`（保持不变）
    3. 调用 `analyze_architecture(digest_text, ...)` → 产出 `analysis/architecture.md`
    4. 调用 `analyze_user_stories(digest_text, arch_content, ...)` → 产出 `analysis/user-stories.md`
    5. 调用 `analyze_risk(digest_text, arch_content, stories_content, ...)` → 产出 `analysis/risk-analysis.md`
  - 非 digest 模式：完全保持现有代码路径不变
  - 优雅降级链：cdigest 不可用 → 打印警告，回退引导文件模式；LLM Key 不存在 → 各维度降级输出
- **完成标准**: `--digest` 时产出 4 个文件（project-overview.md + 3 个 analysis/*.md）；无 `--digest` 时行为与当前版本完全一致
- **验证命令**: 不带 `--digest` 的现有测试必须通过: `python -m pytest tests/test_analyze_project.py -v`

**IMP-4**: 修改 `harness/scripts/help.py`
- **内容**:
  - 版本号 v0.4 → v0.5
  - `analyze_project.py` 描述更新为 `"智能项目分析引擎 (v0.5 --digest 全量文件分析 + LLM 三维度报告)"`
- **完成标准**: `python harness/scripts/help.py` 输出含 v0.5 和 --digest 相关描述
- **验证命令**: `python harness/scripts/help.py`

**IMP-5**: 更新 `harness/project-map/module-map.md`
- **内容**:
  - 新增 `digest_collector.py` 行：描述"codebase-digest 集成与全量文件收集"，主要函数 `is_cdigest_available, collect_digest, preprocess_digest, format_digest_for_llm`
  - 新增 `dimension_analyzer.py` 行：描述"三维度代码分析引擎(架构/用户故事/风险)"，主要函数 `analyze_architecture, analyze_user_stories, analyze_risk`
- **完成标准**: module-map 模块列表包含两个新模块
- **验证命令**: `python harness/scripts/check_structure.py`

**IMP-6**: 更新文档（command-map / data-flow / change-map / README）
- **内容**:
  - `command-map.md`: `analyze_project.py` 描述更新，新增 `--digest` / `--max-size` 参数说明
  - `data-flow.md`: 新增 "Digest 分析流水线" 子章节，绘制 digest 收集 → 三维分析 → analysis/ 输出 的数据流
  - `change-map.md`: 记录 v0.1.5 变更摘要（类型: 新功能，影响文件清单，验证命令）
  - `README.md`: 版本号 v0.4 → v0.5；快速开始新增 `--digest` 示例；目录结构新增 `analysis/` 输出目录说明
- **完成标准**: 4 个文档更新一致，版本号统一为 v0.5
- **验证命令**: `python harness/scripts/check_structure.py`

---

### 测试任务 (→ Tester)

**TST-1**: 新建 `tests/test_digest_collector.py`
- **覆盖功能点**:
  - `is_cdigest_available()` 返回 bool（在当前环境应为 True，因 codebase-digest 已安装）
  - `collect_digest()` 对有效目录返回 status="ok"，text 非空
  - `collect_digest()` 对不存在目录返回 status="error"
  - `preprocess_digest()` 过滤 `[Non-text file]` 内容
  - `format_digest_for_llm()` 输出格式包含 `### File:` 和代码块标记
  - max_size 截断行为正确（文本长度不超过 max_size_kb * 1024）

**TST-2**: 新建 `tests/test_dimension_analyzer.py`
- **覆盖功能点**:
  - 无 LLM Key 时三个函数均返回 status="degraded" 且不崩溃
  - 降级输出包含合理的内容（架构降级含目录结构、用户故事降级含入口函数列表、风险降级含静态检查结果）
  - 有 LLM Key 时架构分析产出 analysis/architecture.md 含 "架构分层" 关键词
  - 有 LLM Key 时用户故事分析产出 analysis/user-stories.md 含交叉引用 `architecture.md`
  - 有 LLM Key 时风险分析产出 analysis/risk-analysis.md 含交叉引用 `user-stories.md`
  - `_write_analysis_file` 原子写入，无 .tmp 残留
  - 输出目录不存在时自动创建 `analysis/` 目录

**TST-3**: 更新 `tests/test_analyze_project.py`
- **覆盖功能点**:
  - `--help` 输出含 `--digest` 和 `--max-size` 参数
  - `--help` 输出含 v0.5 版本号
  - 不带 `--digest` 的现有所有测试继续通过（回归测试）
  - `--digest --quiet` 模式退出码为 0
  - 现有 `test_help_output` 的 `--depth`/`--source-root`/`--llm` 检查保留，新增 `--digest` 存在性检查
  - 现有 `test_no_api_key_exits_one` 在 digest 模式下行为不变（因 LLM 仍是强制依赖）

---

## 3. 依赖关系

```
IMP-1 (digest_collector) ──┐
                            ├──→ IMP-3 (analyze_project.py) ──→ IMP-4 (help.py)
IMP-2 (dimension_analyzer) ─┘                                      │
                                                                    ├──→ IMP-5 (module-map.md)
                                                                    └──→ IMP-6 (closing docs)
                                                                              │
                                                                              ▼
                                                              TST-1, TST-2, TST-3 (可并行)
```

- IMP-1 和 IMP-2 可并行开发（无相互依赖）
- IMP-3 依赖 IMP-1 和 IMP-2（需要导入新模块）
- IMP-4 依赖 IMP-3（需要知道最终参数列表）
- IMP-5 和 IMP-6 依赖 IMP-3（需要知道最终实现细节来写文档）
- TST-1 / TST-2 / TST-3 依赖所有 IMP 完成后执行
- TST-1 和 TST-2 可并行
- TST-3 依赖 IMP-3 完成（需要知道实际 CLI 行为）

---

## 4. 风险点

1. **codebase_digest API 兼容性** — `analyze_directory()` 内部使用 `print()` 输出调试信息（如 `print(f"Debug: Checking {item_path}...")`），会污染 stdout。对策：调用前临时重定向 stdout 到 `os.devnull`，调用后恢复。

2. **全量文件超出 token 限制** — 大型项目（>10MB 文本）可能超出 LLM context window。缓解策略：`--max-size` 默认 10240 KB（10 MB），超出部分在 `preprocess_digest()` 中截断，并按文件优先级保留（优先保留小文件、入口文件）。

3. **codebase_digest 未安装的降级路径** — 用户可能未 `pip install codebase-digest`。对策：`is_cdigest_available()` 用 `try: import` 检测；不可用时打印警告并回退到引导文件模式，不中断分析。

4. **analysis/ 目录冲突** — 目标项目可能已有 `analysis/` 目录。对策：`_write_analysis_file()` 仅覆盖同名分析文件，不删除其他文件。

5. **Prompt 长度控制** — 3 个维度的 prompt 可能叠加过大。对策：每个 prompt 中 digest_text 限制在 `max_tokens * 2` 字符内（留一半给 prompt 模板和 LLM 响应）。

6. **交叉引用一致性** — 用户故事和风险分析文件需要引用前一维度的输出文件。对策：分析函数接收前一维度的文本内容（而非文件路径），确保引用内容一致。
