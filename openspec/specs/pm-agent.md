# Spec: PM Agent 角色

## 1. 要解决什么问题

当前 OpenSpec 工作流中，从用户原始需求到生成 proposal/design/tasks 之间缺少一个"需求澄清与方案讨论"环节。用户经常带着模糊的想法进入开发流程，导致：

- Planner 拿到不清晰的需求，产出偏离用户意图的计划
- Generator 实现的代码不符合用户预期
- 返工和沟通成本高

PM Agent 填补这个空白：在进入正式开发流程前，先与用户充分讨论，把模糊需求变成清晰的 spec。

## 2. 版本目标

v0.1：建立 PM Agent 角色定义和 `/pm:discuss` 命令入口，PM Agent 产出 spec 到 `openspec/specs/`，Planner 能正确读取 spec。

## 3. 功能清单

### 本版本实现

| 功能 | MVP 描述 | 验收标准 |
| ---- | -------- | -------- |
| PM Agent 定义 | 在 `.claude/agents/pm.md` 定义 PM Agent 角色、职责边界和工作流 | 文件存在，内容完整，包含负责/不负责的职责划分 |
| `/pm:discuss` 命令 | 用户可通过 `/pm:discuss <topic>` 启动 PM 讨论 | 命令文件存在，描述清晰，包含完整的执行步骤 |
| Spec 文档 | PM Agent 产出规范化的 spec 文档到 `openspec/specs/` | spec 模板结构完整，覆盖需求、范围、验收标准、风险 |
| Planner 衔接 | Planner 启动流程增加读取 openspec/specs/ 的步骤 | `.claude/agents/planner.md` 更新，明确 spec 读取步骤 |
| 项目地图更新 | command-map.md 登记新命令，change-map.md 记录变更 | 命令已登记，变更已记录 |

### 暂不实现

- PM Agent 自动关联 openspec 变更（propose 时自动读取 spec 生成 tasks）— 后续版本
- PM Agent 产出的 spec 直接触发 propose 流程
- 多个 spec 版本的对比与管理
- PM Agent 的对话历史持久化

## 4. 整体工作流

```
用户需求 → /pm:discuss <topic>
               │
               ▼
      ┌──────────────────────┐
      │  PM Agent 对话环节     │
      │                      │
      │  1. 理解用户需求       │
      │  2. 明确"解决什么问题"  │
      │  3. 界定版本范围       │
      │  4. 定义 MVP 和验收标准 │
      │  5. 识别风险与未决问题  │
      │  6. 输出 spec 文档     │
      └──────────────────────┘
               │
               ▼
      openspec/specs/<name>.md
               │
               ▼
      /opsx:propose <name>
      读取 spec → 生成 tasks.md
               │
               ▼
      /opsx:apply
      Planner 读取 spec 作为上下文 → 后续流程
```

## 5. PM Agent 职责边界

### 负责回答

- 这个项目/功能要解决什么问题？
- 当前版本的目标是什么？
- 哪些功能属于本版本？
- 哪些功能暂不实现？
- 每个功能的最小可用形态（MVP）是什么？
- 每个功能如何验收？
- 哪些地方还存在需求不清、边界不明或风险？

### 不负责回答

- 具体怎么写代码
- 任务如何拆给 Generator
- 测试代码怎么写
- 文件应该逐行如何修改
- 某个 bug 的具体修复实现

## 6. 文件清单

### 新建

| 文件 | 说明 |
| ---- | ---- |
| `.claude/agents/pm.md` | PM Agent 角色定义 |
| `.claude/commands/pm/discuss.md` | `/pm:discuss` 命令入口 |

### 修改

| 文件 | 改动 |
| ---- | ---- |
| `.claude/agents/planner.md` | 启动流程增加读取 openspec/specs/ |
| `harness/project-map/command-map.md` | 登记 `/pm:discuss` 命令 |
| `harness/project-map/change-map.md` | 记录本次变更 |

## 7. 风险与未决问题

- PM Agent 的讨论深度与效率平衡：讨论过于细致会拖慢流程，需要 PM Agent 在适当时主动收敛
- Spec 与 openspec artifacts 的对应关系：spec 和 proposal/design 内容可能重叠，需要明确 spec 更侧重"需求"和"范围"，proposal/design 更侧重"方案"
- 用户如何知道 PM 讨论已足够深入可以产出 spec？需要 PM Agent 有主动判断能力
