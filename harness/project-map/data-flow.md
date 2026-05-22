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
