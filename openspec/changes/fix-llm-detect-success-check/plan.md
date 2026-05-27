# Plan: 修复 LLM 检测成功判断逻辑

## 1. 变更范围

### 需要修改的文件

| 文件 | 改动意图 |
| ---- | -------- |
| `harness/scripts/harness_deploy.py` | 修复 `_llm_detect_project` 异常信息丢失 + 修复 `detect_project` 中 focus_fields 模式成功判断条件错误 |

### 无需修改的文件

- `tests/test_harness_deploy.py` — 现有测试覆盖 `_detect_project_features`、`_adapt_workflow_content`、`_generate_adapted_project_yaml` 等函数，不涉及本次修改的 `_llm_detect_project` 和 `detect_project` 内部逻辑；新增测试在 TST- 任务中完成

## 2. 任务列表

### 实现任务 (→ Generator)

#### IMP-1: 增强 `_llm_detect_project` 失败时的错误输出

- **文件**: `harness/scripts/harness_deploy.py`，函数 `_llm_detect_project`（约 line 296-315）
- **完成标准**:
  1. API 调用异常（网络错误、超时等）时，异常信息打印到 stderr，格式 `[LLM] API 调用异常: {e}`
  2. API 返回空响应时，打印到 stderr，格式 `[LLM] API 返回空响应`
  3. JSON 解析失败时，异常信息打印到 stderr，格式 `[LLM] JSON 解析失败: {e}`
  4. 响应中未找到 JSON 对象时，打印到 stderr，格式 `[LLM] 响应中未找到 JSON 对象`
  5. 所有失败情况下 `_llm_detect_project` 仍返回 `None`（行为不变）
- **具体改动**:
  - Line 298: `except Exception:` → `except Exception as e:`，并 `print(f"  [LLM] API 调用异常: {e}", file=sys.stderr)`
  - Line 301-302 之间: 在 `if not response:` 块内增加 stderr 输出
  - Line 311-313: 在两个 JSON 相关失败分支增加 stderr 输出
- **验证命令**: `python harness/scripts/check_structure.py`

#### IMP-2: 修复 `detect_project` 中 focus_fields 模式的成功判断条件

- **文件**: `harness/scripts/harness_deploy.py`，函数 `detect_project`（约 line 336-433，重点 line 352-371 和 line 387-399）
- **完成标准**:
  1. 当使用 focus_fields 模式（有 baseline 且 `missing_fields` 非空）时，LLM 返回非空 dict → 输出 "LLM 检测成功"
  2. 完整模式（无 baseline）时，行为不变：`"languages" in llm_result` → 输出 "LLM 检测成功"
  3. focus_fields 模式 LLM 返回的 `domain`/`description`/`entry_point` 字段能被正确合并到结果中（不再因缺少 `languages` 字段而被丢弃）
  4. `result["source"]` 在 LLM 成功时设置为 `"llm"`
- **具体改动**:
  - 在 LLM 调用前后引入两个局部变量 `is_focus_mode: bool` 和 `llm_attempted: bool`
  - Line 366-371: 替换硬编码的 `"languages" in llm_result` 为模式感知的成功判断:
    ```python
    if is_focus_mode:
        llm_success = bool(llm_result and isinstance(llm_result, dict) and llm_result)
    else:
        llm_success = bool(llm_result and "languages" in llm_result)
    ```
    同时用 `llm_attempted` 替换不安全的 `missing_fields` 引用（避免 focus_fields 模式外使用未定义变量）
  - Line 387-399: 将 `if llm_result and llm_result.get("languages"):` 的外层条件拆开，`languages`/`framework` 合并仍保留在 `if llm_result.get("languages"):` 子块内，但 `domain`/`description`/`entry_point` 合并和 `source` 设置移到外层 `if llm_result:` 下，确保 focus_fields 模式的结果也能被正确合并
- **验证命令**: `python harness/scripts/check_structure.py` + `python -m pytest tests/test_harness_deploy.py -v`

### 测试任务 (→ Tester)

#### TST-1: 验证 `_llm_detect_project` 错误输出到 stderr

- **文件（新建或追加）**: `tests/test_harness_deploy.py`
- **覆盖功能点**:
  - mock `_call_llm` 抛异常 → 验证 stderr 包含 "API 调用异常"
  - mock `_call_llm` 返回空 → 验证 stderr 包含 "空响应"
  - mock `_call_llm` 返回非法 JSON → 验证 stderr 包含 "JSON 解析失败"
  - mock `_call_llm` 返回无 JSON 对象的文本 → 验证 stderr 包含 "未找到 JSON 对象"
- **技术手段**: `unittest.mock.patch` 替换 `app.analyzer.llm_assistant._call_llm`，使用 `capsys` 捕获 stderr

#### TST-2: 验证 `detect_project` focus_fields 模式的成功判断

- **文件（追加）**: `tests/test_harness_deploy.py`
- **覆盖功能点**:
  - mock `_check_llm_available` 返回 True + mock `_llm_detect_project` 返回 `{"domain": "Web", "description": "test", "entry_point": "main.py"}` + 提供 baseline → 验证 stdout 包含 "LLM 检测成功"，且结果中 `source` 为 `"llm"`
  - mock `_check_llm_available` 返回 True + mock `_llm_detect_project` 返回 `None` + 提供 baseline → 验证 stdout 包含 "LLM 检测失败，降级为静态检测"
  - 完整模式（无 baseline）+ mock 正常返回含 `languages` 的结果 → 验证行为不变（"LLM 检测成功"）
- **技术手段**: `unittest.mock.patch` 替换 `harness.scripts.harness_deploy._check_llm_available` 和 `harness.scripts.harness_deploy._llm_detect_project`，使用 `capsys` 捕获 stdout

## 3. 依赖关系

```
IMP-1  ──(无依赖，可独立执行)──▶  IMP-2
                                         │
                                         ▼
                                       TST-1, TST-2  (可并行)
```

- IMP-1 和 IMP-2 修改同一文件的不同函数，IMP-1 先执行可减少冲突风险
- TST-1 和 TST-2 互相独立，可并行执行
- TST-1/TST-2 依赖 IMP-1/IMP-2 全部完成后才能运行通过

## 4. 风险点

1. **`missing_fields` 变量作用域**: 原代码 line 369 在 `if not baseline or missing_fields:` 中使用 `missing_fields`，该变量仅在 `if baseline:` 分支内定义。虽然 Python 会因 `or` 短路而避免 NameError（baseline 为 None 时），但这仍是代码异味。IMP-2 引入 `llm_attempted` 替换此条件，消除了此隐患。

2. **focus_fields 返回格式不稳定**: LLM 在 focus_fields 模式下返回的 JSON 字段名取决于 prompt 中的描述。当前 prompt（line 270-283）指定了 `domain`、`description`、`entry_point` 三个字段名，与 result merging 中使用的 key 一致。但如果 LLM 返回额外字段或缺少某个字段，`isinstance(llm_result, dict) and llm_result` 仍会判定为成功，只是该字段不会被合并（因为已有静态检测结果兜底）。此风险已在验收标准中通过 `capsys` 检查 stdout 信息来覆盖。

3. **不修改 LLM API 调用本身**: `_call_llm` 的签名和返回值不变，仅在其调用方 `_llm_detect_project` 增加异常打印。`_call_llm` 的调用方式不受影响。

4. **编码规则约束**: 修改 `harness_deploy.py` 后需运行 `check_structure.py` 验证结构完整性，运行 `pytest tests/test_harness_deploy.py` 确保现有测试通过。
