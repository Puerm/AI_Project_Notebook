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

Quick-fix 不设暂停点，全程自动推进。`{user_input}` 直接传递用户原始问题描述。

**硬约束：编排模式下不读取 `.claude/agents/` 和 `openspec/` 下的任何文件。编排器被授权运行 Python 脚本进行状态管理（创建 WorkflowState、记录偏差、追加 FeedbackSignal、运行 generate_rule_evolution.py），这属于编排器职责。**

注意：quick-fix 无 Planner，若 Explorer 发现阻塞问题，编排器直接报告用户并终止。

在阶段循环开始前，初始化工作流状态：
`python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.init('{topic}', ['tester'])"`

### Tester 阻塞回环 (tester -> generator-fix -> tester)

- 若 tester 产出 `test-report.md` 且 `结论: 阻塞` 且 generator-fix 阶段存在：
  - 从 `test-report.md` 第一段提取 `失败测试数量`（搜索 "FAILED" 关键词计数作为 deviation_count）
  - 运行 `python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.record_stage('tester', {deviation_count}, 'blocked')"`
  - 运行 `python -c "from harness.state.workflow_state import WorkflowState; print(WorkflowState.should_continue_loop('tester'))"`
  - 若返回 True（偏差缩小）：继续回环，spawn generator-fix 修复代码，再重新 spawn tester 验证
  - 若返回 False（偏差不变/放大或超过最大次数）：**暂停**，向用户展示偏差趋势和回环次数，请用户决策
  - 回环结束后：运行 `python -c "from harness.state.workflow_state import WorkflowState; s = WorkflowState.to_feedback_signal('tester'); from harness.state.feedback_engine import FeedbackEngine; engine = FeedbackEngine(); engine.add_signal(s); engine.save_signals()"` 将回环记录写入反馈信号

全部阶段结束后，运行 `python harness/scripts/generate_rule_evolution.py` 检查是否有新的重复模式。