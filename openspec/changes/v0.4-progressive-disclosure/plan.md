# Plan: v0.4 渐进式披露分析引擎

## 1. 变更范围

### 需要新建的文件

| 文件 (完整路径) | 改动意图 |
| ---- | ---- |
| `app/analyzer/guiding_files.py` | 引导文件收集模块：扫描目标项目中人类认知项目的关键文件（README、依赖清单、Docker/CI 配置、框架配置），不读取业务源码；生成目录结构摘要（一级+二级目录名，折叠UUID/编译产物目录） |
| `app/analyzer/domain_analyzer.py` | LLM 业务板块识别模块：将引导文件内容 + 目录结构输入 LLM，产出业务板块列表（名称、描述、对应路径、置信度）、板块间关系、一句话定位、技术栈、下一步建议。LLM 不可用时降级为模板输出 |

### 需要修改的文件

| 文件 (完整路径) | 改动意图 |
| ---- | ---- |
| `app/analyzer/__init__.py` | 版本号 0.3.2 -> 0.4.0 |
| `app/analyzer/map_writer.py` | 新增 `generate_progressive_overview()` 函数，输出单一 project-overview.md（一句话定位 + 技术栈 + 板块表格 + 板块关系图 + 下一步建议）；支持原子写入和现有内容合并 |
| `harness/scripts/analyze_project.py` | 主流程重构：默认模式运行渐进式披露分析（引导文件收集 -> 目录摘要 -> LLM 板块识别 -> 输出概览）；`--depth=full` 恢复遗留全量分析模式；`--depth` 参数改为接受 int 或 "full" |
| `harness/scripts/help.py` | 版本号 v0.3.1 -> v0.4，analyze_project.py 命令描述更新 |
| `README.md` | 版本号 v0.3.1 -> v0.4，快速开始新增渐进式分析示例，更新命令行说明 |
| `harness/project-map/command-map.md` | `analyze_project.py` 行更新描述：v0.4 渐进式披露 + --depth=full 保留全量分析 |
| `harness/project-map/module-map.md` | 新增 `guiding_files.py` 和 `domain_analyzer.py` 两个模块登记 |
| `harness/project-map/directory-map.md` | 更新目录结构，新增两个 Python 模块文件 |

### 不需要修改的文件

`app/analyzer/scanner.py`, `app/analyzer/parser.py`, `app/analyzer/overview.py`, `app/analyzer/llm_assistant.py` 保持不变。所有遗留功能路径完整保留。

## 2. 任务列表

### 实现任务 (-> Generator)

---

**IMP-1: 版本号更新**

- 文件: `app/analyzer/__init__.py`
- 内容: `__version__ = "0.4.0"`
- 完成标准: `python -c "from app.analyzer import __version__; print(__version__)"` 输出 `0.4.0`
- 验证: `python harness/scripts/check_structure.py`

---

**IMP-2: 引导文件收集模块 (guiding_files.py)**

- 文件: `app/analyzer/guiding_files.py` (新建)
- 内容:
  1. 定义 `GUIDING_FILE_PATTERNS` 字典，key 为文件名/路径模式，value 为文件用途说明：
     - 文档类: `README.md`, `README.rst`, `README`, `CHANGELOG.md`, `CONTRIBUTING.md`
     - 依赖清单: `package.json`, `pyproject.toml`, `setup.py`, `requirements.txt`, `Pipfile`, `Gemfile`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`
     - 容器/部署: `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`
     - CI/CD: `.github/workflows/` 下所有 `.yml`/`.yaml`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml`
     - 构建/任务: `Makefile`, `GNUmakefile`
     - 框架配置: `tsconfig.json`, `next.config.js`, `next.config.ts`, `next.config.mjs`, `nest-cli.json`, `vite.config.js`, `vite.config.ts`, `webpack.config.js`, `angular.json`
     - 环境提示: `.env.example`, `.env.template`, `.gitignore`, `.dockerignore`
  2. `collect_guiding_files(target_path)` 函数：
     - 在目标项目根目录及一级子目录（如 `.github/`、`config/`）搜索上述模式的文件
     - 读取每个文件的前 N 行（README 取前 80 行，配置文件取完整内容或前 100 行，大文件截断）
     - 返回 dict: `{"found": [{file_path, content, label}], "missing": [label]}` 
     - 总数控制在 5-15 个实际文件；如果超过 15 个，优先保留根目录级别的文件
     - 对于不存在的关键文件（如 README），在 "missing" 列表中标注
  3. `generate_directory_summary(target_path)` 函数：
     - 列出根目录下一级子目录名 + 二级嵌套（仅目录名，不展开文件）
     - 过滤 `EXCLUDE_DIRS`（复用 scanner.py 的定义：`.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.idea`, `.vscode`, `dist`, `build`, `harness`）
     - UUID 格式目录名（如 `a1b2c3d4-e5f6-...` 等哈希模式）折叠为一条 `... UUID 目录 (N 个)`
     - 编译产物目录（如 `dist/`, `build/`, `.next/`, `__pycache__/`）折叠为一条 `... 编译产物目录 (N 个)`
     - 输出不超过 30 行，每行一个目录名
     - 返回纯文本字符串
- 依赖: `app/analyzer/scanner.py` 的 `EXCLUDE_DIRS`（import 或本地复制常量）
- 完成标准: 对 Notebook 自身运行，gathers README.md, package.json（不存在则标记 missing）, pyproject.toml（不存在标记 missing）, CLAUDE.md 等；目录摘要排除 `.git`, `__pycache__` 等
- 验证: `python -c "from app.analyzer.guiding_files import collect_guiding_files, generate_directory_summary; r = collect_guiding_files('.'); print(len(r['found']), 'found,', len(r['missing']), 'missing'); print(generate_directory_summary('.'))"`

---

**IMP-3: LLM 业务板块识别模块 (domain_analyzer.py)**

- 文件: `app/analyzer/domain_analyzer.py` (新建)
- 内容:
  1. `analyze_business_domains(guiding_files_result, dir_summary, project_name, enable_dotenv=True)` 函数：
     - 入参: `guiding_files_result`（来自 IMP-2 的结果）, `dir_summary` 文本, `project_name` 字符串
     - 调用 `llm_assistant._get_llm_config()` 获取 LLM 配置
     - 如果无 API Key：返回降级结果（模板化的板块列表，置信度全部标 "低"）
     - 如果有 API Key：调用 `_call_llm()` 进行业务板块识别
     - 返回 dict: `{one_liner, tech_stack, domains: [{name, description, evidence, paths, confidence}], relationships: [{from, to, type, evidence}], next_steps: [str, str, str], source: "llm"|"degraded"}`
  2. `_build_domain_analysis_prompt(guiding_files_result, dir_summary, project_name)` 函数：
     - 构造 LLM system prompt，包含以下约束：
       - "你是项目架构分析专家。根据目标项目的 README、依赖清单、配置文件、目录结构，推断该项目的业务板块（功能领域）。"
       - "业务板块是从用户视角看的'这个项目有哪些功能模块'，不是代码目录名。一个板块可能跨多个目录。"
       - "每个板块必须注明信息来源（README 哪一段、哪个依赖名、哪个配置文件名）。"
       - "禁止凭空编造板块描述。没有充分证据时标注低置信度。"
       - "板块数量控制在 5-20 个。太少失去意义，太多退回细粒度。"
     - 构造 user prompt，包含：
       - 项目名
       - 每个引导文件的内容（截断后，标注文件路径和用途）
       - 目录结构摘要
       - 要求按指定 JSON 格式输出
     - JSON 输出格式要求：
       ```json
       {
         "one_liner": "一句话定位项目",
         "tech_stack": "技术栈简述",
         "domains": [
           {"name": "板块名", "description": "板块描述...", "evidence": "来源：README 第X行/package.json依赖X", "paths": ["目录A/", "目录B/"], "confidence": "high|medium|low"}
         ],
         "relationships": [
           {"from": "板块A", "to": "板块B", "type": "data_flow|depends_on", "evidence": "来源说明"}
         ],
         "next_steps": ["建议1", "建议2", "建议3"]
       }
       ```
  3. `_parse_domain_response(response_text)` 函数：
     - 尝试从 LLM 响应中提取 JSON
     - 处理 LLM 可能包裹在 ```json 代码块中的情况
     - 解析失败时返回降级结果
     - `max_tokens=2048`（需要足够的输出空间）
     - `timeout=60`（复杂分析需要更长时间）
  4. `_degraded_domain_result(guiding_files_result, dir_summary, project_name)` 函数：
     - LLM 不可用时的降级输出
     - 从引导文件内容中提取项目名和基础信息作为 one_liner
     - 从目录名生成板块列表（按一级目录分组），置信度全部标 "低"
     - 板块间关系为空列表
     - next_steps 为通用建议
- 依赖: `app.analyzer.llm_assistant` 的 `_get_llm_config`, `_call_llm`
- 完成标准: 无 API Key 时返回降级结果且不崩溃；有 API Key 时返回 LLM 推断的板块列表
- 验证: `python -c "from app.analyzer.domain_analyzer import analyze_business_domains; from app.analyzer.guiding_files import collect_guiding_files, generate_directory_summary; r = collect_guiding_files('.'); s = generate_directory_summary('.'); result = analyze_business_domains(r, s, 'AI_Project_Notebook', enable_dotenv=False); print(result['source'], len(result['domains']), 'domains')"`（无 Key 环境输出 `degraded`）

---

**IMP-4: 渐进式概览写入函数 (map_writer.py)**

- 文件: `app/analyzer/map_writer.py`
- 内容: 新增 `generate_progressive_overview(domain_result, output_dir)` 函数：
  - 入参: `domain_result` dict（IMP-3 的输出）, `output_dir` 路径
  - 输出文件: `{output_dir}/project-overview.md`（单一文件）
  - 文件内容结构:
    1. `# 项目概览` — 标题
    2. `## 定位` — one_liner 一句话
    3. `## 技术栈` — tech_stack 文本
    4. `## 业务板块` — 表格：板块名 / 描述 / 涉及路径 / 置信度
    5. `## 板块关系` — 文本列表或简单的 ASCII 关系图
    6. `## 下一步建议` — 编号列表（2-3 条）
    7. 页脚：`> 本文件由 v0.4 渐进式披露分析引擎自动生成。使用 --depth=full 获取完整项目地图。`
  - 置信度用图示标注（高=绿色勾、中=黄色横线、低=红色问号，使用纯文本符号即可）
  - 输出简洁，用户 2 分钟内能读完（控制在约 2 页终端输出）
  - 使用已有的 `_atomic_write()` 和 `_merge_sections()` 进行原子写入和增量合并
- 完成标准: 函数调用后生成 `project-overview.md`，内容包含所有 6 个部分
- 验证: `python harness/scripts/check_structure.py` + 手动运行 `python -c "from app.analyzer.map_writer import generate_progressive_overview; generate_progressive_overview({'one_liner': 'test', 'tech_stack': 'test', 'domains': [], 'relationships': [], 'next_steps': [], 'source': 'degraded'}, '/tmp/test_output')"` 查看输出文件

---

**IMP-5: CLI 入口重构 (analyze_project.py)**

- 文件: `harness/scripts/analyze_project.py`
- 内容: 主流程重构为两种模式分支：

  **A. `--depth` 参数改造**
  - 新增 `_depth_type(value)` 自定义类型函数：
    ```python
    def _depth_type(value):
        if value.lower() == "full":
            return "full"
        try:
            return int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"期望整数或 'full'，实际: {value}")
    ```
  - 将 `parser.add_argument("--depth", type=int, default=3)` 改为 `type=_depth_type, default=3`
  - `--help` epilog 更新，说明新模式和 `--depth=full` 的用法

  **B. 默认模式（`depth != "full"`）：渐进式披露分析**
  - Step 1: 调用 `collect_guiding_files(target_path)` 和 `generate_directory_summary(target_path)`
  - Step 2: 打印收集到的引导文件数量和缺失项
  - Step 3: 如果 `--llm`，调用 `analyze_business_domains()` 进行 LLM 板块识别
  - Step 4: 如果无 `--llm` 或无 API Key，调用降级（enable_dotenv 控制）
  - Step 5: 调用 `generate_progressive_overview()` 输出 `project-overview.md`
  - 成功输出消息：`"渐进式分析完成，已生成 project-overview.md 到 {output_dir}"`
  - 无 LLM 时提示：`"未启用 LLM，使用降级模式。添加 --llm 启用 AI 板块识别。"`

  **C. `--depth=full` 模式：遗留全量分析**
  - 将现有的 Step 1 ~ Step 4 全量分析流程包装在 `if args.depth == "full":` 分支内
  - 代码逻辑完全不变，仅增加条件分支
  - 输出消息保持 `"分析完成，已生成 4 个 project-map 文件到 {output_dir}"`

  **D. 导入结构调整**
  - 新增导入：`from app.analyzer.guiding_files import collect_guiding_files, generate_directory_summary`
  - 新增导入：`from app.analyzer.domain_analyzer import analyze_business_domains`
  - 新增导入：`from app.analyzer.map_writer import generate_progressive_overview`
  - 遗留模式的导入保持不变（从 `app.analyzer.scanner` 等导入）

- 完成标准: 
  - `python harness/scripts/analyze_project.py .` 默认模式运行，输出 `project-overview.md`，无 LLM 时降级
  - `python harness/scripts/analyze_project.py . --depth=full` 运行遗留全量分析，输出 4 个文件
  - `python harness/scripts/analyze_project.py --help` 显示新用法说明
- 验证: `python harness/scripts/check_structure.py` + `python harness/scripts/analyze_project.py . --quiet`（退出码 0，生成 project-overview.md）

---

**IMP-6: help.py 版本与描述更新**

- 文件: `harness/scripts/help.py`
- 内容:
  - 版本号 `v0.3.1` -> `v0.4`
  - `analyze_project.py` 行描述更新为：`"智能项目分析引擎 (v0.4 渐进式披露 / --depth=full 全量分析 / --llm LLM增强)"`
- 完成标准: `python harness/scripts/help.py` 输出版本号 v0.4，analyze 命令描述包含 "渐进式披露"
- 验证: `python harness/scripts/help.py | findstr "v0.4"`

---

**IMP-7: 文档更新**

- 文件: `README.md`, `harness/project-map/command-map.md`, `harness/project-map/module-map.md`, `harness/project-map/directory-map.md`
- 内容:

  **README.md**
  - 版本号 v0.3.1 -> v0.4
  - 描述更新为：`v0.4 — 渐进式披露分析引擎。模拟人类认知路径，通过少量关键文件识别项目业务板块。`
  - 快速开始部分：
    - 默认模式示例：`python harness/scripts/analyze_project.py <目标路径>`
    - LLM 增强：`python harness/scripts/analyze_project.py <目标路径> --llm`
    - 全量分析：`python harness/scripts/analyze_project.py <目标路径> --depth=full`
    - 组合使用：`python harness/scripts/analyze_project.py <目标路径> --depth=full --llm`

  **command-map.md**
  - `analyze_project.py` 行更新为：`"智能项目分析引擎 (v0.4: 渐进式披露 + --depth=full 全量分析 / --llm LLM增强 / --depth 目录深度 / --source-root 源码根)"`

  **module-map.md**
  - 在 "自动分析模块" 表格中新增两行：
    - `app\analyzer\guiding_files.py` | 引导文件收集：扫描README、依赖清单、CI配置等关键文件；生成目录结构摘要 | `collect_guiding_files`, `generate_directory_summary` | - |
    - `app\analyzer\domain_analyzer.py` | LLM 业务板块识别：将引导文件输入 LLM 识别业务领域、推断板块关系、生成项目概览 | `analyze_business_domains`, `_build_domain_analysis_prompt`, `_parse_domain_response`, `_degraded_domain_result` | - |

  **directory-map.md**
  - 在 `app/analyzer/` 子目录下新增两行：
    - `├── guiding_files.py`
    - `├── domain_analyzer.py`

- 完成标准: 所有文档与新版本一致
- 验证: `python harness/scripts/check_structure.py`

---

### 测试任务 (-> Tester)

---

**TST-1: 引导文件收集测试**

- 文件: `tests/test_guiding_files.py` (新建)
- 覆盖点:
  - 标准项目（有 README、package.json、tsconfig.json）收集到预期文件
  - 空项目（无任何引导文件）返回空 found 列表和完整 missing 列表
  - README 截断：大文件只取前 80 行
  - 配置文件读取不截断（或前 100 行）
  - 超过 15 个候选文件时优先保留根目录级别
  - `.github/workflows/` 目录下的 CI 配置被收集
  - 排除目录（node_modules、.git 等）内的同名文件被跳过
- 验证: `python -m pytest tests/test_guiding_files.py -v`

---

**TST-2: 目录摘要生成测试**

- 文件: `tests/test_guiding_files.py` (追加)
- 覆盖点:
  - 标准项目目录输出包含一级和二级目录名
  - UUID 格式目录名被折叠为一条摘要
  - `dist/`、`build/`、`__pycache__/` 等编译产物目录折叠
  - `.git`、`node_modules` 等排除目录不出现
  - 输出行数不超过 30 行
  - 空目录列表输出合理提示
- 验证: `python -m pytest tests/test_guiding_files.py -v -k "directory_summary"`

---

**TST-3: 业务板块识别测试（降级模式）**

- 文件: `tests/test_domain_analyzer.py` (新建)
- 覆盖点:
  - 无 API Key 时 `analyze_business_domains()` 返回 `source="degraded"`
  - 降级结果包含 `one_liner`, `tech_stack`, `domains`, `relationships`, `next_steps` 所有字段
  - 降级结果的每个板块置信度为 "低"
  - `_build_domain_analysis_prompt()` 输出包含引导文件内容和目录摘要
  - `_parse_domain_response()` 正确处理标准 JSON 响应
  - `_parse_domain_response()` 正确处理包裹在 ```json 代码块中的响应
  - `_parse_domain_response()` 处理畸形 JSON 不崩溃，返回降级结果
- 验证: `python -m pytest tests/test_domain_analyzer.py -v`

---

**TST-4: 渐进式概览输出测试**

- 文件: `tests/test_analyze_project.py` (追加)
- 覆盖点:
  - `generate_progressive_overview()` 生成 `project-overview.md`
  - 输出文件包含6个必需部分：定位、技术栈、业务板块、板块关系、下一步建议、页脚
  - 置信度标注正确显示（高/中/低使用适当符号）
  - 空板块列表时不崩溃，输出合理的空状态
  - 原子写入：无 .tmp 残留文件
- 验证: `python -m pytest tests/test_analyze_project.py -v -k "progressive_overview"`

---

**TST-5: CLI 端到端测试**

- 文件: `tests/test_analyze_project.py` (追加)
- 覆盖点:
  - 默认模式（无 --depth=full）生成 `project-overview.md`，不生成 4 个 legacy 文件
  - `--depth=full` 模式生成 4 个 legacy 文件
  - `--help` 输出包含 `--depth=full` 和 `depth_type` 说明
  - `--depth=full --llm --quiet` 组合不报错
  - 默认模式 `--quiet` 退出码 0
  - 无效 `--depth` 值（如 `--depth=abc`）报错退出
- 验证: `python -m pytest tests/test_analyze_project.py -v -k "CLI"`

---

**TST-6: 全量回归测试**

- 文件: `tests/` (全部已有测试)
- 覆盖点: 所有已有测试 (`test_export_report.py`, `test_help.py`, `test_init_project.py`, `test_search_notes.py`, `test_analyze_project.py` 已有部分) 保持通过
- 验证: `python -m pytest tests/ -v`

---

## 3. 依赖关系

```
IMP-1 (版本号) —— 无依赖，可最先执行

IMP-2 (guiding_files.py) —— 无依赖

IMP-3 (domain_analyzer.py) —— 依赖 IMP-2 (需要引导文件数据结构)，依赖 llm_assistant.py 的 _get_llm_config/_call_llm
    |
    v
IMP-4 (map_writer 新增函数) —— 依赖 IMP-3 (需要 domain_result 数据结构)

IMP-5 (analyze_project.py 重构) —— 依赖 IMP-2, IMP-3, IMP-4
    |
    v
IMP-6 (help.py) —— 无依赖（但建议在 IMP-5 之后，以确认 CLI 参数描述准确）
IMP-7 (文档更新) —— 依赖 IMP-5（需要确认最终命令描述）

TST-1 → 依赖 IMP-2 完成
TST-2 → 依赖 IMP-2 完成
TST-3 → 依赖 IMP-3 完成
TST-4 → 依赖 IMP-4 完成
TST-5 → 依赖 IMP-5 完成
TST-6 → 依赖所有 IMP 和 TST 完成
```

### 并行化建议

- **第一波 (并行)**: IMP-1, IMP-2
- **第二波**: IMP-3（依赖 IMP-2 完成）
- **第三波 (并行)**: IMP-4, IMP-6（3 和 6 无文件冲突）
- **第四波**: IMP-5（依赖 IMP-2, IMP-3, IMP-4）
- **第五波**: IMP-7（文档更新）
- **第六波 (并行)**: TST-1, TST-2, TST-3, TST-4
- **第七波**: TST-5
- **第八波**: TST-6

IMP-3 和 IMP-4 可并行：domain_analyzer.py 和 map_writer.py 无文件冲突。IMP-6 (help.py) 和 IMP-4 也无文件冲突。

## 4. 风险点

1. **`--depth` 参数类型变更**：现有 `--depth` 是 `type=int`，改为自定义类型后，管道脚本和自动化调用中的 `--depth 2` 仍然有效（先尝试 `int()` 转换）。但 `--depth=full` 是新增值，不影响现有调用。需确保自定义类型的错误消息清晰。

2. **引导文件读取的编码和权限问题**：目标项目可能包含非 UTF-8 编码的配置、二进制文件或权限受限的文件。`collect_guiding_files()` 需要 `try/except` 包裹每个文件读取，单个文件失败不影响整体。

3. **LLM Prompt 的领域特定性**：业务板块识别依赖 LLM 对项目类型的理解。对于高度专业化领域（如生物信息学、嵌入式系统），LLM 可能无法准确识别板块。置信度标注和证据引用机制是缓解手段，需在 prompt 中强调"不确定时标低"。

4. **引导文件数量边界**：spec 要求 5-15 个引导文件，但大型 monorepo 可能收集到 30+ 个。需实现优先级排序：根目录文件 > 一级子目录 > 深层目录。超出 15 个时截断并告知用户。

5. **JSON 解析容错**：LLM 可能返回不完整 JSON（被截断）、包裹在 Markdown 代码块中、或包含格式错误。`_parse_domain_response()` 需多重尝试：先尝试直接 `json.loads()`，再尝试从 ```json 块提取，最后降级。所有路径不能抛异常。

6. **遗留模式代码不变性**：`--depth=full` 分支中的代码必须是现有代码的精确拷贝，不能引入任何行为变更。重构时需要用 git diff 确认遗留路径零变化。

7. **输出文件命名冲突**：默认模式输出 `project-overview.md`，遗留模式输出 `overview.md`。两个文件名不同，避免互相覆盖。如果用户先运行默认模式再运行 `--depth=full`，两个文件共存。

8. **无 LLM 场景的降级质量**：无 API Key 时输出的降级结果 confidence 全部标 "低"，板块从目录名推断。需在输出文件顶部明确标注"未启用 LLM"以避免用户误以为是 AI 分析结果。

9. **`_call_llm` 交叉依赖**：`domain_analyzer.py` 需要调用 `llm_assistant.py` 的私有函数 `_get_llm_config()` 和 `_call_llm()`。虽然 Python 允许跨模块访问下划线前缀函数，但应避免循环导入。当前依赖方向为单向：`domain_analyzer -> llm_assistant`，无循环风险。

10. **EXCLUDE_DIRS 重复定义风险**：`guiding_files.py` 需要排除目录列表。直接 import scanner.py 的 `EXCLUDE_DIRS` 可避免维护两套列表，但增加模块耦合。建议 import 复用，并在注释中注明来源。
