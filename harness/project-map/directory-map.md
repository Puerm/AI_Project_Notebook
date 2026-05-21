# Directory Map

项目完整目录结构及每个目录的职责说明。

```
AI-Project-Notebook/
├── README.md              # 项目说明与快速开始
├── CLAUDE.md              # Claude Code 工作配置
├── tree.txt               # 目录树快照
├── app/                   # 应用源码（v0.2+ 填充）
├── data/                  # 用户数据，受保护目录，不可删除
├── tests/                 # 测试代码，命名 test_<module>.py
├── openspec/              # OpenSpec 规范驱动开发
│   ├── changes/           # 进行中的变更
│   │   └── archive/       # 已完成归档的变更
│   └── specs/             # 能力规范文档
├── harness/               # Harness 框架（本项目核心）
│   ├── rules/             # 可执行规则（编码、数据安全、工作流）
│   ├── scripts/           # 自动化脚本（结构检查等）
│   ├── skills/            # Agent 技能定义
│   ├── workflow/          # Agent 工作流编排（多 Agent 调用序列）
│   ├── project-map/       # 项目知识地图（本文件所在目录）
│   └── feedback/          # 错误日志与改进建议
└── .claude/               # Claude Code 配置
    ├── agents/            # Agent 角色 prompt
    ├── commands/          # 自定义斜杠命令 (含 workflow/ 子目录)
    └── skills/            # 工作流技能（OpenSpec 等）
```

## 变更规则

- 新增/删除/重命名目录后必须更新本文档
- 修改目录职责说明后检查 `overview.md` 是否需要同步
