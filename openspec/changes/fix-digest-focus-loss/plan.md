# Plan: 修复 LLM 全量分析失焦问题

## 1. 变更范围

### 新增文件

| 文件 | 意图 |
| ---- | ---- |
| `app/analyzer/prompts/__init__.py` | prompt 库加载器，提供 `load_prompt(name)` 函数读取官方 prompt 文本 |
| `app/analyzer/prompts/architecture.txt` | 架构分析官方 prompt，从 codebase-digest prompt_library 挑选并本地化 |
| `app/analyzer/prompts/user_stories.txt` | 用户故事分析官方 prompt，同上来源 |
| `app/analyzer/prompts/risk.txt` | 风险分析官方 prompt，同上来源 |

### 修改文件

| 文件 | 意图 |
| ---- | ---- |
| `app/analyzer/domain_analyzer.py` | LLM prompt 要求输出主板块+子板块两级结构，不确定项标注 `[推测]`；更新 `_parse_domain_response` 和 `_normalize_result` 适配新结构 |
| `app/analyzer/digest_collector.py` | 新增 `filter_for_architecture()` / `filter_for_user_stories()` / `filter_for_risk()` 三个维度筛选函数；`collect_digest()` 不再格式化全量 LLM 文本，仅返回文件池 |
| `app/analyzer/dimension_analyzer.py` | `_build_*_prompt` 三个函数改名为 `_build_*_prompt_from_files()`，接收筛选后的文件列表+官方 prompt，不再接收全量 digest_text；三个公开函数签名同步变更；移除不再使用的 `format_digest_for_llm` 调用 |
| `harness/scripts/analyze_project.py` | digest 模式重构为 7 步新流程：引导文件概览 -> 板块识别（两级）-> 概览输出 -> digest 文件池收集 -> 三维度聚焦分析（每维度传入筛选子集+官方 prompt）；非 digest 模式保持现有行为不变 |
| `app/analyzer/__init__.py` | 版本号 0.5.0 -> 0.5.1 |
| `harness/scripts/help.py` | 版本号 v0.5 -> v0.5.1，analyze_project 描述更新为"聚焦三维度分析" |
| `harness/project-map/module-map.md` | 登记 `prompts/__init__.py` 新模块；更新 `digest_collector.py` 和 `dimension_analyzer.py` 职责描述 |
| `harness/project-map/directory-map.md` | `app/analyzer/` 下新增 `prompts/` 子目录 |
| `harness/project-map/data-flow.md` | 更新 Digest 分析流水线：全量 dump 路径替换为文件池筛选+聚焦分析路径 |
| `harness/project-map/command-map.md` | `--digest` 描述从"全量三维分析"改为"聚焦三维度分析" |
| `harness/project-map/change-map.md` | 记录本次变更摘要 |
| `README.md` | 版本号 v0.5 -> v0.5.1，`--digest` 功能描述更新 |

---

## 2. 任务列表

### 实现任务 (-> Generator)

**IMP-1: domain_analyzer 板块两级结构 + [推测] 标注**

- 文件: `app/analyzer/domain_analyzer.py`
- 改动:
  a) `_build_domain_analysis_prompt()`: 输出格式新增 `sub_domains` 字段，要求 LLM 区分主板块与子板块（一级最多15个主板块，子板块归属主板块）；不确定时在 description 中标注 `[推测]`
  b) `_normalize_result()`: domains 列表中每个 domain 新增 `sub_domains` 字段默认值 `[]`
  c) `_degraded_domain_result()`: 适配新的 domain 结构
- 完成标准: prompt 文本中可找到"主板块""子板块""[推测]"关键词，`_normalize_result` 补齐 `sub_domains` 默认值
- 验证: `grep -n "sub_domains" app/analyzer/domain_analyzer.py` 返回多行匹配

**IMP-2: 创建 prompts 目录和 prompt 文件**

- 文件: `app/analyzer/prompts/__init__.py`, `app/analyzer/prompts/architecture.txt`, `app/analyzer/prompts/user_stories.txt`, `app/analyzer/prompts/risk.txt`
- 改动:
  a) `__init__.py`: 提供 `PROMPTS_DIR` 常量、`load_prompt(name: str) -> str` 函数（从 txt 文件读取文本）
  b) 三个 `.txt` 文件: 基于 codebase-digest prompt_library 的架构/用户故事/风险相关 prompt，适配为中文输出的系统指令。每个文件包含 prompt 模板文本，预留 `{project_name}` 和 `{files_content}` 占位符
- 完成标准: `load_prompt("architecture")` 返回非空字符串，三个 txt 文件均 >200 字符
- 验证: `python -c "from app.analyzer.prompts import load_prompt; print(len(load_prompt('architecture'))); print(len(load_prompt('user_stories'))); print(len(load_prompt('risk')))"`

**IMP-3: digest_collector 维度文件筛选函数**

- 文件: `app/analyzer/digest_collector.py`
- 改动:
  a) 新增 `filter_for_architecture(preprocessed: list) -> list`: 筛选架构相关文件（目录结构文件如 `__init__.py`、配置文件如 `*.json/*.yaml/*.toml`、入口文件如 main/app/index/setup、大型模块文件 >3000 字符），返回文件列表
  b) 新增 `filter_for_user_stories(preprocessed: list) -> list`: 筛选用户故事相关文件（README、docs/、路由文件、handler/controller/view 文件、测试文件），返回文件列表
  c) 新增 `filter_for_risk(preprocessed: list) -> list`: 筛选风险相关文件（含密钥/密码关键词、错误处理文件、配置文件、依赖文件如 requirements.txt/package.json、脚本文件），返回文件列表
  d) `collect_digest()`: 不再调用 `format_digest_for_llm`，返回字段从 `text` 改为 `files`（预处理后的文件列表）；保留 `text` 字段向后兼容（设为空字符串）
  e) 新增 `format_files_for_llm(files: list) -> str`: 将筛选后的文件列表格式化为 LLM 可消费文本（与 `format_digest_for_llm` 功能相同但命名更清晰），用于三个维度分析
- 完成标准: 三个筛选函数返回类型正确（list of dict with path/content），筛选规则基于启发式正则，不引入新依赖
- 验证: 对项目自身运行筛选函数，验证 `filter_for_architecture` 返回了 `__init__.py` 和配置文件，`filter_for_user_stories` 返回了 README 和测试文件，`filter_for_risk` 返回了 requirements 相关文件

**IMP-4: dimension_analyzer 重构 — 聚焦分析替代全量 dump**

- 文件: `app/analyzer/dimension_analyzer.py`
- 改动:
  a) 新增 `from app.analyzer.prompts import load_prompt` 导入
  b) `_build_architecture_prompt()` 改名为 `_build_architecture_prompt_from_files()`，参数从 `(digest_text, project_name, max_chars)` 改为 `(filtered_files, project_name)`，内部使用 `load_prompt("architecture")` 作为 system prompt 基础，用户 prompt 只包含筛选后的文件子集
  c) `_build_stories_prompt()` 同理改造，使用 `load_prompt("user_stories")`
  d) `_build_risk_prompt()` 同理改造，使用 `load_prompt("risk")`
  e) `analyze_architecture()` 签名从 `(digest_text, project_name, output_dir)` 改为 `(filtered_files, project_name, output_dir)`
  f) `analyze_user_stories()` 签名从 `(digest_text, arch_md_text, project_name, output_dir)` 改为 `(filtered_files, arch_md_text, project_name, output_dir)`
  g) `analyze_risk()` 签名从 `(digest_text, arch_md_text, stories_md_text, project_name, output_dir)` 改为 `(filtered_files, arch_md_text, stories_md_text, project_name, output_dir)`
  h) 三个公开函数内部：将 filtered_files 列表传入 `format_files_for_llm()`（从 digest_collector 导入）生成文本后传入 `_build_*_prompt_from_files()`
  i) 移除不再使用的 `_build_architecture_prompt` / `_build_stories_prompt` / `_build_risk_prompt` 旧函数
- 完成标准: 三个 `_build_*_prompt` 函数不再接收全量 digest_text，改为接收筛选文件列表；prompt 使用官方模板；无全量文本在 prompt 中
- 验证: `grep "digest_text" app/analyzer/dimension_analyzer.py` 无匹配（确认全量 dump 参数已移除）

**IMP-5: analyze_project.py digest 模式重构**

- 文件: `harness/scripts/analyze_project.py`
- 改动:
  a) 导入新增：`format_files_for_llm`, `filter_for_architecture`, `filter_for_user_stories`, `filter_for_risk`
  b) digest 模式流程从 D1-D6 改为 7 步新流程:
     - [digest/1] 引导文件概览（同非 digest 模式 Step 1）
     - [digest/2] 业务板块识别（调用 domain_analyzer，现支持两级结构）
     - [digest/3] 生成项目概览
     - [digest/4] digest 文件池收集（`collect_digest` 返回文件列表，不格式化 LLM 文本）
     - [digest/5] 架构聚焦分析：`filter_for_architecture(files)` -> `analyze_architecture(filtered, project_name, target_path)`
     - [digest/6] 用户故事聚焦分析：`filter_for_user_stories(files)` -> `analyze_user_stories(filtered, arch_content, project_name, target_path)`
     - [digest/7] 风险聚焦分析：`filter_for_risk(files)` -> `analyze_risk(filtered, arch_content, stories_content, project_name, target_path)`
  c) 非 digest 模式代码不变
  d) 输出目录中的 `analysis/` 目录路径使用 `target_path` 而非 `output_dir`（与现有 `dimension_analyzer._write_analysis_file` 调用保持一致）
- 完成标准: 全量 `digest_text` 变量不再传入三维度分析函数；每个维度只接收筛选后文件子集；输出仍为 project-overview.md + analysis/ 下三份报告
- 验证: `grep "digest_text" harness/scripts/analyze_project.py` 仅剩 digest_text 定义和 digest 不可用时的赋值，无传入分析函数的调用

**IMP-6: 版本号和文档同步**

- 文件: `app/analyzer/__init__.py`, `harness/scripts/help.py`, `harness/project-map/module-map.md`, `harness/project-map/directory-map.md`, `harness/project-map/data-flow.md`, `harness/project-map/command-map.md`, `README.md`
- 改动:
  a) `__init__.py`: `0.5.0` -> `0.5.1`
  b) `help.py`: 版本号 v0.5 -> v0.5.1，analyze_project 描述改为"聚焦三维度分析（架构/用户故事/风险）"
  c) `module-map.md`: 新增 `prompts/__init__.py` 行；更新 `digest_collector.py` 描述增加"维度文件筛选"；更新 `dimension_analyzer.py` 描述改为"聚焦三维度分析（架构/用户故事/风险），使用官方 prompt + 筛选文件子集"
  d) `directory-map.md`: `app/analyzer/` 下新增 `prompts/` 子目录及三个 `.txt` 文件
  e) `data-flow.md`: Digest 分析流水线图中 Step D3 改为文件池筛选+聚焦分析，`dimension_analyzer` 返回值不变
  f) `command-map.md`: `--digest` 描述从"全量三维分析"改为"聚焦三维度分析"
  g) `README.md`: 版本号 v0.5 -> v0.5.1
- 完成标准: 所有文件版本号一致，module-map 和 directory-map 反映新模块
- 验证: `grep -r "0\.5\.0" app/ README.md harness/scripts/help.py` 无匹配（确认旧版本号已全部替换）

**IMP-7: change-map.md 变更记录**

- 文件: `harness/project-map/change-map.md`
- 改动: 在文件顶部（最近变更记录之前）新增本次变更条目，格式与现有记录一致
- 完成标准: 包含日期、类型（修复）、范围、摘要、影响文件列表、验证命令

---

### 测试任务 (-> Tester)

**TST-1: digest_collector 维度筛选函数测试**

- 文件: `tests/test_analyze_project.py` 或在 `tests/` 下新增 `test_digest_collector.py`
- 覆盖点:
  - `filter_for_architecture()` 筛选出 `__init__.py` 和配置文件
  - `filter_for_user_stories()` 筛选出 README 和测试文件
  - `filter_for_risk()` 筛选出依赖文件和可能含风险关键词的文件
  - `format_files_for_llm()` 格式化输出包含 `### File:` 标记
  - `collect_digest()` 返回的 `files` 字段包含预处理后的文件列表
- 验证: `python -m pytest tests/ -v -k "filter"`

**TST-2: domain_analyzer 两级结构测试**

- 文件: `tests/test_analyze_project.py`
- 覆盖点:
  - `_normalize_result()` 补齐 `sub_domains` 字段
  - `_build_domain_analysis_prompt()` 输出中包含"主板块""子板块""[推测]"关键词
  - `_degraded_domain_result()` 返回的 domains 结构包含 `sub_domains` 字段
- 验证: `python -m pytest tests/ -v -k "domain"`

**TST-3: dimension_analyzer 聚焦分析测试**

- 文件: `tests/test_analyze_project.py` 或新增 `tests/test_dimension_analyzer.py`
- 覆盖点:
  - `analyze_architecture()` 接收 filtered_files 列表能正常执行（用假 Key 降级测试）
  - `analyze_user_stories()` 接收 filtered_files 列表能正常执行
  - `analyze_risk()` 接收 filtered_files 列表能正常执行
  - 降级模式输出包含"降级"字样
  - 公开函数签名不再包含 `digest_text` 参数（传旧参数应报 TypeError）
- 验证: `python -m pytest tests/ -v -k "dimension or architecture or stories or risk"`

**TST-4: CLI digest 模式新流程端到端测试**

- 文件: `tests/test_analyze_project.py`
- 覆盖点:
  - `--digest --quiet` 退出码 0（假 Key 降级路径不崩溃）
  - `--digest` 模式下 analysis/ 目录下三份报告均可生成
  - `--digest --help` 输出含"聚焦"描述
  - `test_help_output` 中 `--digest` 和 `--max-size` 参数仍存在
- 验证: `python -m pytest tests/test_analyze_project.py -v -k "digest or help"`

**TST-5: 回归测试 — 非 digest 模式不受影响**

- 文件: `tests/test_analyze_project.py`
- 覆盖点:
  - 非 digest 模式所有现有测试通过（TestScanner/TestParser/TestOverview/TestLLMAssistant/TestProgressiveOverview/TestCLIIntegration 中 non-digest 测试）
  - `test_valid_project_with_fake_key_generates_overview` 通过
  - `test_quiet_mode_exit_zero` 通过
- 验证: `python -m pytest tests/test_analyze_project.py -v --ignore-glob="*digest*"`

---

## 3. 依赖关系

```
IMP-2 (prompts 目录) ──┐
                        ├──> IMP-4 (dimension_analyzer 重构)
IMP-3 (文件筛选函数) ──┘       │
                                ├──> IMP-5 (analyze_project 重构)
IMP-1 (domain_analyzer) ───────┘       │
                                        ├──> IMP-6 (版本号+文档)
                                        │       │
                                        └───────┴──> IMP-7 (change-map)

所有 TST 任务依赖对应 IMP 任务完成:

IMP-3 -> TST-1
IMP-1 -> TST-2
IMP-4 -> TST-3
IMP-5 -> TST-4
IMP-5 -> TST-5 (回归)
```

**可并行:**
- IMP-1 与 IMP-2 可并行执行
- IMP-3 与 IMP-1/IMP-2 可并行执行
- IMP-6 与 IMP-7 可并行执行
- TST-1, TST-2, TST-3, TST-5 可并行执行（分别依赖各自 IMP 完成）

**必须顺序:**
- IMP-2 + IMP-3 必须在 IMP-4 之前（dimension_analyzer 依赖 prompts 和筛选函数）
- IMP-1 + IMP-4 必须在 IMP-5 之前（analyze_project 编排依赖所有分析模块）
- IMP-5 必须在 IMP-6 之前（文档更新需确认最终版本号）
- TST-4 必须在 IMP-5 完成之后

---

## 4. 风险点

1. **domain_analyzer 数据结构变更**: `domains` 数组新增 `sub_domains` 字段会影响 `map_writer.py` 中 `generate_progressive_overview()` 的板块渲染逻辑。**注意**: 当前 spec 未要求更新 map_writer 的输出格式，但 Generator 需确认 `map_writer.py` 中遍历 domains 的代码不会因新增字段而崩溃。如果 map_writer 使用 for-loop 遍历且只访问字段不检查存在性，是安全的。

2. **文件筛选规则精度**: 三个筛选函数基于启发式正则（文件名、路径、内容关键词），首次实现可能不够精确。筛选过宽会导致聚焦分析不聚焦，筛选过窄会丢失关键文件。筛选规则应作为迭代的基础，后续可调整。

3. **prompt 内容来源**: 三个 `.txt` 文件的内容需从 codebase-digest 的 `prompt_library/` 挑选适配。由于这是一个安装包，其 prompt 可能在 pip 安装的 site-packages 中可找到。如果本地不可用，Generator 需基于 spec 描述自行编写高质量 prompt 作为初始版本。

4. **dimension_analyzer 签名变更对测试的影响**: 现有测试 `test_analyze_project.py` 中可能没有直接调用 `dimension_analyzer` 的公开函数，但 Tester 需要更新/新增测试来覆盖新签名。现有 `test_digest_quiet_mode_exits_zero` 测试使用的是假 Key 降级路径，应继续通过。

5. **analyze_project.py 中 digest_text 变量**: 重构后 digest 模式下不再需要 `digest_text` 变量（全量文本），但 Generator 需确认非 digest 路径完全不引用该变量。建议 digest_text 相关代码只在 `if args.digest:` 分支内作用域。

6. **编码约束遵守**: 所有新增 Python 文件头 3 行内必须有一行描述用途的注释；文件命名用 `snake_case.py`；修改职能后需更新 module-map.md；任何代码修改后运行 `check_structure.py`。
