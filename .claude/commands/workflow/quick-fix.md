---
name: "Workflow: Quick Fix"
description: 快速修复 — Explorer → Generator → Tester
category: Workflow
tags: [workflow, quick-fix]
---

# Quick Fix Workflow

快速修复工作流。适用于小范围 bug 修复和简单改动。

## 适用判断

若用户描述的问题涉及以下任一情况，建议改用 `/workflow:full-cycle`：
- 新功能开发
- 多文件 (>3) 修改
- 架构或接口变更

## 执行

你是轻量编排器。读取 `harness/workflow/quick-fix.md` 的 YAML frontmatter，按 `stages` 逐阶段 spawn 子 Agent。

Quick-fix 不设暂停点，全程自动推进。`{user_input}` 直接传递用户原始问题描述。循环逻辑同 `/workflow:full-cycle`（含 Tester 阻塞 → generator-fix → tester 回环）。

注意：quick-fix 无 Planner，若 Explorer 发现阻塞问题，编排器直接报告用户并终止。