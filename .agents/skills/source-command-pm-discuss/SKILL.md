---
name: "source-command-pm-discuss"
description: "Start a PM discussion to clarify requirements and produce a spec document"
---

# source-command-pm-discuss

Use this skill when the user asks to run the migrated source command `pm-discuss`.

## Command Template

# PM: Discuss

开始 PM 讨论。你将扮演 Project Manager Agent，与用户讨论需求并产出 spec 文档。

**Input**: 要讨论的主题（功能名称或需求描述）。如果用户未提供，先询问。

## 步骤

### 1. 读取 PM Agent 定义

先读取 `.Codex/agents/pm.md` 了解完整的 PM Agent 角色定义和工作流程。

### 2. 了解项目上下文

读取以下文件了解项目当前状态：
- `harness/project-map/overview.md`
- `openspec/specs/` 下已有的 spec 列表

### 3. 与用户讨论

按照 PM Agent 的讨论流程，逐项与用户澄清：

**第一阶段 — 理解需求**
- 一次只问一个问题
- 优先使用选择题
- 覆盖：问题背景、版本目标、范围（做/不做）

**第二阶段 — 细化方案**
- 对每个功能明确 MVP 和验收标准
- 识别风险和未决问题

### 4. 收敛并输出 Spec

当讨论足够清晰时，主动告知用户准备输出 spec：

> "讨论得差不多了，我来整理成 spec 文档。"

根据讨论结果生成 spec 名称（kebab-case），写入 `openspec/specs/<name>.md`。

写入后告知用户：

> "Spec 已写入 `openspec/specs/<name>.md`。请审阅，确认无误后可运行 `/opsx:propose <name>` 生成实现任务。"

### 5. 如果用户要求修改

根据用户的反馈意见更新 spec 文件，直到用户确认无误。

## 约束

- 不替用户做设计决策 — 聚焦在澄清需求而非提出方案
- 讨论过程中不要写 spec 文件，等讨论收敛后再一次性输出
- 不拆任务、不写代码、不写测试
- 如果讨论涉及的内容明显超出 v0.1 范围，提醒用户应推迟到后续版本
