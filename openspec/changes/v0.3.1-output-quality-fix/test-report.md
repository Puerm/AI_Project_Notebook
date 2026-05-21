# Test Report: v0.3.1 Output Quality Fix

## 测试概况

- 新增用例: 0 (本次仅修复旧测试)
- 通过: 51
- 失败: 0
- 跳过: 0

## 修复的测试 (TST-6)

| 测试用例 | 修复原因 | 修改内容 |
| ---- | ---- | ---- |
| `test_generate_data_flow_with_imports` | data-flow 输出格式已变：不再逐条列出 import，改为 LLM 引导模板 | 重命名为 `test_generate_data_flow_without_llm_shows_guidance`，断言改为检查 `LLM 未启用` 和 `--llm` 引导信息，确认不含 `main.py` 即无逐条 import |
| `test_generate_data_flow_empty` | 同上 | 重命名为 `test_generate_data_flow_empty_shows_guidance`，断言改为检查 `LLM 未启用` 和 `--llm` |
| `test_help_output` | `--no-llm` 参数已移除 | 移除 `--no-llm` 断言，新增 `--depth`、`--source-root`、`ANTHROPIC_API_KEY`、`.env` 的断言 |
| `test_valid_project_generates_files` | 调用时传入已移除的 `--no-llm` 参数导致 argparse 报错 | 移除 `--no-llm` 参数传递，改用默认行为 |

## 覆盖情况

| 模块 | 正常路径 | 边界测试 | 状态 |
| ---- | ---- | ---- | ---- |
| scanner.py | 6 | 0 | PASS |
| parser.py | 12 | 0 | PASS |
| overview.py | 10 | 0 | PASS |
| llm_assistant.py | 7 | 0 | PASS |
| map_writer.py (data-flow) | 2 | 0 | PASS (已修复) |
| map_writer.py (其他) | 5 | 0 | PASS |
| CLI 集成 | 9 | 0 | PASS (已修复) |

## 回归检查

修复前通过的 47 个测试全部仍然通过。4 个旧测试更新后也全部通过。总计 51/51 PASS。
