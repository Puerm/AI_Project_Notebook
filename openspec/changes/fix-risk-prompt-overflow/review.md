# Review: fix-risk-prompt-overflow

**审查对象**: fix-risk-prompt-overflow IMP-1~7
**审查依据**: plan.md, spec.md, coding-rules.md, data-safety-rules.md, workflow-rules.md

## 通过项 (17/17)

| # | 任务 | 验证结果 |
| -- | ---- | ---- |
| 1 | IMP-1: `_call_llm` 返回元组 | 通过 |
| 2 | IMP-2: `domain_analyzer.py` 适配 | 通过 |
| 3 | IMP-2: `test_analyze_project.py` 断言同步 | 通过 |
| 4 | IMP-3: `filter_for_risk` 优先级排序+去重 | 通过 |
| 5 | IMP-4: 三个 filter 文件数上限 | 通过 |
| 6 | IMP-5: `format_files_for_llm` 新增 `max_tokens` | 通过 |
| 7 | IMP-5: 新增 `estimate_tokens()` | 通过 |
| 8 | IMP-6: 新增 `_get_model_context_limit()` | 通过 |
| 9 | IMP-6: 新增 `_compute_token_budget()` | 通过 |
| 10 | IMP-6: 三个 builder 新增 `config` 参数 | 通过 |
| 11 | IMP-6: 三个 analyze 函数传入 config | 通过 |
| 12 | IMP-6: HTTP 400 0 次重试 | 通过 |
| 13 | IMP-7: `analyze_project.py` 无需修改 | 通过 |
| 14 | module-map.md 更新 | 通过 |
| 15 | change-map.md 更新 | 通过 |
| 16 | 结构验证 52/52 PASS | 通过 |
| 17 | 单行 docstring | 通过 |

## 第三类：需求/spec 问题

| # | 问题 | 影响 |
| -- | ---- | ---- |
| 1 | 计划影响面评估遗漏了 `harness/scripts/diagnose_and_fix.py`（1处）和 `harness_deploy.py`（3处）的 `_call_llm` 调用点。Generator 已主动修复。 | 低，不阻塞合并 |

## 结论

**有条件通过** — 第三类问题影响低，不阻塞。剩余的 9 个 test_dimension_analyzer.py mock 适配由 Tester 处理。
