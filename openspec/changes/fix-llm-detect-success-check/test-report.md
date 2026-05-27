# 测试报告: 修复 LLM 检测成功判断逻辑

## 结论: 通过

## 测试概况

- 新增用例: 9
- 通过: 64
- 失败: 0
- 跳过: 0

## 新增测试详情

### TST-1: `_llm_detect_project` 错误输出到 stderr (4 个用例)

| 用例 | 场景 | 结果 |
| ---- | ---- | ---- |
| `test_api_exception_prints_to_stderr` | mock `_call_llm` 抛 ConnectionError | PASS |
| `test_empty_response_prints_to_stderr` | mock `_call_llm` 返回空字符串 | PASS |
| `test_json_parse_error_prints_to_stderr` | mock `_call_llm` 返回非法 JSON | PASS |
| `test_no_json_object_prints_to_stderr` | mock `_call_llm` 返回无花括号文本 | PASS |

所有 4 个场景验证了: (a) stderr 包含对应错误信息, (b) 函数返回 None。

### TST-2: `detect_project` focus_fields 模式成功判断 (5 个用例)

| 用例 | 场景 | 结果 |
| ---- | ---- | ---- |
| `test_focus_mode_llm_success` | baseline + focus_fields, LLM 返回 `{domain, description, entry_point}` → "LLM 检测成功", source="llm", 字段正确合并 | PASS |
| `test_focus_mode_llm_failure` | baseline + focus_fields, LLM 返回 None → "LLM 检测失败，降级为静态检测" | PASS |
| `test_full_mode_llm_success` | 无 baseline, LLM 返回含 `languages` 的完整结果 → "LLM 检测成功" (行为不变) | PASS |
| `test_full_mode_llm_failure` | 无 baseline, LLM 返回 None → "LLM 检测失败" (行为不变) | PASS |
| `test_focus_mode_llm_success_reuses_baseline` | baseline 已有字段 (project_name/framework) 不被 LLM 返回的 focus_fields 结果覆盖 | PASS |

## 覆盖情况

| 函数/模块 | 正常路径 | 边界测试 | 状态 |
| ---- | ---- | ---- | ---- |
| `_llm_detect_project` (IMP-1) | -- | 4 个异常分支全部覆盖 (API异常/空响应/JSON解析失败/无JSON对象) | PASS |
| `detect_project` focus 模式 (IMP-2) | focus 成功 + 完整模式成功 = 2 | focus 失败 + 完整模式失败 + baseline 字段保护 = 3 | PASS |

## 回归检查

55 个已有测试全部通过，零回归。

## 失败详情

无失败。
