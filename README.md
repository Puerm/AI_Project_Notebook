# AI Project Notebook

面向 AI 辅助开发的项目理解与 Harness 反馈工作台。

**核心功能：** 把陌生项目的目录结构、模块职责、命令入口、数据流、开发任务、错误反馈和规则优化过程沉淀为可维护的项目知识库。

## 版本

**v0.1** — 最小命令行版本。仅支持本地文件操作，不依赖数据库、Web 服务或大模型 API。

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
```

## 在新项目中使用

```bash
# 在新项目中初始化 harness 骨架
python harness/scripts/init_project.py <目标项目路径>
```

## 目录结构

```
AI-Project-Notebook/
├── README.md              # 项目说明
├── CLAUDE.md              # Claude Code 配置入口
├── app/                   # 应用源码
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
