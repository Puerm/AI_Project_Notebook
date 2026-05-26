# Spec: CodeGraph 集成 — 图谱增强项目分析

## 1. 要解决什么问题

当前 `analyze_project.py` 的项目分析只能看到目录结构和文件列表维度。依赖 `codebase-digest` 收集源码文本给 LLM，但缺少**符号级关系**（函数调用链、类继承、模块依赖图）。LLM 面对一堆源码文本，需要自己推断关系，容易遗漏或错误。

CodeGraph 预索引了完整的符号知识图谱（SQLite），直接提供结构化的调用关系、符号列表、影响范围。将这份图谱数据作为 LLM 的额外上下文，可以显著提升分析质量，让后续 `harness_deploy.py` 的个性化适配更准确。

## 2. 版本目标

在 `analyze_project.py` 中新增 `--codegraph` 选项。检测目标项目中 CodeGraph 索引数据库 → 提取 schema 提供给 LLM → LLM 按需发起 SQL 查询 → 多轮交互探索图谱 → 图谱发现融入 LLM 分析上下文 → 增强全部分析产出（project-map 目录 + analysis 三个维度文档）。

不启用 `--codegraph` 时，现有行为完全不变。

## 3. 功能清单

### 本版本实现

| 功能 | MVP 描述 | 验收标准 |
| ---- | -------- | -------- |
| 数据库检测 | 检查目标项目根目录下是否存在 `.codegraph/codegraph.db`，若存在则连接 | `analyze_project.py <path> --codegraph` 能检测并报告 db 是否存在 |
| Schema 提取 | 读取 SQLite 表结构、索引信息、各表行数、语言分布等摘要统计 | LLM 收到结构化的可用数据描述，能据此决定查什么 |
| 多轮查询交互 | LLM 提出 SQL 查询需求 → 脚本执行 → 结果追加到上下文 → LLM 继续探索或输出分析 | LLM 至少能发起 2-3 轮逐步深入的查询（如先了解有哪些符号 → 再查关键函数的调用链 → 最后确认入口函数） |
| 全产出增强 | 图谱查询结果同时影响 project-map（overview/directory-map/module-map/command-map/data-flow）和 analysis（architecture/user-stories/risk-analysis）的生成 | 启用 `--codegraph` 后，module-map 的函数/类/依赖信息明显更准确，data-flow 能反映真实调用链 |
| 降级兼容 | 目标项目无 CodeGraph 索引时提示用户先安装 CodeGraph 并索引，分析流程降级为现有模式 | 无 `.codegraph/codegraph.db` 时不报错，给出指引信息后继续执行 |

### 暂不实现

- 将图谱数据用于 `project.yaml` 字段自动填充（留给后续版本）
- 图谱数据影响 Agent 工作流（Explorer/Reviewer 等）
- 自动安装或调用 CodeGraph 进行索引（用户需自行安装 CodeGraph 并运行索引）
- 文件监听自动同步（依赖 CodeGraph 自身能力）

## 4. 风险与未决问题

- **CodeGraph API 稳定性**: CodeGraph 的 SQLite schema 可能随版本变化，需确认 schema 的稳定性或做版本兼容
- **多轮交互的成本**: LLM 多轮查询会增加 API 调用次数和延迟，需设置最大轮数（建议 3-5 轮）
- **已决**: SQL 查询权限——只读不限表（仅允许 SELECT，表范围不限制）
- **已决**: 多轮交互实现——使用 tool use（函数调用），定义 `query_codegraph(sql)` 工具函数，LLM 通过 function calling 发起查询
