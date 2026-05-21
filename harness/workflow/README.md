# Workflow

Agent 工作流编排定义。每个工作流文件的 YAML frontmatter 定义了阶段序列，正文提供轻量编排器的执行指令。

## 架构

```
用户输入 /workflow:full-cycle <topic>
              │
              ▼
┌───────────────────────────────────────────┐
│  主会话 (轻量编排器)                        │
│                                            │
│  持有: 工作流 YAML stages                   │
│  不加载: 任何 agent 定义文件                 │
│                                            │
│  循环每个 stage:                            │
│    1. 检查 condition，不满足则跳过           │
│    2. 调用 Agent(subagent_type=...,        │
│       prompt=简短任务描述)                   │
│    3. 收回 ≤200 字的结果摘要                │
│    4. 若 pause=true，暂停等用户确认          │
│    5. 检查 on_blocked，按需触发回环          │
└───────────────────────────────────────────┘
       │          │          │
       ▼          ▼          ▼
   ┌──────┐  ┌──────┐  ┌──────┐
   │Planner│  │Expl.. │  │Tester│  ← 每个是独立子 Agent
   │      │  │      │  │      │    只看到: 自己的 agent 定义
   └──────┘  └──────┘  └──────┘    + 编排器给的任务 prompt
       ▲          │          │
       │          │          │
       └── 阻塞 ──┘          │
       │                     │
       └────── 代码 bug ─────┘
```
**双向回环：** Explorer 发现阻塞 → 路由回 Planner 修正计划；Tester 发现代码 bug → 路由回 Generator 修复。

## 核心原则

- **编排与执行分离**：主会话只做编排（spawn Agent），不亲自执行 agent 的工作
- **独立上下文**：每个子 Agent 在自己的上下文窗口里运行，不共享主会话上下文
- **文件交接**：子 Agent 之间通过文件系统传递产物（前一个写文件，后一个读文件）
- **返回摘要**：子 Agent 只向编排器返回 ≤200 字的结果摘要，不泄漏完整思考过程
- **条件回环**：编排器检查产出物的阻塞标记，按需将流程路由回上游阶段（Explorer 阻塞 → Planner；Tester 阻塞 → Generator），回环最多 2 次

## 工作流文件格式

每个工作流文件的 YAML frontmatter 定义阶段序列：

```yaml
stages:
  - id: planner          # 阶段标识
    agent: planner        # 对应 .claude/agents/{agent}.md
    inputs:               # 传给 agent 的输入文件路径
      - "path/to/input.md"
    outputs:              # agent 应产出的文件路径
      - "path/to/output.md"
    pause: true           # 是否在此阶段后暂停
    on_blocked: replan    # (可选) 阻塞时路由到的回环阶段 id
  - id: replan
    agent: planner
    condition: blocked    # (可选) 条件名称，条件不满足则跳过
    loop_back: explorer   # (可选) 回环完成后回到的阶段 id
```

动态变量 `{topic}` 由用户在命令中提供，编排器在构造 prompt 前替换。

## 当前工作流

| 工作流 | 命令 | 阶段 (含回环) |
| ---- | ---- | ---- |
| full-cycle | `/workflow:full-cycle <topic>` | PM → Planner ⇄ Explorer → Generator → Reviewer → Generator ⇄ Tester |
| implement | `/workflow:implement <topic>` | Planner ⇄ Explorer → Generator → Reviewer → Generator ⇄ Tester |
| quick-fix | `/workflow:quick-fix <描述>` | Explorer → Generator ⇄ Tester |
| review-fix | `/workflow:review-fix <topic>` | PM → Planner → Generator → Generator ⇄ Tester (条件执行) |

## 与 Agent 定义的关系

| 概念 | 位置 | 作用 |
| ---- | ---- | ---- |
| Agent 定义 | `.claude/agents/` | 定义 Agent 的角色、约束和输出格式 (含阻塞标记) |
| 工作流 YAML | `harness/workflow/` frontmatter | 定义阶段序列、回环路由、输入输出路径 |
| 命令入口 | `.claude/commands/workflow/` | 用户入口，含编排器执行指令和回环检查逻辑 |

### 回环机制

```
正常流:  A ──▶ B ──▶ C ──▶ D

回环流:  A ──▶ B (阻塞) ──▶ A' ──▶ B (无阻塞) ──▶ C ──▶ D (阻塞) ──▶ C' ──▶ D (通过) ✓
                    │                         │
                    └── 修正计划 ──┘            └── 修复代码 ──┘
```

两个回环点:
- **Explorer 阻塞** → `planner-replan` 修正计划 → 重新 `explorer` 侦察
- **Tester 阻塞** → `generator-fix` 修复代码 → 重新 `tester` 验证

每次回环最多 2 次，超过则暂停请用户决策。
