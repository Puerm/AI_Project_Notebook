# 变更摘要: 修复 LLM 检测成功判断逻辑

## 修改文件

`harness/scripts/harness_deploy.py` (1 文件, 2 处改动)

## IMP-1: `_llm_detect_project` 增强错误输出

4 个异常分支增加 stderr 输出 (line 298-315):

| 异常场景 | stderr 格式 |
|----------|-------------|
| API 调用异常 | `[LLM] API 调用异常: {e}` |
| 返回空响应 | `[LLM] API 返回空响应` |
| JSON 解析失败 | `[LLM] JSON 解析失败: {e}` |
| 未找到 JSON | `[LLM] 响应中未找到 JSON 对象` |

所有分支仍返回 `None`，行为不变。

## IMP-2: `detect_project` focus_fields 模式成功判断修复

- 引入 `is_focus_mode` / `llm_attempted` 两个局部变量，消除 `missing_fields` 未定义引用隐患
- focus 模式: `llm_success = bool(llm_result and isinstance(llm_result, dict) and llm_result)`
- 完整模式: `llm_success = bool(llm_result and "languages" in llm_result)` (行为不变)
- Result merging: `languages`/`framework` 合并在 `llm_result.get("languages")` 子块，`domain`/`description`/`entry_point`/`source` 提升到 `llm_result` 外层，确保 focus_fields 结果正确合并

## 验证

- `check_structure.py`: 52/52 PASS
- `pytest tests/test_harness_deploy.py`: 55/55 PASS (零回归)
