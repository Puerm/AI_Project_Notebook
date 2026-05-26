# Directory Map

项目完整目录结构及每个目录的职责说明。

```
    AI_Project_Notebook/
    ├── app/
    │   ├── analyze_project.py  # 智能项目分析引擎入口
    │   └── analyzer/  # Python 源码
    │       ├── prompts/  # 官方 prompt 模板
    │       │   ├── __init__.py
    │       │   ├── architecture.txt
    │       │   ├── user_stories.txt
    │       │   └── risk.txt
    │       ├── __init__.py
    │       ├── codegraph.py
    │       ├── digest_collector.py
    │       ├── dimension_analyzer.py
    │       ├── domain_analyzer.py
    │       ├── guiding_files.py
    │       ├── llm_assistant.py
    │       ├── map_writer.py
    │       ├── overview.py
    │       ├── parser.py
    │       └── scanner.py
    ├── data/  # 数据
    ├── harness/
    │   ├── rules/  # 规则
    │   ├── scripts/  # CLI 脚本
    │   │   ├── check_structure.py
    │   │   ├── diagnose_and_fix.py
    │   │   ├── export_report.py
    │   │   ├── generate_rule_evolution.py
    │   │   ├── harness_deploy.py
    │   │   ├── help.py
    │   │   ├── init_project.py
    │   │   └── search_notes.py
    │   ├── skills/  # 技能目录
    │   ├── workflow/  # 工作流定义
    │   ├── config/  # 自我升级配置 + 项目模板变量
    │   │   ├── project.yaml
    │   │   └── self-upgrade.yaml
    │   ├── prompts/  # LLM prompt 模板
    │   │   └── diagnosis.txt
    │   ├── project-map/  # 项目地图
    │   ├── feedback/  # 反馈日志
    │   └── state/  # 工作流运行时状态
    │       ├── __init__.py
    │       ├── feedback_signal.py
    │       ├── feedback_engine.py
    │       └── workflow_state.py
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
