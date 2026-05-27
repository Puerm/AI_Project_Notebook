# Plan: 修复维度分析 Prompt 溢出

参考 spec: `openspec/specs/fix-risk-prompt-overflow.md`

> replan 日期: 2026-05-27 | 状态: 无 recon.md 阻塞问题，原计划验证通过，延续执行

---

## 1. 变更范围

### 需要修改的文件

| 文件 | 改动意图 | 对应 spec |
| ---- | -------- | --------- |
| `app/analyzer/llm_assistant.py` | `_call_llm` 返回值从 `str \| None` 改为元组 `(str \| None, dict \| None)`：成功时 `(text, None)`，HTTPError 时 `(None, {"status": code, "reason": reason})`，其他异常时 `(None, {"status": 0, "reason": str(e)})`，无 api_key 时 `(None, None)` 不变 | 3 节第 3 项 |
| `app/analyzer/domain_analyzer.py` | 行 32: `result = _call_llm(...)` 改为 `result, _ = _call_llm(...)`，保持原有降级行为不变 | 3 节第 3 项 |
| `app/analyzer/dimension_analyzer.py` | (a) 新增 `_get_model_context_limit()` + `_compute_token_budget()` 辅助函数；(b) 三个 `_build_*_prompt_from_files` 各新增 `config` 参数，调用 `format_files_for_llm` 时传入 token 预算；(c) `_call_llm_with_retry` 解包元组返回值，HTTP 400 时 0 次重试直接降级 | 3 节第 1、3 项 |
| `app/analyzer/digest_collector.py` | (a) `filter_for_risk` 增加优先级排序 + 去重逻辑；(b) 三个 filter 函数各加上限裁切（架构 100 / 用户故事 150 / 风险 200）；(c) `format_files_for_llm` 新增可选 `max_tokens` 参数 + `estimate_tokens` 辅助函数 | 3 节第 1、2 项 |
| `tests/test_analyze_project.py` | 行 559: `test_call_llm_no_key_returns_none` 适配元组返回值，断言改为 `assert result is None and err_info is None` | 回归覆盖 |
| `tests/test_digest_collector.py` | 新增测试：filter 优先级排序 + 去重、上限截断、`format_files_for_llm` token 预算截断行为 | 3 节第 1、2 项 |
| `tests/test_dimension_analyzer.py` | 新增测试：HTTP 400 不重试、正常错误仍重试、`_get_model_context_limit` 单元测试、`_compute_token_budget` 验证 | 3 节第 3 项 |

### 不需要修改的文件

- `app/analyze_project.py` — 三个分析函数内部已通过 `_check_llm_available` 获取 config，无需额外传递
- `app/analyzer/prompts/` — 不涉及
- `harness/` — 不涉及
- 非 digest 路径的 `analyze_project.py` 主体流程 — spec 明确排除

---

## 2. 任务列表

### 实现任务 (-> Generator)

#### IMP-1: `_call_llm` 返回值改为元组

- **文件**: `app/analyzer/llm_assistant.py` — `_call_llm` 函数
- **spec 依据**: 3 节第 3 项 "retry 跳过硬错误"的前置依赖
- **当前状态**: 行 56-115，返回 `str | None`
- **完成标准**:
  - 返回值从 `str | None` 变为 `tuple[str | None, dict | None]`
  - 成功时返回 `(response_text, None)`
  - HTTPError (行 93-100) 返回 `(None, {"status": e.code, "reason": e.reason})`
  - 其他异常 (行 101-104) 返回 `(None, {"status": 0, "reason": str(e)})`
  - 无 api_key (行 58-59) 返回 `(None, None)` — 行为不变，仅包装为元组
  - `silent` 参数行为不变
- **验证命令**: `python harness/scripts/check_structure.py`

#### IMP-2: 适配 `_call_llm` 调用方

- **文件**: `app/analyzer/domain_analyzer.py` (行 32), `tests/test_analyze_project.py` (行 559)
- **spec 依据**: 3 节第 3 项 — 向后兼容适配
- **当前状态**:
  - `domain_analyzer.py:32`: `result = _call_llm(...)` 后 `if result is None: return _degraded_domain_result(...)`
  - `test_analyze_project.py:559`: `result = _call_llm("system", "user", config)` 后 `assert result is None`
- **完成标准**:
  - `domain_analyzer.py`: `result = _call_llm(...)` 改为 `result, _ = _call_llm(...)`，其余逻辑不变
  - `test_analyze_project.py`: 改为 `result, err_info = _call_llm(...)`，断言改为 `assert result is None and err_info is None`
- **验证命令**: `python harness/scripts/check_structure.py` + `python -m pytest tests/test_analyze_project.py::TestAnalyzeProjectLLMIntegration::test_call_llm_no_key_returns_none -v`

#### IMP-3: `filter_for_risk` 增加优先级排序 + 去重

- **文件**: `app/analyzer/digest_collector.py` — `filter_for_risk` 函数 (行 214-254)
- **spec 依据**: 3 节第 2 项 "filter 文件数上限" + 4 节风险对策 "按文件优先级排序"
- **当前状态**: 行 214-254，顺序遍历 `preprocessed`，命中即 `result.append(f)` + `continue`，无排序无去重
- **完成标准**:
  - 两遍处理：先收集所有匹配文件并打优先级分，再排序
  - 优先级分（数值越小越优先）：依赖文件 (0) < 配置文件 (1) < 脚本文件 (2) < 错误处理路径关键词 (3) < 安全关键词内容匹配 (4)
  - 去重：同一文件命中多个条件时，以最高优先级（数值最小）为准，只保留一次
  - 同一优先级内按文件路径字典序稳定排序
  - 原匹配规则全部保留（依赖/配置/脚本/错误处理路径/安全关键词）
  - 函数签名不变，返回 `list[dict]`
- **验证命令**: `python -m pytest tests/test_digest_collector.py::TestFilterForRisk -v`

#### IMP-4: 三个 filter 函数增加文件数上限

- **文件**: `app/analyzer/digest_collector.py` — `filter_for_architecture` (行 143), `filter_for_user_stories` (行 177), `filter_for_risk` (行 214)
- **spec 依据**: 3 节第 2 项 "filter 文件数上限"
- **当前状态**: 三个函数均无上限，返回全部匹配结果
- **完成标准**:
  - `filter_for_architecture`: 上限 `MAX_ARCHITECTURE_FILES = 100`，超出截断到前 100
  - `filter_for_user_stories`: 上限 `MAX_USER_STORIES_FILES = 150`，超出截断到前 150
  - `filter_for_risk`: 上限 `MAX_RISK_FILES = 200`，超出截断到前 200（结合 IMP-3 的优先级排序）
  - 上限值定义为函数内具名常量
  - 被截断时 print warning 到 stderr: `[filter] {dimension}: {total} 文件超出上限 {max}，保留前 {max} 个`
  - 函数签名不变
- **验证命令**: `python -m pytest tests/test_digest_collector.py -v -k "TestFilterForArchitecture or TestFilterForUserStories or TestFilterForRisk"`

#### IMP-5: `format_files_for_llm` 增加 token 预算控制

- **文件**: `app/analyzer/digest_collector.py` — `format_files_for_llm` (行 133) + 新增辅助函数
- **spec 依据**: 3 节第 1 项 "prompt token 预算控制"
- **当前状态**: 行 133-140，逐文件拼接 `### File: {path}\n```\n{content}\n```\n`，无截断逻辑
- **完成标准**:
  - `format_files_for_llm(files, max_tokens=None)` 新增可选参数
  - 新增 `estimate_tokens(text: str) -> int`：使用 `len(text.encode("utf-8")) / 4` 上取整 + 10% 安全余量
  - 当 `max_tokens` 为 None 时，行为与当前完全一致
  - 当 `max_tokens` 非 None 时：
    - 预留 500 bytes 给截断标注
    - 逐文件估算 token，累计超出预算时停止
    - 在格式化文本末尾追加截断标注: `\n\n> [截断] 已省略 {N} 个文件：\n> - {path1}\n> - {path2}\n...`
  - 标注中列出全部被截断文件的路径
- **验证命令**: `python -m pytest tests/test_digest_collector.py::TestFormatFilesForLLM -v`

#### IMP-6: `dimension_analyzer.py` 接入 token 预算 + HTTP 400 不重试

- **文件**: `app/analyzer/dimension_analyzer.py`
- **spec 依据**: 3 节第 1 项 "prompt token 预算控制" + 3 节第 3 项 "retry 跳过硬错误"
- **当前状态**:
  - `_call_llm_with_retry` (行 70-93): 用 `result is not None` 判断，3 次指数退避
  - 三个 `_build_*_prompt_from_files` (行 33-67): 调用 `format_files_for_llm` 时不传预算参数
  - 无 `_get_model_context_limit` / `_compute_token_budget`
- **完成标准**:
  - 新增 `_get_model_context_limit(model_name: str) -> int`:
    - `gpt-4o-mini`/`gpt-4o` -> 128000, `claude-3-5-sonnet*`/`claude-3-opus*` -> 200000, `deepseek-*` -> 65536
    - 未知模型 -> 128000, 无 model 名 -> 128000
  - 新增 `_compute_token_budget(config: dict) -> int`:
    - `max(int(_get_model_context_limit(config["model"]) * 0.8), 16000)` — 保证 16000 token 下界
  - 三个 `_build_*_prompt_from_files` 各新增 `config` 参数，调用 `format_files_for_llm(filtered_files, max_tokens=budget)`
  - 调用链适配: `analyze_architecture` / `analyze_user_stories` / `analyze_risk` 内已有 `config`（来自 `_check_llm_available`），传入对应的 `_build_*_prompt_from_files`
  - `_call_llm_with_retry` 修改:
    - 解包 `result, error_info = _call_llm(...)`
    - `error_info` 存在且 `error_info.get("status") == 400` 时: print `[HTTP 400] 请求过大，跳过重试，降级处理`，返回 None
    - 其他 `result is None` 情况: 保持 3 次指数退避
- **验证命令**: `python harness/scripts/check_structure.py` + `python -m pytest tests/test_dimension_analyzer.py -v`

#### IMP-7: 确认 `analyze_project.py` 无需修改

- **文件**: `app/analyze_project.py` (行 296-343 digest 分支)
- **spec 依据**: 确认性质任务
- **当前状态验证**: 行 196 `available, config = _check_llm_available(enable_dotenv)` 在 `analyze_architecture` 内部执行；`analyze_user_stories` 和 `analyze_risk` 同理。config 在分析函数内部获取，IMP-6 的 token 预算计算可直接使用该 config，无需外部传入
- **完成标准**: 确认 `analyze_project.py` 无需修改
- **验证命令**: `python harness/scripts/check_structure.py`

---

### 测试任务 (-> Tester)

#### TST-1: `filter_for_risk` 优先级排序 + 去重

- **文件**: `tests/test_digest_collector.py` (追加到 `TestFilterForRisk`)
- **覆盖功能**:
  - 文件同时命中"配置文件"和"安全关键词"：仅保留一次，按配置优先级归类
  - 排序验证：依赖文件排在安全关键词匹配文件之前
  - 同一优先级内按路径字典序稳定排序

#### TST-2: filter 函数上限截断

- **文件**: `tests/test_digest_collector.py` (追加到 `TestFilterForArchitecture` / `TestFilterForUserStories` / `TestFilterForRisk`)
- **覆盖功能**:
  - architecture 101+ 文件 -> 返回不超过 100
  - user_stories 151+ 文件 -> 返回不超过 150
  - risk 201+ 文件 -> 返回不超过 200
  - 上限以内不截断（如 50 个全部保留）

#### TST-3: `format_files_for_llm` token 预算截断

- **文件**: `tests/test_digest_collector.py` (追加到 `TestFormatFilesForLLM`)
- **覆盖功能**:
  - `max_tokens=None` 不截断（回归）
  - `max_tokens` 足够时全部保留
  - `max_tokens` 不够时截断，输出末尾含 `[截断] 已省略 N 个文件` 标注
  - 标注列出被截断文件路径
  - `max_tokens=0` 或极小值时返回仅含标注的字符串

#### TST-4: `_call_llm_with_retry` HTTP 400 不重试

- **文件**: `tests/test_dimension_analyzer.py`
- **覆盖功能**:
  - mock `_call_llm` 返回 `(None, {"status": 400, "reason": "Bad Request"})` -> 0 次重试，直接返回 None
  - mock `_call_llm` 返回 `(None, {"status": 500, ...})` -> 重试 3 次
  - mock `_call_llm` 返回 `(None, {"status": 0, "reason": "timeout"})` -> 重试 3 次

#### TST-5: `_get_model_context_limit` 单元测试

- **文件**: `tests/test_dimension_analyzer.py`
- **覆盖功能**:
  - 已知模型返回正确 context window 大小
  - 未知模型返回默认 128000
  - `_compute_token_budget` 验证 80% 计算 + 16000 下界

---

## 3. 依赖关系

```
IMP-1 (_call_llm 返回元组)
 ├── IMP-2 (适配 domain_analyzer + 测试)
 └── IMP-6 (_call_llm_with_retry HTTP 400 检测)
                                    │
IMP-3 (filter_for_risk 排序) ──┬── IMP-4 (filter 上限)
                                │
IMP-5 (format_files_for_llm budget) ── IMP-6 (接入 budget)
                                │
IMP-7 (确认 analyze_project.py 无需修改) — 可并行
```

**推荐执行顺序**:
1. IMP-1 + IMP-2（`_call_llm` 返回值改造 + 适配）-> 验证通过
2. 并行: IMP-3 + IMP-4（filter 改造）+ IMP-5（format 改造）
3. IMP-6（集成: retry + budget 接入）
4. IMP-7（确认）

**测试任务**: TST-1/2/3 依赖 IMP-3/4/5，TST-4/5 依赖 IMP-6。所有 TST 可并行执行。

---

## 4. 风险点

1. **`_call_llm` 返回类型变更影响面**: 已确认仅 2 个 app 调用点 (`domain_analyzer.py:32`、`_call_llm_with_retry:76`) + 1 个测试调用点 (`test_analyze_project.py:559`)。无其他调用方。

2. **token 估算精度**: 4 字节/token 粗略估算 + 10% 安全余量。估算偏多时提前截断，最多浪费少量上下文窗口；估算偏少时可能仍溢出，但 `filter_for_risk` 上限 200 + 其他上限已大幅降低风险。

3. **filter 上限值**: 架构 100 / 用户故事 150 / 风险 200 是 spec 建议值。若后续反馈某维度频繁截断丢失关键文件，可调高或配置化。

4. **`_get_model_context_limit` 维护**: 硬编码映射表，未知模型回退 128000 是保守安全策略。`deepseek-*` 的 65536 * 0.8 = 52428，已高于 16000 下界，不会触发下界保护。

5. **截断标注 token 占用**: IMP-5 预留 500 bytes 给标注文本，避免标注导致二次溢出。

6. **编码规则合规**:
   - 修改所有文件后必须运行 `python harness/scripts/check_structure.py` (coding-rules 第 8 条)
   - 新增公开函数后更新 `harness/project-map/module-map.md` (coding-rules 第 7 条)
   - 新增函数需单行 docstring (coding-rules 第 14 条)
