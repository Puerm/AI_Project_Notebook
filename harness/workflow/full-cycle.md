---
name: full-cycle
description: 完整开发周期 — PM(主会话) → Planner → Explorer → Generator → Reviewer → Tester
stages:
  - id: planner
    agent: planner
    inputs:
      - "openspec/specs/{topic}.md"
    outputs:
      - "openspec/changes/{topic}/plan.md"
    pause: true
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

# Full Cycle Workflow

完整开发周期。PM 讨论在主会话完成，后续阶段 spawn 子 Agent 执行。

## 阶段 0: PM 讨论（主会话执行，不 spawn）

你阅读 `.claude/agents/pm.md`，扮演 PM 与用户逐项讨论需求，产出 spec 到 `openspec/specs/{topic}.md`。用户确认后，PM 定义可以从上下文释放，进入编排模式。

## 阶段 1-5: 编排模式

你是轻量编排器。按 frontmatter `stages` 逐阶段 spawn 子 Agent：

1. 将 inputs/outputs 中的 `{topic}` 替换为用户确认的主题名
2. 调用 `Agent(subagent_type=stage.agent, prompt="任务: {stage.id}\n输入: {inputs}\n输出: {outputs}\n按你的 agent 定义执行。完成后返回 ≤200 字摘要。")`
3. 收到返回后只保留摘要
4. 若 stage.pause = true，向用户展示摘要并等待确认
5. **检查是否需要回环**（见下方"回环逻辑"）
6. 进入下一阶段

### 回环逻辑

Explorer 和 Tester 阶段完成后，编排器必须检查产出物中的阻塞标记：

**Explorer 阻塞回环** (explorer → planner-replan → explorer)：
- 读取 `recon.md`，若 `严重程度: 阻塞` 且存在 `planner-replan` 阶段：
  - spawn planner-replan 修正计划
  - 重新 spawn explorer 验证修正后的计划
  - 阻塞消除后才进入 generator
- 回环最多 2 次，2 次后仍阻塞则暂停并请用户决策

**Tester 阻塞回环** (tester → generator-fix → tester)：
- 读取 `test-report.md`，若 `结论: 阻塞` 且存在 `generator-fix` 阶段：
  - spawn generator-fix 修复代码 bug
  - 重新 spawn tester 验证修复
  - 全部通过后才结束工作流
- 回环最多 2 次，2 次后仍阻塞则暂停并请用户决策

**硬约束：**
- 编排模式下不读取 `.claude/agents/` 下的任何文件（pm.md 已在阶段 0 后释放）
- 不读取 `openspec/` 下的任何文件（那是子 Agent 的工作）
- 子 Agent 的 prompt 只含文件路径，不含文件内容
- **检查回环条件时**：编排器只读产出文件的第一段（严重程度/结论），不读全文

全部完成后用表格汇总所有阶段输出。
