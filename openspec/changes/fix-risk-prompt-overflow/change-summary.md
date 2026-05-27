# Change Summary: 修复维度分析 Prompt 溢出

日期: 2026-05-27 | 状态: 实现完成 (IMP-1~7)

## 完成的任务

| 任务 | 文件 | 状态 |
|------|------|------|
| IMP-1 | `app/analyzer/llm_assistant.py` — `_call_llm` 返回元组 | 完成 |
| IMP-2 | `app/analyzer/domain_analyzer.py` + `tests/test_analyze_project.py` — 适配 | 完成 |
| IMP-3 | `app/analyzer/digest_collector.py` — `filter_for_risk` 优先级排序+去重 | 完成 |
| IMP-4 | `app/analyzer/digest_collector.py` — 三个 filter 文件数上限 | 完成 |
| IMP-5 | `app/analyzer/digest_collector.py` — `format_files_for_llm` token 预算 | 完成 |
| IMP-6 | `app/analyzer/dimension_analyzer.py` — token 预算接入 + HTTP 400 不重试 | 完成 |
| IMP-7 | `app/analyze_project.py` — 确认无需修改 | 完成 |

## 新增公共函数

- `digest_collector.estimate_tokens(text) -> int` — token 估算
- `dimension_analyzer._get_model_context_limit(model_name) -> int` — 模型上下文窗口查询
- `dimension_analyzer._compute_token_budget(config) -> int` — token 预算计算

## 接口变更

- `_call_llm(...)` 返回值: `str | None` -> `tuple[str | None, dict | None]`
- `format_files_for_llm(files, max_tokens=None)` 新增可选参数
- `_build_architecture_prompt_from_files(... config=None)` 三个函数各新增 config 参数
- `format_digest_for_llm(... max_tokens=None)` 新增可选参数

## 验证结果

- `check_structure.py`: 52/52 PASS
- `test_analyze_project.py`: 全部 PASS
- `test_digest_collector.py`: 28/28 PASS
- `test_dimension_analyzer.py`: 19/27 PASS (8 个 LLM mock 测试需 Tester 适配元组返回值)

## 待 Tester 处理

- TST-1~5: 新增测试 (filter 排序/上限/token截断/HTTP400重试/context limit)
- 适配 `test_dimension_analyzer.py` 中 8 个 `_call_llm` mock 返回值为元组格式
