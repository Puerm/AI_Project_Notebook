---
name: implement
description: 执行已有计划 — Explorer → Generator → Reviewer → Tester
stages:
  - id: explorer
    agent: explorer
    inputs:
      - "openspec/changes/{topic}/plan.md"
    outputs:
      - "openspec/changes/{topic}/recon.md"
    pause: false
    on_blocked: planner-replan
  - id: planner-replan
    agent: planner
    inputs:
      - "openspec/specs/{topic}.md"
      - "openspec/changes/{topic}/recon.md"
      - "openspec/changes/{topic}/plan.md"
    outputs:
      - "openspec/changes/{topic}/plan.md"
    condition: explorer_blocked
    pause: true
    loop_back: explorer
  - id: generator
    agent: generator
    inputs:
      - "openspec/changes/{topic}/plan.md"
      - "openspec/changes/{topic}/recon.md"
    outputs:
      - "openspec/changes/{topic}/change-summary.md"
    pause: false
  - id: reviewer
    agent: reviewer
    inputs:
      - "openspec/changes/{topic}/plan.md"
      - "openspec/changes/{topic}/change-summary.md"
    outputs:
      - "openspec/changes/{topic}/review.md"
    pause: true
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
    on_blocked: generator-fix
  - id: generator-fix
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

# Implement Workflow

执行已有计划。适用于 spec 和计划已就绪的场景。

## 前置条件

- `openspec/specs/{topic}.md` 已存在
- `openspec/changes/{topic}/plan.md` 已存在

若不满足，提示用户先运行 `/workflow:full-cycle <topic>`。

## Orchestrator 执行指令

与 full-cycle 相同：按 frontmatter `stages` 逐阶段 spawn 子 Agent，并遵循回环逻辑（Explorer 阻塞 → planner-replan → explorer；Tester 阻塞 → generator-fix → tester）。详细循环逻辑见 `full-cycle.md`。
