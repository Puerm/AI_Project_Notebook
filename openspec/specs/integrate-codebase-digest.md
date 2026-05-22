# Spec: 集成 Codebase Digest

## 1. 要解决什么问题

用户在接手新项目时，需要快速全面了解项目。当前 v0.4 的渐进式披露引擎只收集引导文件（package.json 等）并生成摘要，LLM 能看到的上下文受限，分析深度不足。

引入 [codebase-digest](https://github.com/kamilstanuch/codebase-digest)（MIT 协议）作为数据收集层，用全量文件合并 + 精选 LLM Prompt 模板替代引导文件收集，让 LLM 看到完整代码并生成结构化分析报告。

## 2. 版本目标

v0.1.5 — 接入 codebase-digest，替换引导文件收集为全量文件合并，引入 3 个核心分析维度，输出独立分析报告文件。让用户对陌生项目形成"结构 → 功能 → 风险"三层理解。

## 3. 功能清单

### 本版本实现

| 功能 | MVP 描述 | 验收标准 |
| ---- | -------- | -------- |
| **数据层：digest 全量文件收集 + 智能预处理** | 调用 `cdigest` 收集全量文本文件，合并为单一输出后做文件分类和噪声过滤（二进制/编译产物/UUID 折叠），再喂给 LLM | 1. `cdigest` 成功安装并可命令行调用；2. 能收集目标项目的全量文本文件；3. 预处理后 token 量合理（排除二进制/图片等非文本文件）；4. 无 `cdigest` 时优雅降级回引导文件模式 |
| **分析层：架构分层识别** | 使用 digest Architecture 维度 Prompt，分析代码库的架构分层（展示层/业务逻辑/数据访问等），识别分层偏差 | 1. 产出 `analysis/architecture.md`；2. 包含分层描述、各层职责、分层偏差标记；3. 无 LLM API Key 时降级为目录结构分析 |
| **分析层：用户故事重建** | 使用 digest Learning 维度 Prompt，从代码反向重建用户故事，理解项目功能意图 | 1. 产出 `analysis/user-stories.md`；2. 每个故事包含用户角色、目标、对应代码模块；3. 无 LLM 时降级为入口函数列表 |
| **分析层：错误与风险分析** | 使用 digest Quality 维度 Prompt，分析代码中的潜在错误和风险点（安全漏洞/异常处理缺失/数据一致性等） | 1. 产出 `analysis/risk-analysis.md`；2. 风险按严重程度分级；3. 无 LLM 时降级为基础静态检查结果 |
| **输出层：独立分析报告** | 三个维度的分析结果独立输出到 `analysis/` 目录，与现有 project-map 并列 | 1. `analysis/` 目录在目标项目根下创建；2. 每个分析文件格式规范、可独立阅读；3. 报告间交叉引用（如用户故事中引用架构分层） |

### 暂不实现

- 多格式输出（text/json/xml/html）— 本版本只输出 markdown
- Quality 维度的代码复杂度/重复分析/文档覆盖分析
- Learning 维度的代码模式识别/前后端分析
- Architecture 维度的设计模式识别/数据库 Schema 审查
- Testing & Security / Business & Stakeholder / Performance / Evolution 维度
- digest 的 `--copy-to-clipboard` 功能封装
- `.cdigestignore` 自动生成

## 4. 风险与未决问题

- **风险**：全量文件喂给 LLM 可能超出 token 限制 — 缓解策略是智能预处理（文件分类 + 噪声过滤），并设置 `--max-size` 上限
- **风险**：codebase-digest 作为外部 pip 依赖，其 API 可能不兼容未来版本 — 缓解策略是封装调用层，只依赖 `cdigest` CLI 命令接口
- **已决**：分析顺序为 架构分层 → 用户故事重建 → 错误与风险分析（前两步为风险评估提供上下文）
- **已决**：在现有 `analyze_project.py` 上加 `--digest` flag，无需 digest 时保持原有流程不变
