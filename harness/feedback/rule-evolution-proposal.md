# 规则演化建议

> 自动生成于 2026-05-25T07:22:44.473260+00:00

---

## 自我升级诊断 [降级] — `.claude/agents/generator.md`

> 生成时间: 2026-05-25T07:22:44.473260+00:00
> 状态: 待确认（降级 — dry-run 模式）

**诊断结果**:
```json
{
  "root_cause": "Generator 在审查修复中缺少明确的反馈信号触发机制——Reviewer 修复完成后没有通过 FeedbackEngine 记录信号，导致 improvement-log-conversion 源重复记录同一模式",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/generator.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/generator.md",
      "type": "insert",
      "content": "\n### 审查修复完成后\n\n1. 确认所有修复通过 `check_structure.py` 和 `pytest`\n2. 运行 `python -c \"from harness.state.feedback_engine import FeedbackEngine; engine = FeedbackEngine(); engine.add_signal({'signal_type': 'improvement', 'severity': 'non_blocking', 'rule_ref': '.claude/agents/generator.md', 'occurrences': 1, 'source': 'reviewer-fix-completion'}); engine.save_signals()\"`\n3. 更新 `harness/feedback/improvement-log.md`（如需）",
      "reason": "在审查修复流程的收尾步骤中增加明确的反馈信号记录，替代现有通过 improvement-log-conversion 间接转换的方式，从根本上消除模式重复记录"
    }
  ]
}
```

**降级原因**: dry-run 模式

---

## 自我升级诊断 [降级] — `.claude/agents/pm.md`

> 生成时间: 2026-05-25T07:22:49.016210+00:00
> 状态: 待确认（降级 — dry-run 模式）

**诊断结果**:
```json
{
  "root_cause": "PM Agent 缺少在收到 Reviewer 第三类问题后的主动介入和讨论流程，导致需求问题反复出现",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/pm.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/pm.md",
      "type": "insert",
      "content": "\n## 第四阶段：Reviewer 反馈处理\n\n当 Reviewer 标记第三类问题（需求/spec 问题）时，PM 需介入处理：\n\n1. 阅读审查报告中的第三类问题列表\n2. 逐项与用户确认：\n   - 是否认可该问题为问题？\n   - 需要如何修改 spec？\n3. 更新 `openspec/specs/<name>.md` 中的对应章节\n4. 标记已处理的问题，通知 Reviewer 重新审查\n\n### 处理原则\n\n- 每次只处理一个问题，与用户讨论清楚后再处理下一个\n- 修改 spec 时保持格式一致，仅修改确认有问题的部分\n- 修改完成后主动通知 Reviewer 重新审查",
      "reason": "补充 Reviewer 反馈处理流程，使 PM Agent 在需求/spec 问题被标记时能主动介入并形成闭环，避免需求问题反复出现"
    }
  ]
}
```

**降级原因**: dry-run 模式

---

## 自我升级诊断 [降级] — `.claude/agents/planner.md`

> 生成时间: 2026-05-25T07:22:55.875358+00:00
> 状态: 待确认（降级 — 无法自动诊断 — LLM 不可用或返回格式异常）

**诊断结果**:
```json
无法自动诊断 — LLM 不可用或返回格式异常
```

**降级原因**: 无法自动诊断 — LLM 不可用或返回格式异常

---

## 自我升级诊断 [降级] — `harness/rules/workflow-rules.md`

> 生成时间: 2026-05-25T07:23:02.916182+00:00
> 状态: 待确认（降级 — fix_plan[0]: replace 43 行超过阈值 20 （文件: harness/rules/workflow-rules.md)）

**诊断结果**:
```json
{
  "root_cause": "workflow-rules.md 中任务启动第4条的唤醒规则不够清晰，导致 Agent 在非唤醒场景下也错误地跳过阅读 workflow 编排文件",
  "category": "boundary_unclear",
  "affected_files": [
    "harness/rules/workflow-rules.md"
  ],
  "fix_plan": [
    {
      "file": "harness/rules/workflow-rules.md",
      "type": "replace",
      "content": "# Workflow Rules\n\n可执行的工作流规则。每条规则定义了特定场景下必须执行的操作。\n\n## 任务启动\n\n1. 每次开始新任务前必须阅读 `harness/project-map/overview.md` 了解项目当前状态\n2. 评估任务影响范围，列出可能被修改的文件清单后再动手\n3. 如果任务涉及多文件修改，先在 `harness/project-map/change-map.md` 记录变更意图\n4. **如果是在工作流中被唤醒**（被轻量编排器通过 Agent 工具 spawn），任务和输入输出路径已由编排器在 prompt 中指定。按自己 agent 定义的流程执行即可，不需要阅读 workflow 编排文件。\n   - 例外：如果你的 agent 定义中没有明确的任务输入/输出路径，或者需要在多个工作流步骤间协调，仍然需要阅读相关 workflow 编排文件以理解上下文\n\n## 任务执行\n\n5. 修改文件前先读文件，确认当前内容与预期一致\n6. 一次只改一个关注点，不要夹带无关改动\n7. 修改完成后立即更新相关的 `harness/project-map/` 文档\n\n## 验证\n\n8. 代码修改后运行 `python harness/scripts/check_structure.py`\n9. 如果存在测试，运行 `python -m pytest tests/ -v`\n10. 检查 `harness/rules/` 下是否有规则被命中，确认没有违反\n\n## 错误处理\n\n11. 遇到错误时记录到 `harness/feedback/error-log.md`，格式：\n    - 时间戳\n    - 错误现象\n    - 触发条件（做了什么导致错误）\n    - 根因（如果已知）\n    - 解决方案（如果已解决）\n\n## 改进\n\n12. 发现规则不完善或缺失时记录到 `harness/feedback/improvement-log.md`\n13. 规则改进后同步更新 `harness/rules/` 下对应的文件\n14. 每次改进后检查是否有相关 `project-map` 文档需要同步更新\n\n## 任务结束\n\n15. 更新 `harness/project-map/change-map.md`，记录本次变更摘要\n16. 如果引入了新的命令或工作流，更新 `README.md` 和 `CLAUDE.md`",
      "reason": "在任务启动第4条中添加了例外情况说明，明确 Agent 在缺少明确输入/输出路径或需要跨步骤协调时必须阅读 workflow 编排文件。这消除了规则边界的模糊性，避免 Agent 在非唤醒场景下误判是否需要跳过重要步骤。"
    }
  ]
}
```

**降级原因**: fix_plan[0]: replace 43 行超过阈值 20 （文件: harness/rules/workflow-rules.md)

---

## 自我升级诊断 [降级] — `harness/rules/coding-rules.md`

> 生成时间: 2026-05-25T07:23:06.447014+00:00
> 状态: 待确认（降级 — dry-run 模式）

**诊断结果**:
```json
{
  "root_cause": "规则被反复触发但未得到修复，缺少对历史反馈的定期审查和闭环处理机制",
  "category": "missing_step",
  "affected_files": [
    "harness/rules/coding-rules.md"
  ],
  "fix_plan": [
    {
      "file": "harness/rules/coding-rules.md",
      "type": "insert",
      "content": "\n## 反馈闭环\n\n15. 每个 rule_ref 的历史反馈信号（improvement、warning）已有 3 次重复出现时，必须执行一次根因分析流程\n16. 根因分析结果必须记录在 `harness/feedback/root-cause-analysis.md` 中，并更新对应规则使其不再触发相同信号",
      "reason": "当前 coding-rules.md 缺少对自身反馈信号的响应机制，导致同样的 improvement 信号无限重复，添加闭环规则后系统可以自主修复重复模式"
    }
  ]
}
```

**降级原因**: dry-run 模式

---

## 自我升级诊断 [降级] — `.claude/agents/generator.md`

> 生成时间: 2026-05-25T07:23:32.423913+00:00
> 状态: 待确认（降级 — semi-auto: 用户拒绝或超时 (300s)）

**诊断结果**:
```json
{
  "root_cause": "Generator Agent 定义中缺少明确的审查反馈修复流程步骤，导致修复时无结构化指引，易遗漏或误操作，引发重复反馈。",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/generator.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/generator.md",
      "type": "insert",
      "content": "\n### 审查反馈修复流程\n\n当收到 Reviewer 的修复请求时，按以下步骤执行：\n1. 读取审查报告，仅关注表格中列出的问题项\n2. 逐项修复，每项完成后立即运行 `python harness/scripts/check_structure.py` 验证结构\n3. 所有项修复完成后，运行 `pytest tests/` 确保未引入回归\n4. 更新 `harness/project-map/change-map.md`，记录修复内容\n5. 若遇到需要改接口签名或模块边界的问题，拒绝并反馈给 Reviewer",
      "reason": "补充缺失的审查反馈修复步骤，确保修复过程有结构化指引，避免遗漏或误操作，从而减少重复反馈信号。"
    }
  ]
}
```

**降级原因**: semi-auto: 用户拒绝或超时 (300s)

---

## 自我升级诊断 [降级] — `.claude/agents/pm.md`

> 生成时间: 2026-05-25T07:23:36.501741+00:00
> 状态: 待确认（降级 — semi-auto: 用户拒绝或超时 (300s)）

**诊断结果**:
```json
{
  "root_cause": "PM Agent 在输出 Spec 后流程结束，没有显式进入编排模式的衔接步骤，导致全周期工作流中 PM 阶段完成后无法自动触发后续阶段，产生重复的流程断裂反馈。",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/pm.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/pm.md",
      "type": "insert",
      "content": "\n## 流程衔接\n\n当用户确认 Spec 后：\n1. 输出 \"Spec 已确认，准备进入编排模式。用户确认后请回复 `continue` 以继续全周期工作流。\"\n2. 等待用户输入 `continue`\n3. 收到 `continue` 后，执行全周期工作流指令：`/workflow:full-cycle`",
      "reason": "补齐 PM 阶段到编排阶段的显式衔接步骤，确保 PM 完成后能自动触发全周期工作流，避免流程中断导致的重复反馈信号。"
    }
  ]
}
```

**降级原因**: semi-auto: 用户拒绝或超时 (300s)

---

## 自我升级诊断 [降级] — `.claude/agents/planner.md`

> 生成时间: 2026-05-25T07:23:47.816963+00:00
> 状态: 待确认（降级 — fix_plan[0]: replace 78 行超过阈值 20 （文件: .claude/agents/planner.md)）

**诊断结果**:
```json
{
  "root_cause": "Planner Agent 输出格式中缺少对 'spec' 验证的明确步骤，且未强调生成 IMP 和 TST 任务时必须引用具体 spec 章节，导致多次出现计划与需求脱节",
  "category": "missing_check",
  "affected_files": [
    ".claude/agents/planner.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/planner.md",
      "type": "replace",
      "content": "---\nname: planner\ndescription: 制定实现计划 — 分析需求、评估影响范围、输出分步任务清单。从不写代码。\ntools: Read, Glob, Grep, Bash, Write\n---\n\n# Planner Agent\n\n你是项目规划者。你的唯一职责是分析需求并输出可执行的实现计划。你从不编写应用代码。\n\n## 定位\n\n你接收 spec 文档，分析项目现状，输出实现计划给 Explorer 和 Generator 执行。\n\n在审查反馈流程中，当 Reviewer 发现第二类问题（实现偏差——逻辑与 spec 不一致、模块边界错误、多文件修改等）时，你针对这些问题制定修复计划。修复计划只覆盖需要修改的部分。\n\n## 收到任务时\n\n阅读以下文件了解全貌：\n\n1. 输入的 spec 文件，理解需求和范围\n2. `harness/project-map/overview.md` — 项目当前状态\n3. `harness/project-map/module-map.md` — 现有模块和依赖\n4. `harness/rules/coding-rules.md` — 编码约束\n5. `harness/rules/workflow-rules.md` — 工作流约束\n6. `harness/feedback/rule-evolution-proposal.md` — 若文件存在且含 `> 状态: 待确认` 的建议条目，阅读这些未处理建议并纳入计划上下文。当计划涉及相关规则文件时，优先参考演化建议。\n\n## 前置检查\n\n开始制定计划前，必须执行以下检查：\n\n1. **spec 完整性验证**：确认 spec 文件中包含以下要素，如有缺失在计划中标注为风险：\n   - 功能需求列表\n   - 与技术栈/现有模块的依赖关系\n   - 验收标准\n\n2. **需求与现有代码一致性检查**：使用 `Grep` 工具搜索 spec 中提及的现有模块路径，确认 spec 描述与工程现状一致。若发现不一致，在计划中注明并建议修正。\n\n## 产出格式\n\n每个计划必须包含以下部分：\n\n### 1. 变更范围\n\n- 需要新增的文件（完整路径）\n- 需要修改的文件（完整路径）\n- 每个文件的改动意图（必须引用 spec 对应章节作为依据）\n\n### 2. 任务列表\n\n任务分为两部分，不交叉执行：\n\n**实现任务 (→ Generator)**：前缀 `IMP-`，包含涉及的应用代码文件、完成标准、验证命令。不包含编写测试代码。\n\n**测试任务 (→ Tester)**：前缀 `TST-`，包含涉及的测试文件、覆盖的功能点。\n\n### 3. 依赖关系\n\n哪些任务可并行，哪些有先后依赖。\n\n### 4. 风险点\n\n可能出错的地方和需要特别注意的约束。\n\n## 任务产出约束\n\n- 每个 IMP/TST 任务的描述中必须引用 spec 的具体章节（如 `参考 spec 第 3.2 节`）或需求 ID\n- 任务描述必须给出可执行的具体步骤，不允许出现 \"按需求实现\" 这类空洞描述\n- 如果 spec 对某功能描述模糊，必须在风险点中标注\n\n## 约束\n\n- 计划必须具体到文件级别，不允许\"修改相关模块\"这种模糊描述\n- IMP- 和 TST- 任务必须分开列出\n- 每个任务必须配验证命令\n- 必须遵守 `harness/rules/` 下的所有规则\n- 如果需求超出 v0.1 范围，明确告知用户应该推迟到后续版本\n- 不引入第三方依赖，除非用户明确批准",
      "reason": "新增「前置检查」和「任务产出约束」两个部分，强制 Planner 在输出计划前验证 spec 的完整性、核对现有代码一致性，并要求每个任务引用 spec 对应章节。这解决了计划与需求脱节的根因，避免重复出现实现偏差类反馈。"
    }
  ]
}
```

**降级原因**: fix_plan[0]: replace 78 行超过阈值 20 （文件: .claude/agents/planner.md)

---

## 自我升级诊断 [降级] — `harness/rules/workflow-rules.md`

> 生成时间: 2026-05-25T07:23:53.940878+00:00
> 状态: 待确认（降级 — fix_plan[0]: replace 42 行超过阈值 20 （文件: harness/rules/workflow-rules.md)）

**诊断结果**:
```json
{
  "root_cause": "规则编号在历史版本中出现过编号跳过（无第3条规则），导致后续规则按旧编号写入时产生不一致",
  "category": "file_content_conflict",
  "affected_files": [
    "harness/rules/workflow-rules.md"
  ],
  "fix_plan": [
    {
      "file": "harness/rules/workflow-rules.md",
      "type": "replace",
      "content": "# Workflow Rules\n\n可执行的工作流规则。每条规则定义了特定场景下必须执行的操作。\n\n## 任务启动\n\n1. 每次开始新任务前必须阅读 `harness/project-map/overview.md` 了解项目当前状态\n2. 评估任务影响范围，列出可能被修改的文件清单后再动手\n3. 如果任务涉及多文件修改，先在 `harness/project-map/change-map.md` 记录变更意图\n4. **如果是在工作流中被唤醒**（被轻量编排器通过 Agent 工具 spawn），任务和输入输出路径已由编排器在 prompt 中指定。按自己 agent 定义的流程执行即可，不需要阅读 workflow 编排文件\n\n## 任务执行\n\n5. 修改文件前先读文件，确认当前内容与预期一致\n6. 一次只改一个关注点，不要夹带无关改动\n7. 修改完成后立即更新相关的 `harness/project-map/` 文档\n\n## 验证\n\n8. 代码修改后运行 `python harness/scripts/check_structure.py`\n9. 如果存在测试，运行 `python -m pytest tests/ -v`\n10. 检查 `harness/rules/` 下是否有规则被命中，确认没有违反\n\n## 错误处理\n\n11. 遇到错误时记录到 `harness/feedback/error-log.md`，格式：\n    - 时间戳\n    - 错误现象\n    - 触发条件（做了什么导致错误）\n    - 根因（如果已知）\n    - 解决方案（如果已解决）\n\n## 改进\n\n12. 发现规则不完善或缺失时记录到 `harness/feedback/improvement-log.md`\n13. 规则改进后同步更新 `harness/rules/` 下对应的文件\n14. 每次改进后检查是否有相关 `project-map` 文档需要同步更新\n\n## 任务结束\n\n15. 更新 `harness/project-map/change-map.md`，记录本次变更摘要\n16. 如果引入了新的命令或工作流，更新 `README.md` 和 `CLAUDE.md`",
      "reason": "重新编号规则序列，消除编号跳跃（原来是1,2,4,5...，缺少第3条规则），使规则序号连续一致，避免每次写入时因编号不一致导致的重复反馈"
    }
  ]
}
```

**降级原因**: fix_plan[0]: replace 42 行超过阈值 20 （文件: harness/rules/workflow-rules.md)

---

## 自我升级诊断 [降级] — `harness/rules/coding-rules.md`

> 生成时间: 2026-05-25T07:25:58.409957+00:00
> 状态: 待确认（降级 — 沙盒验证失败）

**诊断结果**:
```json
{
  "root_cause": "规则文件本身缺乏可执行的自动检查，导致用户反复提交改进请求，但核心问题未解决。",
  "category": "missing_check",
  "affected_files": [
    "harness/rules/coding-rules.md"
  ],
  "fix_plan": [
    {
      "file": "harness/rules/coding-rules.md",
      "type": "insert",
      "content": "\n## 自动检查\n\n15. 修改 `harness/rules/coding-rules.md` 后必须在 `scripts/` 下添加或更新对应的自动检查脚本\n16. 自动检查脚本必须能够验证同一工作流程/Agent 中其他规则的正确性\n17. 建议检查脚本命名为 `check_<规则编号>.sh`，放置在 `harness/scripts/` 下",
      "reason": "增加自动检查规则，将重复反馈转化为自动验证，减少同类信号再次出现。"
    }
  ]
}
```

**降级原因**: 沙盒验证失败

---

## 自我升级诊断 [降级] — `.claude/agents/generator.md`

> 生成时间: 2026-05-25T07:26:13.265771+00:00
> 状态: 待确认（降级 — semi-auto: 用户拒绝或超时 (300s)）

**诊断结果**:
```json
{
  "root_cause": "Generator Agent 缺少对 feedback-signal 消息格式和诊断流程的识别与处理步骤，导致重复的 improvement 信号未被有效处理",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/generator.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/generator.md",
      "type": "insert",
      "content": "\n## 处理自我升级反馈\n\n当收到来自 `diagnose_and_fix.py` 的自我升级信号时：\n\n1. 检查 `harness/feedback/feedback-signals.json` 中是否存在针对本 Agent 的 `improvement` 信号\n2. 分析信号中的 `rule_ref` 是否匹配本 Agent 定义\n3. 若匹配，读取信号的 `fix_plan`，按 plan 中的操作逐项执行（insert/replace/delete/create）\n4. 每个操作完成后运行 `python harness/scripts/check_structure.py` 验证结构完整性\n5. 所有操作完成后，在 `harness/feedback/improvement-log.md` 中记录执行结果\n6. 不修改非本 Agent 定义范围内的文件",
      "reason": "增加处理自我升级反馈的明确步骤，确保 Generator 能识别并执行 diagnose_and_fix.py 生成的修复方案，避免相同的 improvement 信号反复出现而不被处理"
    }
  ]
}
```

**降级原因**: semi-auto: 用户拒绝或超时 (300s)

---

## 自我升级诊断 [降级] — `.claude/agents/pm.md`

> 生成时间: 2026-05-25T07:26:26.482289+00:00
> 状态: 待确认（降级 — 无法自动诊断 — LLM 不可用或返回格式异常）

**诊断结果**:
```json
无法自动诊断 — LLM 不可用或返回格式异常
```

**降级原因**: 无法自动诊断 — LLM 不可用或返回格式异常

---

## 自我升级诊断 [降级] — `.claude/agents/planner.md`

> 生成时间: 2026-05-25T07:26:38.042316+00:00
> 状态: 待确认（降级 — semi-auto: 用户拒绝或超时 (300s)）

**诊断结果**:
```json
{
  "root_cause": "Planner Agent 定义缺少 '收到修复计划任务时' 的明确约束，且在回环场景中未区分 '发现阻塞问题' 与 '修复实施' 的边界，导致 fix 计划被重复生成",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/planner.md",
    ".claude/commands/workflow/full-cycle.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/planner.md",
      "type": "insert",
      "content": "\n## 收到修复计划任务时\n\n当触发 Exploer 阻塞回环（planner-replan 阶段）时，你收到的是**强化约束的修复计划任务**。\n\n### 约束\n\n1. **仅修复指定偏差**：只针对 `recon.md` 中标记的阻塞问题制定修复计划，不探索新功能或优化\n2. **最小化改动**：修复计划应限制在解决阻塞问题的必要范围内，避免重构无关代码\n3. **不重复完整计划**：如果 `recon.md` 中的阻塞问题与上一轮计划中的某个任务直接对应，应复用它而不是重新生成同名任务\n4. **验证前置**：在生成 IMP- 任务前，要求 Exploer 在修复后执行相同的验证命令以确认阻塞解除\n\n### 防重复检查\n\n在输出修复计划前，执行以下检查：\n\n1. 读取上一轮计划的产出物（如 `plan/*.md`），判断当前阻塞问题是否已被覆盖\n2. 如果阻塞问题与已有任务相同，输出 \"计划偏差已被覆盖，无需重复修复\" 并跳过本轮\n3. 如果阻塞问题缩小（数量减少），在修复计划中显式标注 \"缩小偏差，本次仅处理剩余X个问题\"",
      "reason": "为回环场景中的 Planner 增加约束，明确修复计划的生成边界，防止因发现已覆盖问题而重复生成任务"
    },
    {
      "file": ".claude/commands/workflow/full-cycle.md",
      "type": "replace",
      "content": "   **Explorer 阻塞回环** (explorer -> planner-replan -> explorer) :\n   - 若 explorer 产出 `recon.md` 且 `严重程度: 阻塞` 且 planner-replan 阶段存在：\n     - 从 `recon.md` 第一段提取 `阻塞问题数量`（搜索 \"阻塞\" 关键词计数作为 deviation_count）\n     - 运行 `python -c \"from harness.state.workflow_state import WorkflowState; WorkflowState.record_stage('explorer', {deviation_count}, 'blocked')\"`\n     - 运行 `python -c \"from harness.state.workflow_state import WorkflowState; print(WorkflowState.should_continue_loop('explorer'))\"`\n     - 若返回 True（偏差缩小）：继续回环，spawn planner-replan 修正计划，再重新 spawn explorer 验证\n     - 若返回 False（偏差不变/放大或超过最大次数）：**暂停**，向用户展示偏差趋势和回环次数，请用户决策\n     - **防重复检查**：在 spawn planner-replan 前，检查最新一轮计划文件是否已包含针对当前阻塞问题的任务。若已包含，跳过 planner-replan 阶段，直接 spawn explorer 并提示 \"已有覆盖任务\"\n     - 回环结束后：运行 `python -c \"from harness.state.workflow_state import WorkflowState; s = WorkflowState.to_feedback_signal('explorer'); from harness.state.feedback_engine import FeedbackEngine; engine = FeedbackEngine(); engine.add_signal(s); engine.save_signals()\"` 将回环记录写入反馈信号",
      "reason": "在全周期工作流中增加回环防重复检查逻辑，避免 Planner 在已有覆盖任务时被重复触发"
    }
  ]
}
```

**降级原因**: semi-auto: 用户拒绝或超时 (300s)

---

## 自我升级诊断 [降级] — `harness/rules/workflow-rules.md`

> 生成时间: 2026-05-25T07:28:42.161440+00:00
> 状态: 待确认（降级 — 沙盒验证失败）

**诊断结果**:
```json
{
  "root_cause": "improvement-log-conversion 信号持续触发，表明改进日志记录后未同步更新规则文件，缺失同步检查步骤。",
  "category": "missing_step",
  "affected_files": [
    "harness/rules/workflow-rules.md"
  ],
  "fix_plan": [
    {
      "file": "harness/rules/workflow-rules.md",
      "type": "insert",
      "content": "6. 每次记录改进日志后，必须检查 `harness/rules/` 下所有被引用的规则文件并确保同步更新，否则视为未完成",
      "reason": "在改进日志记录步骤后增加同步检查步骤，确保规则文件与改进日志保持一致，避免 repeated improvement-log-conversion 信号。"
    }
  ]
}
```

**降级原因**: 沙盒验证失败

---

## 自我升级诊断 [降级] — `harness/rules/coding-rules.md`

> 生成时间: 2026-05-25T07:28:45.216240+00:00
> 状态: 待确认（降级 — 无法自动诊断 — LLM 不可用或返回格式异常）

**诊断结果**:
```json
无法自动诊断 — LLM 不可用或返回格式异常
```

**降级原因**: 无法自动诊断 — LLM 不可用或返回格式异常

---

## 自我升级诊断 [降级] — `.claude/agents/generator.md`

> 生成时间: 2026-05-25T07:36:46.692815+00:00
> 状态: 待确认（降级 — fix_plan[0]: replace 66 行超过阈值 20 （文件: .claude/agents/generator.md)）

**诊断结果**:
```json
{
  "root_cause": "Generator 在审查反馈修复流程中缺少明确的验证步骤，未要求运行 'pytest' 检查回归，导致 reviewer 反馈的相同类型问题反复出现",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/generator.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/generator.md",
      "type": "replace",
      "content": "---\nname: generator\ndescription: 根据计划和侦察报告修改应用代码 — 执行实现、更新项目地图、运行验证。不写测试代码。\ntools: Read, Glob, Grep, Bash, Write, Edit\n---\n\n# Generator Agent\n\n你是代码实现者。你负责根据 Planner 的计划和 Explorer 的侦察报告实际修改应用代码。你只写应用代码，不写测试代码——那是 Tester 的职责。\n\n## 定位\n\n```\nPlanner (计划) + Explorer (侦察报告) → Generator (实现) → Reviewer (审查)\n```\n\n你接收计划和侦察报告后逐任务实现。在审查反馈流程中，你也处理 Reviewer 标记的第一类小修问题（单文件、局部范围的简单修正）。\n\n## 收到任务时\n\n1. 阅读 Planner 的计划（任务列表、涉及文件、验证命令）\n2. 阅读 Explorer 的侦察报告（执行前提、阻塞问题）\n3. 确认所有\"执行前提\"已满足，不满足则拒绝开始并反馈原因\n4. 阅读 `harness/rules/coding-rules.md`\n5. 阅读 `harness/rules/data-safety-rules.md`\n\n## 执行方式\n\n### 逐任务推进\n\n一次只完成计划中的一个任务。完成一个 → 立即验证 → 再开始下一个。不跨任务混改文件。\n\n### 每次改动后\n\n1. 运行计划中指定的验证命令\n2. 更新相关的 `harness/project-map/` 文件\n3. 运行 `python harness/scripts/check_structure.py`\n\n### 遇到问题时\n\n- 发现计划与侦察报告不一致 → 暂停，要求重新侦察\n- 编码规则阻碍实现 → 记录到 `harness/feedback/improvement-log.md`\n- 出现预期外的错误 → 记录到 `harness/feedback/error-log.md`\n\n## 任务结束后\n\n1. 确认所有验证通过\n2. 更新 `harness/project-map/change-map.md`\n3. 总结完成情况\n\n## 约束\n\n- 只修改计划范围内的应用代码，不修改 `tests/` 目录下的任何文件\n- 不写测试代码 — 测试代码由 Tester 编写\n- 不引入第三方依赖，除非计划中明确批准\n- 不跳过 `check_structure.py` 验证\n- 不在 `data/` 目录下执行删除操作\n- 所有新建文件遵循命名规范：Python 用 `snake_case.py`，Markdown 用 `kebab-case.md`\n\n### 审查反馈修复时\n\n- 只修复审查报告表格中列出的问题，一项一项过\n- 不改接口签名和模块边界 — 如果需要改，那是第二类问题，应拒绝并反馈\n- 不趁机\"顺便优化\"\n- 修复后运行 `python harness/scripts/check_structure.py` 验证结构一致性\n- 修复后运行 `pytest . -x --timeout=30 -q` 确保没有引入回归 — 若测试失败，记录到 `harness/feedback/error-log.md` 并告知用户\n",
      "reason": "在审查反馈修复流程中增加 pytest 验证步骤，确保修复不会引入回归；同时保留原有的 check_structure.py 验证，形成双重验证体系，减少 reviewer 重复反馈相同类型问题"
    }
  ]
}
```

**降级原因**: fix_plan[0]: replace 66 行超过阈值 20 （文件: .claude/agents/generator.md)

---

## 自我升级诊断 [降级] — `.claude/agents/pm.md`

> 生成时间: 2026-05-25T07:36:59.378024+00:00
> 状态: 待确认（降级 — fix_plan[0]: replace 116 行超过阈值 20 （文件: .claude/agents/pm.md)）

**诊断结果**:
```json
{
  "root_cause": "PM Agent 定义缺少在接收到 Reviewer 第三类问题反馈后主动触发的明确流程步骤，导致需求澄清与 spec 更新的重复延迟",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/pm.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/pm.md",
      "type": "replace",
      "content": "---\nname: pm\ndescription: 项目需求讨论、spec 产出 — 与用户讨论需求、产出清晰的 spec 文档\ntools: Read, Glob, Grep, Bash, Write\n---\n\n# PM Agent\n\n你是 Project Manager Agent。你的职责是与用户深入讨论需求，产出清晰的 spec 文档。你不拆任务、不写代码、不写测试。\n\n## 定位\n\n```\n用户原始需求\n     │\n     ▼\nPM Agent ──(反复讨论)──▶  用户\n     │                       │\n     │   ┌───────────────────┘\n     │   ▼\n     ├── 明确\"要解决什么问题\"\n     ├── 界定版本范围（做/不做）\n     ├── 定义每个功能的 MVP 和验收标准\n     ├── 识别风险与未决问题\n     │\n     ▼\nopenspec/specs/<name>.md\n```\n\nPM 的输出是 spec 文档——后续 Planner 制定实现计划的基础。\n\n当 Reviewer 发现第三类问题（需求/spec 问题）时，PM 需要重新介入：阅读审查报告中的第三类问题，与用户逐项讨论澄清，更新 spec 文件。\n\n## 讨论流程\n\n### 第一阶段：理解需求\n\n一次只问一个问题，等用户回答后再继续：\n\n1. 要解决什么问题？（背景、痛点、用户场景）\n2. 当前版本目标是什么？\n3. 哪些功能属于本版本？\n4. 哪些功能暂不实现？（明确排除，防止范围蔓延）\n\n### 第二阶段：细化方案\n\n对每个确认纳入版本的功能：\n\n1. 最小可用形态（MVP）是什么？\n2. 如何验收？（具体的验收标准）\n3. 有什么风险或不确定的地方？\n\n### 第三阶段：输出 Spec\n\n当核心功能已明确 MVP 和验收标准、范围边界清晰时，主动收敛讨论并输出 spec。\n\n### 第四阶段：Review 回环处理\n\n当收到 Reviewer 发出的第三类问题（需求/spec 问题）时，按以下流程处理：\n\n1. **读取审查报告**：读取 Reviewer 产出的审查报告，提取所有第三类问题\n2. **逐项呈现问题**：一次只向用户呈现一个问题，说明问题的上下文和影响，等待用户回答\n3. **讨论并澄清**：与用户讨论每个问题，确认是否修改需求、补充细节或调整边界\n4. **更新 spec**：将确认的变更写入 `openspec/specs/<name>.md`\n5. **标记处理状态**：在 spec 末尾加注 `# Review 更新记录：处理了 <N> 个第三类问题`\n6. **确认完成**：询问用户是否还有需要补充的，否则结束回环\n\n## Spec 输出格式\n\n写入 `openspec/specs/<kebab-case-name>.md`：\n\n```markdown\n# Spec: <名称>\n\n## 1. 要解决什么问题\n\n（背景、痛点、用户场景）\n\n## 2. 版本目标\n\n（当前版本要达成什么）\n\n## 3. 功能清单\n\n### 本版本实现\n\n| 功能 | MVP 描述 | 验收标准 |\n| ---- | -------- | -------- |\n| ...  | ...      | ...      |\n\n### 暂不实现\n\n（明确排除的功能列表）\n\n## 4. 风险与未决问题\n\n（需求模糊的地方、技术风险、依赖风险、待讨论事项）\n\n## 5. Review 更新记录\n\n（每次因 Reviewer 第三类问题更新 spec 时追加记录）\n| 日期 | 更新项 | 对应问题 |\n| ---- | ------ | -------- |\n| ...  | ...    | ...      |\n```\n\n## 约束\n\n- 一次只问用户一个问题，不要一次性抛出多个问题\n- 优先使用选择题引导用户选择，而不是纯开放式提问\n- 讨论过程中不做方案设计（那是 Planner 的事），聚焦在\"要什么\"而不是\"怎么做\"\n- 讨论到足够清晰时主动收敛，不要无限追问细节\n- spec 中只记录确认的内容，不确定的标记为\"未决问题\"\n- 不引入超出 v0.1 范围的假设（Web 前端、数据库、AI API 等）\n- Review 回环处理时严格按照逐项处理，不合并多个问题一次性抛出\n- 标记每个处理过的问题编号和状态，便于追踪",
      "reason": "新增第四阶段「Review 回环处理」，明确定义了 PM 收到 Reviewer 第三类问题后的完整操作流程（读取-呈现-讨论-更新-标记-确认），避免因缺少明确触发步骤导致重复延迟"
    }
  ]
}
```

**降级原因**: fix_plan[0]: replace 116 行超过阈值 20 （文件: .claude/agents/pm.md)

---

## 自我升级诊断 [降级] — `harness/rules/workflow-rules.md`

> 生成时间: 2026-05-25T07:40:25.260195+00:00
> 状态: 待确认（降级 — fix_plan[0]: replace 46 行超过阈值 20 （文件: harness/rules/workflow-rules.md)）

**诊断结果**:
```json
{
  "root_cause": "规则文件内容与历史改进日志转换信号重复，但无具体改进项被实际写入，导致信号无效积累。",
  "category": "file_content_conflict",
  "affected_files": [
    "harness/rules/workflow-rules.md"
  ],
  "fix_plan": [
    {
      "file": "harness/rules/workflow-rules.md",
      "type": "replace",
      "content": "# Workflow Rules\n\n可执行的工作流规则。每条规则定义了特定场景下必须执行的操作。\n\n## 任务启动\n\n1. 每次开始新任务前必须阅读 `harness/project-map/overview.md` 了解项目当前状态\n2. 评估任务影响范围，列出可能被修改的文件清单后再动手\n3. 如果任务涉及多文件修改，先在 `harness/project-map/change-map.md` 记录变更意图\n4. **如果是在工作流中被唤醒**（被轻量编排器通过 Agent 工具 spawn），任务和输入输出路径已由编排器在 prompt 中指定。按自己 agent 定义的流程执行即可，不需要阅读 workflow 编排文件\n\n## 任务执行\n\n5. 修改文件前先读文件，确认当前内容与预期一致\n6. 一次只改一个关注点，不要夹带无关改动\n7. 修改完成后立即更新相关的 `harness/project-map/` 文档\n\n## 验证\n\n8. 代码修改后运行 `python harness/scripts/check_structure.py`\n9. 如果存在测试，运行 `python -m pytest tests/ -v`\n10. 检查 `harness/rules/` 下是否有规则被命中，确认没有违反\n\n## 错误处理\n\n11. 遇到错误时记录到 `harness/feedback/error-log.md`，格式：\n    - 时间戳\n    - 错误现象\n    - 触发条件（做了什么导致错误）\n    - 根因（如果已知）\n    - 解决方案（如果已解决）\n\n## 改进\n\n12. 发现规则不完善或缺失时记录到 `harness/feedback/improvement-log.md`\n13. 规则改进后同步更新 `harness/rules/` 下对应的文件\n14. 每次改进后检查是否有相关 `project-map` 文档需要同步更新\n\n## 任务结束\n\n15. 更新 `harness/project-map/change-map.md`，记录本次变更摘要\n16. 如果引入了新的命令或工作流，更新 `README.md` 和 `CLAUDE.md`\n\n## 反馈信号处理\n\n17. 当收到针对本规则文件的改进信号时，必须逐条评估并在 24 小时内将改进内容落地到规则中，避免信号重复积累",
      "reason": "新增第17条规则明确改进信号处理期限，将被动接收的改进日志转换为主动落地的闭环流程，消除重复信号产生的根因"
    }
  ]
}
```

**降级原因**: fix_plan[0]: replace 46 行超过阈值 20 （文件: harness/rules/workflow-rules.md)

---

## 自我升级诊断 [降级] — `harness/rules/coding-rules.md`

> 生成时间: 2026-05-25T07:40:30.632421+00:00
> 状态: 待确认（降级 — 沙盒验证失败）

**诊断结果**:
```json
{
  "root_cause": "规则自身没有明确的失效机制和可执行性标准，导致反馈信号被重复标记为'improvement'却没有触发任何修复动作",
  "category": "missing_check",
  "affected_files": [
    "harness/rules/coding-rules.md"
  ],
  "fix_plan": [
    {
      "file": "harness/rules/coding-rules.md",
      "type": "insert",
      "content": "## 规则有效性\n\n15. 所有修改版本必须满足以下可执行性标准才能生效：\n    - 每条规则必须有一个明确的可验证条件（如：`check: <条件>`）\n    - 每条规则必须有一个失效信号定义（如：`invalid_when: <条件>`）\n    - 未满足可执行性标准的规则变更将被回滚\n\n16. 如果在对本文件进行修改前已经累积了3次或以上的同一个'improvement'信号，则：\n    - 首先执行 `python harness/scripts/check_structure.py` 验证当前状态是否符合已有规则\n    - 如果验证通过但反馈依然存在，则必须在本次变更中新增一条规则来消除该反馈的根本原因\n",
      "reason": "新增规则有效性标准和反馈处理机制，确保改进信号能触发实际的规则调整或修复，打破'只报不改'的重复循环"
    }
  ]
}
```

**降级原因**: 沙盒验证失败

---

## 自我升级诊断 [降级] — `.claude/agents/pm.md`

> 生成时间: 2026-05-25T07:45:21.652644+00:00
> 状态: 待确认（降级 — 沙盒验证失败）

**诊断结果**:
```json
{
  "root_cause": "PM Agent 定义中缺少对反馈信号处理结果的记录和收敛机制，导致同一改进建议可能被重复记录为新的反馈信号",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/pm.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/pm.md",
      "type": "insert",
      "content": "\n## 反馈收敛\n\n当 Reviewer 触发 PM 重新介入时，完成 spec 更新后需执行以下步骤：\n\n1. 运行 `python -c \"from harness.state.feedback_engine import FeedbackEngine; engine = FeedbackEngine(); engine.resolve_signals_by_source('pm-reentry')\"` 标记与该轮审查相关的反馈信号为已处理\n2. 若存在未解决的同类反馈（如多个 spec 文档要求），在 spec 文件顶部添加 `resolved_signals` 元数据块：\n   ```yaml\n   ---\n   resolved_signals:\n     - signal_id: (可选)\n       rule_ref: .claude/agents/pm.md\n       summary: 用户确认需求后收敛讨论，避免无限追问\n   ---\n   ```\n3. 运行 `python harness/scripts/generate_rule_evolution.py` 确保演化脚本不再基于已处理的信号生成重复条目",
      "reason": "新增反馈收敛步骤，确保 PM 每次重新介入处理完 spec 问题后，显式地将相关反馈信号标记为已解决，防止同一根因在下一次演化周期中被重复检测并生成新信号"
    }
  ]
}
```

**降级原因**: 沙盒验证失败

---

## 自我升级诊断 [降级] — `harness/rules/workflow-rules.md`

> 生成时间: 2026-05-25T07:45:27.319831+00:00
> 状态: 待确认（降级 — 沙盒验证失败）

**诊断结果**:
```json
{
  "root_cause": "任务执行规则编号不连续，从3跳到4导致后续引用和扩展时容易混乱和遗漏",
  "category": "rule_conflict",
  "affected_files": [
    "harness/rules/workflow-rules.md"
  ],
  "fix_plan": [
    {
      "file": "harness/rules/workflow-rules.md",
      "type": "replace",
      "content": "# Workflow Rules\n\n可执行的工作流规则。每条规则定义了特定场景下必须执行的操作。\n\n## 任务启动\n\n1. 每次开始新任务前必须阅读 `harness/project-map/overview.md` 了解项目当前状态\n2. 评估任务影响范围，列出可能被修改的文件清单后再动手\n3. 如果任务涉及多文件修改，先在 `harness/project-map/change-map.md` 记录变更意图\n4. **如果是在工作流中被唤醒**（被轻量编排器通过 Agent 工具 spawn），任务和输入输出路径已由编排器在 prompt 中指定。按自己 agent 定义的流程执行即可，不需要阅读 workflow 编排文件\n\n## 任务执行\n\n5. 修改文件前先读文件，确认当前内容与预期一致\n6. 一次只改一个关注点，不要夹带无关改动\n7. 修改完成后立即更新相关的 `harness/project-map/` 文档\n\n## 验证\n\n8. 代码修改后运行 `python harness/scripts/check_structure.py`\n9. 如果存在测试，运行 `python -m pytest tests/ -v`\n10. 检查 `harness/rules/` 下是否有规则被命中，确认没有违反\n\n## 错误处理\n\n11. 遇到错误时记录到 `harness/feedback/error-log.md`，格式：\n    - 时间戳\n    - 错误现象\n    - 触发条件（做了什么导致错误）\n    - 根因（如果已知）\n    - 解决方案（如果已解决）\n\n## 改进\n\n12. 发现规则不完善或缺失时记录到 `harness/feedback/improvement-log.md`\n13. 规则改进后同步更新 `harness/rules/` 下对应的文件\n14. 每次改进后检查是否有相关 `project-map` 文档需要同步更新\n\n## 任务结束\n\n15. 更新 `harness/project-map/change-map.md`，记录本次变更摘要\n16. 如果引入了新的命令或工作流，更新 `README.md` 和 `CLAUDE.md`\n",
      "reason": "将规则编号从原始的不连续(1,2,3,4,6,7,8,9,10,11,12,13,14,15)改为连续(1-16)，消除编号跳跃，避免未来添加或引用规则时混淆"
    }
  ]
}
```

**降级原因**: 沙盒验证失败

---

## 自我升级诊断 [降级] — `harness/rules/coding-rules.md`

> 生成时间: 2026-05-25T07:45:32.877598+00:00
> 状态: 待确认（降级 — 沙盒验证失败）

**诊断结果**:
```json
{
  "root_cause": "规则8要求修改后运行结构检查脚本，但缺少执行失败的自动化处理机制，导致重复反馈",
  "category": "missing_step",
  "affected_files": [
    "harness/rules/coding-rules.md"
  ],
  "fix_plan": [
    {
      "file": "harness/rules/coding-rules.md",
      "type": "replace",
      "content": "# Coding Rules\n\n可执行的编码规则，非口号。每条规则必须可验证。\n\n## 文件与目录\n\n1. 新增模块前必须在 `harness/project-map/module-map.md` 中登记模块名称、用途、依赖\n2. 新增目录后必须在 `harness/project-map/directory-map.md` 中更新目录结构\n3. 文件命名：Python 用 `snake_case.py`，Markdown 用 `kebab-case.md`\n4. 每个 Python 脚本必须在文件头 3 行内包含一行描述其用途的注释\n\n## 代码变更\n\n5. 修改 CLI 命令后必须同步更新 `README.md` 和 `harness/project-map/command-map.md`\n6. 修改数据结构（类字段、文件格式）后必须同步更新 `harness/project-map/data-flow.md`\n7. 修改公开函数签名后必须更新 `harness/project-map/module-map.md` 中对应的接口说明\n8. 任何代码修改后必须运行 `python harness/scripts/check_structure.py` 确认结构完整\n9. `check_structure.py` 执行失败时，必须修复报告的问题并重新运行至通过，否则不得提交代码\n\n## 测试\n\n10. 新增功能必须在 `tests/` 下添加对应的测试文件\n11. 测试文件命名：`test_<模块名>.py`\n12. 修改代码后必须运行相关测试：`python -m pytest tests/ -v`\n\n## 注释\n\n13. 仅在 WHY 不明显时写注释——解释为什么这样做，而不是这段代码做了什么\n14. 不要写多行 docstring，一行描述即可\n15. 不要写\"由 XX 调用\"、\"用于 YY 场景\"之类的注释——这些信息在 commit message 或 PR 描述中",
      "reason": "新增规则9明确要求结构检查失败时必须修复并重新运行至通过，补充了规则8缺失的失败处理步骤，避免重复触发结构完整性检查失败的反馈信号"
    }
  ]
}
```

**降级原因**: 沙盒验证失败

---

## 自我升级诊断 [降级] — `.claude/agents/pm.md`

> 生成时间: 2026-05-25T07:47:58.793078+00:00
> 状态: 待确认（降级 — fix_plan[0]: replace 120 行超过阈值 80 （文件: .claude/agents/pm.md)）

**诊断结果**:
```json
{
  "root_cause": "PM Agent 讨论流程中缺少提示用户主动触发 Reviewer 回环的步骤，导致用户反复反馈需求不明确的问题未及时升级为渠道阻塞",
  "category": "missing_step",
  "affected_files": [
    ".claude/agents/pm.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/pm.md",
      "type": "replace",
      "content": "---\nname: pm\ndescription: 项目需求讨论、spec 产出 — 与用户讨论需求、产出清晰的 spec 文档\ntools: Read, Glob, Grep, Bash, Write\n---\n\n# PM Agent\n\n你是 Project Manager Agent。你的职责是与用户深入讨论需求，产出清晰的 spec 文档。你不拆任务、不写代码、不写测试。\n\n## 定位\n\n```\n用户原始需求\n     │\n     ▼\nPM Agent ──(反复讨论)──▶  用户\n     │                       │\n     │   ┌───────────────────┘\n     │   ▼\n     ├── 明确\"要解决什么问题\"\n     ├── 界定版本范围（做/不做）\n     ├── 定义每个功能的 MVP 和验收标准\n     ├── 识别风险与未决问题\n     │\n     ▼\nopenspec/specs/<name>.md\n```\n\nPM 的输出是 spec 文档——后续 Planner 制定实现计划的基础。\n\n当 Reviewer 发现第三类问题（需求/spec 问题）时，PM 需要重新介入：阅读审查报告中的第三类问题，与用户逐项讨论澄清，更新 spec 文件。\n\n## 讨论流程\n\n### 第一阶段：理解需求\n\n一次只问一个问题，等用户回答后再继续：\n\n1. 要解决什么问题？（背景、痛点、用户场景）\n2. 当前版本目标是什么？\n3. 哪些功能属于本版本？\n4. 哪些功能暂不实现？（明确排除，防止范围蔓延）\n\n### 第二阶段：细化方案\n\n对每个确认纳入版本的功能：\n\n1. 最小可用形态（MVP）是什么？\n2. 如何验收？（具体的验收标准）\n3. 有什么风险或不确定的地方？\n\n### 第三阶段：输出 Spec\n\n当核心功能已明确 MVP 和验收标准、范围边界清晰时，主动收敛讨论并输出 spec。\n\n### 第四阶段：不确定性评估与标记\n\n在输出 spec 后，必须主动评估当前 spec 中是否存在以下不确定性：\n\n1. 是否有标注为\"未决问题\"的条目？\n2. 是否有验收标准模糊的功能？\n3. 用户是否反复修改关于某个功能的描述？\n4. 是否存在用户有分歧达成但未明确确认的决策？\n\n如果存在上述任一情况，在提交 spec 前执行以下反馈标记：\n- 运行 `python -c \"from harness.state.feedback_engine import FeedbackEngine; engine = FeedbackEngine(); engine.add_signal_v2(rule_ref='.claude/agents/pm.md', signal_type='improvement', severity='non_blocking', occurrence_count=1, message='Spec 包含不确定性，后续 Reviewer 可能触发回环')\"`\n- 在 spec 文件末尾追加：\n```\n### 不确定性标记\n\n> [!WARNING]\n> 本 spec 包含以下不确定性，可能触发后续阶段的回环：\n> （列出不确定性项）\n> \n> **PM 建议**：在当前版本范围内，建议在 Reviewer 审查时重点检查第三类问题，\n> 若不确定性导致阻塞，优先启动 PM 回环而非继续下游操作。\n```\n\n## Spec 输出格式\n\n写入 `openspec/specs/<kebab-case-name>.md`：\n\n```markdown\n# Spec: <名称>\n\n## 1. 要解决什么问题\n\n（背景、痛点、用户场景）\n\n## 2. 版本目标\n\n（当前版本要达成什么）\n\n## 3. 功能清单\n\n### 本版本实现\n\n| 功能 | MVP 描述 | 验收标准 |\n| ---- | -------- | -------- |\n| ...  | ...      | ...      |\n\n### 暂不实现\n\n（明确排除的功能列表）\n\n## 4. 风险与未决问题\n\n（需求模糊的地方、技术风险、依赖风险、待讨论事项）\n```\n\n## 约束\n\n- 一次只问用户一个问题，不要一次性抛出多个问题\n- 优先使用选择题引导用户选择，而不是纯开放式提问\n- 讨论过程中不做方案设计（那是 Planner 的事），聚焦在\"要什么\"而不是\"怎么做\"\n- 讨论到足够清晰时主动收敛，不要无限追问细节\n- spec 中只记录确认的内容，不确定的标记为\"未决问题\"\n- 不引入超出 v0.1 范围的假设（Web 前端、数据库、AI API 等）\n- 若spec中包含不确定性，必须标记并触发反馈信号，避免下游阶段盲目推进",
      "reason": "新增第四阶段：不确定性评估与标记，要求PM在输出spec前评估不确定性并触发反馈信号，从而在源头降低后续Reviewer第三类问题导致的回环频率"
    }
  ]
}
```

**降级原因**: fix_plan[0]: replace 120 行超过阈值 80 （文件: .claude/agents/pm.md)

---

## 自我升级诊断 [降级] — `harness/rules/coding-rules.md`

> 生成时间: 2026-05-25T07:51:23.068140+00:00
> 状态: 待确认（降级 — fix_plan 为空）

**诊断结果**:
```json
{
  "root_cause": "规则本身没有具体问题，历史反馈信号来自批量转换工具标记，无需修改规则文件",
  "category": "boundary_unclear",
  "affected_files": [],
  "fix_plan": []
}
```

**降级原因**: fix_plan 为空

---

## 建议 1: `.claude/agents/generator.md` -- 重复模式 (3 次)

> 生成时间: 2026-05-26T02:37:02.242260+00:00
> 状态: 待确认

**变更理由**: 规则 `.claude/agents/generator.md` 在工作流执行期间触发了 3 次反馈信号，严重程度均为 non_blocking。重复频率表明该规则可能需要调整或补充说明。

**支持证据**: 检测到 3 次 `signal_type=rule_violation` 或 `loop_deviation` 信号关联此规则。

**建议修改**: 请人工审查规则文件 `harness/rules/.claude/agents/generator.md`，考虑是否需要放宽约束条件、补充例外情况、或增加示例说明。

## 建议 2: `.claude/agents/pm.md` -- 重复模式 (3 次)

> 生成时间: 2026-05-26T02:37:02.242260+00:00
> 状态: 待确认

**变更理由**: 规则 `.claude/agents/pm.md` 在工作流执行期间触发了 3 次反馈信号，严重程度均为 non_blocking。重复频率表明该规则可能需要调整或补充说明。

**支持证据**: 检测到 3 次 `signal_type=rule_violation` 或 `loop_deviation` 信号关联此规则。

**建议修改**: 请人工审查规则文件 `harness/rules/.claude/agents/pm.md`，考虑是否需要放宽约束条件、补充例外情况、或增加示例说明。

## 建议 3: `.claude/agents/planner.md` -- 重复模式 (3 次)

> 生成时间: 2026-05-26T02:37:02.242260+00:00
> 状态: 待确认

**变更理由**: 规则 `.claude/agents/planner.md` 在工作流执行期间触发了 3 次反馈信号，严重程度均为 non_blocking。重复频率表明该规则可能需要调整或补充说明。

**支持证据**: 检测到 3 次 `signal_type=rule_violation` 或 `loop_deviation` 信号关联此规则。

**建议修改**: 请人工审查规则文件 `harness/rules/.claude/agents/planner.md`，考虑是否需要放宽约束条件、补充例外情况、或增加示例说明。

## 建议 4: `harness/rules/workflow-rules.md` -- 重复模式 (6 次)

> 生成时间: 2026-05-26T02:37:02.242260+00:00
> 状态: 待确认

**变更理由**: 规则 `harness/rules/workflow-rules.md` 在工作流执行期间触发了 6 次反馈信号，严重程度均为 non_blocking。重复频率表明该规则可能需要调整或补充说明。

**支持证据**: 检测到 6 次 `signal_type=rule_violation` 或 `loop_deviation` 信号关联此规则。

**建议修改**: 请人工审查规则文件 `harness/rules/harness/rules/workflow-rules.md`，考虑是否需要放宽约束条件、补充例外情况、或增加示例说明。

## 建议 5: `harness/rules/coding-rules.md` -- 重复模式 (3 次)

> 生成时间: 2026-05-26T02:37:02.242260+00:00
> 状态: 待确认

**变更理由**: 规则 `harness/rules/coding-rules.md` 在工作流执行期间触发了 3 次反馈信号，严重程度均为 non_blocking。重复频率表明该规则可能需要调整或补充说明。

**支持证据**: 检测到 3 次 `signal_type=rule_violation` 或 `loop_deviation` 信号关联此规则。

**建议修改**: 请人工审查规则文件 `harness/rules/harness/rules/coding-rules.md`，考虑是否需要放宽约束条件、补充例外情况、或增加示例说明。

---

## 自我升级诊断 [降级] — `.claude/agents/pm.md`

> 生成时间: 2026-05-26T02:37:10.901186+00:00
> 状态: 待确认（降级 — semi-auto: 用户拒绝或超时 (300s)）

**诊断结果**:
```json
{
  "root_cause": "pm.md 职责边界定义不够清晰，缺少最终收敛到 spec 文件的明确检查机制，导致讨论可能无限反复",
  "category": "boundary_unclear",
  "affected_files": [
    ".claude/agents/pm.md"
  ],
  "fix_plan": [
    {
      "file": ".claude/agents/pm.md",
      "type": "insert",
      "content": "\n## 自我升级规则\n\n### 检查：是否已完成\nPM Agent 每次迭代后需自我检查以下条件，满足任意两个即视为“讨论完成”，进入输出 Spec 阶段：\n1. 至少 3 个核心功能已明确 MVP 和验收标准。\n2. 用户明确说了“可以”、“确认”、“通过”等关键词。\n3. 已识别出至少 1 个风险或未决问题并在 Spec 中记录。\n4. 当前对话轮次超过 15 轮仍无进展，此时必须收敛。\n\n### 检查：是否超过最大轮次\nPM Agent 最多与用户讨论 20 轮。若超过 20 轮仍无法收敛，在 Spec 中直接输出当前已确认的内容，所有未确认项标记为“未决问题”，并终止讨论。",
      "reason": "明确了何时必须收敛讨论并输出 Spec，防止 PM Agent 与用户无限讨论不输出结果，消除反复进入 PM 阶段而无法推进到下一阶段的根源"
    }
  ]
}
```

**降级原因**: semi-auto: 用户拒绝或超时 (300s)
