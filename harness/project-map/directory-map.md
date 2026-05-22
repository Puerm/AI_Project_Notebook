# Directory Map

项目完整目录结构及每个目录的职责说明。

```
    AI_Project_Notebook/
    ├── app/
    │   └── analyzer/  # Python 源码
    │       ├── __init__.py
    │       ├── domain_analyzer.py
    │       ├── guiding_files.py
    │       ├── llm_assistant.py
    │       ├── map_writer.py
    │       ├── overview.py
    │       ├── parser.py
    │       └── scanner.py
    ├── data/  # 数据
    ├── openspec/
    │   ├── changes/
    │   │   ├── archive/
    │   │   ├── v0.2-harness-deployment/  # 文档
    │   │   │   ├── change-summary.md
    │   │   │   └── plan.md
    │   │   ├── v0.3-project-analysis/  # 文档
    │   │   │   ├── change-summary.md
    │   │   │   ├── fix-plan.md
    │   │   │   ├── plan.md
    │   │   │   └── recon.md
    │   │   ├── v0.3.1-output-quality-fix/  # 文档
    │   │   │   ├── change-summary.md
    │   │   │   ├── plan.md
    │   │   │   └── test-report.md
    │   │   └── v0.3.2-llm-integration-fix/  # 文档
    │   │       └── plan.md
    │   └── specs/  # 文档
    │       ├── pm-agent.md
    │       ├── project.md
    │       ├── v0.2-harness-deployment.md
    │       ├── v0.3-project-analysis.md
    │       ├── v0.3.1-output-quality-fix.md
    │       └── v0.3.2-llm-integration-fix.md
    ├── tests/  # 测试
    │   ├── test_analyze_project.py
    │   ├── test_export_report.py
    │   ├── test_help.py
    │   ├── test_init_project.py
    │   └── test_search_notes.py
    ├── CLAUDE.md
    └── README.md
```


## 变更规则

- 新增/删除/重命名目录后必须更新本文档
- 修改目录职责说明后检查 `overview.md` 是否需要同步
