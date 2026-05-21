---
name: quick-fix
description: 快速修复 — Explorer → Generator → Tester
stages:
  - id: explorer
    agent: explorer
    inputs:
      topic: "{user_input}"
    outputs: []
    pause: false
  - id: generator
    agent: generator
    inputs:
      topic: "{user_input}"
    outputs: []
    pause: false
  - id: tester
    agent: tester
    inputs:
      topic: "{user_input}"
    outputs: []
    pause: false
    on_blocked: generator-fix
  - id: generator-fix
    agent: generator
    inputs:
      topic: "{user_input}"
    outputs: []
    condition: tester_blocked
    pause: false
    loop_back: tester
---

# Quick Fix Workflow

快速修复工作流。适用于小范围 bug 修复、文本调整、配置修改。

## 不适用场景

- 新功能开发 → 使用 `/workflow:full-cycle`
- 多文件 (>3) 修改、架构变更 → 使用 `/workflow:full-cycle`

## Orchestrator 执行指令

按 frontmatter `stages` 逐阶段 spawn 子 Agent。Quick-fix 不设暂停点，全程自动推进。`{user_input}` 直接传递用户原始问题描述。详细循环逻辑见 `full-cycle.md`。
