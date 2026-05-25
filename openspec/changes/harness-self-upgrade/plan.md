# Plan: Harness 框架自我升级系统 v0.1

## 1. 变更范围

### 新建文件

| 文件路径 | 改动意图 |
| -------- | -------- |
| `harness/config/self-upgrade.yaml` | 自动程度配置：按 glob 模式指定 rules→auto / agents+workflows+commands→semi-auto / hooks+skills→disabled，包含长匹配优先逻辑说明 |
| `harness/prompts/diagnosis.txt` | LLM 诊断 prompt 模板，头部含版本号+变更理由。prompt 设计为宽上下文策略：目标文件 + funnel 关联文件 + 历史反馈信号 → 根因分类 + 受影响文件列表 + 修复方案 |
| `harness/scripts/diagnose_and_fix.py` | 自我升级主引擎：加载反馈信号 → 检测重复模式 → 24h 去重 → 安全边界判断 → LLM 诊断 → 修复方案生成 → git worktree 沙盒验证 → 合并或降级。复用 `app/analyzer/llm_assistant.py` 的 `_get_llm_config` / `_call_llm` |

### 修改文件

| 文件路径 | 改动意图 |
| -------- | -------- |
| `.gitignore` | 追加 `harness/state/upgrade-history.json` 到忽略列表 |
| `harness/scripts/check_structure.py` | REQUIRED_DIRS 新增 `harness/config` 和 `harness/prompts`；REQUIRED_FILES 新增 `harness/config/self-upgrade.yaml`、`harness/prompts/diagnosis.txt`、`harness/scripts/diagnose_and_fix.py` |
| `.claude/commands/workflow/full-cycle.md` | 收尾阶段 `generate_rule_evolution.py` 之后追加 self-upgrade 触发逻辑：auto 静默、semi-auto 展示 diff 等确认、disabled 跳过 |
| `.claude/commands/workflow/implement.md` | 同上，收尾阶段追加 self-upgrade 触发逻辑 |
| `.claude/commands/workflow/quick-fix.md` | 同上，收尾阶段追加 self-upgrade 触发逻辑 |
| `.claude/commands/workflow/review-fix.md` | 同上，收尾阶段追加 self-upgrade 触发逻辑 |
| `harness/project-map/directory-map.md` | 目录树新增 `harness/config/` 和 `harness/prompts/` |
| `harness/project-map/module-map.md` | 登记 `diagnose_and_fix.py` 模块（职责、依赖） |
| `harness/project-map/command-map.md` | 登记 `diagnose_and_fix.py` 命令条目 |
| `harness/project-map/data-flow.md` | 新增自我升级数据流一节：反馈信号 → 模式检测 → LLM 诊断 → 修复方案 → git worktree 验证 → 合并/降级 → 升级历史 |
| `harness/project-map/change-map.md` | 记录本次变更摘要 |

---

## 2. 任务列表

### 实现任务 (→ Generator)

---

**IMP-1: 创建 `harness/config/self-upgrade.yaml`**

- 完成标准：
  - 文件存在且为合法 YAML（最小化手动解析兼容，不使用 PyYAML 等第三方库）
  - 包含 `auto_levels` 配置块，按 glob 模式列出 `auto` / `semi-auto` / `disabled`
  - 默认配置：`harness/rules/*` → auto，`harness/workflow/*` / `.claude/agents/*` / `.claude/commands/*` → semi-auto，`harness/hooks/*` / `harness/skills/*` → disabled
  - 包含 `safety_boundary` 配置块：`add_max_lines: 50`，`replace_max_lines: 20`，`delete: require_confirmation`
  - 包含 `dedup` 配置块：`window_hours: 24`
  - 包含注释说明：长匹配优先于短匹配、缺失字段的默认值
- 验证命令：`python -c "import json; print('YAML exists')"` （文件存在检查）+ 人工检查 schema

---

**IMP-2: 创建 `harness/prompts/diagnosis.txt`**

- 完成标准：
  - 文件头部含 `# 版本: v1.0.0` 和 `# 变更理由: 初始版本` 注释
  - prompt 主体为 LLM 系统指令，要求 LLM 分析反馈信号历史、定位根因、输出结构化诊断结果
  - prompt 要求 LLM 输出 JSON 格式：`{ "root_cause": "...", "category": "missing_step|rule_conflict|missing_check|boundary_unclear|file_content_conflict", "affected_files": [...], "fix_plan": [{"file": "...", "type": "insert|replace|delete|create", "content": "...", "reason": "..."}] }`
  - prompt 包含宽上下文指令：分析目标文件 + funnel 关联文件（agent→workflow 引用链、规则交叉引用）+ 历史信号
- 验证命令：文件存在且非空，`python -c "with open('harness/prompts/diagnosis.txt','r',encoding='utf-8') as f: content=f.read(); assert len(content) > 200, 'Prompt too short'; assert 'version' in content.lower() or '版本' in content, 'Missing version'"`

---

**IMP-3: 创建 `harness/scripts/diagnose_and_fix.py`**

这是核心引擎脚本。完成标准详见下方子任务。

**IMP-3a: 模块骨架与配置加载**
- `main()` 入口函数
- 加载 `harness/config/self-upgrade.yaml`（最小化 YAML 解析：只解析顶层 key-value 和列表的简单块映射即可）
- 配置缺失时的默认值降级
- 加载 `harness/state/feedback-signals.json`（通过 `FeedbackEngine.load_signals()`）
- 调用 `detect_patterns()` 获取重复模式
- 载入 `harness/state/upgrade-history.json`（不存在则初始化空列表）

**IMP-3b: 24h 去重逻辑**
- 遍历重复模式，对每个 `rule_ref` 检查 upgrade-history.json 中 24 小时内是否有相同信号 ID 的成功修复记录
- 有 → 跳过
- 无 → 进入诊断流程

**IMP-3c: 安全边界 + 自动程度双层门禁**
- 一级门禁（操作类型 + 改动量）：
  - 新增 ≤50 行 → 自动
  - 替换 ≤20 行 → 自动
  - 删除任何行 → 人工确认（降级输出到 rule-evolution-proposal.md）
  - 超任何阈值 → 降级输出到 rule-evolution-proposal.md
- 二级门禁（文件类型自动程度配置）：
  - 加载 self-upgrade.yaml 的 auto_levels glob 配置
  - 对目标文件路径匹配 glob，长匹配优先
  - `auto` → 静默执行
  - `semi-auto` → 展示 diff 等待用户确认（通过 stdout 输出 + stdin 读取）
  - `disabled` → 跳过
- 两级都通过 → 进入 LLM 诊断
- 由一级门禁判断为"删除"或超阈值的，即使二级配置为 auto 也要降级

**IMP-3d: LLM 诊断调用**
- 构建宽上下文：
  - 目标文件内容（从 rule_ref 提取文件路径，读取文件）
  - funnel 关联文件（agent 定义文件 → 搜索工作流文件中的引用；规则文件 → 搜索其他规则文件中的交叉引用）
  - 历史反馈信号（同 rule_ref 的所有信号，从 `FeedbackEngine.load_signals()` 中筛选）
- 从 `harness/prompts/diagnosis.txt` 加载模板，填充上下文
- 调用 `app/analyzer/llm_assistant._get_llm_config()` 和 `_call_llm()`（max_tokens 较大，建议 4096；timeout 60s）
- LLM 不可用时（API Key 缺失或调用失败）：降级输出 `"无法自动诊断"` 标记到 rule-evolution-proposal.md，记录到 upgrade-history.json 但不标记为成功
- 解析 LLM 返回的 JSON 修复方案，校验格式（必须包含 file/type/content/reason 字段）

**IMP-3e: git worktree 沙盒验证**
- 在项目根目录运行 `git worktree add` 创建临时工作树（路径如 `../.self-upgrade-worktree`）
- 在 worktree 中应用修复方案（Write/Edit 操作——注意 worktree 的绝对路径）
- 在 worktree 中依次运行：
  1. `python harness/scripts/check_structure.py`（使用 worktree 的项目根）
  2. `python -m pytest tests/ -v`（使用 worktree 的 Python 环境）
  3. agent YAML frontmatter 有效性检查：遍历 `.claude/agents/*.md` 文件，检查是否存在有效的 `---` 包裹的 YAML frontmatter（name 字段存在即可，最小化解析）
- 全部通过 → `git -C <project_root> merge <worktree_branch>` 合并回当前分支，`git worktree remove <path>` 清理
- 任一失败 → `git worktree remove --force <path>` 丢弃沙盒，降级输出修复方案到 rule-evolution-proposal.md
- 验证失败记录到 `harness/feedback/error-log.md`

**IMP-3f: 升级历史记录写入**
- 每次自动修复（无论成功/失败/降级）生成记录写入 `harness/state/upgrade-history.json`
- 记录字段：`timestamp`（ISO）、`signal_id`（rule_ref）、`diagnosis_summary`（根因摘要 ≤100 字）、`affected_files`（修改文件路径列表）、`verification_result`（"passed" / "failed" / "degraded"）、`rollback_note`（失败时的回滚说明）
- 原子写入（.tmp + os.replace）

**IMP-3g: semi-auto 交互流程**
- 当自动程度为 semi-auto 时，在控制台展示修复 diff（使用 `git diff` 命令输出）
- 等待用户输入 `y/n` 确认
- 用户确认 → 执行 worktree 合并
- 用户拒绝 → 降级输出到 rule-evolution-proposal.md

**IMP-3 验证命令**：
- `python harness/scripts/diagnose_and_fix.py --dry-run`（建议支持 dry-run 模式，只诊断不修改）
- `python harness/scripts/check_structure.py`

---

**IMP-4: 更新 `.gitignore`**

- 完成标准：`.gitignore` 文件末尾追加 `harness/state/upgrade-history.json`
- 验证命令：`grep -q "upgrade-history.json" .gitignore`

---

**IMP-5: 更新 `harness/scripts/check_structure.py`**

- 完成标准：
  - `REQUIRED_DIRS` 列表新增 `"harness/config"` 和 `"harness/prompts"`
  - `REQUIRED_FILES` 列表新增三个路径：`"harness/config/self-upgrade.yaml"`、`"harness/prompts/diagnosis.txt"`、`"harness/scripts/diagnose_and_fix.py"`
  - 检查项总数从当前的 47 项（13 dirs + 34 files）增加到位 50 项（15 dirs + 35 files）
- 验证命令：`python harness/scripts/check_structure.py` 输出 50/50 PASS

---

**IMP-6: 更新 4 个 `.claude/commands/workflow/*.md` 工作流编排器指令**

需要修改的文件：
- `.claude/commands/workflow/full-cycle.md`
- `.claude/commands/workflow/implement.md`
- `.claude/commands/workflow/quick-fix.md`
- `.claude/commands/workflow/review-fix.md`

- 完成标准：
  - 每个文件在收尾部分（`generate_rule_evolution.py` 运行之后）追加 self-upgrade 触发指令
  - 触发逻辑描述：
    - 运行 `python harness/scripts/diagnose_and_fix.py`
    - 脚本内部已按 auto/semi-auto/disabled 分流
    - auto 级别：编排器仅通知用户"已自动修复 N 个问题"
    - semi-auto 级别：脚本暂停等待确认
    - disabled 级别：跳过
  - 编排器不需要读取诊断细节或修复 diff（那是脚本和用户的事）
  - 保持现有回环逻辑不变
- 验证命令：文件内容包含 `diagnose_and_fix.py` 字样（grep 验证）

---

**IMP-7: 更新 5 个 project-map 文档**

**IMP-7a: `harness/project-map/directory-map.md`**
- 在 `harness/` 目录树下新增 `config/` 和 `prompts/` 目录条目，并列出其下的文件

**IMP-7b: `harness/project-map/module-map.md`**
- 在"自动分析模块"表格中新增一行：
  - 文件路径：`harness/scripts/diagnose_and_fix.py`
  - 模块描述：自我升级引擎 — 反馈信号驱动的自动诊断与修复
  - 主要函数：`main`, `_load_config`, `_check_dedup`, `_apply_safety_boundary`, `_call_llm_diagnosis`, `_sandbox_verify`, `_write_upgrade_history`
  - 依赖：`harness.state.feedback_engine`, `app.analyzer.llm_assistant`, `harness.config.self-upgrade.yaml`

**IMP-7c: `harness/project-map/command-map.md`**
- 在 CLI 命令表格中新增一行：
  - 命令：`python harness/scripts/diagnose_and_fix.py`
  - 用途：自我升级引擎 — 扫描反馈信号的重复模式，自动诊断并应用修复（沙盒验证）
  - 来源文件：`harness/scripts/diagnose_and_fix.py`

**IMP-7d: `harness/project-map/data-flow.md`**
- 新增"## 自我升级数据流"章节，描述数据流路径：
  ```
  feedback-signals.json
      │
      ├── FeedbackEngine.detect_patterns() → 重复模式
      │
      ├── self-upgrade.yaml → 自动程度判定 + 安全边界
      │
      ├── upgrade-history.json → 24h 去重检查
      │
      ├── LLM 诊断（宽上下文）
      │   ├── 目标文件内容
      │   ├── funnel 关联文件（agent↔workflow 引用链、规则交叉引用）
      │   └── 历史反馈信号
      │
      ├── 修复方案（JSON）
      │   ├── 安全边界通过 + auto → git worktree 沙盒验证
      │   │   ├── check_structure.py 通过
      │   │   ├── pytest 通过
      │   │   ├── agent YAML 有效 → 合并到主分支 + 升级历史
      │   │   └── 任一失败 → 丢弃沙盒 + 降级输出
      │   └── 安全边界不通过 / semi-auto 拒绝 → rule-evolution-proposal.md
      │
      └── upgrade-history.json（每次修复记录）
  ```

**IMP-7e: `harness/project-map/change-map.md`**
- 在文件顶部（最新变更位置）新增一条变更记录：
  - 日期：2026-05-25
  - 类型：新功能
  - 摘要：Harness 自我升级引擎 v0.1 — LLM 根因诊断 + git worktree 沙盒验证 + 自动程度分层处理
  - 影响文件范围：3 新建 + 11 修改

验证命令（IMP-7 整体）：`python harness/scripts/check_structure.py`

---

### 测试任务 (→ Tester)

---

**TST-1: 配置加载测试**

- 测试文件：`tests/test_diagnose_and_fix.py`
- 覆盖功能点：
  - 默认配置文件存在且可解析
  - 缺失 `self-upgrade.yaml` 文件时所有 glob 降级为默认值（rules→auto 等）
  - 缺失 `auto_levels` 字段时降级为默认值
  - 缺失 `safety_boundary` 字段时使用硬编码默认值
  - glob 长匹配优先于短匹配（如 `harness/rules/coding-rules.md` 匹配 `harness/rules/coding-rules.md` 优先于 `harness/rules/*`）
  - `disabled` 优先级测试：即使长匹配到 semi-auto，如果规则明确 disabled 则应该 disabled

---

**TST-2: 安全边界逻辑测试**

- 测试文件：`tests/test_diagnose_and_fix.py`
- 覆盖功能点：
  - 新增 ≤50 行 → 自动通过
  - 新增 51 行 → 降级
  - 替换 ≤20 行 → 自动通过
  - 替换 21 行 → 降级
  - 删除任意行数 → 一律标记 requires_confirmation（降级）
  - 混合操作（insert + delete）→ 按最严格规则判定

---

**TST-3: 24h 去重逻辑测试**

- 测试文件：`tests/test_diagnose_and_fix.py`
- 覆盖功能点：
  - 同一 signal_id 在 24 小时内已有成功修复记录 → 跳过
  - 同一 signal_id 在 24 小时外 → 正常触发
  - 同一 signal_id 上次修复验证失败 → 正常触发（不因失败而永远跳过）
  - 无历史记录 → 正常触发

---

**TST-4: LLM 诊断输出解析测试**

- 测试文件：`tests/test_diagnose_and_fix.py`
- 覆盖功能点：
  - 合法 JSON 修复方案正确解析（file/type/content/reason 字段齐全）
  - 缺少必需字段的 JSON → 降级输出
  - LLM 返回非 JSON 文本 → 降级输出
  - LLM 调用失败（网络超时、API 错误）→ 降级输出 + 记录错误日志
  - API Key 缺失 → 正确降级（不崩溃）

---

**TST-5: worktree 生命周期测试**

- 测试文件：`tests/test_diagnose_and_fix.py`
- 覆盖功能点（使用临时 git 仓库模拟）：
  - worktree 创建成功，路径正确
  - 修改应用到 worktree 而非主工作区
  - check_structure.py 在 worktree 中通过 → merge 成功
  - check_structure.py 在 worktree 中失败 → worktree 被 force remove，主工作区不受影响
  - pytest 失败 → worktree 被清理
  - agent YAML frontmatter 检查失败 → worktree 被清理
  - merge 后 worktree 被正确删除

---

**TST-6: 升级历史记录测试**

- 测试文件：`tests/test_diagnose_and_fix.py`
- 覆盖功能点：
  - 成功修复后 upgrade-history.json 包含完整字段（timestamp、signal_id、diagnosis_summary、affected_files、verification_result）
  - 失败修复后 verification_result 为 "failed"，包含 rollback_note
  - 降级修复后 verification_result 为 "degraded"
  - 去重检查能正确读取 upgrade-history.json

---

**TST-7: 集成测试 — 端到端工作流**

- 测试文件：`tests/test_diagnose_and_fix.py`
- 覆盖功能点：
  - 从 feedback-signals.json 读取 → 检测模式 → 诊断 → 修复 → 验证流程走通（mock LLM 响应）
  - 重复模式 < 3 次 → 不触发修复
  - auto 级别静默合并
  - semi-auto 级别（mock 用户输入 "y"）正常合并
  - disabled 级别完全跳过
  - 修复后 rule-evolution-proposal.md 降级输出包含正确的修复方案信息

---

## 3. 依赖关系

```
IMP-1 (self-upgrade.yaml)
  │
  ├── IMP-2 (diagnosis.txt) ──────────────────────┐
  │                                                │
  └── IMP-3 (diagnose_and_fix.py) ◄───────────────┘
        │                                          │
        ├── IMP-4 (.gitignore) ◄── 可并行          │
        ├── IMP-5 (check_structure.py) ◄── 可并行  │
        │                                          │
        └── IMP-6 (workflow commands) ──── 依赖 IMP-3 API 确定
              │
              └── IMP-7 (project-map docs) ──── 最后执行（汇总所有变更）

TST-1 ~ TST-7 ──── 全部依赖 IMP-3 完成
```

### 并行建议

- IMP-1 和 IMP-2 可并行（互不依赖）
- IMP-4 与 IMP-5 可在 IMP-3 开发进行中并行修改（文件路径已预先确定）
- IMP-6 必须在 IMP-3 完成后（需要知道命令行参数和输出格式）
- IMP-7 应在所有实现任务完成后执行（汇总文档）
- TST-1 至 TST-7 在 IMP-3 完成后全部可并行

### 推荐执行顺序

1. 先并行执行 IMP-1 + IMP-2（配置 + prompt 模板，无代码依赖）
2. IMP-3（核心引擎，依赖 IMP-1 和 IMP-2 的输出格式）
3. IMP-4 + IMP-5 + IMP-6（并行修改 .gitignore / check_structure / workflow 命令）
4. IMP-7（汇总 project-map 文档）
5. TST-1 ~ TST-7（并行执行所有测试）

---

## 4. 风险点

### 高风险

1. **YAML 解析无第三方库** — `self-upgrade.yaml` 和 agent YAML frontmatter 都需要解析 YAML。PyYAML 不满足"不引入第三方依赖"的规则。必须实现最小化 YAML 解析器（仅解析简单 key-value 块和列表）。风险：Unicode 字符、多行字符串、缩进异常可能导致解析失败。缓解：只解析顶层简单结构，复杂的 YAML 特性（anchor、tag、flow style 嵌套）不实现。如果 YAML 太复杂就报错让用户简化。

2. **git worktree 在 Windows 上的兼容性** — worktree 需要同一磁盘分区（NTFS 不支持跨分区 hardlink）。如果在不同驱动器上创建 worktree 会失败。缓解：始终在项目根目录的父目录下创建 worktree（`../.self-upgrade-worktree`），确保同一分区。在 `diagnose_and_fix.py` 中检查 worktree 创建是否成功。

3. **worktree 中 pytest 依赖** — worktree 是完整的 git checkout，但可能缺少虚拟环境或测试依赖。缓解：worktree 共享主工作区的 `.git`，代码文件一致。如果 pytest 依赖在虚拟环境中，需要确保 worktree 使用同一个虚拟环境（通过检查 `sys.executable` 并使用主工作区的 Python 路径）。

4. **LLM 诊断质量不稳定** — LLM 可能误判根因或生成不合理修复方案，修复方案可能引入新 bug。缓解：三层防护 — 沙盒验证（check_structure + pytest + frontmatter）+ 安全边界（限制修改行数）+ 失败降级（输出建议而非强制修改）。

5. **修复循环** — 自动修复引入新问题 → 新问题被检测为新信号 → 再次触发修复... 形成无限循环。缓解：24h 去重窗口 + 上次修复验证失败且未产生新信号时不重复修复 + 升级历史可审计。

### 中风险

6. **semi-auto 交互阻塞** — 当 `diagnose_and_fix.py` 在 semi-auto 模式下等待用户输入 `y/n` 时，如果编排器在后台运行（无人值守），会永久阻塞。缓解：可以增加 `--timeout` 参数（默认 300 秒），超时后降级为输出建议。

7. **宽上下文策略的上下文窗口** — 目标文件 + funnel 关联文件 + 历史信号的总 token 数可能超过 LLM 上下文窗口。缓解：在 `diagnose_and_fix.py` 中对每个部分设置字符数上限（目标文件 ≤5000 chars，关联文件 ≤3000 chars，历史信号 ≤2000 chars），超过则截断。

8. **Prompt 自我演化的递归风险** — `diagnosis.txt` 本身通过 `harness/prompts/*` 匹配到 auto 级别（因为按默认 glob，`harness/prompts/*` 不在 rules 的 glob 中，应该匹配 semi-auto 或 disabled）。需要用 glob 配置确保 `harness/prompts/diagnosis.txt` 属于 semi-auto（需要人工确认），避免 LLM 静默修改自己的诊断 prompt。受 spec 确认：prompt 修改归为 semi-auto。

### 低风险

9. **`app/analyzer/llm_assistant.py` 的导入路径** — `diagnose_and_fix.py` 在 `harness/scripts/` 下，导入 `app.analyzer.llm_assistant` 需要确保 `sys.path` 包含项目根目录。缓解：在脚本开头 `sys.path.insert(0, _PROJECT_ROOT)`，与 `generate_rule_evolution.py` 保持一致。

10. **`check_structure.py` 检查项计数** — 新增目录和文件后，总数从 47 变为 50（15 dirs + 35 files）。如果在实现过程中又新增/删除其他文件，计数可能不匹配。缓解：在 IMP-5 完成后运行 `check_structure.py` 验证，根据实际输出调整断言。

### 编码规则注意事项

- 所有 Python 文件头 3 行内必须包含用途描述注释（coding-rules #4）
- `diagnose_and_fix.py` 新增函数需在 `module-map.md` 登记（coding-rules #7）
- 数据结构变更后需更新 `data-flow.md`（coding-rules #6）
- 修改 CLI 命令后需同步 `command-map.md`（coding-rules #5）
- 原子写入（.tmp + os.replace）用于 upgrade-history.json 和 rule-evolution-proposal.md 追加（data-safety-rules #8）
