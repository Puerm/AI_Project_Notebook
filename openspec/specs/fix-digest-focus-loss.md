# Spec: 修复 LLM 全量分析失焦问题

## 1. 要解决什么问题

**痛点**: `--digest` 模式下，codebase-digest 收集全量文件后原样塞给 LLM，导致 LLM 被海量信息淹没，分析结果严重偏移。v0.4 只看引导文件（README + docker-compose + package.json）能正确识别 10 个业务板块，v0.5 digest 拿到全部代码后却只盯住一个 CLI 脚本。

**根因**: 当前 digest 使用方式错误——全量文件 dump 掩盖了引导文件中的高层信号。digest 本身是好的文件收集工具，但应该作为"文件池"按维度筛选后使用，而非一次性全量灌入 LLM。

**核心教训**: 更多数据 ≠ 更好分析。

## 2. 版本目标

- 修复业务板块识别：区分主板块与子板块（两级），解决 v0.4 子板块被识别为独立板块的问题
- 移除全量 dump 行为：不再将全量文件文本一次性塞给 LLM
- 导入官方 prompt library：从 codebase-digest GitHub 仓库下载 prompt，作为项目持久资产
- 重构 digest 使用方式：digest 作为文件池，按分析维度筛选文件子集后配合官方 prompt 调用 LLM

## 3. 功能清单

### 本版本实现

| 功能 | MVP 描述 | 验收标准 |
| ---- | -------- | -------- |
| 板块层级识别 | domain_analyzer 的 LLM prompt 要求输出主板块+子板块两级结构，不确定的标注 [推测] | 主板块不重复不遗漏、子板块归属正确；分析可以浅但必须准确 |
| 官方 prompt 集成 | 从 codebase-digest GitHub 下载 prompt_library，挑出架构/用户故事/风险相关 prompt，放入 `app/analyzer/prompts/` | prompt 文件就位，可被 analyze_project.py 引用 |
| digest 文件筛选 | digest_collector 新增按维度筛选文件的函数（架构/用户故事/风险各取相关文件子集），替代全量 dump | 每个维度传入 LLM 的内容只包含该维度相关文件，不再有全量文本 |
| 砍掉全量 dump 调用 | dimension_analyzer 中三个 `_build_*_prompt` 不再接收全量 digest_text，改为接收筛选后的文件子集 + 官方 prompt | 无全量 dump 行为，每次 LLM 调用聚焦单维度 |
| `--digest` 改为聚焦分析模式 | CLI 保留 `--digest` 参数，但行为变为：引导文件概览 → 板块识别 → 三维度聚焦分析（每个维度只看到相关文件） | 输出 project-overview.md + analysis/ 下三份报告，每份报告分析结果聚焦准确 |

### 暂不实现

- Phase 2 交互式板块选择（让用户挑选深入分析的板块）
- Phase 2 按板块聚焦的深度分析（每个板块独立报告）

## 4. 风险与未决问题

- **未决**: codebase-digest prompt_library 的具体文件结构需从 GitHub 确认后筛选
- **风险**: 文件筛选规则（哪些文件属于架构维度？哪些属于用户故事维度？）可能不够精确，需要基于启发式规则迭代
- **风险**: 维度分析 prompt 从 codebase-digest 官方 prompt 适配为中文输出，可能影响 prompt 效果
