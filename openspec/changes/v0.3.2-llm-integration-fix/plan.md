# Plan: v0.3.2 LLM 集成修复

## 1. 变更范围

### 需要修改的文件

| 文件 (完整路径) | 改动意图 |
| ---- | ---- |
| `app/analyzer/__init__.py` | 版本号 0.3.1 -> 0.3.2 |
| `app/analyzer/scanner.py` | `detect_source_root()` 替换为 `detect_source_roots()`，返回多个源码根列表 |
| `app/analyzer/overview.py` | `_detect_tech_stack()` 改为递归深搜索 (根目录起 3 层)；新增 `_gather_tech_features()` 收集技术特征供 LLM 上下文使用；`_infer_project_type()` 支持传入预收集的特征数据 |
| `app/analyzer/llm_assistant.py` | 新增 3 个 LLM 增强函数：`enhance_module_descriptions_batch()` (自适应批量模块描述)、`enhance_data_flow_llm()` (LLM 推断数据流)、`enhance_tech_stack_llm()` (LLM 推断技术栈/项目类型)；新增 `detect_entry_functions()` (硬编码规则检测入口函数，用于无 LLM 数据流降级) |
| `app/analyzer/map_writer.py` | `generate_module_map()` 表头新增"源码根"列；`_build_dir_table_section()` 支持源码根标注；`generate_data_flow()` 无 LLM 时接受入口函数列表生成降级列表；`generate_all()` 签名新增 `entry_functions` 参数 |
| `harness/scripts/analyze_project.py` | 编排逻辑重构：单源码根 -> 多源码根分组、`--llm` 时调用 LLM 增强三个维度 (模块描述/数据流/技术栈)、无 LLM 时调用 `detect_entry_functions()` 收集入口函数列表、结果结构中传递 `source_roots` 和 `entry_functions` |
| `harness/project-map/command-map.md` | 命令表 `analyze_project.py` 行版本号 v0.3.2，描述新增"多源码根" |

### 不需要新建的文件

本版本所有改动均为修改现有文件，无需新建。

## 2. 任务列表

### 实现任务 (-> Generator)

---

**IMP-1: 版本号更新**

- 文件: `app/analyzer/__init__.py`
- 内容: `__version__ = "0.3.2"`
- 完成标准: `python -c "from app.analyzer import __version__; print(__version__)"` 输出 `0.3.2`
- 验证: `python harness/scripts/check_structure.py`

---

**IMP-2: 多源码根检测 (scanner.py)**

- 文件: `app/analyzer/scanner.py`
- 内容: 新增 `detect_source_roots(target_path, files)` 函数，返回 `list[str]` (相对路径列表)
  - 算法: 
    1. 对每个 `.py` 文件，向上查找最近的 `__init__.py` 祖先目录，收集为 Python 包候选
    2. 对 JS/TS 文件，向上查找最近的包含 `package.json` 或 `tsconfig.json` 的目录，收集为 JS 候选
    3. 合并去重，按目录深度排序 (浅层优先)，过滤父子包含关系 (只保留顶层)
    4. 如果项目根目录本身包含 `__init__.py` 或 `package.json` 等标记文件，则项目根作为唯一个源码根
  - 保留旧 `detect_source_root()` 函数 (兼容性)，内部调用新函数取首个结果
- 完成标准: 对 BioTec 项目能返回 `["back/python/paper_agent", "front"]` 两个源码根；对 Notebook 自身返回 `["app/analyzer"]`
- 验证: `python -c "from app.analyzer.scanner import detect_source_roots; print(detect_source_roots('path/to/project', ['file1.py']))"`

---

**IMP-3: 技术栈深目录检测 (overview.py)**

- 文件: `app/analyzer/overview.py`
- 内容:
  1. `_detect_tech_stack(root_path)` 重写：从根目录递归 walk，最大深度 3 层 (或受限于 `EXCLUDE_DIRS`)，收集所有层级遇到的 `TECH_INDICATORS` 文件
  2. 新增 `_gather_tech_features(root_path)` 函数，返回 dict:
     - `indicator_files`: 检测到的特征文件列表 (如 `back/python/pyproject.toml`)
     - `python_deps`: 从 pyproject.toml 提取的依赖列表
     - `node_deps`: 从 package.json 提取的依赖列表
     - `dir_structure`: 顶层 2 级目录概要
  - 用于同时支持规则推断和 LLM 上下文
  3. `_infer_project_type()` 改为接受可选 `features` 参数 (预收集特征)，沿用现有逻辑
- 完成标准: BioTec 的 `pyproject.toml` (`back/python/`) 和 `tsconfig.json` (`front/`) 被检测到，技术栈输出 `["Python", "TypeScript", "Node.js"]`
- 验证: 对包含深层 pyproject.toml 的测试目录运行 `analyze_overview()`，输出 tech_stack 包含 "Python"

---

**IMP-4: LLM 模块描述自适应批量 (llm_assistant.py)**

- 文件: `app/analyzer/llm_assistant.py`
- 内容: 新增 `enhance_module_descriptions_batch(dir_modules, project_name, source_root)` 函数
  - 入参: `dir_modules` 列表 (每个含 `dir`, `dependencies`, `files`, `functions`, `classes`), `project_name`, `source_root`
  - 自适应批量: 模块数 <= 10 逐模块调 LLM；> 10 打包一批调 LLM (要求 LLM 返回 JSON 数组)
  - 每个模块传给 LLM 的上下文必须包含: 项目名 + 源码根 + 同级模块名列表 + 依赖关系 + 关键文件名 (前 5 个)
  - system prompt: "根据模块名、关键文件、同级模块关系、依赖关系，用 ≤30 字中文描述该模块的职责。禁止出现"包含 X 个文件"等模板废话。"
  - 返回: 与 `dir_modules` 等长的描述列表
  - LLM 调用失败时降级到模板返回
- 保留旧 `enhance_module_description()` 函数
- 完成标准: BioTec 的 adapters 模块描述从 "包含 X 个文件的 adapters 模块" 变为 "集成外部学术数据源(arXiv/PubMed/智汇雅)"
- 验证: 用 mock 或 .env 配置的 API Key 调用 `enhance_module_descriptions_batch()`，验证返回的描述不包含 "X 个文件"

---

**IMP-5: LLM 数据流推断 (llm_assistant.py)**

- 文件: `app/analyzer/llm_assistant.py`
- 内容: 新增 `enhance_data_flow_llm(entry_functions, dir_modules, module_deps, project_name)` 函数
  - 入参: `entry_functions` 列表 (每个含 `name`, `file`, `module_dir`), `dir_modules`, `module_deps`, `project_name`
  - 对每个入口函数构造上下文: 入口名 + 所在模块 + 模块依赖图 (简化版)
  - system prompt: "根据入口函数和模块依赖图，推断数据从入口到存储/输出的关键调用链。每步格式：入口 -> 模块A.函数 -> 模块B.函数 -> ... -> 输出/存储，标注所属模块。不完整时说明不确定部分。"
  - 返回: Markdown 格式的数据流文档内容
  - LLM 失败时降级返回 None (由调用方 fallback 到入口函数列表)
- 完成标准: BioTec 的 `build_parser` 入口生成 `build_parser -> cli.default_literature -> orchestrator.xxx -> adapters.xxx -> models.xxx -> (存储)` 格式的数据流
- 验证: 用已知入口函数列表 + 已知模块依赖图调用 `enhance_data_flow_llm()`，验证返回 Markdown 包含 `入口 ->` 格式的调用链

---

**IMP-6: LLM 技术栈推断 (llm_assistant.py)**

- 文件: `app/analyzer/llm_assistant.py`
- 内容: 新增 `enhance_tech_stack_llm(tech_features, rule_based_tech, rule_based_type)` 函数
  - 入参: `tech_features` (来自 `_gather_tech_features()`), `rule_based_tech` (规则检测的技术栈), `rule_based_type` (规则检测的项目类型)
  - 上下文: 特征文件路径 + 依赖列表 (package.json deps + pyproject.toml deps 摘要) + 目录结构概览
  - system prompt: "根据特征文件和依赖列表，判断项目的技术栈和项目类型。技术栈列出具体框架/库名。项目类型为 Web应用/CLI工具/库/全栈应用 + 简短说明。"
  - 返回: `{"tech_stack": [...], "project_type": "..."}`
  - LLM 失败时降级返回规则推断结果
- 完成标准: BioTec 技术栈输出 `["Python", "TypeScript", "Prisma", "Next.js"]` 或类似具体框架名，项目类型不再是 "通用项目"
- 验证: 用模拟 tech_features 调用 `enhance_tech_stack_llm()`，验证返回 dict 包含 `tech_stack` 和 `project_type` 两个键，且 tech_stack 包含具体框架名 (非 "通用")

---

**IMP-7: 无 LLM 数据流降级 — 入口函数检测 (llm_assistant.py)**

- 文件: `app/analyzer/llm_assistant.py`
- 内容: 新增 `detect_entry_functions(target_path, source_files, source_roots)` 函数
  - 硬编码规则: 
    - Python: 搜索文件内容匹配 `argparse.ArgumentParser` / `click.command()` / `click.group()` / `typer.run(` / `def main(` + `if __name__` 块
    - JS/TS: 搜索 `app.listen(` / `express()` / `fastify.listen(` / `commander.program` 等模式
  - 对每个匹配返回: `{"name": 函数名, "file": 相对路径, "module_dir": 所属模块目录}`
  - 仅搜索 `source_roots` 内的文件，避免扫描无关代码
- 完成标准: BioTec 无 LLM 时返回 `[{"name": "build_parser", "file": "back/python/paper_agent/cli/default_literature.py", "module_dir": "cli"}, ...]`
- 验证: 对 Notebook 自身调用 `detect_entry_functions()`, 验证检测到 `analyze_project.py` 的 `main()` 函数

---

**IMP-8: map_writer.py 适配 (map_writer.py)**

- 文件: `app/analyzer/map_writer.py`
- 内容:
  1. `_build_dir_table_section()` 表头新增 "源码根" 列: `| 源码根 | 模块路径 | 模块描述 | 主要函数/类 | 模块依赖 |`
  2. 模块行插入 source_root 作为第一列
  3. `generate_module_map()` 签名保持，内部 `dir_modules` 元素新增 `source_root` 字段
  4. `generate_data_flow()` 第三个参数改为 `entry_functions=None` (替换原 `llm_data_flow=None`)，`_generate_data_flow_template()` 重写:
     - 当 `entry_functions` 非空时: 列出所有检测到的入口函数 (表格: 函数名 / 文件 / 所属模块)，附说明引导用户手工追踪
     - 当 `entry_functions` 为空时: 保留当前 "未检测到入口函数" 提示
  5. `generate_all()` 签名新增 `entry_functions=None` 参数，透传给 `generate_data_flow()`
- 完成标准: module-map 新格式的表头含 "源码根"；无 LLM 时 data-flow.md 列出入口函数表格而非 "LLM 未启用"
- 验证: `python harness/scripts/check_structure.py`

---

**IMP-9: analyze_project.py 编排重构 (analyze_project.py)**

- 文件: `harness/scripts/analyze_project.py`
- 内容: 主流程重构 (替换现有 Step 1.5 ~ Step 4):
  1. Step 1.5 改为调用 `detect_source_roots()` 获得 `source_roots` 列表
  2. Step 2 之后新增 Step 2.5: 对每个 source_root 分别执行模块分组 + 依赖计算，结果合并为带 `source_root` 字段的 `dir_modules`
  3. Step 3 概览分析保持不变 (规则推断)，额外调用 `_gather_tech_features()` 收集特征
  4. Step 3.5 (LLM 增强段):
     - 如果 `--llm`:
       a. 对每个 source_root 调用 `enhance_module_descriptions_batch()` 增强模块描述
       b. 调用 `detect_entry_functions()` 获取入口函数列表
       c. 对入口函数列表调用 `enhance_data_flow_llm()` 生成数据流内容
       d. 调用 `enhance_tech_stack_llm()` 增强技术栈/项目类型
       e. 将 LLM 结果合并回 `overview_result` 和 `results`
     - 如果无 `--llm`:
       a. 调用 `detect_entry_functions()` 获取入口函数列表 (用于 data-flow 降级)
  5. Step 4 传递 `source_roots`, `entry_functions` 给 `generate_all()`
- 完成标准: 三个 LLM 增强点 (模块描述 / 数据流 / 技术栈) 全部在 `--llm` 时有调用；无 `--llm` 时 data-flow 列出入口函数
- 验证: `python harness/scripts/analyze_project.py . --llm --quiet` (需要 .env 配置) 正常完成；`python harness/scripts/analyze_project.py . --quiet` (无 --llm) 正常完成

---

### 测试任务 (-> Tester)

---

**TST-1: 多源码根检测测试**

- 文件: `tests/test_analyze_project.py` (新增或追加)
- 覆盖点:
  - 单一 Python 包的源码根检测 (如 Notebook 自身的 `app/analyzer`)
  - 多语言混合项目 (Python + JS/TS 分属不同目录) 的多源码根检测
  - 项目根即为源码根 (根目录有 `__init__.py` 或 `package.json`)
  - 空文件列表返回空列表
  - 父子包含关系去重 (子目录被父目录包含时只保留父)
- 验证: `python -m pytest tests/test_analyze_project.py -v -k "source_root"`

---

**TST-2: 深目录技术栈检测测试**

- 文件: `tests/test_analyze_project.py` (追加)
- 覆盖点:
  - pyproject.toml 在 2 层子目录下被检测到
  - package.json 在 3 层子目录下被检测到
  - go.mod / Cargo.toml 等其他指标文件被检测
  - 被排除目录 (node_modules, .git) 内的同名文件被正确跳过
- 验证: `python -m pytest tests/test_analyze_project.py -v -k "deep_tech"`

---

**TST-3: 入口函数检测 (无 LLM 数据流降级) 测试**

- 文件: `tests/test_analyze_project.py` (追加)
- 覆盖点:
  - Python `argparse.ArgumentParser` 检测
  - Python `click.command()` / `click.group()` 检测
  - Python `typer.run()` 检测
  - JS/TS `app.listen()` 检测
  - `if __name__ == "__main__": main()` 模式检测
  - 非入口文件 (未定义入口模式) 不产生误报
- 验证: `python -m pytest tests/test_analyze_project.py -v -k "entry_func"`

---

**TST-4: LLM 批量模块描述测试**

- 文件: `tests/test_llm_assistant.py` (新增或追加)
- 覆盖点:
  - 模块数 <= 10 时逐模块调用 `_call_llm` (mock LLM 响应，验证调用次数)
  - 模块数 > 10 时单次批量调用 (验证只调用 1 次)
  - LLM 失败时降级返回模板描述 (不抛异常)
  - 每个模块描述不包含 "X 个文件" 模板废话
  - 无 API Key 时返回模板 (不尝试网络请求)
- 验证: `python -m pytest tests/test_llm_assistant.py -v -k "batch_module"`

---

**TST-5: LLM 数据流推断测试**

- 文件: `tests/test_llm_assistant.py` (追加)
- 覆盖点:
  - 给定入口函数 + 模块依赖图，LLM 调用接收到完整上下文 (项目名、模块关系)
  - LLM 返回结果包含 "入口 ->" 格式的调用链
  - LLM 失败时返回 None (不抛异常)
- 验证: `python -m pytest tests/test_llm_assistant.py -v -k "data_flow"`

---

**TST-6: LLM 技术栈推断测试**

- 文件: `tests/test_llm_assistant.py` (追加)
- 覆盖点:
  - 给定特征文件 + 依赖列表，LLM 推断出具体框架名
  - LLM 失败时降级返回规则推断结果
  - 返回 dict 包含 `tech_stack` 和 `project_type` 两个键
- 验证: `python -m pytest tests/test_llm_assistant.py -v -k "tech_stack_llm"`

---

**TST-7: 端到端测试**

- 文件: `tests/test_analyze_project.py` (追加)
- 覆盖点:
  - `--llm --quiet` 模式对 Notebook 自身运行不报错 (需 .env 配置)
  - `--quiet` 模式 (无 LLM) 生成 data-flow.md 包含入口函数表格
  - module-map.md 表头包含 "源码根" 列
  - overview.md 版本号显示 v0.1 (由 analyze_project 自动生成)
- 验证: `python -m pytest tests/test_analyze_project.py -v -k "e2e"`

---

**TST-8: 全量回归测试**

- 文件: `tests/` (全部已有测试)
- 覆盖点: 所有已有测试 (`test_export_report.py`, `test_help.py`, `test_init_project.py`, `test_search_notes.py`) 保持通过
- 验证: `python -m pytest tests/ -v`

---

## 3. 依赖关系

```
IMP-1 (版本号) —— 无依赖，可最先执行

IMP-2 (多源码根) —— 无依赖
    |
    v
IMP-9 (编排重构) —— 依赖 IMP-2, IMP-3, IMP-4, IMP-5, IMP-6, IMP-7, IMP-8
    |
    v
IMP-3 (深目录检测) —— 无依赖
IMP-4 (LLM批量模块) —— 无依赖
IMP-5 (LLM数据流) —— 无依赖
IMP-6 (LLM技术栈) —— 依赖 IMP-3 (gather_tech_features)
IMP-7 (入口函数检测) —— 依赖 IMP-2 (source_roots 参数)
IMP-8 (map_writer适配) —— 依赖 IMP-4 (模块描述格式), IMP-7 (entry_functions 格式)

TST-1 ~ TST-7 依赖对应 IMP-2~IMP-7 完成
TST-8 依赖所有 IMP 任务完成
```

### 并行化建议

- **第一波 (并行)**: IMP-1, IMP-2, IMP-3
- **第二波 (并行)**: IMP-4, IMP-5, IMP-7, IMP-8 (IMP-6 在 IMP-3 完成后)
- **第三波**: IMP-9 (依赖所有 IMP-2~IMP-8)
- **第四波 (并行)**: TST-1 ~ TST-7
- **第五波**: TST-8

实际上 IMP-4, IMP-5, IMP-6, IMP-7 都在同一个文件 `llm_assistant.py`，理论上可以并行修改互不冲突的函数。但为避免合并冲突，建议一个开发者顺序执行。

## 4. 风险点

1. **多源码根检测精度**：`detect_source_roots()` 依赖 `__init__.py` 和 `package.json` 的位置推断，边界情况多 (项目根目录同时有 __init__.py 和子 package、父子目录同时是包)。需仔细处理去重逻辑。

2. **LLM token 消耗**：多源码根模块数可能翻倍 (BioTec: 2 个源码根 x 各 5-6 个模块 = 10-12 个)，自适应批量策略 (<=10 逐模块, >10 批处理) 需在 `max_tokens=256` 约束下工作。批处理 prompt 需要 LLM 返回结构化 JSON，解析需容错。

3. **入口函数检测正则精度**：`detect_entry_functions()` 使用正则匹配，覆盖 `argparse`/`click`/`typer`/`app.listen`/`express()`/`fastify.listen` 等模式，但正则可能误匹配注释中的代码或导入语句 (如 `import argparse`)。需区分 import 和调用。

4. **深目录技术栈检测性能**：递归 walk 3 层可能在大项目中遍历很多文件。需复用 `EXCLUDE_DIRS` 跳过 `node_modules` 等，且限制在源码根范围内搜索。

5. **LLM 响应格式不稳定**：批量模块描述要求 LLM 返回 JSON 数组，数据流要求返回 Markdown 调用链。LLM 可能返回不符合格式的内容，需要 `try/except` 处理并降级。

6. **`generate_data_flow()` 签名变更**：原参数 `llm_data_flow=None` 改为 `entry_functions=None`，需检查是否有外部调用方 (当前仅在 `generate_all()` 和 `analyze_project.py` 中调用，无外部)。

7. **module-map 表头变更**：从 4 列变为 5 列 (新增"源码根")，旧 `_parse_module_table_rows()` 解析逻辑需要适配新格式。`_build_dir_table_section()` 和 `_build_file_table_section()` 都需要传 `source_root` 信息。

8. **向后兼容**：`detect_source_roots()` 返回列表，但 `--source-root` CLI 参数接受单值。当用户手动指定 `--source-root` 时，应覆盖自动检测，`source_roots` 为 `[args.source_root]`。
