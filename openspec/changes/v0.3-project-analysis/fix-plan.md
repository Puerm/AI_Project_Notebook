# Fix Plan: v0.3 智能项目分析引擎 — 审查反馈修复

## 审查来源

基于 `recon.md` 预先标记的问题 与 plan.md 对比实际代码, 识别出以下第二类问题（实现偏差）。

## 问题列表

| # | 问题 | 严重程度 | 涉及文件 |
|---|------|---------|---------|
| D1 | scanner.py EXCLUDE_DIRS 缺少 `harness`，未与 init_project.py 对齐 | 中 | `app/analyzer/scanner.py` |
| D2 | init_project.py 部署的 command-map.md 模板缺少 `analyze_project.py` 命令 | 低 | `harness/scripts/init_project.py` |
| D3 | map_writer.py 合并策略过于简化: 全有或全无，非按段落增量合并 | 中 | `app/analyzer/map_writer.py` |

---

## 1. 变更范围

### 需要修改的文件

| 文件路径 | 改动意图 |
| -------- | -------- |
| `app/analyzer/scanner.py` | D1: EXCLUDE_DIRS 增加 `"harness"`，与 init_project.py 对齐 |
| `harness/scripts/init_project.py` | D2: `make_template_command_map()` 的 CLI 命令表追加 `analyze_project.py` 条目 |
| `app/analyzer/map_writer.py` | D3: 重构 `_merge_sections()` 为按段落合并；`generate_module_map()` 支持增量更新 |

---

## 2. 任务列表

### 实现任务 (IMP- → Generator)

---

**IMP-FIX-1: 修复 scanner.py EXCLUDE_DIRS 对齐**

- 文件: `app/analyzer/scanner.py`
- 改动: 第 5-8 行的 `EXCLUDE_DIRS` 集合增加 `"harness"` 元素
- 理由: `init_project.py` 的 EXCLUDE_DIRS 包含 `harness` 和 `.claude`（`.claude` 已被 scanner 的隐藏项跳过逻辑覆盖）。scanner 扫描当前 AI_Project_Notebook 项目自身时会递归进入 `harness/` 目录，导致 project-map 文件和 rules 文件被当作源码分析，产生噪音。
- 完成标准: `EXCLUDE_DIRS` 集合内容为 `{".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode", "dist", "build", "harness"}`
- 验证: `python -c "from app.analyzer.scanner import scan_directory; r = scan_directory('.'); print('EXCLUDE_DIRS' in str(r['stats'].get('excluded_dirs', [])) or 'harness' not in [f.split(os.sep)[0] for f in r['files']])"`

---

**IMP-FIX-2: 补全 init_project.py 部署模板的 analyze_project.py 命令**

- 文件: `harness/scripts/init_project.py`
- 改动: `make_template_command_map()` 函数（第 136-155 行）的 CLI 命令表追加一行:
  ```
  | `python harness/scripts/analyze_project.py <目标路径>` | 智能项目分析引擎 | `harness/scripts/analyze_project.py` |
  ```
  插入位置: `init_project.py` 行之后、`export_report.py` 行之前（按命令功能分组: 初始化类命令在前，分析类命令在后，报告类命令最后）
- 完成标准: 模板字符串中新增 analyze_project.py 条目
- 验证: `python -c "from harness.scripts.init_project import make_template_command_map; print('analyze_project.py' in make_template_command_map())"`

---

**IMP-FIX-3: 重构 map_writer.py 合并策略为按段落增量**

- 文件: `app/analyzer/map_writer.py`
- 改动:
  1. **重写 `_merge_sections()`**: 当前逻辑是"全文有 MANUAL_MARKER 即保留全文"。新逻辑应:
     - 将文件按 `## ` 标题分割为段落
     - 每个段落若包含 `<!-- MANUAL -->` 则保留该段落（从 existing 中取）
     - 每个段落若不包含 `<!-- MANUAL -->` 则用新内容替换该段落（从 new 中取）
     - 新内容中有而旧内容中没有的段落（新增标题）直接追加
  2. **增量更新 `generate_module_map()`**: 当前逻辑是全量生成表格。新逻辑应:
     - 读取已有 module-map.md（如果存在）
     - 提取旧表格中的模块行
     - 对于新增模块（file_path 不在旧表格中）→ 追加行
     - 对于已有模块（file_path 在旧表格中且该行无 `<!-- MANUAL -->` 标记）→ 更新描述/函数/类
     - 对于已有模块（file_path 在旧表格中且该行有 `<!-- MANUAL -->` 标记）→ 保留旧行
  3. `generate_overview()` / `generate_directory_map()` / `generate_data_flow()`: 三个函数调用改为传递 section_headers 参数给 `_merge_sections()`，以支持按标题段落合并
- 完成标准:
  - 首次生成: 4 个文件正常生成（无已有文件时与当前行为一致）
  - 二次生成: 已有文件中 `<!-- MANUAL -->` 标记的段落被保留，未标记段落被更新
  - module-map: 新增模块追加到表格末尾，已有非 MANUAL 模块更新，已有 MANUAL 模块保留
- 验证:
  - `python -c "from app.analyzer.map_writer import _merge_sections; old = '## A\n<!-- MANUAL -->\nkeep\n\n## B\nreplace me'; new = '## A\nnew a\n\n## B\nnew b'; r = _merge_sections(old, new, ['## A', '## B']); print('PASS' if 'keep' in r and 'new b' in r else 'FAIL')"`
  - `python harness/scripts/analyze_project.py . ` 运行两次，检查 `harness/project-map/` 下文件内容是否正确合并

---

### 测试任务 (TST- → Tester)

---

**TST-FIX-1: 验证 scanner EXCLUDE_DIRS 排除 `harness`**

- 测试文件: `tests/test_analyze_project.py`
- 覆盖点:
  - `scan_directory('.')` 返回的 `files` 列表中不包含任何 `harness/` 前缀的路径
  - `stats.excluded_dirs` 包含 `"harness"`
- 验证: `python -m pytest tests/test_analyze_project.py::ScannerTest -v -k "exclude"`

---

**TST-FIX-2: 验证 init_project 模板包含 analyze_project 命令**

- 测试文件: `tests/test_init_project.py`
- 覆盖点:
  - `make_template_command_map()` 返回内容包含 `analyze_project.py`
- 验证: `python -m pytest tests/test_init_project.py -v -k "command_map"`

---

**TST-FIX-3: 验证 map_writer 按段落合并**

- 测试文件: `tests/test_analyze_project.py`（MapWriterTest 类）
- 覆盖点:
  - `_merge_sections()`: MANUAL 段落保留、非 MANUAL 段落替换、新段落追加
  - `generate_module_map()`: 二次生成时新增模块追加、已有非 MANUAL 模块更新、已有 MANUAL 模块保留
  - 首次生成（无已有文件）正常输出
- 验证: `python -m pytest tests/test_analyze_project.py::MapWriterTest -v`

---

## 3. 依赖关系

```
IMP-FIX-1 (scanner EXCLUDE_DIRS)  ──→  可并行
IMP-FIX-2 (init_project 模板)     ──→  可并行
IMP-FIX-3 (map_writer 合并)       ──→  可并行

所有 3 个 IMP-FIX 任务无相互依赖，可并行执行。

TST-FIX-1 依赖 IMP-FIX-1 完成
TST-FIX-2 依赖 IMP-FIX-2 完成
TST-FIX-3 依赖 IMP-FIX-3 完成
```

推荐执行顺序: IMP-FIX-1, IMP-FIX-2, IMP-FIX-3 并行 → TST-FIX-1, TST-FIX-2, TST-FIX-3 并行

---

## 4. 风险点

| 风险 | 说明 | 应对 |
| ---- | ---- | ---- |
| `_merge_sections()` 按标题分割的边界情况 | Markdown 标题 `##` 可能出现在代码块内部，导致错误分割 | 实现时只对行首的 `## ` 进行分割（忽略缩进的），排除 code fence 内的标题 |
| module-map 增量更新中 `file_path` 匹配 | 模块表格中第一列是相对路径，需确保路径格式一致 | 统一使用 `os.path.relpath()` 格式，大小写敏感保留 |
| 混合模式: 部分段落有 MANUAL 标记、部分没有 | 合并后新旧段落交错可能导致内容重复或丢失 | `_merge_sections()` 实现时按标题逐段匹配，新内容中独有的标题直接追加 |
