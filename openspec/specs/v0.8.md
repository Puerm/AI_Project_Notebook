# Spec: Harness 框架自我升级系统

## 1. 要解决什么问题

v0.7 反馈调节系统能检测重复模式并产出 `rule-evolution-proposal.md`，但修复仍需人工执行。实际运行中，同一类问题（如 agent 缺少启动步骤、规则文件与实际行为偏差、workflow 阶段遗漏检查）会反复出现，每次都需要用户确认和手动修改。

核心缺失：**从"检测问题"到"修复问题"之间缺少自动化的根因诊断、方案生成、安全应用、验证回滚的完整闭环**。

用户场景：项目经过多次 workflow 运行后，反馈信号累积。当同一规则/文件被命中 ≥3 次形成重复模式时，系统自动分析、生成修复方案，在沙盒中验证，验证通过后合并；验证失败则丢弃沙盒并降级输出建议文件等待人工处理。

## 2. 版本目标

构建 Harness 自我升级引擎 v0.1，在 v0.7 反馈调节系统之上新增三个核心能力：

1. **LLM 根因诊断** — 对重复模式调用 LLM 分析反馈信号历史，定位根因，生成针对性修复方案
2. **沙盒验证** — 在 git worktree 中应用修复、运行 `check_structure.py` + `pytest` + agent 定义完整性检查，全部通过才合并
3. **按自动程度分层处理** — workflow 收尾统一触发，auto 级别静默合并，semi-auto 展示 diff 等待确认，disabled 仅输出建议

## 3. 功能清单

### 本版本实现

| 功能 | MVP 描述 | 验收标准 |
| ---- | -------- | -------- |
| 1. LLM 诊断引擎 | 新增 `harness/scripts/diagnose_and_fix.py`；宽上下文策略——向 LLM 提供目标文件 + 关联文件（funnel 相关，如 agent 定义对应的 workflow 引用、规则依赖链）+ 历史反馈信号；调用 LLM 分析根因（缺失步骤/规则冲突/遗漏检查/职责边界不清/文件内容冲突），输出结构化诊断结果（根因分类、受影响文件列表、修复方案描述） | 诊断结果包含根因分类和受影响文件列表；能正确处理 v0.7 积累的反馈信号；LLM 不可用时降级输出"无法自动诊断"标记 |
| 2. 修复方案生成 | LLM 基于诊断结果生成具体文件修改方案；输出 JSON 格式：文件路径 + 修改类型（insert/replace/delete/create）+ 修改内容 + 修改理由；支持的目标文件类型：`harness/rules/*.md`、`.claude/agents/*.md`、`harness/workflow/*.md`、`.claude/commands/workflow/*.md` | 修复方案为结构化 JSON，可直接被 Edit/Write 工具消费；每个修改项包含理由字段；不可逆操作标记 `requires_confirmation: true` |
| 3. 安全边界 | 改动量 + 操作类型组合分级：新增 ≤50 行自动 / 替换 ≤20 行自动 / 删除一律人工确认 / 超任何门槛降级为人工建议。此边界独立于文件类型配置——即使 rules 设为 auto，删除操作仍然必须确认 | 边界判断逻辑正确；所有降级操作输出到 rule-evolution-proposal.md 而非直接修改 |
| 4. 自动程度配置 | 在 `harness/config/self-upgrade.yaml`（新建）中按 glob 模式配置：`auto` / `semi-auto` / `disabled`；默认值：rules → auto，agents/workflows/commands → semi-auto，hooks/skills → disabled。无配置文件或字段缺失时使用默认值 | 配置 schema 清晰；glob 匹配正确优先级（长匹配优先于短匹配）；无文件或缺失字段降级为默认值 |
| 5. 沙盒验证 | 修改应用前创建 git worktree；在 worktree 中依次运行 `check_structure.py`、`pytest`、agent 定义完整性检查（至少验证 agent 文件 YAML frontmatter 有效）；全部通过 → merge 回主分支 + 删除 worktree；任一失败 → `git worktree remove --force` + 降级输出建议文件 | worktree 创建/合并/清理流程完整；验证失败时原始工作区不受任何影响；验证通过后变更自动合并到当前分支 |
| 6. 触发时机 | 仅在 workflow 收尾阶段统一触发：编排器运行 `generate_rule_evolution.py` 后，检查是否有可自动修复的重复模式。`auto` 级别静默处理，`semi-auto` 展示 diff 等待用户确认，`disabled` 跳过。不提供独立 `/workflow:self-upgrade` 命令 | 编排器指令中包含触发逻辑；auto 级别用户只看到通知消息；semi-auto 暂停等待用户输入 |
| 7. 升级历史记录 | 每次自动修复生成记录写入 `harness/state/upgrade-history.json`；字段：时间戳、触发信号 ID、诊断摘要、修改文件列表、验证结果、回滚情况；去重：同一信号 ID 在 24h 内不重复修复 | 升级历史可读可审计；去重逻辑有效 |
| 8. 诊断 Prompt 模板 | 诊断 prompt 独立为 `harness/prompts/diagnosis.txt`（模板文件，非硬编码）；版本号 + 变更理由记录在文件头部；诊断引擎加载时读取模板，版本号写入诊断记录 | 模板独立可读；版本号记录在诊断结果中；修改模板时更新版本号和变更理由 |

### 暂不实现

- 修改 `harness/state/` 下 Python 源文件（feedback_engine.py、workflow_state.py 等）
- 修改 `.claude/settings.json` 或 CLI 配置
- 跨项目知识迁移（从其他项目学习修复模式）
- 修复方案的 A/B 测试（先应用再观察效果）
- 独立命令 `/workflow:self-upgrade`

## 4. 关键概念定义

- **宽上下文诊断**: LLM 输入包含目标文件（被信号关联命中的文件）+ funnel 关联文件（agent 定义对应的 workflow 引用链、规则文件的交叉引用）+ 历史反馈信号（同规则 ID 的所有信号）。不喂全量 `harness/`，但比精准单文件更广一层跨文件视野
- **安全边界**: 二级门禁。第一级：操作类型 + 改动量（新增 ≤50/替换 ≤20/删除→人工）。第二级：文件类型自动程度配置（auto/semi-auto/disabled）。两级都通过才自动执行
- **沙盒验证**: 利用 `git worktree` 在独立目录中应用修改，不影响主工作区。验证三步：`check_structure.py` 全过 + `pytest` 全过 + agent YAML frontmatter 有效性检查。全部通过则 merge 回原分支并删除 worktree；任一失败则 force remove worktree 并降级输出建议文件
- **自动程度分层**: 按目标文件 glob 模式匹配，长匹配优先于短匹配。默认 `harness/rules/*` → auto，`harness/workflow/*` / `.claude/agents/*` / `.claude/commands/*` → semi-auto，其他 → disabled
- **修复去重**: 同一反馈信号 ID 在 24 小时内最多触发一次自动修复。上次修复验证失败且未产生新信号时不重复修复
- **Prompt 版本化**: `harness/prompts/diagnosis.txt` 头部包含版本号和变更理由，诊断引擎加载时读取，版本号写入诊断历史。prompt 本身可通过"rules 自动升级"路径被 LLM 建议修改——形成 meta 自我升级闭环
- **触发时机**: 仅 workflow 收尾时统一触发。编排器运行 `generate_rule_evolution.py` → 检查可修复模式 → 按自动程度分流（auto 静默 / semi-auto 确认 / disabled 跳过）。不提供独立触发命令

## 5. 风险与未决问题

- **LLM 诊断质量不稳定**: LLM 可能误判根因或生成不合理的修复方案。缓解：沙盒验证 + 验证失败降级为人工建议 + 安全边界阻止大范围修改
- **修复循环**: 自动修复可能引入新问题，新问题又被检测为新信号，再次触发修复。缓解：24h 去重窗口 + 升级历史审计 + 同一信号上次修复失败时不重复修
- **worktree 性能**: 大型仓库创建 worktree 可能较慢。缓解：可复用已验证清理的旧 worktree 名称
- **覆盖范围有限**: 暂不修改 Python 源文件（harness/state/*.py 等），核心引擎的 bug 仍无法自动修复——需在 spec 和文档中明确此边界
- **Prompt 自我演化的风险**: LLM 修改自身诊断 prompt 形成"递归升级"，可能偏离原始设计意图。缓解：prompt 修改归类为 semi-auto（需人工确认）
