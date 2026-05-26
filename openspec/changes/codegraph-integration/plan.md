# Plan: CodeGraph 集成 — 图谱增强项目分析

> 对应 spec: `openspec/specs/codegraph-integration.md`
> 生成时间: 2026-05-26

---

## 1. 变更范围

### 需要新增的文件

| 文件 (完整路径) | 改动意图 |
| ---- | ---- |
| `app/analyzer/codegraph.py` | CodeGraph 集成核心模块。提供数据库检测、Schema 提取、只读 SQL 查询执行、Schema 格式化等功能。参考 spec 第 3 节"数据库检测" + "Schema 提取" + "多轮查询交互"。 |
| `tests/test_codegraph.py` | codegraph.py 模块的独立单元测试，覆盖数据库检测、Schema 提取、查询执行、SQL 注入防护、空数据库处理。 |

### 需要修改的文件

| 文件 (完整路径) | 改动意图 |
| ---- | ---- |
| `app/analyze_project.py` | 新增 `--codegraph` CLI 参数及 CodeGraph 探索阶段流程。检测 db -> 提取 schema -> LLM tool-use 多轮探索 -> 将探索结果注入 domain_analyzer 和 dimension_analyzer 的 prompt 上下文。参考 spec 第 3 节"数据库检测" + "全产出增强" + "降级兼容"。 |
| `app/analyzer/llm_assistant.py` | 新增 `_call_llm_with_tools()` 函数，支持 function calling / tool use 模式。兼容 Anthropic Messages API 和 OpenAI Chat Completions API 的 tool 调用格式。支持多轮对话循环（最大 5 轮）。参考 spec 第 4 节"已决: 多轮交互实现——使用 tool use（函数调用）"。 |
| `app/analyzer/domain_analyzer.py` | `analyze_business_domains()` 新增可选参数 `codegraph_context: str = None`。当传入非空上下文时，追加到 LLM prompt 末尾作为 CodeGraph 发现数据源。参考 spec 第 3 节"全产出增强 — project-map"。 |
| `app/analyzer/dimension_analyzer.py` | 三个分析函数 (`analyze_architecture` / `analyze_user_stories` / `analyze_risk`) 各新增可选参数 `codegraph_context: str = None`。当传入非空上下文时，追加到对应 prompt builder 生成的 prompt 末尾。参考 spec 第 3 节"全产出增强 — analysis 三个维度文档"。 |

### 需要更新的项目地图文件

| 文件 (完整路径) | 改动意图 |
| ---- | ---- |
| `harness/project-map/module-map.md` | 新增 `app/analyzer/codegraph.py` 模块登记行，更新 `app/analyzer/llm_assistant.py` 和 `app/analyze_project.py` 的函数列表。 |
| `harness/project-map/directory-map.md` | 在 `app/analyzer/` 下新增 `codegraph.py` 条目。 |
| `harness/project-map/command-map.md` | 更新 `analyze_project.py` 命令行说明，补充 `--codegraph` 参数。 |
| `harness/project-map/data-flow.md` | 新增 CodeGraph 增强分析流水线数据流图。 |

---

## 2. 任务列表

### 实现任务 (-> Generator)

---

**IMP-1: 新建 `app/analyzer/codegraph.py` — CodeGraph 集成核心模块**

- 参考 spec: 第 3 节 "数据库检测" + "Schema 提取" + "多轮查询交互"
- 完成标准:
  - 函数 `detect_codegraph_db(target_path: str) -> Optional[str]`: 检查 `<target_path>/.codegraph/codegraph.db` 是否存在，返回 db 路径或 None
  - 函数 `connect_codegraph_db(db_path: str) -> sqlite3.Connection`: 以只读模式 (`uri=True`, `mode=ro`) 打开 SQLite 连接
  - 函数 `extract_schema_summary(conn: sqlite3.Connection) -> dict`: 读取 `sqlite_master` 获取所有表名和 CREATE TABLE SQL；对每个表执行 `SELECT COUNT(*)` 获取行数；尝试按语言/文件扩展名列统计分布；提取索引信息。返回结构化 dict
  - 函数 `execute_query(conn: sqlite3.Connection, sql: str) -> list[dict]`: 验证 SQL 必须以 `SELECT` 开头（大小写不敏感），拒绝所有非 SELECT 语句；执行查询并以 `[{col1: val1, ...}, ...]` 列表格式返回结果；对结果行数设上限（默认 200 行），超出时截断并在末尾标注
  - 函数 `format_schema_for_llm(schema: dict) -> str`: 将 schema 摘要格式化为 Markdown 风格的文本，供 LLM 读取
  - 模块文件头含用途描述注释（coding-rule 4）
- 验证命令: `python -c "from app.analyzer.codegraph import detect_codegraph_db, extract_schema_summary, execute_query, format_schema_for_llm; print('import OK')"`

---

**IMP-2: 扩展 `app/analyzer/llm_assistant.py` — 新增 tool-use LLM 调用函数**

- 参考 spec: 第 4 节 "已决: 多轮交互实现——使用 tool use（函数调用）"
- 完成标准:
  - 新增 `_call_llm_with_tools(system_prompt, user_prompt, tools_def, tool_handler, config, max_rounds=5, timeout=120) -> Optional[str]` 函数
  - 支持 Anthropic Messages API 的 `tools` 参数格式，解析响应中的 `tool_use` content block
  - 支持 OpenAI Chat Completions API 的 `tools` 参数格式，解析响应中的 `tool_calls`
  - 多轮循环: 发送 user_prompt -> 收到 tool_call 请求 -> 调用 tool_handler 获取结果 -> 追加 assistant(tool_use) + tool_result 消息 -> 继续直到 LLM 返回纯文本或达到 max_rounds
  - tool_handler 签名: `tool_handler(tool_name: str, arguments: dict) -> str`，返回工具执行结果字符串
  - 达到 max_rounds 时返回最后一轮累积的文本结果
  - LLM 不可用时返回 None（与现有 `_call_llm` 一致）
- 验证命令: `python -c "from app.analyzer.llm_assistant import _call_llm_with_tools; print('import OK')"`

---

**IMP-3: 修改 `app/analyze_project.py` — 添加 --codegraph 选项和探索阶段**

- 参考 spec: 第 3 节全部 5 个功能点
- 完成标准:
  - `argparse` 新增 `--codegraph` 参数 (`action="store_true"`)
  - 非 digest 模式：Step 1(引导文件) -> Step 1.5(CodeGraph 检测+探索，若启用) -> Step 2(domain analysis 含 CodeGraph 上下文) -> Step 3(map writer)
  - digest 模式：Step 1-3 不变 -> Step 3.5(CodeGraph 检测+探索，若启用) -> Step 4(digest 收集) -> Step 5-7(三维度分析，每个 LLM 调用注入 CodeGraph 上下文)
  - 数据库检测逻辑：调用 `detect_codegraph_db(target_path)`。若 db 不存在，打印指导信息（"未检测到 .codegraph/codegraph.db，建议安装 CodeGraph 并运行索引后重试"），继续后续分析流程（降级兼容）
  - CodeGraph 探索阶段：连接 db -> 提取 schema -> 调用 `_call_llm_with_tools()` 传入 schema 格式文本 + `query_codegraph` tool 定义 -> 收集 LLM 探索结果文本
  - 将探索结果作为 `codegraph_context` 字符串传递给 `analyze_business_domains()` 和三个 dimension analyze 函数
  - `--codegraph` 未启用时行为与现有版本完全一致，不引入任何额外开销
  - 在 `--help` 输出中显示 `--codegraph` 参数说明
- 验证命令: `python app/analyze_project.py --help | findstr "codegraph"`

---

**IMP-4: 修改 `app/analyzer/domain_analyzer.py` — domain 分析接受 CodeGraph 上下文**

- 参考 spec: 第 3 节 "全产出增强 — project-map"
- 完成标准:
  - `analyze_business_domains()` 签名新增可选参数 `codegraph_context: str = None`
  - 当 `codegraph_context` 非空时，在 `_build_domain_analysis_prompt()` 生成的 prompt 末尾追加 `# CodeGraph 符号知识图谱发现\n\n{codegraph_context}\n\n请综合以上图谱发现优化业务板块识别，特别是调用关系/模块依赖信息。`
  - 当 `codegraph_context` 为 None 时行为与现有版本完全一致
- 验证命令: `python -c "from app.analyzer.domain_analyzer import analyze_business_domains; import inspect; sig = inspect.signature(analyze_business_domains); print(sig)"`

---

**IMP-5: 修改 `app/analyzer/dimension_analyzer.py` — 三维度分析接受 CodeGraph 上下文**

- 参考 spec: 第 3 节 "全产出增强 — analysis 三个维度文档"
- 完成标准:
  - `analyze_architecture(filtered_files, project_name, output_dir, enable_dotenv=True, codegraph_context=None)`: 当 context 非空时，在 `_build_architecture_prompt_from_files` 返回的 prompt 末尾追加 CodeGraph 上下文，引导 LLM 利用调用链数据增强架构分析（如识别真正的分层边界、关键模块依赖）
  - `analyze_user_stories(filtered_files, arch_md_text, project_name, output_dir, enable_dotenv=True, codegraph_context=None)`: 同上，引导 LLM 利用符号关系重建用户故事中的功能依赖链
  - `analyze_risk(filtered_files, arch_md_text, stories_md_text, project_name, output_dir, enable_dotenv=True, codegraph_context=None)`: 同上，引导 LLM 利用符号关系识别高风险调用路径和耦合热点
  - 各函数 context 为 None 时行为与现有版本完全一致
- 验证命令: `python -c "from app.analyzer.dimension_analyzer import analyze_architecture; import inspect; sig = inspect.signature(analyze_architecture); print(sig)"`

---

**IMP-6: 更新项目地图文件**

- 参考 coding-rule 1/2/5/6/7
- 完成标准:
  - `harness/project-map/module-map.md`: 在 analyzer 模块表格新增 `app/analyzer/codegraph.py` 行；更新 `llm_assistant.py` 行新增 `_call_llm_with_tools` 函数；更新 `analyze_project.py` 行提及 `--codegraph` 参数
  - `harness/project-map/directory-map.md`: 在 `app/analyzer/` 下新增 `codegraph.py` 条目
  - `harness/project-map/command-map.md`: 更新 `analyze_project.py` 命令行的参数说明，追加 `[--codegraph]`
  - `harness/project-map/data-flow.md`: 新增 "CodeGraph 增强分析流水线" 数据流图，展示从 db 检测 -> schema 提取 -> LLM tool-use 探索 -> context 注入 -> domain/dimension 分析的完整链路
- 验证命令: `python harness/scripts/check_structure.py`

---

### 测试任务 (-> Tester)

---

**TST-1: `tests/test_codegraph.py` — codegraph.py 模块单元测试**

- 覆盖功能点:
  - `detect_codegraph_db`: 存在 db 时返回路径；不存在时返回 None；路径不是目录时返回 None
  - `connect_codegraph_db`: 正常连接返回 Connection；无效路径抛出异常
  - `extract_schema_summary`: 含表的 db 返回完整摘要（表名/列名/行数）；空 db 返回空表列表不崩溃
  - `execute_query`: 有效 SELECT 返回正确行数据；验证结果格式为 list[dict]；非 SELECT 语句（INSERT/UPDATE/DELETE/DROP）被拒绝并抛出异常；SQL 注入尝试被安全拒绝；空结果返回空列表
  - `format_schema_for_llm`: 正常 schema dict 输出含 Markdown 格式文本；空 schema 不崩溃
  - 涉及 spec: 第 3 节 "数据库检测" + "Schema 提取" + 第 4 节 "已决: SQL 查询权限——只读不限表"
- 验证命令: `python -m pytest tests/test_codegraph.py -v`

---

**TST-2: `tests/test_analyze_project.py` — 扩展 CLI 集成测试**

- 覆盖功能点:
  - `--codegraph --help` 输出含 `--codegraph` 参数说明
  - `--codegraph` 对无 `.codegraph/` 目录的目标项目输出降级提示信息且退出码为 0（降级兼容）
  - `--digest --codegraph --quiet` 组合参数不冲突，正常生成 project-overview.md 和 analysis/*.md
  - `--codegraph` 未启用时不影响现有 `--digest` 和默认模式行为（回归测试）
  - 涉及 spec: 第 3 节 "降级兼容"
- 验证命令: `python -m pytest tests/test_analyze_project.py -v -k "codegraph or digest or help"`

---

**TST-3: `tests/test_codegraph.py` — tool-use LLM 调用函数测试**

- 覆盖功能点:
  - `_call_llm_with_tools` 无 API Key 时返回 None（与 `_call_llm` 行为一致）
  - tool_handler 被正确调用且参数解析正确（用 mock LLM 响应验证）
  - 多轮对话在达到 max_rounds 后终止并返回文本
  - 涉及 spec: 第 4 节 "多轮交互的成本 —— 设置最大轮数"
- 验证命令: `python -m pytest tests/test_codegraph.py -v -k "tool"`

---

## 3. 依赖关系

```
IMP-1 (codegraph.py)  ──────────────────────────────────────┐
     │                                                       │
IMP-2 (llm_assistant tool-use)  ────────────────────────────┤
     │                                                       │
     ├── IMP-3 (analyze_project.py --codegraph)  ────────────┤
     │        │                                               │
     │        ├── IMP-4 (domain_analyzer context)  ──────────┤
     │        │                                               │
     │        └── IMP-5 (dimension_analyzer context)  ────────┤
     │                                                        │
     └── IMP-6 (project-map updates) (可最后执行)  ───────────┘

测试任务依赖:
  TST-1 依赖 IMP-1 完成
  TST-2 依赖 IMP-3/4/5 完成
  TST-3 依赖 IMP-2 完成
```

- IMP-1 和 IMP-2 可并行执行，二者无相互依赖
- IMP-3 依赖 IMP-1 + IMP-2 完成后才能集成
- IMP-4 和 IMP-5 依赖 IMP-1 完成，可与 IMP-3 并行执行（因为它们只是新增可选参数，不改变调用方的 import）
- IMP-6 在所有实现完成后统一执行
- TST-1 在 IMP-1 完成后可执行
- TST-3 在 IMP-2 完成后可执行
- TST-2 在 IMP-3/4/5 全部完成后执行

---

## 4. 风险点

| 风险 | 说明 | 缓解措施 |
| ---- | ---- | ---- |
| **CodeGraph schema 版本差异** | CodeGraph 的 SQLite schema 可能随其版本变化（表名、列名不同），导致 extract_schema_summary 依赖的表名失效 | `extract_schema_summary` 从 `sqlite_master` 动态读取表结构，不硬编码表名。如果 CodeGraph 版本导致关键表缺失，在 schema 格式化时标注"部分表结构无法解析"。spec 第 4 节也标记了此风险。 |
| **Tool use 格式兼容** | Anthropic 和 OpenAI 的 tool calling API 格式差异较大（tool_use content block vs tool_calls + role:tool），`_call_llm_with_tools` 需要正确解析两种格式 | 在 `_call_llm_with_tools` 中根据 `config["provider"]` 分支处理。Anthropic: 遍历 `content` 数组找 `type: "tool_use"`，构造 `tool_result` content block。OpenAI: 从 `choices[0].message.tool_calls` 解析，追加 `role: "tool"` 消息。 |
| **多轮 API 调用成本** | 每次 CodeGraph 探索可能需要 3-5 轮 LLM 调用，叠加 domain + 3 个 dimension 分析，最多增加 20+ 次 API 调用 | `max_rounds` 默认 5 且可配置；仅在 `--codegraph` 启用时生效；探索阶段的 token 消耗通过返回结果截断（200 行上限）控制。spec 第 4 节已标注此风险。 |
| **非 SELECT 语句注入** | 虽然 CodeGraph 连接是只读的，但需要显式防御非 SELECT SQL（如 ATTACH 等 SQLite 特有指令） | `execute_query` 中先用 `sql.strip().upper().startswith("SELECT")` 验证，拒绝所有非 SELECT 语句。同时使用只读连接 `mode=ro` 作为第二层防护。 |
| **大型 db 查询性能** | 某些表可能有数十万行，全量返回会 OOM | `execute_query` 结果行数硬上限 200 行，超出截断并标注 `...(结果截断，共 N 行，显示前 200 行)`。LLM Schema 摘要中也提示表行数，让 LLM 自行判断是否需要 LIMIT。 |
| **现有测试回归** | 修改 `domain_analyzer.py` 和 `dimension_analyzer.py` 的函数签名（新增可选参数）不应破坏现有调用方 | 新增参数均为带默认值的可选参数（`codegraph_context=None`），向后兼容。TST-2 包含回归测试验证未启用 `--codegraph` 时的行为不变。 |
| **第三方依赖** | sqlite3 是 Python 标准库模块，无需额外安装。无需引入第三方依赖。 | 确认 `import sqlite3` 可用，无 pip install 需求。 |

---

## 5. 前置条件

- CodeGraph 已安装并完成目标项目索引（用户侧依赖，不在本变更范围内 — spec 第 3 节 "暂不实现"）
- 目标项目根目录下存在 `.codegraph/codegraph.db` 文件

---

## 6. 不纳入本版本

以下功能明确排除（对应 spec 第 3 节 "暂不实现"）：

- 将图谱数据用于 `project.yaml` 字段自动填充
- 图谱数据影响 Agent 工作流（Explorer/Reviewer 等）
- 自动安装或调用 CodeGraph 进行索引
- 文件监听自动同步
