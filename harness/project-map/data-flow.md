# Data Flow

v0.4 渐进式披露引擎的数据流转路径。

## 分析流水线

```
target_path/
    │
    ├── [Step 1] guiding_files.py
    │   ├── collect_guiding_files() → 引导文件内容 (found/missing)
    │   └── generate_directory_summary() → 目录结构摘要 (≤30行)
    │
    ├── [Step 2] domain_analyzer.py
    │   ├── _build_domain_analysis_prompt() → LLM prompt
    │   ├── _call_llm() → LLM 响应 (max_tokens=2048, timeout=60)
    │   └── _parse_domain_response() → 结构化 domain_result
    │       └── 降级: _degraded_domain_result()
    │
    └── [Step 3] map_writer.py
        └── generate_progressive_overview()
            └── → project-overview.md (单一输出文件)
```

## 数据结构

### domain_result (domain_analyzer.py 输出，v0.5.1 支持两级结构)

```json
{
    "one_liner": "string (≤50字)",
    "tech_stack": ["string", ...],
    "domains": [{
        "name": "string (≤15字)",
        "description": "string (≤60字)",
        "evidence": "string",
        "paths": ["string", ...],
        "confidence": "高 | 中 | 低",
        "sub_domains": [{
            "name": "string (≤10字)",
            "description": "string (≤40字)",
            "evidence": "string",
            "paths": ["string", ...],
            "confidence": "高 | 中 | 低"
        }]
    }],
    "relationships": [...],
    "next_steps": [...],
    "source": "llm | degraded"
}
```

## 变更规则

- 增加新的数据文件格式后必须更新本文档
- 增加新的数据流路径后必须更新上图

---

## harness-deploy 数据流 (v1.0)

```
目标项目目录/
    │
    ├── [Phase 1] 项目检测
    │   ├── 目录结构扫描（scan_tree, max_depth=3）
    │   ├── 引导文件收集（README.md, package.json, go.mod, Cargo.toml ...）
    │   ├── LLM 增强检测（_llm_detect_project → JSON: languages/framework/domain/description/entry_point）
    │   │   └── 降级: _detect_project_features() → 静态检测（后缀统计 + 配置文件检测）
    │   └── 输出: 检测摘要 features dict → 用户确认
    │
    ├── [Phase 2] 适配建议生成
    │   ├── Agent 文件（.claude/agents/*.md）:
    │   │   ├── 解析 ADAPTABLE_ZONE_START/END 标记
    │   │   └── LLM 适配可适配区内容 → 替换命令引用/文件命名约定/语言特定约束
    │   ├── Workflow 文件（harness/workflow/*.md）:
    │   │   └── 模板变量替换 + 项目类型适配（纯前端跳过 tester 阶段等）
    │   ├── Rule 文件（harness/rules/*.md）:
    │   │   ├── {{test_command}} 等占位符替换
    │   │   └── LLM 重写语言特定规则（如 TypeScript → ESLint/tsconfig, Go → gofmt）
    │   ├── project.yaml: 填入 Phase 1 检测到的值
    │   └── CLAUDE.md: 生成项目定位描述 + 项目地图入口表
    │
    └── [Phase 3] 交互式确认
        ├── 检测摘要确认（第一个确认项，缓解 LLM 检测偏差）
        ├── 逐文件 diff 展示（project.yaml → CLAUDE.md → agents → workflows → rules）
        ├── 用户交互: y(确认) / n(跳过) / e(编辑器手动修改)
        ├── 原子写入: .tmp + os.replace（data-safety-rule 8）
        └── 一致性检查: 扫描残留 {{...}} 占位符 + ADAPTABLE_ZONE 标记
```

---

## Digest 分析流水线 (v0.5.1 聚焦分析)

```
target_path/
    │
    ├── [Step digest/1] guiding_files.py (引导文件概览)
    │   ├── collect_guiding_files() → 引导文件内容 (found/missing)
    │   └── generate_directory_summary() → 目录结构摘要 (≤30行)
    │
    ├── [Step digest/2] domain_analyzer.py (两级：主板块+子板块)
    │   ├── _build_domain_analysis_prompt() → LLM prompt (含 sub_domains 结构)
    │   ├── _call_llm() → LLM 响应
    │   └── _parse_domain_response() → 结构化 domain_result (含 sub_domains 默认值)
    │       └── 降级: _degraded_domain_result()
    │
    ├── [Step digest/3] map_writer.py
    │   └── generate_progressive_overview() → project-overview.md
    │
    ├── [Step digest/4] digest_collector.py (文件池收集，不格式化 LLM 文本)
    │   ├── is_cdigest_available() → 检查 codebase-digest
    │   ├── run_digest_collection() → 全量文件收集
    │   ├── preprocess_digest() → 噪声过滤
    │   └── collect_digest() → {files: [...], status: "ok"} (不再返回 text 字段)
    │
    ├── [Step digest/5-7] dimension_analyzer.py — 聚焦三维度分析
    │   ├── filter_for_architecture(files) → 架构相关文件子集
    │   │   └── analyze_architecture(filtered_files) → analysis/architecture.md
    │   │       ├── _build_architecture_prompt_from_files() → 使用 load_prompt("architecture")
    │   │       └── 降级: _degraded_architecture()
    │   ├── filter_for_user_stories(files) → 用户故事相关文件子集
    │   │   └── analyze_user_stories(filtered_files, arch_content) → analysis/user-stories.md
    │   │       ├── _build_stories_prompt_from_files() → 使用 load_prompt("user_stories")
    │   │       └── 降级: _degraded_user_stories()
    │   └── filter_for_risk(files) → 风险相关文件子集
    │       └── analyze_risk(filtered_files, arch_content, stories_content) → analysis/risk-analysis.md
    │           ├── _build_risk_prompt_from_files() → 使用 load_prompt("risk")
    │           └── 降级: _degraded_risk()
    │
    └── 输出 (4 个文件):
        ├── harness/project-map/project-overview.md  (现有)
        ├── analysis/architecture.md                  (聚焦)
        ├── analysis/user-stories.md                  (聚焦)
        └── analysis/risk-analysis.md                 (聚焦)
```

### dimension_analyzer 返回值

```json
{
    "file_path": "analysis/architecture.md",
    "status": "llm | degraded | error",
    "content": "完整的 Markdown 文本"
}
```

### digest_collector 返回值 (v0.5.1)

```json
{
    "text": "",
    "files": [{"path": "...", "content": "..."}, ...],
    "status": "ok | cdigest_unavailable | error",
    "stats": {
        "files": 91,
        "total_tokens": 136794
    }
}
```

---

## CodeGraph 增强分析流水线 (v0.5.2 --codegraph)

```
target_path/
    │
    ├── [codegraph/1] 数据库检测 (codegraph.py)
    │   └── detect_codegraph_db(target_path) → db_path | None
    │       └── 不存在时打印指导信息，降级为普通分析流程
    │
    ├── [codegraph/2] Schema 提取 (codegraph.py)
    │   ├── connect_codegraph_db(db_path) → sqlite3.Connection (只读)
    │   └── extract_schema_summary(conn) → {tables, language_stats}
    │       └── format_schema_for_llm(schema) → Markdown 文本
    │
    ├── [codegraph/3] LLM tool-use 多轮探索 (llm_assistant.py)
    │   ├── _call_llm_with_tools(schema_text + query_codegraph tool)
    │   │   ├── LLM 收到 schema 摘要 → 决定查询方向
    │   │   ├── LLM 调用 query_codegraph(sql) → execute_query() 执行只读 SELECT
    │   │   ├── 结果追加到对话上下文 → LLM 继续探索或输出总结
    │   │   └── 最多 5 轮, 每轮结果截断 200 行
    │   └── 返回探索结果文本 (codegraph_context)
    │
    ├── [codegraph/4] context 注入 (analyze_project.py)
    │   ├── domain_analyzer: analyze_business_domains(..., codegraph_context)
    │   │   └── prompt 末尾追加 "# CodeGraph 符号知识图谱发现" 段落
    │   └── dimension_analyzer: analyze_architecture/user_stories/risk(..., codegraph_context)
    │       └── prompt 末尾追加 CodeGraph 上下文 + 维度特定的分析引导
    │
    └── 降级兼容:
        ├── --codegraph 未启用 → 行为与现有版本完全一致
        ├── 无 .codegraph/codegraph.db → 提示安装指导，继续分析
        └── LLM 不可用 → 返回 None，分析以无 CodeGraph 上下文继续
```

### codegraph.py 返回值

| 函数 | 返回值 |
| ---- | ---- |
| detect_codegraph_db | str (db 路径) \| None |
| connect_codegraph_db | sqlite3.Connection (只读) |
| extract_schema_summary | dict {tables: [...], language_stats: {...}} |
| execute_query | list[dict] (最多 200 行) |
| format_schema_for_llm | str (Markdown 格式 schema 文本) |

---

## 反馈信号与工作流状态

### FeedbackSignal (feedback_signal.py 输出)

```json
{
    "signal_type": "rule_violation | error | improvement | loop_deviation",
    "severity": "blocking | non_blocking | info",
    "rule_ref": "string (关联规则路径)",
    "occurrences": 1,
    "first_seen": "ISO timestamp",
    "last_seen": "ISO timestamp",
    "source": "string (来源标识)"
}
```

### WorkflowState (workflow_state.py 管理的 current-workflow.json)

```json
{
    "topic": "string",
    "started_at": "ISO timestamp",
    "stages": {
        "explorer": {
            "iterations": 0,
            "history": [
                {
                    "deviation_count": 0,
                    "status": "ok",
                    "timestamp": "..."
                }
            ]
        },
        "tester": {
            "iterations": 0,
            "history": [...]
        }
    }
}
```

---

## 自我升级数据流

```
feedback-signals.json
    │
    ├── FeedbackEngine.detect_patterns() → 重复模式 (occurrences >= 3)
    │
    ├── self-upgrade.yaml → 自动程度判定 + 安全边界
    │
    ├── upgrade-history.json → 24h 去重检查
    │
    ├── LLM 诊断（宽上下文）
    │   ├── 目标文件内容
    │   ├── funnel 关联文件（agent↔workflow 引用链、规则交叉引用）
    │   └── 历史反馈信号
    │
    ├── 修复方案（JSON）
    │   ├── 安全边界通过 + auto → git worktree 沙盒验证
    │   │   ├── pytest 通过
    │   │   ├── agent YAML 有效 → 合并到主分支 + 升级历史
    │   │   └── 任一失败 → 丢弃沙盒 + 降级输出
    │   └── 安全边界不通过 / semi-auto 拒绝 → rule-evolution-proposal.md
    │
    └── upgrade-history.json（每次修复记录）
```

---

## project.yaml 模板填充数据流 (v0.9)

```
init_project.py
    │
    ├── _detect_project_features() → 项目特征 (languages/test_framework/test_command/package_manager)
    │   ├── 文件后缀统计 → languages
    │   ├── 配置文件检测 → package_manager
    │   └── 测试框架推断 → test_command
    │
    ├── _generate_project_yaml() → harness/config/project.yaml
    │
    ├── _fill_templates() → 遍历 harness/ 下 .md/.yaml/.txt 文件
    │   ├── {{project_name}} → project.yaml 中的值
    │   ├── {{version}} → "0.1"
    │   ├── {{test_command}} → 检测到的测试命令
    │   ├── {{validation_command}} → 语言特定的验证命令
    │   └── {{package_manager}} → 检测到的包管理器
    │
    └── 输出: 已填充占位符的部署文件
```
