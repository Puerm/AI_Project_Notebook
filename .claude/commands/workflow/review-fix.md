---
name: "Workflow: Review Fix"
description: 审查反馈修复 — 第三类(PM 主会话) → 第二类(Planner) → 第一类(Generator) → Tester
category: Workflow
tags: [workflow, review-fix]
---

# Review Fix Workflow

审查反馈修复。处理 Reviewer 的审查报告。

## 前置

- `openspec/changes/{topic}/review.md` 存在
- 用户需提供 topic 名称

## 执行

### 阶段 0: 读取审查报告

读取 `openspec/changes/{topic}/review.md` 的分类摘要，判断哪些类别有问题。

### 阶段 0a: 第三类问题 → PM（你亲自执行）

若有第三类问题，你阅读 `.claude/agents/pm.md`，扮演 PM 与用户逐项讨论澄清，更新 spec。完成后释放 pm.md。

### 阶段 1-3: 编排模式

读取 `harness/workflow/review-fix.md` 的 YAML frontmatter，按 `stages` 顺序 spawn 子 Agent。`condition` 不满足则跳过。循环逻辑同 full-cycle（含 Tester 阻塞 → generator-test-fix → tester 回环）。