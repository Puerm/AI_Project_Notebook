# Change Map

记录每次变更的摘要，保持项目演化历史可追溯。

## 变更记录

### 2026-05-21: 工作流回环机制 — Explorer/Tester 阻塞路由

- **类型**: 新功能
- **范围**: Agent 定义 + 工作流 YAML + 编排器命令
- **摘要**: 填补工作流中两个缺失的失败处理路径
  - **Explorer 阻塞回环**: Explorer 发现计划与现实的阻塞差距 → 路由回 Planner 修正计划 → 重新侦察 → Generator
  - **Tester 阻塞回环**: Tester 发现代码 bug → 路由回 Generator 修复 → 重新测试 → 通过
  - 修改 `.claude/agents/explorer.md` — 新增严重程度判定（阻塞/无阻塞），输出格式增加阻塞问题表格和路由说明
  - 修改 `.claude/agents/tester.md` — 失败分类体系（测试自身问题/代码 bug），路由目标从 Reviewer 改为 Generator
  - 修改 4 个 `harness/workflow/*.md` — YAML 新增 `on_blocked`、`condition`、`loop_back` 字段，新增 planner-replan / generator-fix / generator-test-fix 回环阶段
  - 修改 4 个 `.claude/commands/workflow/*.md` — 编排器指令新增回环检查逻辑（最多 2 次）
  - 更新 `harness/workflow/README.md` — 架构图加入双向回环，新增回环机制说明
- **影响文件**: 2 Agent + 4 workflow YAML + 3 command + 1 README = 10 文件
- **验证**: `python harness/scripts/check_structure.py` 通过 (44/44)

### 2026-05-21: v0.2 Harness 部署范围修正 — 工作流系统部署

- **类型**: 新功能
- **范围**: `harness/scripts/init_project.py`, `harness/scripts/check_structure.py`
- **摘要**: 修正 init_project.py 部署范围，使目标项目获得完整的工作流执行能力
  - **IMP-1**: 部署后删除目标项目中的 `init_project.py`，确保目标项目不包含 Notebook 专用初始化脚本
  - **IMP-2**: 部署 `.claude/agents/` (7 个 agent 定义) 到目标项目
  - **IMP-3**: 部署 `.claude/commands/` (pm + workflow，共 5 个命令) 到目标项目，排除 opsx/
  - **IMP-4**: 创建空的 `.claude/skills/` 目录 (不复制 OpenSpec 技能)
  - **IMP-5**: `check_structure.py` 加回 `.claude/` 目录和文件检查 (4 目录 + 12 文件)，移除 `init_project.py` 检查项
- **影响文件**: 2 修改 + 2 更新 (project-map)
- **验证**: `python harness/scripts/check_structure.py` 通过 (44/44)

### 2026-05-20: 修复 check_structure.py — 移除 .claude/ 目录检查

- **类型**: 修复
- **范围**: `harness/scripts/check_structure.py`
- **摘要**: `REQUIRED_DIRS` 包含 `.claude/`、`.claude/agents/`、`.claude/commands/`、`.claude/skills/`，但这些目录不属于部署到目标项目的 harness 骨架，导致 init_project 后 check_structure 必然 FAIL。已移除这 4 个条目。
- **影响文件**: 1
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: 工作流执行模型重构 — 轻量编排器 + 独立子 Agent 上下文

- **类型**: 重构
- **范围**: 全部 workflow 文件 + 全部 agent 定义 + 全部 command 入口 + workflow rules
- **摘要**: 将工作流执行模型从"主会话角色扮演所有 agent"重构为"轻量编排器 spawn 独立子 Agent"
  - 修改 4 个 `harness/workflow/*.md` — 新增结构化 YAML stages frontmatter，正文替换为编排器指令
  - 修改 6 个 `.claude/agents/*.md` — 正文精简为纯角色定义，移除执行步骤和启动流程
  - 修改 4 个 `.claude/commands/workflow/*.md` — 入口文件指向编排器执行模型
  - 修改 `harness/workflow/README.md` — 新增架构图和核心原则
  - 修改 `harness/rules/workflow-rules.md` — 规则 4 更新：agent 不再需要读 workflow 文件
- **核心变化**:
  - 主会话上下文从数千行（agent 定义 + 中间产物 + 思考过程）压缩到 ~70 行（YAML + 5 段摘要）
  - 每个子 Agent 拥有独立上下文窗口，只加载自己的 agent 定义 + 任务 prompt
  - 子 Agent 之间通过文件系统交接，返回 ≤200 字摘要
- **影响文件**: 14 修改
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: 新增 Agent 工作流编排系统

- **类型**: 新功能
- **范围**: harness 框架 / Agent 工作流
- **摘要**: 创建 `harness/workflow/` 目录，定义 Agent 工作流编排，省去用户手动逐个唤醒 Agent 的步骤
  - 创建 `harness/workflow/README.md` — 工作流系统说明
  - 创建 `harness/workflow/full-cycle.md` — 完整开发周期 (PM→Planner→Explorer→Generator→Reviewer→Tester)
  - 创建 `harness/workflow/implement.md` — 执行已有计划 (Explorer→Generator→Reviewer→Tester)
  - 创建 `harness/workflow/quick-fix.md` — 快速修复 (Explorer→Generator→Tester)
  - 创建 `.claude/commands/workflow/full-cycle.md` — `/workflow:full-cycle` 命令入口
  - 创建 `.claude/commands/workflow/implement.md` — `/workflow:implement` 命令入口
  - 创建 `.claude/commands/workflow/quick-fix.md` — `/workflow:quick-fix` 命令入口
  - 更新 `directory-map.md`, `command-map.md`, `check_structure.py`
- **影响文件**: 7 新建 + 2 修改
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: Agent 启动流程统一加入工作流文件阅读步骤

- **类型**: 规则更新
- **范围**: 全部 Agent 定义 + 工作流规则
- **摘要**: 之前 Agent 被工作流唤醒时不知道自己在流程中的位置。新增硬性规定
  - 修改 `harness/rules/workflow-rules.md` — 新增第 4 条：如果在工作流中被唤醒，必须先阅读 `harness/workflow/README.md` 和对应 workflow 文件
  - 修改全部 6 个 Agent (`pm`, `planner`, `explorer`, `generator`, `reviewer`, `tester`) 的启动流程 — 每个启动流程新增第 0 步：阅读 workflow 文件确认上下文
  - 每个 Agent 的第 0 步针对其角色定制了关注点 (PM 关注下游交接，Generator 关注三种调用模式区分，Reviewer 关注三类分类规则等)
- **影响文件**: 1 规则 + 6 Agent
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: Tester 测试编写依据补全 — 四份输入源

- **类型**: 修复
- **范围**: Tester Agent 定义 + 全部工作流文档
- **摘要**: Tester 原来只写"读计划"作为测试编写依据，缺少关键输入。补全为四份依据
  - 修改 `.claude/agents/tester.md` — 启动流程改为四份依据依次阅读：Spec (验收标准) → 计划 (TST- 任务) → 实际代码 (接口签名) → 审查报告 (已知问题优先覆盖)
  - 更新 4 个工作流文档中 Tester 的调用 prompt — 全部改为传递四份输入
  - review-fix 工作流新增独立的 Tester 阶段（之前缺少，只写了手动运行 pytest）
  - quick-fix 工作流的 Tester 以问题描述 + 实际代码为替代依据（无正式 spec/plan）
- **影响文件**: 1 Agent + 4 工作流
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: 明确 Generator/Tester 职责边界 — 测试代码由 Tester 编写

- **类型**: 修复
- **范围**: Generator, Tester, Planner Agent 定义
- **摘要**: Generator 之前被描述为"唯一可以写代码的 agent"，但 Tester 也需要写测试代码。明确职责边界
  - 修改 `.claude/agents/generator.md` — 移除"唯一可写代码"声明，改为"只写应用代码，不写测试代码"；约束中新增"不修改 tests/ 目录"
  - 修改 `.claude/agents/tester.md` — 定位改为"项目中唯一编写测试代码的 Agent"
  - 修改 `.claude/agents/planner.md` — 任务列表拆分为实现任务 (IMP- → Generator) 和测试任务 (TST- → Tester)，不允许混在一起
- **影响文件**: 3 个 Agent 定义
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: PM Agent 升级为工作流驱动 + 全部 Agent 定义同步更新

- **类型**: 重构
- **范围**: 全部 Agent 定义 + 全部工作流文档
- **摘要**: 将 "主 Agent" 抽象概念替换为 PM Agent 作为工作流驱动者，同步更新全部 6 个 Agent 定义
  - 更新 `.claude/agents/pm.md` — 新增工作流驱动角色和审查反馈介入职责
  - 更新 `.claude/agents/planner.md` — 新增两种工作流定位（正常流程 + 审查反馈修复计划响应）
  - 更新 `.claude/agents/generator.md` — 新增三种指令来源（正常流程 + 第一类小修 + 修复计划）
  - 更新 `.claude/agents/explorer.md` — 新增工作流调用时机说明
  - 更新 `.claude/agents/reviewer.md` — 新增 review-fix 衔接关系图
  - 更新 `.claude/agents/tester.md` — 新增四种工作流的调用时机说明
  - 更新 4 个工作流文档 (`full-cycle.md`, `implement.md`, `quick-fix.md`, `review-fix.md`) + `README.md` — 全部 "主 Agent" 替换为 "PM Agent"
  - 更新 `.claude/commands/workflow/full-cycle.md` — 命令描述同步
- **影响文件**: 6 Agent + 5 工作流 + 1 命令 + change-map = 13 文件
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: 新增 Review Fix 工作流 + Reviewer 问题分类

- **类型**: 新功能
- **范围**: harness 框架 / 审查反馈流程
- **摘要**: 将 Reviewer 输出改为三类结构化分类，创建 review-fix 工作流自动路由修复
  - 修改 `.claude/agents/reviewer.md` — 新增三类问题分类体系（小修/实现偏差/需求问题）和结构化输出格式
  - 创建 `harness/workflow/review-fix.md` — 审查反馈修复工作流，按优先级 (第三类→第二类→第一类) 自动路由
  - 创建 `.claude/commands/workflow/review-fix.md` — `/workflow:review-fix` 命令入口
  - 三类路由规则：
    - 第一类 (小修) → Generator 直接修复
    - 第二类 (实现偏差) → Planner 制定修复计划 → Generator 执行
    - 第三类 (需求问题) → PM 澄清 → Planner 修订计划 → Generator 执行
  - 更新 `command-map.md`
- **影响文件**: 2 新建 + 1 修改 + 1 更新
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-20: v0.1 脚本实现

- **类型**: 新功能
- **范围**: 全项目
- **摘要**: 实现 v0.1 全部 7 个功能
  - 创建 `harness/scripts/export_report.py` — 导出项目理解报告
  - 创建 `harness/scripts/search_notes.py` — 搜索笔记
  - 创建 `harness/scripts/help.py` — 打印可用命令
  - 创建 `harness/scripts/init_project.py` — 初始化新项目地图（复制骨架+扫描目录）
  - 创建 `tests/test_export_report.py`, `tests/test_search_notes.py`, `tests/test_help.py`, `tests/test_init_project.py` — 12 个测试用例
  - 更新 `command-map.md`, `module-map.md`, `overview.md`, `README.md`
- **影响文件**: 4 新建脚本 + 4 新建测试 + 4 修改文档
- **验证**: `python harness/scripts/check_structure.py` 通过, `python -m pytest tests/ -v` 12/12 通过

### 2026-05-20: 新增 PM Agent 角色

- **类型**: 新功能
- **范围**: 工作流 / Agent 定义
- **摘要**: 在现有 OpenSpec 工作流中新增 PM Agent 角色，填补"需求讨论→spec 产出"环节
  - 创建 `.claude/agents/pm.md` — PM Agent 角色定义
  - 创建 `.claude/commands/pm/discuss.md` — `/pm:discuss` 命令入口
  - 修改 `.claude/agents/planner.md` — 启动流程增加读取 openspec/specs/ 步骤
  - 更新 `command-map.md` — 登记 `/pm:discuss` 命令
  - 创建 `openspec/specs/pm-agent.md` — PM Agent 自身 spec 文档
- **影响文件**: 2 新建 + 2 修改 + 1 新增 spec
- **验证**: `python harness/scripts/check_structure.py` 通过

### 2026-05-19: 项目初始化

- **类型**: 初始化
- **范围**: 全项目
- **摘要**: 创建 AI Project Notebook v0.1 骨架
  - 建立目录结构
  - 创建 harness 框架（rules, scripts, skills, project-map, feedback）
  - 编写可执行规则（coding, data-safety, workflow）
  - 创建项目地图文件（overview, directory-map, module-map, command-map, data-flow, change-map）
  - 创建结构检查脚本 `check_structure.py`
- **影响文件**: 全部为新建
- **验证**: `python harness/scripts/check_structure.py` 通过

---

## 记录规则

每次变更必须记录：
1. 日期和变更名称
2. 变更类型（初始化/新功能/修复/重构/规则更新）
3. 影响范围（哪些文件/模块）
4. 摘要
5. 验证命令及其结果
