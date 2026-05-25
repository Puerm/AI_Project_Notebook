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
