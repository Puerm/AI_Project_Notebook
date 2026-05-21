---
name: "Workflow: Full Cycle"
description: 完整开发周期 — PM(主会话交互) → Planner → Explorer → Generator → Reviewer → Tester
category: Workflow
tags: [workflow, full-cycle]
---

# Full Cycle Workflow

启动完整开发周期。

## 前置

用户需提供需求主题。若未提供，先询问："你要开发什么功能？（提供 kebab-case 名称，如 add-note-feature）"

## 执行

### 阶段 0: PM 讨论（你亲自执行）

你阅读 `.claude/agents/pm.md`，扮演 PM 与用户逐项讨论需求。产出 spec 到 `openspec/specs/{topic}.md`。用户确认 spec 后，释放 pm.md 定义，进入编排模式。

### 阶段 1-5: 编排模式

读取 `harness/workflow/full-cycle.md` 的 YAML frontmatter，按 `stages` 逐阶段 spawn 子 Agent。

**按此循环执行：**
1. 将 inputs/outputs 中的 `{topic}` 替换为确认的主题名
2. 如果 stage.condition 不满足，跳过该阶段
3. 调用 `Agent(subagent_type=stage.agent, prompt="任务: {stage.id}\n输入: {inputs}\n输出: {outputs}\n按你 agent 定义中的流程执行。完成后返回 ≤200 字摘要。")`
4. 子 Agent 返回后只保留摘要
5. 若 stage.pause=true，向用户展示摘要并等待确认
6. **检查回环**：若 stage.on_blocked 存在，检查产出物的阻塞标记：
   - Explorer (严重程度: 阻塞) → 执行 planner-replan 阶段，然后重新执行 explorer
   - Tester (结论: 阻塞) → 执行 generator-fix 阶段，然后重新执行 tester
   - 回环最多 2 次，超过则暂停请用户决策
7. 进入下一阶段

**硬约束：编排模式下不读取 `.claude/agents/` 和 `openspec/` 下的任何文件。**

全部完成后汇总表格。