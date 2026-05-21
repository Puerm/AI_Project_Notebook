# Fix Plan: v0.3.2 LLM Integration Fix

审查反馈修复计划。针对 3 个测试失败和 2 个多源码根场景下的实现偏差。

## 审查发现的问题

| 编号 | 问题 | 类型 | 严重程度 |
| ---- | ---- | ---- | -------- |
| R1 | `_get_llm_config()` 无条件加载 `.env`，导致测试环境 API Key 泄漏，`test_enhance_description_no_api_key` 失败 | 实现偏差 — 代码不可测试 | P0 (测试失败) |
| R2 | `_generate_data_flow_template()` 文本从 "LLM 未启用" 改为 "未检测到入口函数"，2 个测试断言未同步更新 | 测试偏差 — 断言过时 | P0 (测试失败) |
| R3 | `_get_module_dir()` 忽略 source_root 前缀，多源码根项目返回错误的 module_dir | 逻辑与 spec 不一致 — 多源码根模块归属错误 | P1 (功能偏差) |
| R4 | `_batch_individual()` / `_batch_single_call()` 对所有模块使用统一 source_root 标签，多源码根项目 LLM 上下文不准确 | 逻辑与 spec 不一致 — LLM 上下文错误 | P1 (功能偏差) |

---

## 1. 变更范围

### 需要修改的文件

| 文件 (完整路径) | 改动意图 |
| ---- | ---- |
| `app/analyzer/llm_assistant.py` | FIX-1: `_get_llm_config()` 和所有公开函数新增 `enable_dotenv` 参数；FIX-3: `_get_module_dir()` 支持传入 source_root 做前缀剥离；FIX-4: `_batch_individual()` / `_batch_single_call()` 从每个模块自身的 `source_root` 字段获取标签 |
| `tests/test_analyze_project.py` | FIX-1: `test_enhance_description_no_api_key` 传入 `enable_dotenv=False`；FIX-2: 2 个 data-flow 测试断言从 "LLM 未启用" 更新为 "未检测到入口函数" |

### 不需要新建的文件

所有变更为修改既有文件。

---

## 2. 任务列表

### 实现任务 (-> Generator)

---

**FIX-IMP-1: `.env` 加载可控化 (`llm_assistant.py`)**

- 文件: `app/analyzer/llm_assistant.py`
- 内容:
  1. `_get_llm_config(enable_dotenv=True)` 新增 `enable_dotenv` 参数，当 `enable_dotenv=False` 时跳过 `_load_dotenv(os.getcwd())` 调用
  2. 以下所有公开函数新增 `enable_dotenv=True` 关键字参数并透传给 `_get_llm_config()`：
     - `enhance_dir_description(dir_name, files, enable_dotenv=True)`
     - `enhance_module_description(module_name, functions, classes, enable_dotenv=True)`
     - `enhance_project_description(name, tech_stack, project_type, enable_dotenv=True)`
     - `enhance_description(text, context=None, enable_dotenv=True)`
     - `enhance_module_descriptions_batch(dir_modules, project_name, source_root, enable_dotenv=True)`
     - `enhance_data_flow_llm(entry_functions, dir_modules, module_deps, project_name, enable_dotenv=True)`
     - `enhance_tech_stack_llm(tech_features, rule_based_tech, rule_based_type, enable_dotenv=True)`
     - `check_api_key_available(enable_dotenv=True)`
  3. 所有内部调用处 (如 `enhance_module_descriptions_batch` 内部调用 `_get_llm_config`) 传递 `enable_dotenv`
- 完成标准: 测试 `test_enhance_description_no_api_key` 在传入 `enable_dotenv=False` 后通过
- 验证: `python -m pytest tests/test_analyze_project.py::TestLLMAssistant::test_enhance_description_no_api_key -v`

---

**FIX-IMP-2: `_get_module_dir()` 支持 source_root 前缀剥离 (`llm_assistant.py`)**

- 文件: `app/analyzer/llm_assistant.py`
- 内容:
  1. `_get_module_dir(file_path, source_root=None)` 新增 `source_root` 参数
  2. 若 `source_root` 非空且非 `"."`，先将 `file_path` 去除 `source_root` 前缀，再取剩余路径的第一级目录作为 module_dir
  3. 在 `detect_entry_functions()` 中，对每个文件先通过匹配找到其所属 source_root，再将 source_root 传入 `_get_module_dir()`
  4. 新增辅助函数 `_find_source_root_for_file(file_path, source_roots)` 按最长前缀匹配确定文件所属 source_root
- 完成标准: 对多源码根项目，`detect_entry_functions()` 返回的 `module_dir` 是相对于各 source_root 的目录而非相对于项目根
- 验证: 构造临时目录模拟 `back/python/paper_agent/cli/main.py` + source_root `back/python/paper_agent`，验证 module_dir 为 `cli` 而非 `back`

---

**FIX-IMP-3: 批量模块描述使用各模块自身 source_root (`llm_assistant.py`)**

- 文件: `app/analyzer/llm_assistant.py`
- 内容:
  1. `_batch_individual(dir_modules, project_name, source_root, config)` 中将 `sr_label = source_root or "(项目根)"` 改为 `sr_label = mod.get("source_root", source_root) or "(项目根)"`，从每个模块自身取 source_root
  2. `_batch_single_call(dir_modules, project_name, source_root, config)` 中同样改为按模块取 source_root 标签
  3. `enhance_module_descriptions_batch()` 函数签名保持不变 (保留 `source_root` 作为 fallback)
- 完成标准: 多源码根项目的 LLM 模块描述上下文标注正确的源码根
- 验证: 构造 2 个不同 source_root 的 dir_modules 调用 `_batch_individual()`，验证不同模块的 prompt 中源码根不同

---

### 测试任务 (-> Tester)

---

**FIX-TST-1: 更新 `test_enhance_description_no_api_key` 测试**

- 文件: `tests/test_analyze_project.py`
- 内容:
  1. 在 `enhance_description()` 调用处传入 `enable_dotenv=False`
  2. 保持原有断言不变 (`result["enhanced"] is False`, `result["source"] == "template"`)
- 覆盖点: 通过 `enable_dotenv=False` 禁用 `.env` 加载后，无 API Key 时正确降级到模板描述
- 验证: `python -m pytest tests/test_analyze_project.py::TestLLMAssistant::test_enhance_description_no_api_key -v`

---

**FIX-TST-2: 更新 data-flow 测试断言**

- 文件: `tests/test_analyze_project.py`
- 内容:
  1. `test_generate_data_flow_without_llm_shows_guidance`: 将 `assert "LLM 未启用" in content` 改为 `assert "未检测到入口函数" in content` (这是 v0.3.2 `_generate_data_flow_template()` 当 `entry_functions=None` 时输出的新文本)；保留 `assert "--llm" in content`
  2. `test_generate_data_flow_empty_shows_guidance`: 同上
- 覆盖点: 无 LLM 时 data-flow.md 显示正确的降级引导文本
- 验证: `python -m pytest tests/test_analyze_project.py::TestMapWriter::test_generate_data_flow_without_llm_shows_guidance tests/test_analyze_project.py::TestMapWriter::test_generate_data_flow_empty_shows_guidance -v`

---

## 3. 依赖关系

```
FIX-IMP-1 (.env 可控化) —— 无依赖
    |
    v
FIX-TST-1 (测试更新) —— 依赖 FIX-IMP-1

FIX-IMP-2 (_get_module_dir 修复) —— 无依赖
FIX-IMP-3 (source_root 标签修复) —— 无依赖

FIX-TST-2 (data-flow 断言更新) —— 无依赖 (纯测试修改)
```

### 并行化建议

- **第一波 (并行)**: FIX-IMP-1, FIX-IMP-2, FIX-IMP-3, FIX-TST-2
  - FIX-IMP-1/2/3 都在 `llm_assistant.py`，修改不同的函数，互不冲突
  - FIX-TST-2 只改测试文件，无代码依赖
- **第二波**: FIX-TST-1 (依赖 FIX-IMP-1 完成)

---

## 4. 风险点

1. **`enable_dotenv` 参数传递链长**：涉及 8 个公开函数签名变更。需确保所有调用处 (包括 `analyze_project.py` 中的调用) 保持向后兼容 (参数默认值为 True，现有调用无需修改)。

2. **`_get_module_dir` source_root 前缀剥离**：需处理路径分隔符差异 (Windows `\` vs POSIX `/`)。在比较前缀前统一标准化为 `/`。同时 `source_root = "."` 的情况不应剥离任何前缀。

3. **`_batch_individual` source_root fallback**：`mod.get("source_root", source_root)` 逻辑需确保当模块无 `source_root` 字段时 (如旧数据格式)，仍能使用函数参数 `source_root` 作为 fallback，不破坏单源码根场景。

4. **测试断言更新**：`test_generate_data_flow_without_llm_shows_guidance` 除了修改 "LLM 未启用" 断言，还需确认 `assert "--llm" in content` 仍然通过 (当前模板中包含该文字，已验证)。

5. **全量回归**：所有修改完成后必须运行 `python -m pytest tests/ -v` 确认 71 个测试全部通过 (+ 原有的 4 个警告可忽略)。同时运行 `python harness/scripts/check_structure.py`。
