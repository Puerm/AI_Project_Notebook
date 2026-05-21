# Plan: v0.3 智能项目分析引擎

## 1. 变更范围

### 新增文件

| 文件路径 | 改动意图 |
| -------- | -------- |
| `app/analyzer/__init__.py` | 包初始化，导出公共接口 |
| `app/analyzer/scanner.py` | 目录扫描引擎：递归扫描目标项目目录树、识别标准目录名并标注用途、对非标准目录基于内容推断用途 |
| `app/analyzer/parser.py` | 代码解析引擎：Python AST 解析（函数/类/import 提取）、JS/TS 解析器管理（自动检测 esprima/acorn 是否可用、不可用时提示并帮助安装）、JS/TS 文件解析（函数/类/import 提取） |
| `app/analyzer/overview.py` | 项目概览检测：技术栈识别（requirements.txt/pyproject.toml/package.json/tsconfig.json 等）、入口文件检测（main/app/index 模式）、项目类型推断（Web/CLI/库）、生成一句话描述 |
| `app/analyzer/llm_assistant.py` | LLM 语义增强（可选）：通过环境变量读取 API 配置、为模块描述/目录标注/项目概述生成增强文本、LLM 不可用时降级到模板描述、绝对不崩溃 |
| `app/analyzer/map_writer.py` | 项目地图文件生成：生成 overview.md / directory-map.md / module-map.md / data-flow.md 四个文件、原子写入（临时文件 + rename）、读取已有文件并合并更新 |
| `harness/scripts/analyze_project.py` | CLI 入口命令：解析命令行参数（目标路径、--llm/--no-llm、--output-dir）、编排分析流水线（scanner → parser → overview → 可选 LLM → map_writer）、打印进度信息、处理错误 |
| `tests/test_analyze_project.py` | 测试文件：覆盖全部分析子模块和 CLI 集成 |

### 修改文件

| 文件路径 | 改动意图 |
| -------- | -------- |
| `harness/scripts/check_structure.py` | REQUIRED_DIRS 增加 `app/` 和 `app/analyzer/`；REQUIRED_FILES 增加 `harness/scripts/analyze_project.py` |
| `harness/project-map/module-map.md` | 登记 7 个新模块（analyze_project 命令 + 6 个 analyzer 子模块），填写名称、路径、职责、依赖 |
| `harness/project-map/command-map.md` | 登记 `analyze_project.py` CLI 命令，填写用途和来源文件 |
| `harness/project-map/directory-map.md` | 更新目录树，标注 `app/analyzer/` 目录职责为"智能项目分析引擎" |
| `harness/project-map/change-map.md` | 记录本次变更摘要（在任务完成后由最后执行者更新） |
| `README.md` | 快速开始新增 `analyze_project.py` 命令用法示例，版本号更新为 v0.3 |
| `harness/project-map/overview.md` | 当前版本更新为 v0.2（当前未同步），下一步计划更新 |

## 2. 任务列表

### 实现任务 (IMP- → Generator)

---

**IMP-1: 创建 `app/analyzer/` 包结构**

- 文件: `app/analyzer/__init__.py`
- 内容: 包初始化，定义版本号常量 `__version__`，导出子模块入口
- 完成标准: `python -c "import app.analyzer; print(app.analyzer.__version__)"` 成功执行
- 验证: `python -c "import app.analyzer"`

---

**IMP-2: 创建 `app/analyzer/scanner.py` — 目录扫描引擎**

- 文件: `app/analyzer/scanner.py`
- 职责:
  - 接收目标项目根路径，递归扫描目录树
  - 生成嵌套的目录结构数据（dict/列表形式）
  - 标准目录名匹配标注：`src/` → "源代码"、`tests/` → "测试"、`docs/` → "文档"、`lib/` → "库文件"、`bin/` → "可执行文件"、`config/` → "配置文件" 等
  - 非标准目录：检查目录内文件扩展名分布，推断用途（.py 多 → "Python 源码"、.js 多 → "JavaScript 源码"）
  - 排除 `.git`、`node_modules`、`__pycache__`、`.venv`、`venv`、`dist`、`build` 等常见非源码目录
  - 收集所有需要解析的源代码文件路径列表（.py、.js、.ts、.jsx、.tsx）
- 完成标准:
  - 对包含混合文件类型的测试项目能正确分类目录
  - 排除列表完全生效
  - 返回结构化的目录树数据和文件列表
- 验证: `python -c "from app.analyzer.scanner import scan_directory; result = scan_directory('.'); print(type(result), len(result.get('files', [])))"`

---

**IMP-3: 创建 `app/analyzer/parser.py` — 代码解析引擎**

- 文件: `app/analyzer/parser.py`
- Python 解析（stdlib `ast` 模块）:
  - 提取所有 `import` / `from ... import` 语句及其导入的模块名
  - 提取所有 `def` 函数定义（函数名）
  - 提取所有 `class` 类定义（类名）
  - 每个解析到的元素附带行号（用于后续定位）
- JS/TS 解析:
  - 检测系统是否安装 Node.js（运行 `node --version`）
  - 检查 esprima 或 acorn 是否可用（首选 acorn，因为更轻量纯 JS）
  - 不可用时输出清晰的安装提示（`npm install -g acorn` 或项目本地安装）
  - 通过子进程调用 Node.js 脚本完成 JS/TS 解析：`node -e "const acorn = require('acorn'); ..."`
  - 如果 JS/TS 解析器不可用且用户拒绝安装，JS/TS 文件返回最简模式（仅正则提取 import/require 和 function/class 声明）
  - 提取结果格式与 Python 解析对齐：函数名、类名、导入关系
- 完成后返回统一结构: `{file_path: {imports: [...], functions: [...], classes: [...], language: "python"|"javascript"|"typescript"}}`
- 完成标准:
  - Python 文件解析精度 >= 95%（能正确提取标准语法下的函数/类/import）
  - JS/TS 解析器检测逻辑正确，安装引导清晰
  - 未安装解析器时 JS/TS 降级正则模式不崩溃
- 验证:
  - `python -c "from app.analyzer.parser import parse_file; result = parse_file('harness/scripts/check_structure.py'); print(result.keys())"`
  - `python -c "from app.analyzer.parser import check_js_parser; print(check_js_parser())"`

---

**IMP-4: 创建 `app/analyzer/overview.py` — 项目概览检测**

- 文件: `app/analyzer/overview.py`
- 技术栈检测:
  - 检查根目录是否存在 `requirements.txt` / `pyproject.toml` / `setup.py` / `Pipfile` → Python 项目
  - 检查 `package.json` → Node.js 项目；进一步检查 dependencies 中是否有 React/Vue/Angular/Next/Express 等框架
  - 检查 `tsconfig.json` → TypeScript
  - 检查 `Cargo.toml` → Rust（仅标注，不深入分析）
  - 检查 `go.mod` → Go（仅标注，不深入分析）
  - 返回检测到的技术栈列表
- 入口文件检测:
  - 搜索常见入口文件名: `main.py`、`app.py`、`index.py`、`run.py`、`server.py`；`index.js`、`app.js`、`server.js`
  - 优先级：根目录 > src/ 子目录
- 项目类型推断:
  - 检测到 Web 框架依赖（Flask/FastAPI/Django/Express/Next）→ "Web 应用"
  - 检测到 `setup.py` / `pyproject.toml` 包含 build 配置 → "库"
  - 检测到 `Click`/`argparse`/`commander` 依赖 → "CLI 工具"
  - 默认 → "通用项目"
- 一句话描述:
  - 读取 README.md 第一行标题（如有）
  - 结合项目名（目录名）+ 技术栈 + 项目类型 拼接生成
  - 如启用 LLM 则由 llm_assistant 覆写（在 orchestration 层处理）
- 返回统一结构: `{name, description, tech_stack: [...], project_type, entry_files: [...]}`
- 完成标准: 对 Express 项目能识别为 "Web 应用 (Node.js/Express)"，对 Flask 项目能识别为 "Web 应用 (Python/Flask)"
- 验证: `python -c "from app.analyzer.overview import analyze_overview; result = analyze_overview('.'); print(result.get('tech_stack'), result.get('project_type'))"`

---

**IMP-5: 创建 `app/analyzer/llm_assistant.py` — LLM 语义增强**

- 文件: `app/analyzer/llm_assistant.py`
- 配置读取:
  - 从环境变量读取 LLM 配置: `LLM_API_KEY`、`LLM_API_BASE`（可选，默认 OpenAI 兼容端点）、`LLM_MODEL`（可选，默认 `gpt-4o-mini`）
  - 支持 Anthropic 格式（检测 `ANTHROPIC_API_KEY`）和 OpenAI 兼容格式
  - 优先级: 命令行参数 > 环境变量 > 默认值
- LLM 调用:
  - 使用 stdlib `urllib.request` 发送 HTTP POST，不引入第三方 Python 包
  - 三个分析点各有一套 prompt 模板:
    1. 目录标注增强：输入目录名 + 文件列表 → 期望输出中文用途描述
    2. 模块描述增强：输入模块名 + 函数/类列表 → 期望输出一句话职责描述
    3. 项目概述增强：输入项目名 + 技术栈 + 入口文件 → 期望输出一句话中文描述
  - 每个 prompt 控制 token 消耗（system prompt < 200 字，输入数据精简）
- 降级策略:
  - API Key 未配置 → 直接返回硬编码模板描述，不报错
  - 网络超时（默认 10 秒）→ 返回模板描述
  - API 返回错误 → 打印警告，返回模板描述
  - 任何异常都不抛出，静默降级
- 返回: `{enhanced: bool, description: str, source: "llm"|"template"}`
- 完成标准:
  - 未设置任何环境变量时直接走降级，不崩溃
  - 设置无效 API Key 时能正确处理错误并降级
- 验证: `LLM_API_KEY="" python -c "from app.analyzer.llm_assistant import enhance_description; print(enhance_description('test module'))"` (应走降级)

---

**IMP-6: 创建 `app/analyzer/map_writer.py` — 项目地图文件生成**

- 文件: `app/analyzer/map_writer.py`
- 接收分析结果数据（来自 scanner / parser / overview / llm_assistant），生成 4 个 markdown 文件
- 每个文件生成：
  - `overview.md`: 项目名称 + 一句话描述 + 技术栈 + 入口文件 + 项目类型
  - `directory-map.md`: ASCII 目录树 + 每个目录的中文标注
  - `module-map.md`: 每个文件的表格（文件路径、模块描述、主要函数/类、各自一句话职责）
  - `data-flow.md`: 模块间依赖关系（A import B 的列表/图示）
- 原子写入:
  - 先写 `{filename}.tmp` 临时文件
  - 写入完成后 `os.replace()` 覆盖原文件
  - 如果目标目录不存在则先创建
- 合并策略:
  - 如果目标 project-map 文件已存在（非首次运行），读取现有内容
  - 保留用户手动添加的内容（通过标记识别：`<!-- MANUAL -->` 注释标记的段落不覆盖）
  - 对模块表格进行增量更新：新增模块追加行，已有模块更新描述
- 完成标准:
  - 对测试数据生成 4 个格式正确的 markdown 文件
  - 原子写入后不会出现半截文件
  - 对已有 project-map 文件能正确合并
- 验证:
  - `python -c "from app.analyzer.map_writer import generate_all; generate_all({}, '/tmp/test_output'); import os; print(os.listdir('/tmp/test_output'))"`
  - (在临时目录验证 4 个文件均生成)

---

**IMP-7: 创建 `harness/scripts/analyze_project.py` — CLI 入口命令**

- 文件: `harness/scripts/analyze_project.py`
- 文件头注释: `# analyze_project.py — 智能项目分析引擎，自动生成 project-map 文件`
- 命令行参数 (stdlib `argparse`):
  - `target_path` (位置参数): 目标项目路径，默认当前目录 `"."`
  - `--output-dir` / `-o`: 输出目录，默认 `"{target_path}/harness/project-map/"`
  - `--llm` / `--no-llm`: 是否启用 LLM 增强，默认 `--no-llm`（用户需显式启用）
  - `--quiet` / `-q`: 精简输出模式
- 编排流程:
  1. 验证 target_path 存在且是目录
  2. 调用 scanner.scan_directory(target_path) → 目录树 + 文件列表
  3. 对文件列表中每个文件调用 parser.parse_file(file_path) → 模块信息
  4. 调用 overview.analyze_overview(target_path) → 项目概览
  5. (如果 --llm 启用) 调用 llm_assistant 增强扫描/解析/概览结果
  6. 调用 map_writer.generate_all(results, output_dir) → 生成 4 个文件
- 输出:
  - 每一步打印进度: `[1/5] 扫描目录结构...` / `[2/5] 解析源代码...`
  - 统计信息: `发现 23 个源码文件 (Python: 15, JavaScript: 8)`
  - 完成提示: `分析完成，已生成 4 个 project-map 文件到 {output_dir}`
- 错误处理:
  - 目标路径不存在 → 打印错误并退出(1)
  - 目标路径不是目录 → 打印错误并退出(1)
  - 目标路径为空目录 → 打印提示并退出(0)（无可分析内容）
  - 任何子模块异常 → 打印异常类型和信息，不崩溃，继续执行剩余步骤
- 完成标准:
  - 对 AI_Project_Notebook 自身运行 `python harness/scripts/analyze_project.py .` 能生成 4 个文件
  - `--no-llm` 默认行为不尝试网络调用
  - `--help` 输出完整参数说明
- 验证:
  - `python harness/scripts/analyze_project.py --help`
  - `python harness/scripts/analyze_project.py .` (对当前项目自分析)
  - `python harness/scripts/check_structure.py`

---

**IMP-8: 更新项目文档和结构检查**

- 修改 `harness/scripts/check_structure.py`:
  - REQUIRED_DIRS 新增 `app/analyzer/`（`app/` 已存在，无需新增）
  - REQUIRED_FILES 新增 `harness/scripts/analyze_project.py`
- 修改 `harness/project-map/module-map.md`:
  - 新增 `analyze_project` 命令模块行
  - 新增 6 个 `app/analyzer/` 子模块行（scanner / parser / overview / llm_assistant / map_writer），每个填写路径、职责、依赖
- 修改 `harness/project-map/command-map.md`:
  - CLI 命令表新增 `python harness/scripts/analyze_project.py <目标路径>` 行
- 修改 `harness/project-map/directory-map.md`:
  - 目录树 `app/` 下新增 `│   └── analyzer/` + 标注"智能项目分析引擎"
- 修改 `harness/project-map/overview.md`:
  - 当前版本更新为 v0.2
  - 下一步计划移除"初始化第一个应用模块"行（已通过本变更实现），替换为 v0.3 分析引擎
- 修改 `README.md`:
  - 快速开始新增 `python harness/scripts/analyze_project.py <目标路径>` 示例
  - 版本号更新为 v0.3
- 完成标准: `python harness/scripts/check_structure.py` 通过（预计 63/63，原 62 + 1 dir + 1 file - init_project 已不检查）
- 验证: `python harness/scripts/check_structure.py`

---

### 测试任务 (TST- → Tester)

---

**TST-1: 测试目录扫描器 (scanner.py)**

- 测试文件: `tests/test_analyze_project.py`（ScannerTest 类）
- 覆盖点:
  - 标准目录名识别（src/ → 源代码，tests/ → 测试等）
  - 非标准目录内容推断（基于文件扩展名分布）
  - 排除列表生效（.git / node_modules / __pycache__ 等）
  - 空目录处理
  - 仅含非源码文件的目录处理（图片/数据文件等）
- 验证: `python -m pytest tests/test_analyze_project.py::ScannerTest -v`

---

**TST-2: 测试代码解析器 (parser.py)**

- 测试文件: `tests/test_analyze_project.py`（ParserTest 类）
- 覆盖点:
  - Python 函数/类/import 提取精度（对已知内容的 .py 文件验证输出）
  - JS/TS 解析器检测逻辑（模拟 Node.js 存在/不存在两种环境）
  - JS/TS 降级正则模式（无解析器时降级不崩溃）
  - 空文件、语法错误文件、二进制文件的容错
- 验证: `python -m pytest tests/test_analyze_project.py::ParserTest -v`

---

**TST-3: 测试项目概览检测 (overview.py)**

- 测试文件: `tests/test_analyze_project.py`（OverviewTest 类）
- 覆盖点:
  - 技术栈检测：Python（requirements.txt / pyproject.toml）、Node.js（package.json）、TypeScript（tsconfig.json）
  - 项目类型推断：Web/CLI/库/通用
  - 入口文件检测：main.py / app.py / index.js 等常见模式
  - 缺少所有标志文件时返回合理默认值
- 验证: `python -m pytest tests/test_analyze_project.py::OverviewTest -v`

---

**TST-4: 测试 LLM 助手 (llm_assistant.py)**

- 测试文件: `tests/test_analyze_project.py`（LLMAssistantTest 类）
- 覆盖点:
  - 未设置 API Key 时降级不崩溃
  - 设置无效 API Key 后网络超时降级
  - 三个分析点的 prompt 模板均生成有效输出
  - 环境变量读取逻辑
- 验证: `python -m pytest tests/test_analyze_project.py::LLMAssistantTest -v`

---

**TST-5: 测试地图文件生成 (map_writer.py)**

- 测试文件: `tests/test_analyze_project.py`（MapWriterTest 类）
- 覆盖点:
  - 4 个文件均生成且格式正确
  - 原子写入：模拟写入中断时原文件不被破坏
  - 目标目录不存在时自动创建
  - 已有文件合并逻辑（手动标记段落保留）
- 验证: `python -m pytest tests/test_analyze_project.py::MapWriterTest -v`

---

**TST-6: 测试 CLI 入口集成 (analyze_project.py)**

- 测试文件: `tests/test_analyze_project.py`（CLIIntegrationTest 类）
- 覆盖点:
  - `--help` 输出完整
  - `--no-llm` 默认行为
  - 无效路径报错退出
  - 有效路径完成分析流程并生成文件
  - 空目录优雅退出
  - 使用临时项目目录作为测试 fixture
- 验证: `python -m pytest tests/test_analyze_project.py::CLIIntegrationTest -v`

## 3. 依赖关系

```
IMP-1 (包结构)
 ├─→ IMP-2 (scanner)      [可并行]
 ├─→ IMP-3 (parser)       [可并行]
 ├─→ IMP-4 (overview)     [可并行，但逻辑上需要 scanner 输出格式对齐]
 ├─→ IMP-5 (llm_assistant)[可并行]
 └─→ IMP-6 (map_writer)   [可并行，但逻辑上需要其他模块的输出格式对齐]
        │
        └─→ IMP-7 (CLI 入口)  [依赖 IMP-2~IMP-6 全部完成]
               │
               └─→ IMP-8 (文档更新)  [依赖 IMP-7 完成]
```

所有 TST 任务依赖 IMP-7 完成后才能运行集成测试。TST-1 至 TST-5 的单元测试可在对应 IMP 完成后立即编写。

推荐执行顺序: IMP-1 → IMP-2, IMP-3, IMP-4, IMP-5, IMP-6 并行执行 → IMP-7 → IMP-8 → TST-1~TST-6

## 4. 风险点

| 风险 | 说明 | 应对 |
| ---- | ---- | ---- |
| **JS/TS 解析器选型** | esprima vs acorn 未决定。acorn 更轻量但 esprima 对 TS 支持更好 | IMP-3 实现时首选 acorn（纯 JS，安装简单），如 TS 解析能力不足则 Explorer 评估 esprima 替代方案 |
| **LLM API 配置方式** | 环境变量 vs 配置文件未决定 | IMP-5 实现时用环境变量（`LLM_API_KEY`，与 OpenAI 兼容），符合 12-factor app 惯例。后续版本可扩展配置文件 |
| **大项目性能** | 大型项目可能耗时较长，LLM token 消耗可能很大 | IMP-2 设文件数量上限提示（> 200 个源码文件时警告），LLM 默认不启用（`--no-llm` 为默认值） |
| **AST 解析精度** | Python AST 对语法错误的文件会失败；JS/TS 正则降级模式精度有限 | IMP-3 对解析失败的文件不崩溃，记录警告并跳过该文件 |
| **已有 project-map 内容覆盖** | 用户可能手动编辑过 project-map 文件，被分析引擎覆盖会丢失信息 | IMP-6 实现合并策略：`<!-- MANUAL -->` 标记的段落保留，无标记的自动生成段落会更新 |
| **跨平台兼容** | Windows/PowerShell 与 Unix/bash 的子进程调用差异 | IMP-3 的 JS 解析器子进程调用需同时处理 `node` 和 `node.exe`；IMP-7 的文件路径使用 `os.path` 处理 |
| **模块间接口对齐** | 各子模块独立开发，返回结构不统一会导致 orchestration 层难以集成 | 每个 IMP 任务中明确列出返回数据结构。IMP-7 前由 Generator 做一次接口一致性检查 |
| **未引入第三方 Python 依赖** | 编码规则禁止未批准的第三方库 | LLM 调用用 stdlib `urllib.request`，AST 解析用 stdlib `ast`，JS/TS 通过 Node.js 子进程而非 Python 绑定包 |
