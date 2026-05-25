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

**硬约束：编排模式下不读取 `.claude/agents/` 和 `openspec/` 下的任何文件。编排器被授权运行 Python 脚本进行状态管理（创建 WorkflowState、记录偏差、追加 FeedbackSignal、运行 generate_rule_evolution.py），这属于编排器职责。**

在阶段循环开始前，初始化工作流状态：
`python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.init('{topic}', ['explorer', 'tester'])"`

按此循环执行：
1. 将 inputs/outputs 中的 `{topic}` 替换为确认的主题名
2. 如果 stage.condition 不满足，跳过该阶段
3. 调用 `Agent(subagent_type=stage.agent, prompt="任务: {stage.id}\n输入: {inputs}\n输出: {outputs}\n按你 agent 定义中的流程执行。完成后返回 <= 200 字摘要。")`
4. 子 Agent 返回后只保留摘要
5. 若 stage.pause=true，向用户展示摘要并等待确认
6. **检查回环**：若 stage.on_blocked 存在，检查产出物的阻塞标记：

   **Explorer 阻塞回环** (explorer -> planner-replan -> explorer)：
   - 若 explorer 产出 `recon.md` 且 `严重程度: 阻塞` 且 planner-replan 阶段存在：
     - 从 `recon.md` 第一段提取 `阻塞问题数量`（搜索 "阻塞" 关键词计数作为 deviation_count）
     - 运行 `python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.record_stage('explorer', {deviation_count}, 'blocked')"`
     - 运行 `python -c "from harness.state.workflow_state import WorkflowState; print(WorkflowState.should_continue_loop('explorer'))"`
     - 若返回 True（偏差缩小）：继续回环，spawn planner-replan 修正计划，再重新 spawn explorer 验证
     - 若返回 False（偏差不变/放大或超过最大次数）：**暂停**，向用户展示偏差趋势和回环次数，请用户决策
     - 回环结束后：运行 `python -c "from harness.state.workflow_state import WorkflowState; s = WorkflowState.to_feedback_signal('explorer'); from harness.state.feedback_engine import FeedbackEngine; engine = FeedbackEngine(); engine.add_signal(s); engine.save_signals()"` 将回环记录写入反馈信号

   **Tester 阻塞回环** (tester -> generator-fix -> tester)：
   - 若 tester 产出 `test-report.md` 且 `结论: 阻塞` 且 generator-fix 阶段存在：
     - 从 `test-report.md` 第一段提取 `失败测试数量`（搜索 "FAILED" 关键词计数作为 deviation_count）
     - 运行 `python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.record_stage('tester', {deviation_count}, 'blocked')"`
     - 运行 `python -c "from harness.state.workflow_state import WorkflowState; print(WorkflowState.should_continue_loop('tester'))"`
     - 若返回 True（偏差缩小）：继续回环，spawn generator-fix 修复代码，再重新 spawn tester 验证
     - 若返回 False（偏差不变/放大或超过最大次数）：**暂停**，向用户展示偏差趋势和回环次数，请用户决策
     - 回环结束后：同上通过 to_feedback_signal + FeedbackEngine 将记录写入反馈信号

7. 进入下一阶段

全部阶段结束后，运行 `python harness/scripts/generate_rule_evolution.py` 检查是否有新的重复模式。