# Project Overview

## 项目名称

AI Project Notebook

## 一句话描述

面向 AI 辅助开发的项目理解与 Harness 反馈工作台 — v0.9 CLI 版本。

## 当前版本

v0.9 — Harness 框架通用化

## 核心能力

1. **项目分析** — 渐进式披露 + LLM 三维度分析（架构/用户故事/风险）
2. **Agent 工作流编排** — PM → Planner ⇄ Explorer → Generator → Reviewer → Generator ⇄ Tester，含双向阻塞回环
3. **反馈信号收集** — 标准化 FeedbackSignal，跨 workflow 累积，重复模式检测
4. **规则演化** — 基于反馈信号生成规则调整建议，不自动修改但持续施加影响
5. **框架自我升级** — LLM 宽上下文根因诊断 → 安全边界双门禁 → git worktree 沙盒验证 → 分层合并/降级输出
6. **Harness 框架通用化** — 移除 Python/pytest 硬编码，`project.yaml` 模板变量定义，目录结构分离，`init_project.py` LLM 项目检测与模板填充

## 版本历史

| 版本 | 关键能力 |
| ---- | ---- |
| v0.3 | 智能项目分析引擎 — 自动扫描 + LLM 语义增强 |
| v0.4 | 渐进式披露 — 引导文件 + LLM 业务板块识别 |
| v0.5 | codebase-digest + 三维度聚焦分析 |
| v0.6 | Agent 工作流编排 — PM→Planner→Explorer→Generator→Reviewer→Tester |
| v0.7 | 反馈调节系统 — FeedbackSignal + 重复模式检测 + 偏差趋势自适应回环 |
| v0.8 | 自我升级引擎 — LLM 诊断 + worktree 沙盒 + 自动修复合并 |
| v0.9 | Harness 框架通用化 — project.yaml 模板变量 + 语言无关 agent/规则 + 目录结构分离 |

## 当前状态

| 指标 | 状态 |
| ---- | ---- |
| 版本 | v0.9 |
| 应用代码 | analyzer 引擎 + analyze_project.py + 6 个 harness 脚本 |
| 测试 | 69+ 用例 |
| Agent | 7 个 (pm / planner / explorer / generator / reviewer / tester / harness_maintainer) |
| 工作流 | 4 个 (full-cycle / implement / quick-fix / review-fix) |
| 最近变更 | 2026-05-25: Harness 框架通用化 |

## 下一步计划

1. 在实际项目中验证自我升级引擎的诊断准确率
2. 补强结构验证从骨架检查到内容校验
3. 精简框架层与功能层的比重
