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

### domain_result (domain_analyzer.py 输出)

```json
{
    "one_liner": "string (≤50字)",
    "tech_stack": ["string", ...],
    "domains": [{
        "name": "string (≤15字)",
        "description": "string (≤60字)",
        "evidence": "string",
        "paths": ["string", ...],
        "confidence": "高 | 中 | 低"
    }],
    "relationships": [{
        "from": "string",
        "to": "string",
        "type": "依赖 | 调用 | 数据流 | 配置",
        "evidence": "string"
    }],
    "next_steps": ["string", "string", "string"],
    "source": "llm | degraded"
}
```

## 变更规则

- 增加新的数据文件格式后必须更新本文档
- 增加新的数据流路径后必须更新上图

---

## Digest 分析流水线 (v0.5 新增)

```
target_path/
    │
    ├── [Step D1] digest_collector.py
    │   ├── is_cdigest_available() → 检查 codebase-digest 包是否可用
    │   ├── run_digest_collection() → 调用 analyze_directory() 收集全量文件
    │   │   └── 降级: 回退到引导文件模式
    │   ├── preprocess_digest() → 过滤 [Non-text file]、折叠编译产物目录
    │   └── format_digest_for_llm() → 格式化为 LLM 可消费文本
    │
    ├── [Step D2] domain_analyzer.py + map_writer.py (保持不变)
    │   ├── analyze_business_domains() → LLM 业务板块识别
    │   └── generate_progressive_overview() → project-overview.md
    │
    ├── [Step D3] dimension_analyzer.py — LLM 三维度分析
    │   ├── analyze_architecture(digest_text) → analysis/architecture.md
    │   │   └── 降级: _degraded_architecture()
    │   ├── analyze_user_stories(digest_text, arch_content) → analysis/user-stories.md
    │   │   └── 降级: _degraded_user_stories()
    │   └── analyze_risk(digest_text, arch_content, stories_content) → analysis/risk-analysis.md
    │       └── 降级: _degraded_risk()
    │
    └── 输出 (4 个文件):
        ├── harness/project-map/project-overview.md  (现有)
        ├── analysis/architecture.md                  (新增)
        ├── analysis/user-stories.md                  (新增)
        └── analysis/risk-analysis.md                 (新增)
```

### dimension_analyzer 返回值

```json
{
    "file_path": "analysis/architecture.md",
    "status": "llm | degraded | error",
    "content": "完整的 Markdown 文本"
}
```

### digest_collector 返回值

```json
{
    "text": "格式化后的全量文件文本",
    "status": "ok | cdigest_unavailable | error",
    "stats": {
        "files": 91,
        "total_tokens": 136794
    }
}
```
