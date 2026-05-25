# AI Project Notebook

面向 AI 辅助开发的项目理解与 Harness 反馈工作台。

**核心能力：** 项目分析（渐进式披露 + LLM 三维度分析）→ Agent 工作流编排 → 反馈信号收集 → 规则演化 → **框架自我升级**（自动检测→诊断→修复→沙盒验证）。

## 版本

**v0.8** — Harness 自我升级引擎。在反馈调节系统之上新增完整闭环：LLM 宽上下文根因诊断 → 安全边界双门禁 → git worktree 沙盒验证 → 按自动程度分层（auto/semi-auto/disabled）合并或降级输出。workflow 收尾自动触发。

### 版本历史

| 版本 | 关键能力 |
| ---- | ---- |
| v0.3 | 智能项目分析引擎 — 自动扫描 + LLM 语义增强 |
| v0.4 | 渐进式披露 — 引导文件 + LLM 业务板块识别 |
| v0.5 | codebase-digest + 三维度聚焦分析 |
| v0.6 | Agent 工作流编排 — PM→Planner→Explorer→Generator→Reviewer→Tester |
| v0.7 | 反馈调节系统 — FeedbackSignal + 重复模式检测 + 偏差趋势自适应回环 |
| v0.8 | 自我升级引擎 — LLM 诊断 + worktree 沙盒 + 自动修复合并 |

## 快速开始

```bash
# 查看所有可用命令
python harness/scripts/help.py

# 检查项目结构完整性
python harness/scripts/check_structure.py

# 查看项目总览
cat harness/project-map/overview.md

# 渐进式分析项目（LLM 必需）
python harness/scripts/analyze_project.py <目标路径>

# 聚焦三维度分析（架构/用户故事/风险）
pip install codebase-digest
python harness/scripts/analyze_project.py <目标路径> --digest

# 规则演化检查（扫描反馈信号，检测重复模式）
python harness/scripts/generate_rule_evolution.py

# Harness 自我升级（自动诊断并修复重复问题）
python harness/scripts/diagnose_and_fix.py          # 交互模式
python harness/scripts/diagnose_and_fix.py --yes    # 自动确认 semi-auto
python harness/scripts/diagnose_and_fix.py --dry-run # 仅诊断不修改
```

## 在新项目中使用

```bash
# 初始化 harness 骨架
python harness/scripts/init_project.py <目标项目路径>

# 分析目标项目
python harness/scripts/analyze_project.py <目标项目路径>
```

> **提示**：LLM 增强需要 API Key。在 Notebook 根目录创建 `.env` 文件写入 `ANTHROPIC_API_KEY=你的Key`。

## 目录结构

```
AI-Project-Notebook/
├── README.md
├── CLAUDE.md
├── app/
│   └── analyzer/              # 智能项目分析引擎
│       ├── prompts/           # 分析 prompt 模板
│       ├── scanner.py         # 目录扫描 + 源码根检测
│       ├── llm_assistant.py   # LLM 调用基础设施
│       ├── map_writer.py      # 项目地图生成
│       └── ...
├── data/                      # 用户数据（不可删除）
├── tests/                     # 测试代码
├── openspec/
│   ├── changes/               # 活跃变更 + 归档
│   └── specs/                 # 能力规范
├── harness/
│   ├── rules/                 # 可执行规则（coding / data-safety / workflow）
│   ├── scripts/               # CLI 脚本
│   │   ├── analyze_project.py
│   │   ├── generate_rule_evolution.py
│   │   └── diagnose_and_fix.py   # 自我升级引擎
│   ├── workflow/              # 工作流定义（full-cycle / implement / quick-fix / review-fix）
│   ├── config/                # 自我升级配置
│   │   └── self-upgrade.yaml
│   ├── prompts/               # LLM prompt 模板
│   │   └── diagnosis.txt
│   ├── state/                 # 运行时状态 + 反馈引擎
│   │   ├── feedback_signal.py
│   │   ├── feedback_engine.py
│   │   └── workflow_state.py
│   ├── project-map/           # 项目知识地图
│   └── feedback/              # 错误与改进日志
└── .claude/
    ├── agents/                # Agent 角色定义（pm / planner / explorer / generator / reviewer / tester）
    ├── commands/              # 自定义命令（/workflow:*, /pm:discuss）
    └── skills/                # 工作流技能
```

## 规则

- 修改目录结构后必须更新 `harness/project-map/directory-map.md`
- 添加新命令后必须更新 `harness/project-map/command-map.md`
- 不得删除 `data/` 下的用户数据
- 任何代码修改后运行 `python harness/scripts/check_structure.py` 验证
- 修改 harness 规则/agent 后运行 `python harness/scripts/diagnose_and_fix.py` 检查是否有可自动修复的重复模式
