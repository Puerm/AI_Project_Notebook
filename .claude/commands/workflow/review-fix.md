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

读取 `harness/workflow/review-fix.md` 的 YAML frontmatter，按 `stages` 顺序 spawn 子 Agent。`condition` 不满足则跳过。

**硬约束：编排模式下不读取 `.claude/agents/` 和 `openspec/` 下的任何文件。编排器被授权运行 Python 脚本进行状态管理（创建 WorkflowState、记录偏差、追加 FeedbackSignal、运行 generate_rule_evolution.py），这属于编排器职责。**

在阶段循环开始前，初始化工作流状态：
`python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.init('{topic}', ['tester'])"`

### Tester 阻塞回环 (tester -> generator-test-fix -> tester)

- 若 tester 产出 `test-report.md` 且 `结论: 阻塞` 且 generator-test-fix 阶段存在：
  - 从 `test-report.md` 第一段提取 `失败测试数量`（搜索 "FAILED" 关键词计数作为 deviation_count）
  - 运行 `python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.record_stage('tester', {deviation_count}, 'blocked')"`
  - 运行 `python -c "from harness.state.workflow_state import WorkflowState; print(WorkflowState.should_continue_loop('tester'))"`
  - 若返回 True（偏差缩小）：继续回环，spawn generator-test-fix 修复代码，再重新 spawn tester 验证
  - 若返回 False（偏差不变/放大或超过最大次数）：**暂停**，向用户展示偏差趋势和回环次数，请用户决策
  - 回环结束后：运行 `python -c "from harness.state.workflow_state import WorkflowState; s = WorkflowState.to_feedback_signal('tester'); from harness.state.feedback_engine import FeedbackEngine; engine = FeedbackEngine(); engine.add_signal(s); engine.save_signals()"` 将回环记录写入反馈信号

全部阶段结束后，运行 `python harness/scripts/generate_rule_evolution.py` 检查是否有新的重复模式。