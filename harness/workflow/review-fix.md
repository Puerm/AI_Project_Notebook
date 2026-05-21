---
name: review-fix
description: 审查反馈修复 — 第三类(PM 主会话) → 第二类(Planner) → 第一类(Generator) → Tester
stages:
  - id: planner-fix
    agent: planner
    inputs:
      - "openspec/specs/{topic}.md"
      - "openspec/changes/{topic}/review.md"
      - "openspec/changes/{topic}/plan.md"
    outputs:
      - "openspec/changes/{topic}/fix-plan.md"
    condition: has_category_2_or_3
    pause: true
  - id: generator-fix
    agent: generator
    inputs:
      - "openspec/changes/{topic}/review.md"
      - "openspec/changes/{topic}/fix-plan.md"
    outputs:
      - "openspec/changes/{topic}/change-summary.md"
    condition: has_any_category
    pause: false
  - id: tester
    agent: tester
    inputs:
      - "openspec/specs/{topic}.md"
      - "openspec/changes/{topic}/plan.md"
      - "openspec/changes/{topic}/change-summary.md"
      - "openspec/changes/{topic}/review.md"
    outputs:
      - "openspec/changes/{topic}/test-report.md"
    pause: false
    on_blocked: generator-test-fix
  - id: generator-test-fix
    agent: generator
    inputs:
      - "openspec/changes/{topic}/test-report.md"
      - "openspec/changes/{topic}/plan.md"
    outputs:
      - "openspec/changes/{topic}/change-summary.md"
    condition: tester_blocked
    pause: false
    loop_back: tester
---

# Review Fix Workflow

审查反馈修复。第三类问题 PM 在主会话处理，第二类/第一类 spawn 子 Agent。

## 阶段 0: 读取审查报告（主会话执行）

读取 `openspec/changes/{topic}/review.md`，只读报告头部的总结部分。根据有哪些问题类别设置条件判断。

## 阶段 0a: 第三类问题 → PM（主会话执行，不 spawn）

如果审查报告中有第三类问题（需求/spec 问题），你阅读 `.claude/agents/pm.md`，扮演 PM 与用户逐项讨论澄清，更新 spec。完成后释放 pm.md。

## 阶段 1-3: 编排模式

按 frontmatter `stages` 顺序执行，`condition` 不满足则跳过。

处理优先级: 第二类(planner-fix) → 第一类(generator-fix) → 测试(tester)。

编排循环逻辑同 `full-cycle.md`。
