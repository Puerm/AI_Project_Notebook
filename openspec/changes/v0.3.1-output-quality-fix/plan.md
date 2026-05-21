# Implementation Plan: v0.3.1 输出质量修复

## 1. 变更范围

### 需要修改的文件

| 文件 | 改动意图 |
| ---- | -------- |
| `app/analyzer/__init__.py` | 版本号 `0.3.0` -> `0.3.1` |
| `app/analyzer/scanner.py` | 新增 `detect_source_root()` 函数，自动识别源码根目录 |
| `app/analyzer/map_writer.py` | 重构 `generate_module_map`(目录级模块+依赖)、重构 `generate_data_flow`(真实数据流/空模板)、`generate_directory_map` 新增深度控制和折叠显示、更新 `generate_all` 传参 |
| `app/analyzer/llm_assistant.py` | 新增 `.env` 文件解析 `_load_dotenv()`、新增 `check_api_key_available()` API Key 检查与引导函数 |
| `harness/scripts/analyze_project.py` | 新增 `--depth`、`--source-root` 参数；整合源码根检测、目录级模块分组、模块依赖计算；LLM 启用时检查 API Key；`--help` 列出环境变量 |
| `harness/scripts/help.py` | 版本号 `v0.3` → `v0.3.1`，`analyze_project.py` 命令描述追加环境变量提示 |
| `tests/test_analyze_project.py` | 更新受影响的旧测试(3 个)；新增 v0.3.1 功能的测试用例(约 12 个) |

### 不需要修改的文件

| 文件 | 原因 |
| ---- | ---- |
| `app/analyzer/parser.py` | 解析逻辑无需变更 |
| `app/analyzer/overview.py` | 概览检测逻辑无需变更（源码根检测在 scanner.py 新增） |
| `harness/scripts/check_structure.py` | 无新文件/目录，检查清单不变 |
| `harness/project-map/*.md` | 由 Generator 执行后自动更新 |

### 需要新增的文件

无。所有变更均为修改已有文件。

---

## 2. 任务列表

### 实现任务 (-> Generator)

---

**IMP-1: `app/analyzer/__init__.py` — 版本号更新**

- 将 `__version__ = "0.3.0"` 改为 `__version__ = "0.3.1"`
- 完成标准: 文件可正常 import，`__version__` 值为 `"0.3.1"`
- 验证: `python -c "from app.analyzer import __version__; print(__version__)"`

---

**IMP-2: `app/analyzer/scanner.py` — 新增源码根自动识别**

- 新增函数 `detect_source_root(target_path, files)`:
  - 输入: 项目根路径、源码文件列表(相对路径)
  - 算法:
    1. 找出所有包含 `__init__.py` 的目录
    2. 计算所有源码文件的公共祖先目录
    3. 从公共祖先向上查找第一个含 `__init__.py` 的目录，即为源码根
    4. 降级: 若未找到含 `__init__.py` 的祖先，退回使用源码文件的共同祖先目录自身
    5. 若共同祖先即为项目根路径自身，说明无明确源码根，返回 `None`
  - 返回: 源码根相对于 `target_path` 的路径字符串，或 `None`
- 完成标准: 对 BioTec 项目（`back/python/paper_agent/` 含 `__init__.py`）能正确返回 `back/python/paper_agent`
- 验证: `python -m pytest tests/test_analyze_project.py::TestSourceRootDetection -v`

---

**IMP-3: `app/analyzer/map_writer.py` — 目录树深度控制和折叠显示**

- 修改 `_format_tree(node, prefix, is_last, in_tree, max_depth, current_depth)`:
  - 新增参数 `max_depth`(默认 3)、`current_depth`(当前递归层数)
  - 当 `current_depth >= max_depth` 且节点为目录时，不展开子节点，生成折叠摘要行:
    - 统计子文件按扩展名分类
    - 全部同类型文件 → `"Python 源码目录，X 个文件"`
    - 混合类型 → `"N 个子目录，M 个文件"`
  - 摘要行使用 `... ` 前缀区别于正常子树
- 修改 `_build_directory_tree_lines(tree, root_name, max_depth=3)`:
  - 新增 `max_depth` 参数并透传给 `_format_tree`
- 修改 `generate_directory_map(tree, project_name, output_dir, max_depth=3)`:
  - 新增 `max_depth` 参数(默认 3)，透传给 `_build_directory_tree_lines`
- 完成标准: 默认 depth=3 时 BioTec 298KB 的 directory-map 压缩到合理篇幅(<50KB)
- 验证: `python -m pytest tests/test_analyze_project.py::TestDepthControl -v`

---

**IMP-4: `app/analyzer/map_writer.py` — module-map 重构为目录级模块**

- 新增辅助函数 `_group_modules_by_directory(modules, source_root)`:
  - 将每个源码文件按其相对于 `source_root` 的一级子目录分组
  - `source_root` 为 `None` 时使用项目根的一级子目录
  - 返回 `{dir_name: [file_modules]}` 字典
- 新增辅助函数 `_infer_module_description(dir_name, file_list, all_functions, all_classes)`:
  - 基于目录名和内容做规则推断:
    - `adapters/` + 含 `*_adapter.py` → "适配器模块，集成外部数据源"
    - `models/` + 含类定义 → "数据模型层"
    - `services/` → "业务服务层"
    - `controllers/` 或 `routes/` → "路由/控制器层"
    - `utils/` 或 `helpers/` → "工具函数模块"
    - `config/` → "配置管理模块"
    - `tests/` → "测试代码"
    - 无匹配规则时统计: `"包含 N 个文件的 {dir_name} 模块"`
  - 返回描述字符串
- 新增辅助函数 `_compute_module_dependencies(modules_by_dir, all_imports, source_root, target_path)`:
  - 检查模块 A 中任意文件 import 了模块 B 中任意文件 (排除 stdlib 和第三方包)
  - stdlib 过滤: 使用已知 Python stdlib 模块名集合(`sys`, `os`, `json`, `re`, `ast`, `subprocess`, `pathlib`, `typing`, `collections`, `itertools`, `functools`, `datetime`, `logging`, `unittest`, `io`, `hashlib`, `uuid`, `copy`, `math`, `random`, `string`, `textwrap`, `argparse`, `shutil`, `tempfile`, `urllib`, `http`, `socket`, `ssl`, `email`, `csv`, `xml`, `html`, `configparser`, `dataclasses`, `abc`, `enum`, `asyncio`, `threading`, `multiprocessing`, `queue`, `concurrent`, `traceback`, `warnings`, `weakref`, `inspect`, `types`, `importlib`, `pkgutil`, `atexit`, `signal`, `getpass`, `getopt`, `platform`, `sysconfig`, `builtins`, `contextlib` 等)
  - 第三方包识别: import 名称不含 `.` 且不在 stdlib 集合中 → 第三方包
  - 返回 `{module_dir: [dep_module_dirs]}` 字典
- 重构 `_build_table_section(modules, existing_content)`:
  - 表头改为 `| 模块路径 | 模块描述 | 主要函数/类 | 模块依赖 |`
  - 每行数据来源: `_group_modules_by_directory` + `_infer_module_description` + `_compute_module_dependencies`
- 重构 `generate_module_map(dir_modules, output_dir)`:
  - 参数改为 `dir_modules`(目录级模块列表，而非文件级)
  - 调用新的 `_build_table_section`
  - 仍保留 MANUAL 行合并逻辑
- 完成标准: BioTec 项目 module-map 行数从 682 降到 20-40 行
- 验证: `python -m pytest tests/test_analyze_project.py::TestModuleGrouping -v`

---

**IMP-5: `app/analyzer/map_writer.py` — data-flow 重定义为真实数据流**

- 新增函数 `_generate_data_flow_template(source_root)`:
  - 无 LLM 时生成引导模板:
    ```
    ## 数据流分析
    
    > LLM 未启用，无法自动推断数据流路径。
    > 请使用 `--llm` 参数重新运行分析以启用 LLM 语义推断。
    > 或在此手动填写数据流分析内容。
    
    ### 待分析的数据流
    
    - 入口函数 → 处理节点 → 数据变换路径
    - （使用 --llm 自动生成，或手动填写）
    ```
- 修改 `generate_data_flow(all_imports, output_dir, llm_data_flow=None, source_root=None)`:
  - 新增 `llm_data_flow` 参数(LLM 推断的数据流文本，或 None)
  - 新增 `source_root` 参数
  - 有 `llm_data_flow` 时写入 LLM 推断内容
  - 无 `llm_data_flow` 时调用 `_generate_data_flow_template` 生成引导模板
  - 移除逐条 import 的旧逻辑
- 完成标准: 无 LLM 时 data-flow.md 包含引导信息而非虚假的逐条 import 列表
- 验证: `python -m pytest tests/test_analyze_project.py::TestDataFlowTemplate -v`

---

**IMP-6: `app/analyzer/map_writer.py` — `generate_all` 签名更新**

- 修改 `generate_all(results, output_dir)` 为 `generate_all(results, output_dir, max_depth=3, source_root=None)`:
  - 新增 `max_depth` 透传给 `generate_directory_map`
  - 新增 `source_root` 透传给 `generate_module_map` 和 `generate_data_flow`
  - `results` 字典新增可选 key: `dir_modules`(目录级模块)、`llm_data_flow`(LLM 数据流文本)
- 完成标准: 现有调用方(analyze_project.py)传入新参数后功能正常
- 验证: 运行 `python -m pytest tests/test_analyze_project.py::TestMapWriter -v`

---

**IMP-7: `app/analyzer/llm_assistant.py` — .env 加载和 API Key 引导**

- 新增函数 `_load_dotenv(project_root)`:
  - 读取 `project_root/.env` 文件（不存在时静默跳过）
  - 逐行解析 `KEY=VALUE` 格式（忽略空行和 `#` 注释行）
  - 去掉引号包裹(`"VALUE"` 或 `'VALUE'` → `VALUE`)
  - 将解析结果设置到 `os.environ`（只在环境变量不存在时设置，不覆盖已有值）
  - 不使用第三方库(如 python-dotenv)，纯标准库实现
- 修改 `_get_llm_config()`:
  - 在读取环境变量前调用 `_load_dotenv(os.getcwd())` (当前工作目录即目标项目根)
  - 其余逻辑不变
- 新增函数 `check_api_key_available()`:
  - 返回 `(available: bool, guidance: str)`
  - `available=True` 当 `LLM_API_KEY` 或 `ANTHROPIC_API_KEY` 环境变量已设置
  - `guidance` 内容(当不可用时):
    ```
    LLM 功能需要 API Key，但未检测到有效的 API Key。
    
    配置步骤:
    1. 在项目根目录创建 .env 文件
    2. 添加以下内容（选择其一）:
       ANTHROPIC_API_KEY=sk-ant-xxx...  （Anthropic Claude）
       或
       LLM_API_KEY=sk-xxx...           （OpenAI 兼容）
    3. 重新运行: python harness/scripts/analyze_project.py <路径> --llm
    
    可选环境变量:
      LLM_API_BASE    自定义 API 地址
      LLM_MODEL       模型名称 (默认: gpt-4o-mini)
    ```
- 当 `_call_llm` 因 API Key 缺失而失败时: 已有逻辑返回 `None`，调用方(analyze_project.py)负责在此前检查并打印引导
- 完成标准: `.env` 读取与 API Key 缺失时打印引导信息
- 验证: `python -m pytest tests/test_analyze_project.py::TestDotenvAndApiKey -v`

---

**IMP-8: `harness/scripts/analyze_project.py` — CLI 参数和编排逻辑更新**

- 新增 CLI 参数:
  - `--depth N` (type=int, default=3): 目录树展开深度
  - `--source-root PATH` (type=str, default=None): 手动指定源码根目录，覆盖自动检测
  - 移除 `--no-llm` 参数（`--llm` 已明确指定启用，无 `--llm` 即为默认不启用）
- `--help` 增强:
  - 在 argparse description 或 epilog 中追加环境变量说明:
    ```
    环境变量 (LLM 模式需要):
      ANTHROPIC_API_KEY   Anthropic API Key
      LLM_API_KEY         OpenAI 兼容 API Key
      LLM_API_BASE        自定义 API 地址 (可选)
      LLM_MODEL           模型名称 (可选, 默认: gpt-4o-mini)
    
    也可在项目根目录创建 .env 文件配置以上变量。
    ```
- 编排逻辑变更 (Step 1.5 新增于扫描和解析之间):
  ```
  # Step 1.5: Detect source root
  source_root = args.source_root
  if source_root is None:
      from app.analyzer.scanner import detect_source_root
      source_root = detect_source_root(target_path, scan_result["files"])
  if not args.quiet:
      print(f"  源码根: {source_root or '(项目根)'}")
  ```
- 解析步骤 (Step 2) 后新增模块分组:
  ```
  # Group modules by first-level directory under source root
  from app.analyzer.map_writer import _group_modules_by_directory, _compute_module_dependencies, _infer_module_description
  dir_modules_raw = _group_modules_by_directory(modules, source_root)
  module_deps = _compute_module_dependencies(dir_modules_raw, all_imports, source_root, target_path)
  dir_modules = []
  for dir_name, file_mods in dir_modules_raw.items():
      all_funcs = []
      all_classes = []
      for fm in file_mods:
          all_funcs.extend(fm.get("functions", []))
          all_classes.extend(fm.get("classes", []))
      desc = _infer_module_description(dir_name, [fm["file"] for fm in file_mods], all_funcs, all_classes)
      deps = module_deps.get(dir_name, [])
      dir_modules.append({
          "dir": dir_name,
          "description": desc,
          "functions": all_funcs,
          "classes": all_classes,
          "dependencies": deps,
          "file_count": len(file_mods),
          "files": [fm["file"] for fm in file_mods],
      })
  ```
- LLM 步骤 (Step 3) 增强:
  - 启用 `--llm` 时先检查 API Key: 调用 `check_api_key_available()`
  - Key 不可用时打印引导信息到 stderr，继续执行但 LLM 增强跳过
  - Key 可用时正常调用 LLM
- 生成步骤 (Step 4) 更新:
  - `results` 字典新增: `"dir_modules": dir_modules`、`"source_root": source_root`
  - `generate_all(results, output_dir, max_depth=args.depth, source_root=source_root)` 
- 完成标准: 所有新参数可正常使用，编排流程执行正确
- 验证: `python -m pytest tests/test_analyze_project.py -v`

---

**IMP-9: `harness/scripts/help.py` — 版本号更新和命令描述增强**

- 版本号 `v0.3` → `v0.3.1`
- `analyze_project.py` 描述追加: `(支持 --llm LLM增强 / --depth 目录深度控制 / --source-root 源码根指定)`
- 完成标准: `python harness/scripts/help.py` 输出包含 v0.3.1
- 验证: `python harness/scripts/help.py` 查看输出

---

### 测试任务 (-> Tester)

---

**TST-1: 测试源码根自动识别**

- 测试文件: `tests/test_analyze_project.py`
- 新增类 `TestSourceRootDetection`:
  1. `test_detect_source_root_with_init_py`: 构造 nested 目录结构（`back/python/paper_agent/` 含 `__init__.py`），验证检测到 `back/python/paper_agent`
  2. `test_detect_source_root_no_init_py`: 无 `__init__.py` 时退回到源码文件共同祖先
  3. `test_detect_source_root_given_none`: 所有文件在根目录，返回 `None`
  4. `test_source_root_cli_override`: `--source-root custom/path` 手动指定生效

---

**TST-2: 测试模块分组和依赖计算**

- 测试文件: `tests/test_analyze_project.py`
- 新增类 `TestModuleGrouping`:
  1. `test_group_modules_flat`: 单层目录下模块正确分组
  2. `test_group_modules_nested`: 嵌套目录按一级子目录分组
  3. `test_module_dependency_computed`: 模块 A 文件 import 模块 B 文件 → 依赖正确
  4. `test_stdlib_imports_filtered`: `import os`, `import json` 不出现在模块依赖中
  5. `test_rule_based_description`: `adapters/` + `*_adapter.py` → "适配器模块"

---

**TST-3: 测试深度控制和折叠显示**

- 测试文件: `tests/test_analyze_project.py`
- 新增类 `TestDepthControl`:
  1. `test_depth_default_three`: 默认 depth=3 只展开 3 层
  2. `test_depth_one_shallow`: `--depth 1` 只显示顶层目录
  3. `test_folded_same_type`: 同类型目录折叠为 "Python 源码目录，X 个文件"
  4. `test_folded_mixed_type`: 混合类型折叠为 "N 个子目录，M 个文件"
  5. `test_cli_depth_flag`: `--depth 2` 命令行参数生效

---

**TST-4: 测试 .env 加载和 API Key 引导**

- 测试文件: `tests/test_analyze_project.py`
- 新增类 `TestDotenvAndApiKey`:
  1. `test_load_dotenv_reads_file`: 创建 `.env`，验证环境变量被设置
  2. `test_load_dotenv_no_file`: 无 `.env` 文件不报错
  3. `test_load_dotenv_does_not_overwrite`: 已有环境变量不被 `.env` 覆盖
  4. `test_load_dotenv_ignores_comments`: `# 注释` 和空行被忽略
  5. `test_llm_without_key_prints_guidance`: `--llm` 但无 API Key 时 stderr 包含引导信息
  6. `test_llm_without_key_still_completes`: Key 缺失时分析仍正常完成（仅 LLM 跳过）
  7. `test_help_lists_env_vars`: `--help` 输出包含 `ANTHROPIC_API_KEY` 和 `.env` 说明

---

**TST-5: 测试 data-flow 空模板**

- 测试文件: `tests/test_analyze_project.py`
- 新增类 `TestDataFlowTemplate`:
  1. `test_data_flow_without_llm_shows_guidance`: 无 LLM 时 data-flow.md 包含 "LLM 未启用"
  2. `test_data_flow_without_llm_no_raw_imports`: 无 LLM 时不出现逐条 import 列表

---

**TST-6: 更新受影响的旧测试**

- `tests/test_analyze_project.py`:
  1. `TestCLIIntegration.test_help_output`: 确认新参数 `--depth`、`--source-root` 出现在帮助中
  2. `TestMapWriter.test_generate_data_flow_with_imports`: 数据流格式变更，断言改为检查引导模板
  3. `TestMapWriter.test_generate_data_flow_empty`: 断言改为检查 "LLM 未启用" 引导

---

## 3. 依赖关系

```
IMP-1 (版本号)     → 无依赖，可最先执行
IMP-2 (源码根检测)  → 无依赖
IMP-3 (深度控制)    → 无依赖
IMP-7 (.env/ApiKey) → 无依赖

IMP-4 (module-map)  → 依赖 IMP-2 (需要 source_root)
IMP-5 (data-flow)   → 依赖 IMP-2 (需要 source_root)

IMP-8 (CLI编排)     → 依赖 IMP-2, IMP-3, IMP-4, IMP-5, IMP-6, IMP-7 (所有模块级变更)
IMP-6 (generate_all) → 依赖 IMP-3, IMP-4, IMP-5 (需要新的函数签名)
IMP-9 (help.py)     → 依赖 IMP-8 (CLI 参数最终确定后更新描述)

TST-1..TST-5 (新测试) → 依赖对应 IMP 任务完成后
TST-6 (旧测试更新)     → 依赖 IMP-4, IMP-5, IMP-8 完成后

并行组:
  [IMP-1, IMP-2, IMP-3, IMP-7] → 可并行
  [IMP-4, IMP-5] → 可并行(需要在 IMP-2 之后)
  [IMP-6] → 需要在 IMP-3, IMP-4, IMP-5 之后
  [IMP-8] → 需要在 IMP-2..IMP-7 之后
  [IMP-9] → 需要在 IMP-8 之后

  [TST-1..TST-6] → 所有 IMP 完成后可并行执行
```

---

## 4. 风险点

| 风险 | 级别 | 缓解措施 |
| ---- | ---- | -------- |
| **源码根识别在非标准结构下不准** | 中 | 预留 `--source-root` 手动覆盖；自动识别失败降级到项目根的一级子目录；不崩溃 |
| **模块描述规则推断覆盖不全** | 低 | 兜底模板"包含 N 个文件的 XX 模块"，不会产生空描述 |
| **`.env` 文件解析不支持复杂语法**（多行值、export 前缀） | 低 | 只支持 `KEY=VALUE` 基本格式，在 --help 中明确说明格式要求 |
| **旧测试 test_generate_data_flow_with_imports 可能失败** | 中 | 该测试断言逐条 import 的存在性，需更新为新格式断言(TST-6) |
| **depth 参数默认为 3 可能在极深项目(>6 层)仍产生较大输出** | 低 | depth 参数可手动调整，未来可基于项目规模动态调整默认值 |
| **不引入第三方依赖约束** | 高 | `.env` 解析用纯标准库实现，不依赖 `python-dotenv`；不使用 `requests` 库（已有 `urllib`） |

---

## 5. 验证命令（全部 IMP 完成后）

```bash
# 结构完整性
python harness/scripts/check_structure.py

# 全部测试
python -m pytest tests/ -v

# 手动测试: 对真实项目运行分析
python harness/scripts/analyze_project.py <目标项目> --depth 3

# 检查输出质量: module-map 应为目录级(非文件级)、data-flow 应含引导模板、directory-map 应受深度控制
```
