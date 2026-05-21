# Improvement Log

记录规则、流程、工具中发现的改进机会，驱动 Harness 框架演化。

## 格式

```
### YYYY-MM-DD — 改进建议标题

- **当前状态**: 现在是什么样
- **问题**: 当前做法有什么问题
- **建议**:改进后的做法
- **影响范围**: 改进后哪些文件/规则需要更新
- **状态**: 待处理 / 已采纳 / 已拒绝
```

## 记录

### 2026-05-21 — v0.2 部署内容不够通用：feedback、rules、workflow 全部照搬

- **当前状态**: `init_project.py` 通过 `shutil.copytree(harness/, ...)` 将整个 `harness/` 目录（含 feedback、rules、workflow 等）完整复制到目标项目
- **问题**: 
  1. `harness/feedback/` 中 error-log.md 和 improvement-log.md 是 Notebook 项目自身的问题反馈，不属于新项目
  2. `harness/rules/` 中 coding-rules.md、data-safety-rules.md、workflow-rules.md 包含 Notebook 项目特定约束，对目标项目可能不适用甚至误导
  3. `harness/workflow/` 下部分内容同样可能有项目绑定
- **建议**:
  1. feedback 目录部署空模板（仅保留格式说明头），Notebook 自身反馈日志留在源项目
  2. rules 提炼通用部分（如"修改后跑 check_structure"、"记录 change-map"）部署，项目特定规则（如"不引入超出 v0.1 范围的假设"）由目标项目 `CLAUDE.md` 管理
  3. workflow 同理——通用编排逻辑部署，项目特定偏好通过模板或 CLAUDE.md 覆盖
- **影响范围**: `init_project.py`、`harness/rules/*.md`、`harness/feedback/*.md`、`harness/workflow/*.md`
- **状态**: 待处理

### 2026-05-21 — init_project.py 兼容性弱：拒绝已有 harness 或直接覆盖

- **当前状态**: `init_project.py` 检测到 `harness/` 已存在时直接报错退出；对 `.claude/agents/`、`.claude/commands/` 直接覆盖同名文件
- **问题**: 目标项目可能已有 harness（之前部署的旧版）或已有 `.claude/` 配置（如 `settings.local.json`）——直接拒绝或覆盖都不合适
- **建议**:
  1. 检测到 `harness/` 已存在时，逐文件检查——跳过已有、只补缺失、标记冲突文件让用户决定
  2. `.claude/` 部署时同理——同名 agent 询问是否覆盖，已有文件不声不响覆盖容易丢失用户配置
  3. 提供 `--force` 标志允许全量覆盖，默认行为是增量更新
- **影响范围**: `init_project.py`
- **状态**: 待处理

### 2026-05-21 — 框架缺少"部署边界"质量闸门——非通用内容泄漏到目标项目的根因追溯

- **当前状态**: 工作流链条（Spec → Planner → Reviewer → 规则层）的每个环节都没有检查"部署内容是否通用"
- **根因追溯**:
  1. Spec: "复制 harness 骨架目录"——"骨架"一词表达了意图但太模糊，没定义什么算骨架、什么不算
  2. Planner: 拆任务时没有追问骨架与实例数据的边界，没把"通用性"翻译成可验证的检查点
  3. Generator: `shutil.copytree(HARNESS_ROOT, target_harness)` 一把全拷，没有选择性过滤
  4. Reviewer: 审查清单（对照计划/对照规则/代码质量/验证完整性）四项都没有"部署通用性"检查
  5. 规则层: `coding-rules.md`、`workflow-rules.md`、`data-safety-rules.md` 均未定义部署边界
- **建议**:
  1. 新增规则定义"部署边界"——哪些内容属于模板（部署）、哪些属于实例数据（不部署）
  2. Reviewer 审查清单增加"部署通用性"检查项
  3. `init_project.py` 从 `shutil.copytree` 改为选择性部署
- **影响范围**: `harness/rules/`（新规则或补充现有规则）、`init_project.py`、Reviewer agent 定义
- **状态**: 待处理

- **当前状态**: `init_project.py` 扫描目标目录 3 层深度，只排除 `.git`、`node_modules` 等硬编码清单
- **问题**: BioTec 的 `back/storage/` 下有 25 个 UUID 目录（`15952cc3-.../`），全部展开铺满 30 行。还有 `test-auth.d.ts`、`test-auth.js`、`test-auth.js.map` 三文件并列——编译产物和 UUID 数据目录对理解项目结构毫无帮助，反而压住关键信息
- **建议**:
  1. 增加默认排除目录：UUID 格式目录名、`*.map` 编译产物
  2. 同类文件过多时折叠显示（如 `storage/ (25 个子目录)`）
  3. 支持 `.harnessignore` 文件让用户自定义排除规则
- **影响范围**: `init_project.py`、`directory-map.md` 格式
- **状态**: 待处理

### 2026-05-20 — v0.1 真机测试 (BioTec): export_report.py 输出空模板

- **当前状态**: `export_report.py` 合并 project-map 下所有 `.md` 文件，无差别输出
- **问题**: 刚初始化的项目中，`data-flow.md`、`module-map.md`、`overview.md` 全是"待填写"模板，没有任何实际笔记。报告一半篇幅是无价值内容
- **建议**: 导出时标注未填写的 file（如 `[待填写]`），或允许指定导出哪些文件
- **影响范围**: `export_report.py`
- **状态**: 待处理

### 2026-05-20 — v0.1 真机测试 (BioTec): help.py 硬编码 Unix 命令

- **当前状态**: `help.py` 的"手工操作"区打印 `cat harness/project-map/overview.md` 等 Unix 命令
- **问题**: Windows 用户看到 `cat` 命令无法直接执行，降低可用性
- **建议**: 检测操作系统，Windows 下显示 `type` 或 `Get-Content`，或统一用"用编辑器打开"
- **影响范围**: `help.py`
- **状态**: 待处理

### 2026-05-20 — v0.1 真机测试 (BioTec): 核心瓶颈 — 理解全靠手写

- **当前状态**: v0.1 工具链能搬运 harness 骨架、扫描目录树，但 module-map、overview 等真正承载"理解"的文件全部是空模板
- **问题**: 面对一个陌生项目，用户拿到一份目录树后，需要自己逐个阅读源文件、理解模块关系、填入表格。脚本没有做任何自动分析——不读 `package.json` 获取技术栈、不读 `src/` 推断模块架构、不读 import 关系推断依赖
- **建议**: v0.2 考虑加入自动分析能力——至少从 `package.json`/`requirements.txt` 提取技术栈、从目录结构推断架构模式（NestJS 的 module 模式、React 的 pages/components/hooks 分层）
- **影响范围**: 可能需要新增 `analyze.py` 或增强 `init_project.py`
- **状态**: 待处理

- **当前状态**: Workflow 文件（full-cycle、implement 等）描述了 Agent 调用的蓝图，但执行时主会话逐一读入 agent 定义文件后自己扮演不同角色。所有中间文件（代码、计划、审查报告）留在同一上下文窗口。
- **问题**: 没有真正的上下文隔离。Planner 读的代码、Explorer 扫的目录、Generator 的 diff、Reviewer 的报告全部堆在主会话上下文里。做完一轮 full-cycle 上下文窗口所剩无几。此外 PM 即使改用 Agent 工具 spawn 子 agent，自身也会因累积各阶段产出而膨胀。
- **建议**:
  1. PM Controller 使用 Agent 工具真正 spawn 子 agent，子 agent 只看到 agent 定义 + prompt，返回结果摘要
  2. 子 agent 结果压缩返回——不把完整对话历史带回 PM
  3. 关键中间产物（如 spec、plan）写文件而非嵌入 prompt，子 agent 自己去读
- **影响范围**: 所有 workflow 文件、agent 定义文件、CLAUDE.md
- **状态**: 改进中

---

> 每当发现规则不完善、流程有痛点、工具不够用，在此文件顶部添加一条记录。
