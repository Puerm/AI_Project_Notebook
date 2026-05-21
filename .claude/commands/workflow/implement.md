---
name: "Workflow: Implement"
description: 执行已有计划 — Explorer → Generator → Reviewer → Tester
category: Workflow
tags: [workflow, implement]
---

# Implement Workflow

执行已有实现计划。

## 前置检查

用户需提供 topic 名称。若未提供，先询问。确认以下文件存在：

- `openspec/changes/{topic}/plan.md` — 实现计划
- `openspec/specs/{topic}.md` — spec 文档

若不满足，提示用户先运行 `/workflow:full-cycle <topic>`。

## 执行

你是轻量编排器。读取 `harness/workflow/implement.md` 的 YAML frontmatter，按 `stages` 逐阶段 spawn 子 Agent。

循环逻辑同 `/workflow:full-cycle`（含回环：Explorer 阻塞 → planner-replan → explorer；Tester 阻塞 → generator-fix → tester）。不读取 agent 定义文件和 openspec 文件。