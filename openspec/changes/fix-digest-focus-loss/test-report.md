## 测试报告

### 结论: 通过

所有测试执行通过，无需阻塞。

### 测试概况

- 全新用例: 179 (修复前: 144)
- 通过: 179
- 失败: 0
- 跳过: 0

### 失败详情

（无）

### 失败分类

（无）

### 原有测试修复

本轮修复了 8 个因 v0.5.1 签名变更导致的测试端错误：

| 测试用例 | 失败类型 | 修复方式 |
| ---- | ---- | ---- |
| test_valid_dir_with_cdigest_installed | 测试自身问题 | assert text > 0 改为 assert text == "" + assert files > 0 |
| test_prompt_contains_output_format_spec | 测试自身问题 | "5-20" 改为 "5-15" + 新增 sub_domains/[推测] 断言 |
| test_llm_path_writes_architecture_file | 测试自身问题 | 第一参数从 "code text" 改为 [{path, content}] 列表 |
| test_llm_call_fails_falls_back_to_degraded (arch) | 测试自身问题 | 同上 |
| test_llm_path_writes_stories_with_crossref | 测试自身问题 | 第一参数从 "code" 改为 [{path, content}] 列表 |
| test_llm_call_fails_falls_back_to_degraded (stories) | 测试自身问题 | 同上 |
| test_llm_path_writes_risk_with_crossrefs | 测试自身问题 | 第一参数从 "code" 改为 [{path, content}] 列表 |
| test_llm_call_fails_falls_back_to_degraded (risk) | 测试自身问题 | 同上 |

### 新增测试覆盖

| TST 任务 | 覆盖点 | 用例数 | 文件 |
| ---- | ---- | ---- | ---- |
| TST-1 | filter_for_architecture/user_stories/risk 筛选函数 | 16 | test_digest_collector.py |
| TST-2 | sub_domains 字段补齐/degraded/parse | 4 | test_domain_analyzer.py |
| TST-3 | 签名验证(filtered_files 无 digest_text) + 降级测试 | 9 | test_dimension_analyzer.py |
| TST-4 | --digest E2E (help聚焦描述/overview生成/analysis文件) | 4 | test_analyze_project.py |
| TST-5 | 回归验证 (非digest模式不受影响) | -- | 全部原有测试通过 |

### 覆盖情况

| 函数/模块 | 正常路径 | 边界测试 | 状态 |
| ---- | ---- | ---- | ---- |
| filter_for_architecture() | init.py/配置/入口/大文件筛选 | 空列表、小文件排除 | 通过 |
| filter_for_user_stories() | README/文档/路由/handler/测试筛选 | 空列表、无关文件排除 | 通过 |
| filter_for_risk() | 依赖/配置/env/脚本/错误关键词 | 空列表、无关文件排除 | 通过 |
| format_files_for_llm() | 文件列表格式化成 LLM 文本 | 空列表返回 "" | 通过 |
| collect_digest() | cdigest 可用时返回 files | cdigest 不可用/目录不存在 | 通过 |
| _normalize_result() | 补齐 sub_domains 默认值 | 已有 sub_domains 不覆盖 | 通过 |
| _degraded_domain_result() | sub_domains 字段存在 | -- | 通过 |
| _parse_domain_response() | 含 sub_domains 的 JSON 解析 | [推测] 标注保留 | 通过 |
| analyze_architecture() | filtered_files 列表调用降级 | 空列表降级、假 Key 不崩溃 | 通过 |
| analyze_user_stories() | filtered_files 列表调用降级 | 空列表降级、假 Key 不崩溃 | 通过 |
| analyze_risk() | filtered_files 列表调用降级 | 空列表降级、假 Key 不崩溃 | 通过 |
| analyze_project --digest --quiet | project-overview.md 生成 | cdigest 不可用时仍可用 | 通过 |
| analyze_project --digest | analysis/ 三份报告生成 | cdigest 可用时架构/故事/风险 | 通过 |
| 签名契约 | digest_text 参数已移除 | inspect.signature 验证 | 通过 |
| 非 digest 模式回归 | 所有 144 原有测试 | -- | 通过 |

### 回归检查

全部 144 个原有测试（包括 Scanner/Parser/Overview/LLMAssistant/ProgressiveOverview/CLIIntegration）均通过，非 digest 模式行为未受影响。
