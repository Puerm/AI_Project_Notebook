# Test Report: CodeGraph 集成

> 对应 spec: `openspec/specs/codegraph-integration.md`
> 对应 plan: `openspec/changes/codegraph-integration/plan.md`
> 测试时间: 2026-05-26

---

## 结论: 通过

所有 42 个新增测试用例全部通过，未发现代码 bug，无需阻塞工作流。

---

## 测试概况

- 新增用例: 42
- 通过: 42
- 失败: 0
- 跳过: 0

| 任务 | 测试文件 | 用例数 | 通过 | 失败 |
| ---- | ---- | ---- | ---- | ---- |
| TST-1: codegraph.py 单元测试 | `tests/test_codegraph.py` | 28 | 28 | 0 |
| TST-2: CLI 集成测试 | `tests/test_analyze_project.py` (新增 8 个) | 8 | 8 | 0 |
| TST-3: tool-use LLM 测试 | `tests/test_codegraph.py` | 6 | 6 | 0 |

---

## 失败详情

（无失败）

---

## 失败分类

（无失败）

---

## 覆盖情况

### TST-1: `app/analyzer/codegraph.py` 模块

| 函数 | 正常路径 | 边界测试 | 状态 |
| ---- | ---- | ---- | ---- |
| `detect_codegraph_db` | db 存在返回路径 | 无 db 返回 None；.codegraph/ 存在但无 db 返回 None；非目录路径返回 None；文件路径返回 None | PASS |
| `connect_codegraph_db` | 返回 Connection，row_factory 为 Row | 只读连接拒绝写入；无效路径抛出异常 | PASS |
| `extract_schema_summary` | 提取表名、列名、行数、索引、CREATE TABLE | 空 db 返回空列表不崩溃；含 language 列的表提取语言分布 | PASS |
| `execute_query` | 返回 list[dict]；WHERE 过滤；空结果返回 [] | INSERT/UPDATE/DELETE/DROP 被拒绝(ValueError)；多语句注入被拒绝；前导空白+小写 select 正常；超过 max_rows 截断并标注 | PASS |
| `format_schema_for_llm` | 输出 Markdown 含表名/列名/索引/语言分布 | 空 schema 不崩溃；无索引不崩溃；row_count=None 显示"未知"；无语言统计不崩溃 | PASS |

### TST-2: CLI `--codegraph` 集成

| 功能点 | 覆盖 | 状态 |
| ---- | ---- | ---- |
| `--help` 含 `--codegraph` 说明 | `test_help_output_contains_codegraph` | PASS |
| `--digest --help` 同时含 `--codegraph` | `test_codegraph_help_with_digest` | PASS |
| 无 `.codegraph/` 降级提示 | `test_no_codegraph_dir_outputs_guidance` | PASS |
| `--codegraph --quiet` 安静降级 | `test_no_codegraph_dir_quiet_silent` | PASS |
| 降级后仍生成 project-overview.md | `test_codegraph_degraded_still_generates_overview` | PASS |
| `--digest --codegraph --quiet` 组合不冲突 | `test_digest_codegraph_quiet_exits_zero` | PASS |
| 未启用 `--codegraph` 默认模式回归 | `test_no_codegraph_flag_default_mode_still_works` | PASS |
| 未启用 `--codegraph` digest 模式回归 | `test_no_codegraph_flag_digest_mode_still_works` | PASS |

### TST-3: `_call_llm_with_tools` tool-use LLM

| 功能点 | 覆盖 | 状态 |
| ---- | ---- | ---- |
| 无 API Key 返回 None | `test_no_api_key_returns_none` | PASS |
| OpenAI 格式 tool_calls 解析 + handler 调用 | `test_openai_tool_handler_called_with_correct_args` | PASS |
| Anthropic 格式 tool_use 解析 + handler 调用 | `test_anthropic_tool_handler_called_with_correct_args` | PASS |
| max_rounds 到达后终止 | `test_max_rounds_reached_terminates_and_returns_text` | PASS |
| tool_handler 异常被捕获不中断循环 | `test_tool_handler_exception_caught_continues_loop` | PASS |
| 空 arguments 参数正常传递 | `test_tool_handler_receives_empty_arguments_defaults` | PASS |

---

## 回归检查

现有测试仍然通过：

| 测试 | 说明 | 状态 |
| ---- | ---- | ---- |
| `TestCLIIntegration::test_help_output` | 原有 help 输出检查 | PASS |
| `TestCLIIntegration::test_digest_quiet_mode_exits_zero` | digest 安静模式 | PASS |
| `TestDigestCLIE2E::test_non_digest_mode_still_works_regression` | 非 digest 模式回归 | PASS |

---

## 附加说明

1. `connect_codegraph_db` 在 Windows 上的 URI 格式 (`file:C:\path?mode=ro`) 经测试验证正常工作，sqlite3 能正确解析包含盘符的绝对路径。
2. `_call_llm_with_tools` 的 mock 测试使用内存模拟 LLM 响应，未执行真实 API 调用。函数签名（`tool_handler(tool_name, arguments) -> str`）与实际使用一致。
3. CLI 集成测试使用子进程方式运行 `analyze_project.py`，通过假 API Key + 不可达端点验证降级路径。这些测试耗时较长（每项约 12s，因 LLM 调用超时），但全面覆盖了降级兼容场景。
4. 所有新增参数均为带默认值的可选参数（`codegraph_context=None`），未启用 `--codegraph` 时行为与现有版本完全一致，回归测试已确认。
