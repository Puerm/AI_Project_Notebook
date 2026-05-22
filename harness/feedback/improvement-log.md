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

### 2026-05-22 — Architecture Prompt 需要"全局扫描→深入分析"两阶段设计

- **当前状态**: `dimension_analyzer.py:_build_architecture_prompt()` 将所有 digest 文件内容一次性喂给 LLM，Prompt 要求直接进行分层分析
- **问题**: v0.1.5 BioTec 实测中，LLM 被 `paper_agent/main.py` 的巨大 argparse 吸引全部注意力，只分析了这一个 CLI 脚本，完全忽略了 NestJS 后端（`back/src/`）、React 前端（`front/`）、Worker 集群等主体架构。v0.4 引导文件模式反而正确识别了 10 个业务板块
- **建议**:
  1. Architecture Prompt 改为两阶段：**阶段一 "全局组件识别"** — 先列出所有顶级目录及其角色（不深入任何文件），用表格输出组件名/路径/一句话角色；**阶段二 "分层深入"** — 基于阶段一的组件列表，逐层分析架构分层
  2. digest 输出中将引导文件（README.md、package.json、docker-compose.yml）放在 prompt 最前面，保留高层信号，代码文件放在后面作为证据支撑
  3. 考虑两轮 LLM 调用：第一轮轻量级（≤512 tokens）识别模块，第二轮完整分析；或使用单个 prompt 但明确要求先输出组件清单再分析
  4. 第一轮调用可使用低 max_tokens 强制 LLM 收敛到全局视角
- **影响范围**: `dimension_analyzer.py:_build_architecture_prompt()`、Prompt 模板设计
- **状态**: 待处理
- **严重程度**: **重大** — digest 集成的核心价值（"全面了解新项目"）因此问题未达成

### 2026-05-21 — LLM 调用缺少差异化超时与分批策略

- **当前状态**: `_call_llm()` 所有调用统一 10 秒超时，单次 prompt 不论大小
- **问题**: v0.3.2 data-flow 的 prompt 包含完整模块依赖 JSON + 12 个入口函数，远超其他增强点，DeepSeek 处理超时。其他 4 个 LLM 调用均成功，唯独 data-flow 挂掉
- **建议**: `_call_llm()` 新增 `timeout` 参数；大 prompt 自动分批（每批 ≤5 个）；Plan 阶段预估 prompt 规模
- **影响范围**: `llm_assistant.py`
- **状态**: 临时修复（v0.3.2 已加分批+30秒超时），框架级方案待定

### 2026-05-21 — 多源码根检测缺少去重和父子过滤

- **当前状态**: `detect_source_roots()` 返回所有候选，不做去重和父子包含过滤
- **问题**: BioTec 中 `back/` 和 `front/` 互为子目录，模块分组时交叉污染——front 源码根下出现 back 模块
- **建议**: 父子包含过滤（A 是 B 祖先 → 只保留 B）；最小文件数阈值（< 5 文件不作为独立源码根）；多源码根 module-map 分区显示
- **影响范围**: `scanner.py`、`map_writer.py`
- **状态**: 待处理

### 2026-05-21 — 源码根检测不够深入，粒度过粗

- **当前状态**: `detect_source_roots()` 找到最上层候选即停止
- **问题**: BioTec 的 `back/python/paper_agent/` 是真正的 Python 源码根，但算法只返回了 `back/`
- **建议**: 递归深入直到无可拆子包的最小单元
- **影响范围**: `scanner.py`
- **状态**: 待处理

### 2026-05-21 — Generator 缺少"Spec 功能覆盖度"自检

- **当前状态**: Generator 完成后运行 `check_structure.py` + `pytest` 验证，两项只检查结构完整性和功能正确性
- **问题**: v0.3.1 Spec 明确要求 LLM 增强模块描述（"模块描述在无 LLM 时基于函数/类名做规则推断"）和数据流（"LLM 启用时由 LLM 推断关键数据流路径"），但 Generator 实际只在 `analyze_project.py` 第 163-184 行对 overview 一句话描述调了 LLM，模块描述完全走模板、数据流直接输出"LLM 未启用"模板。Spec 要求的 3 个 LLM 增强点只实现了 1 个，第二和第三个被遗漏
- **建议**:
  1. Generator 完成后对照 Spec 功能清单逐项自检，确认每个功能点都已实现
  2. Reviewer 审查清单增加"Spec 覆盖度"维度——对照 Spec 逐条检查
  3. IMP 任务描述应更精确：不能写"增强模块描述"而是"在 --llm 启用时调用 enhance_module_description() 为每个模块生成描述"
- **影响范围**: Generator agent 定义、Reviewer agent 定义、Plan 模板
- **状态**: 待处理

### 2026-05-21 — analyze_project.py 运行位置与配置归属不清晰

- **当前状态**: `analyze_project.py` 既可被 `init_project.py` 部署到目标项目，也可从 Notebook 侧以目标路径参数运行。README 最初将 `.env` 指引写在目标项目侧，造成了"分析引擎在哪运行、配置在哪维护"的混淆
- **问题**: Spec/Plan 从未明确"分析引擎的运行位置"——是从 Notebook 分析外部项目，还是部署后在目标项目内自分析。两种模式对配置（.env、API Key）、依赖（Node.js/acorn）、路径处理的要求不同
- **建议**:
  1. 明确 v0.3 的分析模式为"Notebook → 目标项目"（分析引擎在 Notebook 侧运行，以目标路径为参数），.env 和依赖均在 Notebook 侧管理
  2. 如果未来需要目标项目自分析能力，应作为独立模式设计（`analyze_project.py` 在目标项目内无参数运行，读取本地配置）
  3. Spec 模板新增"## 运行位置与配置归属"章节
- **影响范围**: Spec 模板、README.md、analyze_project.py 帮助文本
- **状态**: 待处理

### 2026-05-21 — v0.3 实战暴露：PM Spec 缺少"关键概念定义"环节

- **当前状态**: PM 讨论流程分三阶段——理解需求 → 细化方案 → 输出 Spec。Spec 模板包含"要解决什么问题 / 版本目标 / 功能清单 / 风险与未决问题"
- **问题**: v0.3 的 module-map 将"文件"等同于"模块"，导致 BioTec 项目输出 682 行无意义的文件列表。根因是 PM 阶段从未定义"什么是模块"——是按文件？按目录？按逻辑分组？这个概念模糊贯穿了后续 Planner → Generator 全链路
- **建议**:
  1. PM 讨论新增"关键概念定义"步骤——对 spec 中出现的核心概念（如"模块"、"依赖"、"分析粒度"）在进入 Planner 前明确定义
  2. Spec 模板新增"## 关键概念定义"章节，列出每个核心术语在本 spec 中的确切含义
  3. Planner 被要求检查 spec 中的概念定义是否清晰，不清晰则退回 PM
- **影响范围**: PM agent 定义、Spec 模板、Planner agent 定义
- **状态**: 待处理

### 2026-05-21 — v0.3 实战暴露：Plan 缺少"输出质量约束"

- **当前状态**: Plan 的 IMP 任务描述"要做什么"（生成 module-map.md），但不描述"什么是好的输出"（多少行以内、必须聚合到模块级、依赖图只显示内部依赖）
- **问题**: v0.3 三个输出文件全部缺乏可读性约束——module-map 682 行平铺、data-flow 逐条 import 未聚合、directory-map 298KB 全展开。三个文件对用户几乎没有帮助
- **建议**:
  1. Plan 中每个 IMP 任务新增"输出质量标准"——如"module-map 表格行数不超过 50 行（模块级聚合，非文件级）"、"directory-map 展开深度不超过 3 层"、"data-flow 只显示项目内部模块依赖，过滤 stdlib 和第三方包"
  2. Generator 实现前先评估目标项目规模，输出超过阈值时警告并建议重新设计
  3. Explorer 侦察报告增加"目标项目规模评估"——文件数、目录深度、语言分布，供 Planner 设定合理的质量约束
- **影响范围**: Planner agent 定义、Generator agent 定义、Explorer agent 定义、Plan 模板
- **状态**: 待处理

### 2026-05-21 — v0.3 实战暴露：缺少"用户上手引导"作为强制交付物

- **当前状态**: v0.3 实现了 LLM 增强功能，通过环境变量 `ANTHROPIC_API_KEY` / `LLM_API_KEY` 配置。但 `--help` 不提示需要哪些环境变量，没有 `.env` 文件支持，API Key 缺失时静默降级不告知用户
- **问题**: 用户拿到工具后不知道如何启用核心功能（LLM 增强），甚至不知道这个功能存在。Spec 将 LLM 配置方式标记为"未决"，Plan 选了环境变量方案，但没有一个环节要求"告诉用户怎么用"
- **建议**:
  1. Spec 模板新增"## 用户上手"章节——描述用户第一次使用该功能的完整步骤（安装依赖、配置环境、运行命令）
  2. CLI 命令必须包含：`--help` 输出环境变量说明、API Key 未设置时的引导提示（而非静默降级）、`README` 中的配置示例
  3. 规则层新增"用户引导规则"——任何需要配置的 CLI 命令必须包含可发现的配置引导
- **影响范围**: PM Spec 模板、Generator agent 定义、coding-rules.md
- **状态**: 待处理

### 2026-05-21 — v0.3 实战暴露：Generator 缺少"输出可用性"自检

- **当前状态**: Generator 完成 IMP 任务后运行 `check_structure.py` 和 `pytest` 验证，这两项只检查结构完整性和功能正确性
- **问题**: v0.3 的输出通过了结构检查（46/46）、测试全部通过（71/71），但对用户完全不可用。生成 298KB 的 directory-map、682 行的 module-map、逐条列出的 data-flow——技术上"正确"，实际上"无用"
- **建议**:
  1. Generator 完成实现后增加"输出可用性自检"步骤——用自己刚写的工具分析一个真实项目，检查输出文件的体积和行数，超过合理阈值时自我标记为"需优化"
  2. Reviewer 审查清单增加"用户体验"维度——不仅检查代码正确性，也检查输出是否对人有意义
  3. IMP 任务完成标准从"生成了文件"升级为"生成了对人有用的文件"
- **影响范围**: Generator agent 定义、Reviewer agent 定义、coding-rules.md
- **状态**: 待处理

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
