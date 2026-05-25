# AI Project Notebook

面向 AI 辅助开发的项目理解与 Harness 反馈工作台。

**核心功能：** 把陌生项目的目录结构、模块职责、命令入口、数据流、开发任务、错误反馈和规则优化过程沉淀为可维护的项目知识库。

## 版本

**v0.5.1** — 渐进式披露引擎。收集引导文件 + LLM 识别业务板块（两级结构），生成单一项目概览文档。支持 `--digest` 聚焦三维度分析（架构/用户故事/风险），每维度仅传入筛选后的文件子集。LLM 为必需依赖。

## 快速开始

```bash
# 查看所有可用命令
python harness/scripts/help.py

# 检查项目结构完整性
python harness/scripts/check_structure.py

# 查看项目总览
cat harness/project-map/overview.md

# 搜索笔记
python harness/scripts/search_notes.py <关键词>

# 导出报告
python harness/scripts/export_report.py

# 渐进式分析项目（LLM 必需）
python harness/scripts/analyze_project.py <目标路径>

# 聚焦三维度分析（每维度仅传入筛选后的文件子集，需安装 codebase-digest）
pip install codebase-digest
python harness/scripts/analyze_project.py <目标路径> --digest

# 查看完整选项
python harness/scripts/analyze_project.py --help
```

## 在新项目中使用

```bash
# 第一步：初始化 harness 骨架（从 Notebook 往目标项目部署）
python harness/scripts/init_project.py <目标项目路径>

# 第二步：分析目标项目（LLM 必需，需先在 Notebook 根目录配置 API Key）
python harness/scripts/analyze_project.py <目标项目路径>

# 可选：聚焦三维度分析（需先 pip install codebase-digest）
python harness/scripts/analyze_project.py <目标项目路径> --digest
```

> **提示**：LLM 增强需要 Anthropic API Key。在 Notebook 项目根目录创建 `.env` 文件写入 `ANTHROPIC_API_KEY=你的Key`，或设置同名环境变量。

## 目录结构

```
AI-Project-Notebook/
├── README.md              # 项目说明
├── CLAUDE.md              # Claude Code 配置入口
├── app/                   # 应用源码
│   └── analyzer/          # 智能项目分析引擎
│       ├── digest_collector.py    # codebase-digest 全量文件收集
│       ├── dimension_analyzer.py  # 三维度分析（架构/用户故事/风险）
│       ├── ... (其他分析模块)
├── analysis/              # --digest 模式输出目录（按需生成）
│   ├── architecture.md    # 架构分析报告
│   ├── user-stories.md    # 用户故事重建
│   └── risk-analysis.md   # 风险分析报告
├── data/                  # 用户数据（不可删除）
├── tests/                 # 测试代码
├── openspec/              # OpenSpec 规范与变更管理
│   ├── changes/           # 活跃变更
│   │   └── archive/       # 已归档变更
│   └── specs/             # 能力规范
├── harness/               # Harness 框架
│   ├── rules/             # 可执行规则
│   ├── scripts/           # 自动化脚本
│   ├── skills/            # Agent 技能定义
│   ├── project-map/       # 项目知识地图
│   └── feedback/          # 错误与改进日志
└── .claude/               # Claude Code 配置
    ├── agents/            # Agent 角色定义
    ├── commands/          # 自定义命令
    └── skills/            # 工作流技能
```

## 规则

- 修改目录结构后必须更新 `harness/project-map/directory-map.md`
- 添加新命令后必须更新 `harness/project-map/command-map.md`
- 不得删除 `data/` 下的用户数据
- 任何代码修改后运行 `python harness/scripts/check_structure.py` 验证
