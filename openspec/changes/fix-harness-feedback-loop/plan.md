# Plan: Harness 反馈调节系统 v0.1

> **Planner replan revision #2** (2026-05-25). 架构澄清：`.claude/commands/workflow/*.md` 是实际执行入口（主会话逐行执行其正文），`harness/workflow/*.md` 只是数据源（YAML stages 定义）+ 参考文档。命令文件只读 workflow 的 YAML，不读正文。IMP-7 修改范围从 `harness/workflow/*.md` 正文改为 `.claude/commands/workflow/*.md` 正文。

## 1. 变更范围

### 需要新增的文件

| 文件路径 | 改动意图 |
| ---- | ---- |
| `harness/state/__init__.py` | 包初始化，导出 FeedbackSignal、FeedbackEngine、WorkflowState |
| `harness/state/feedback_signal.py` | 定义 FeedbackSignal 数据类（dataclass），包含字段：signal_type、severity、rule_ref、occurrences、first_seen、last_seen、source；提供 to_dict()/from_dict()/to_json_schema() |
| `harness/state/feedback_engine.py` | FeedbackEngine 类：JSON 文件读取/写入/去重（唯一键为 (signal_type, rule_ref)）/重复模式检测（同一 rule_ref >=3 次标记为 repeated_pattern） |
| `harness/state/workflow_state.py` | WorkflowState 类：管理 `harness/state/current-workflow.json` 共享状态快照，记录阶段进展、偏差量、路由历史；提供 get_deviation_trend() 和 should_continue_loop() |
| `harness/scripts/generate_rule_evolution.py` | CLI 脚本：扫描 feedback 目录和 state 文件，检测重复模式，生成 `harness/feedback/rule-evolution-proposal.md` |

### 需要修改的文件

| 文件路径 | 改动意图 |
| ---- | ---- |
| `harness/scripts/check_structure.py` | REQUIRED_DIRS 新增 `"harness/state"`（总数 12 -> 13）；REQUIRED_FILES 不新增（feedback-signals.json 和 current-workflow.json 是运行时生成的，不要求存在） |
| `.gitignore` | 新增 `harness/state/feedback-signals.json` 和 `harness/state/current-workflow.json`，防止运行时生成的 JSON 文件被提交 |
| `.claude/commands/workflow/full-cycle.md` | **(主更新文件)** 编排器执行入口升级：阶段 1-5 启动时创建 WorkflowState；回环前记录偏差快照；回环决策从"回环最多 2 次"改为 should_continue_loop()（偏差缩小->继续，不变/放大->暂停，2 次为硬上限）；回环结束后追加 FeedbackSignal；工作流结束时运行 generate_rule_evolution.py；硬约束节更新（新增"允许运行 Python 状态管理脚本"） |
| `.claude/commands/workflow/implement.md` | 当前正文 `循环逻辑同 /workflow:full-cycle` 替换为自包含的完整回环指令（Explorer 阻塞 + Tester 阻塞两套，含 WorkflowState 调用和偏差趋势判断），不再引用 full-cycle 命令 |
| `.claude/commands/workflow/quick-fix.md` | 当前正文 `循环逻辑同 /workflow:full-cycle` 替换为自包含的 Tester 回环指令（quick-fix 无 Explorer 阻塞回环），含 WorkflowState 初始化/record_stage/should_continue_loop/to_feedback_signal、generate_rule_evolution.py 调用 |
| `.claude/commands/workflow/review-fix.md` | 当前正文 `编排循环逻辑同 full-cycle` 替换为自包含的 Tester 回环指令（review-fix Tester 阻塞 -> generator-test-fix -> tester），含 WorkflowState 调用和 generate_rule_evolution.py |
| `.claude/agents/planner.md` | "收到任务时"节新增第 6 步：若 `harness/feedback/rule-evolution-proposal.md` 存在，阅读未处理建议并纳入上下文 |
| `harness/project-map/directory-map.md` | 目录树新增 `harness/state/` 目录及子文件（`__init__.py`、`feedback_signal.py`、`feedback_engine.py`、`workflow_state.py`） |
| `harness/project-map/module-map.md` | 在"自动分析模块"表格中新增 4 行，记录 harness/state/ 下的新模块；generate_rule_evolution.py 作为脚本也需一行 |
| `harness/project-map/data-flow.md` | 在"数据结构"节下新增"反馈信号与工作流状态"小节，包含 FeedbackSignal JSON Schema 和 WorkflowState JSON 结构 |
| `harness/project-map/command-map.md` | CLI 命令表新增 `python harness/scripts/generate_rule_evolution.py` |
| `harness/project-map/change-map.md` | 记录本次变更摘要 |

### 不修改的文件

- `harness/workflow/full-cycle.md` -- YAML frontmatter（stages 定义）保持不变，正文（参考文档）保持不变。命令文件只读 YAML，不读正文，无需修改
- `harness/workflow/implement.md` -- 同上，YAML frontmatter + 参考文档不变
- `harness/workflow/quick-fix.md` -- 同上，YAML frontmatter + 参考文档不变
- `harness/workflow/review-fix.md` -- 同上，YAML frontmatter + 参考文档不变
- `harness/workflow/README.md` -- 架构说明文档，保持现状
- `harness/feedback/error-log.md` -- 已有记录保持不变，新信号写入 JSON 而非 Markdown
- `harness/feedback/improvement-log.md` -- 同上。注意：`rule-evolution-proposal.md` 是新增生成文件，会写入此目录，但不修改现有两个日志文件
- `harness/rules/*.md` -- 本版本规则文件保持静态，规则演化引擎只产出建议不自动修改
- `app/analyzer/` -- 本变更不触及分析引擎代码
- `.claude/agents/` (除 planner.md 外) -- Explorer/Generator/Reviewer/Tester 接收的任务 prompt 由编排器构造，无需修改 agent 定义

## 2. 任务列表

### 实现任务 (-> Generator)

**IMP-1: 创建 FeedbackSignal 数据模型**

- 文件：`harness/state/__init__.py`、`harness/state/feedback_signal.py`
- 内容：
  - `FeedbackSignal` dataclass，字段：`signal_type` (str: "rule_violation"/"error"/"improvement"/"loop_deviation")、`severity` (str: "blocking"/"non_blocking"/"info")、`rule_ref` (str: 关联规则文件路径如 "harness/rules/coding-rules.md#4")、`occurrences` (int: 默认 1)、`first_seen` (str: ISO timestamp，默认当前时间)、`last_seen` (str: ISO timestamp，默认当前时间)、`source` (str: 来源如 "explorer-blocked" / "tester-failed")
  - `to_dict()` 返回 dict，`from_dict(d: dict)` 类方法构造实例
  - `to_json_schema()` 类方法，返回合法 JSON Schema dict（含所有字段的 type/description）
  - coding-rules #4 命中：文件头 3 行内包含用途注释
- 完成标准：`python -c "from harness.state.feedback_signal import FeedbackSignal; s = FeedbackSignal(signal_type='rule_violation', severity='blocking', rule_ref='coding-rules.md#5'); print(s.to_dict())"` 正常输出
- 验证命令：`python -c "from harness.state.feedback_signal import FeedbackSignal; print(FeedbackSignal.to_json_schema()['properties']['signal_type'])"`

**IMP-2: 创建 FeedbackEngine 反馈信号引擎**

- 文件：`harness/state/feedback_engine.py`
- 内容：
  - `FeedbackEngine` 类，构造函数接收 `signals_file`（默认 `harness/state/feedback-signals.json`，路径基于 `__file__` 相对计算到项目根）
  - `load_signals() -> list[FeedbackSignal]`：从 JSON 加载，文件不存在返回 `[]`
  - `add_signal(signal: FeedbackSignal) -> None`：去重后追加。去重逻辑：以 `(signal_type, rule_ref)` 为唯一键，相同则 `occurrences += 1` 并更新 `last_seen`，不同则新增
  - `save_signals() -> None`：原子写入（先写 `.tmp` 再 `os.replace`），文件不存在时自动创建
  - `detect_patterns() -> list[dict]`：查找同一 rule_ref 出现 >= 3 次的重复模式，返回 `[{"rule_ref": "...", "occurrences": N, "severity": "..."}]`
- 完成标准：能正确读写 JSON、去重、检测模式
- 验证命令：`python harness/state/feedback_engine.py`（脚本尾部含 `if __name__ == "__main__":` 自测逻辑：创建临时文件、添加信号、保存、加载、检测模式、清理临时文件）

**IMP-3: 创建 WorkflowState 工作流状态管理器**

- 文件：`harness/state/workflow_state.py`
- 内容：
  - 状态文件路径：`harness/state/current-workflow.json`
  - `WorkflowState` 类方法（无实例状态，操作 JSON 文件）：
    - `init(topic: str, stages: list[str])`：创建新状态 JSON，重置所有迭代计数
    - `record_stage(stage_id: str, deviation_count: int, status: str)`：追加阶段记录，自动递增该 stage 的迭代计数
    - `get_deviation_trend(stage_id: str) -> str`：比较当前迭代与上一迭代的 deviation_count。返回 "first_iteration" / "shrinking" / "stable" / "growing"
    - `should_continue_loop(stage_id: str, max_loops: int = 2) -> bool`：偏差缩小且未超 max_loops 返回 True，否则返回 False
    - `to_feedback_signal(stage_id: str) -> FeedbackSignal`：将最后一次回环记录转为 FeedbackSignal（signal_type="loop_deviation"）
  - 偏差量化代理：
    - Explorer 阻塞：用 `blocking_issues_count`（侦察报告中"阻塞"问题的数量）
    - Tester 阻塞：用 `failed_test_count`（测试报告中失败测试的数量）
    - 编排器从产出文件头部提取这些数值传给 `record_stage()`
  - 原子写入（先写 `.tmp` 再 `os.replace`）
- 完成标准：能正确创建/更新状态 JSON、计算趋势、判断是否继续
- 验证命令：`python harness/state/workflow_state.py`（脚本尾部含自测逻辑：模拟 init -> record_stage x3 -> 验证趋势判断 -> 清理）

**IMP-4: 创建规则演化建议生成脚本**

- 文件：`harness/scripts/generate_rule_evolution.py`
- 内容：
  - 无命令行参数（仅被 workflow 编排器在阶段结束时调用）
  - 实例化 FeedbackEngine，调用 `detect_patterns()`
  - 存在重复模式时，生成/更新 `harness/feedback/rule-evolution-proposal.md`：
    - 文件顶部记录生成时间戳
    - 每个建议含：`## 建议 N: [规则文件名] -- [简述]`、变更理由、支持证据（列出该规则所有关联的 FeedbackSignal）、建议修改的具体规则文本、状态标记 `> 状态: 待确认`
    - 若 proposal 已存在：读取已有建议，已有 pattern 不重复生成，新 pattern 追加到末尾（追加前加分割线 `---`）
  - 不存在重复模式时：输出 `No repeated patterns detected.` 到 stdout，不修改 proposal 文件
  - coding-rules #4 命中：文件头 3 行内包含用途注释
- 完成标准：手动运行 `python harness/scripts/generate_rule_evolution.py` 正常执行，无信号时输出 "No repeated patterns"
- 验证命令：`python harness/scripts/generate_rule_evolution.py`

**IMP-5: 更新 check_structure.py 注册新目录**

- 文件：`harness/scripts/check_structure.py`
- 内容：
  - `REQUIRED_DIRS` 新增 `"harness/state"`
  - 注意：REQUIRED_FILES 不新增 `feedback-signals.json` 和 `current-workflow.json`，因为它们运行时生成，初始不存在
  - 新增后 REQUIRED_DIRS 总数从 12 变为 13
- 完成标准：`python harness/scripts/check_structure.py` 通过（需要先创建 `harness/state/` 目录和 `__init__.py`）
- 验证命令：`python harness/scripts/check_structure.py`

**IMP-6: 更新 .gitignore**

- 文件：`.gitignore`
- 内容：在文件末尾新增两行：
  ```
  # Harness runtime state
  harness/state/feedback-signals.json
  harness/state/current-workflow.json
  ```
- 完成标准：`git status` 在生成这些文件后不显示它们为 untracked
- 验证命令：`git check-ignore harness/state/feedback-signals.json harness/state/current-workflow.json`

**IMP-7: 升级 .claude/commands/workflow/ 命令入口文件（共享状态 + 偏差趋势自适应回环）**

- 涉及文件：`.claude/commands/workflow/full-cycle.md`（主修改）、`.claude/commands/workflow/implement.md`、`.claude/commands/workflow/quick-fix.md`、`.claude/commands/workflow/review-fix.md`
- 核心原则：这些文件是主会话逐行执行的实际入口，必须自包含完整逻辑，不依赖跨文件引用。`harness/workflow/*.md` 的 YAML frontmatter 仍被读取以获取 stages 定义，但正文不被读取。
- YAML frontmatter 不变（name/description/category/tags 保持原样）。

**full-cycle.md 修改（主文件）**：

当前正文中的 "阶段 1-5: 编排模式" 节和 "回环逻辑" 指令需要按以下方式升级：

1. "硬约束"节更新为：
   ```
   **硬约束：编排模式下不读取 `.claude/agents/` 和 `openspec/` 下的任何文件。编排器被授权运行 Python 脚本进行状态管理（创建 WorkflowState、记录偏差、追加 FeedbackSignal、运行 generate_rule_evolution.py），这属于编排器职责。**
   ```

2. "阶段 1-5: 编排模式" 第 1 步之前新增第 0 步：
   ```
   0. **初始化工作流状态**：若主题名已确定，运行：
      `python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.init('{topic}', ['explorer', 'tester'])"`
   ```

3. "检查回环"（当前第 6 步）完整替换为：

   **Explorer 阻塞回环** (explorer -> planner-replan -> explorer)：
   - 若 explorar 产出 `recon.md` 且 `严重程度: 阻塞` 且 planner-replan 阶段存在：
     - 从 `recon.md` 第一段提取 `阻塞问题数量`（搜索 "阻塞" 关键词作为 deviation_count）
     - 运行 `python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.record_stage('explorer', {deviation_count}, 'blocked')"`
     - 运行 `python -c "from harness.state.workflow_state import WorkflowState; print(WorkflowState.should_continue_loop('explorer'))"`
     - 若返回 True（偏差缩小）：继续回环，spawn planner-replan 修正计划，再重新 spawn explorer 验证
     - 若返回 False（偏差不变/放大或超过最大次数）：**暂停**，向用户展示偏差趋势和回环次数，请用户决策
     - 回环结束后：运行 `python -c "from harness.state.workflow_state import WorkflowState; s = WorkflowState.to_feedback_signal('explorer'); from harness.state.feedback_engine import FeedbackEngine; engine = FeedbackEngine(); engine.add_signal(s); engine.save_signals()"` 将回环记录写入反馈信号

   **Tester 阻塞回环** (tester -> generator-fix -> tester)：
   - 若 tester 产出 `test-report.md` 且 `结论: 阻塞` 且 generator-fix 阶段存在：
     - 从 `test-report.md` 第一段提取 `失败测试数量`（搜索 "FAILED" 关键词作为 deviation_count）
     - 运行 `python -c "from harness.state.workflow_state import WorkflowState; WorkflowState.record_stage('tester', {deviation_count}, 'blocked')"`
     - 运行 `python -c "from harness.state.workflow_state import WorkflowState; print(WorkflowState.should_continue_loop('tester'))"`
     - 若返回 True（偏差缩小）：继续回环，spawn generator-fix 修复代码，再重新 spawn tester 验证
     - 若返回 False（偏差不变/放大或超过最大次数）：**暂停**，向用户展示偏差趋势和回环次数，请用户决策
     - 回环结束后：同上通过 to_feedback_signal + FeedbackEngine 将记录写入反馈信号

4. 全部阶段结束后（"全部完成后汇总表格"之前）新增：
   ```
   **收尾**：运行 `python harness/scripts/generate_rule_evolution.py` 检查是否有新的重复模式。
   ```

**implement.md 修改**：

当前正文中的执行指令仅一句话 `循环逻辑同 /workflow:full-cycle`，需替换为自包含的完整编排器指令。结构与 full-cycle.md 一致但无色 0 PM 讨论：

1. 在阶段循环开始前新增：WorkflowState.init() 调用（stages: ['explorer', 'tester']）
2. 完整的 Explorer 阻塞回环逻辑（record_stage/should_continue_loop/to_feedback_signal）——与 full-cycle.md 一致
3. 完整的 Tester 阻塞回环逻辑——与 full-cycle.md 一致
4. 阶段结束后运行 generate_rule_evolution.py
5. "硬约束：不读取 agent 定义文件和 openspec 文件"保留，追加 Python 脚本授权

**quick-fix.md 修改**：

当前正文中的 `循环逻辑同 /workflow:full-cycle` 替换为自包含逻辑。quick-fix 无 Explorer 阻塞回环（其 stages YAML 无 planner-replan），仅需：

1. 阶段循环前：WorkflowState.init()（stages: ['tester']，无 'explorer' 因为 quick-fix 的 explorer 阻塞后直接报告用户并终止，不走回环）
2. Tester 阻塞回环完整逻辑：record_stage('tester', ...)、should_continue_loop('tester')、to_feedback_signal + FeedbackEngine 写入
3. 阶段结束后运行 generate_rule_evolution.py
4. "注意：quick-fix 无 Planner，若 Explorer 发现阻塞问题，编排器直接报告用户并终止"保留
5. 追加 Python 脚本授权

**review-fix.md 修改**：

当前正文中的 `编排循环逻辑同 full-cycle` 替换为自包含逻辑，仅含 Tester 回环（generator-test-fix -> tester）：

1. 阶段循环前：WorkflowState.init()（stages: ['tester']）
2. Tester 阻塞回环完整逻辑：record_stage('tester', ...)、should_continue_loop('tester')、to_feedback_signal + FeedbackEngine 写入
3. 阶段结束后运行 generate_rule_evolution.py
4. 追加 Python 脚本授权

- 完成标准：4 个命令入口文件各自包含完整的偏差趋势自适应回环指令，不再引用其他文件
- 验证命令：`python harness/scripts/check_structure.py`（确认 .claude/commands/workflow/*.md 文件路径仍在 REQUIRED_FILES 中）

**IMP-8: 更新 Planner Agent 定义（规则演化建议注入）**

- 文件：`.claude/agents/planner.md`
- 内容：
  - "收到任务时" 当前第 5 步后新增第 6 步：
    ```
    6. `harness/feedback/rule-evolution-proposal.md` — 若文件存在且含 `> 状态: 待确认` 的建议条目，阅读这些未处理建议并纳入计划上下文。当计划涉及相关规则文件时，优先参考演化建议。
    ```
- 完成标准：Planner agent 定义文件包含此步骤
- 验证命令：`grep -c "rule-evolution-proposal" .claude/agents/planner.md`（输出 >= 1）

**IMP-9: 更新项目地图文档**

- 文件：`harness/project-map/directory-map.md`、`harness/project-map/module-map.md`、`harness/project-map/data-flow.md`、`harness/project-map/command-map.md`、`harness/project-map/change-map.md`
- 内容：
  - **directory-map**：在 AI_Project_Notebook/ 目录树中新增：
    ```
        ├── harness/state/          # 工作流运行时状态
        │   ├── __init__.py
        │   ├── feedback_signal.py
        │   ├── feedback_engine.py
        │   └── workflow_state.py
    ```
    （不列出运行时生成的 feedback-signals.json 和 current-workflow.json，它们是数据文件不是源文件）
  - **module-map**：在"自动分析模块"表格中新增 4 行（目录为 harness/state/）：

    | 文件路径 | 模块描述 | 主要函数 | 主要类 |
    | ---- | ---- | ---- | ---- |
    | harness/state/feedback_signal.py | 反馈信号数据模型 | to_dict, from_dict, to_json_schema | FeedbackSignal |
    | harness/state/feedback_engine.py | 反馈信号引擎（读写/去重/模式检测） | load_signals, add_signal, save_signals, detect_patterns | FeedbackEngine |
    | harness/state/workflow_state.py | 工作流状态管理器（偏差趋势/回环决策） | init, record_stage, get_deviation_trend, should_continue_loop, to_feedback_signal | WorkflowState |
    | harness/scripts/generate_rule_evolution.py | 规则演化建议生成脚本 | - | - |

    注意：generate_rule_evolution.py 路径在 harness/scripts/ 下，与上述 3 个不同目录，但统一登记在此表格中。

  - **data-flow**：在现有"数据结构"节（`### domain_result` 之后）新增小节：
    ```
    ### FeedbackSignal (feedback_signal.py 输出)

    ```json
    {
        "signal_type": "rule_violation | error | improvement | loop_deviation",
        "severity": "blocking | non_blocking | info",
        "rule_ref": "string (关联规则路径)",
        "occurrences": 1,
        "first_seen": "ISO timestamp",
        "last_seen": "ISO timestamp",
        "source": "string (来源标识)"
    }
    ```

    ### WorkflowState (workflow_state.py 管理的 current-workflow.json)

    ```json
    {
        "topic": "string",
        "started_at": "ISO timestamp",
        "stages": {
            "explorer": {"iterations": 0, "history": [{"deviation_count": 0, "status": "ok", "timestamp": "..."}]},
            "tester": {"iterations": 0, "history": [...]}
        }
    }
    ```
    ```
  - **command-map**：CLI 命令表新增：
    | `python harness/scripts/generate_rule_evolution.py` | 扫描反馈信号，生成规则演化建议 | `harness/scripts/generate_rule_evolution.py` |
  - **change-map**：记录本次变更摘要（按现有格式追加）

- 完成标准：所有 project-map 文件内容准确反映新结构
- 验证命令：`python harness/scripts/check_structure.py`

### 测试任务 (-> Tester)

**TST-1: FeedbackSignal 数据模型测试**

- 文件：`tests/test_feedback_signal.py`
- 覆盖功能点：
  - `to_dict()` / `from_dict()` 往返序列化正确
  - `to_json_schema()` 返回合法 JSON Schema（包含所有字段定义，各字段 type 正确）
  - 默认字段值：occurrences 默认为 1，timestamps 自动设置且格式为 ISO 8601
  - 边界：signal_type 为非法值时的行为（不强制校验，只测构造不出错）

**TST-2: FeedbackEngine 反馈引擎测试**

- 文件：`tests/test_feedback_engine.py`
- 覆盖功能点：
  - 加载不存在的 JSON 文件返回空列表（不抛异常）
  - 添加新信号后保存/加载正确（verify round-trip）
  - 相同 `(signal_type, rule_ref)` 去重：occurrences 累加，last_seen 更新，first_seen 不变
  - 不同 signal_type 但相同 rule_ref 不互串（各自独立去重）
  - `detect_patterns()` 正确识别 >=3 次的重复模式（恰好 3 次时触发）
  - 原子写入：模拟写入中途文件损坏场景，原文件内容完整
  - 测试使用临时目录（`tempfile`），测试后清理

**TST-3: WorkflowState 工作流状态测试**

- 文件：`tests/test_workflow_state.py`
- 覆盖功能点：
  - `init()` 创建正确的初始状态 JSON（topic 和 stages 字段正确）
  - `init()` 重复调用覆盖旧状态
  - `record_stage()` 追加阶段记录，迭代计数递增
  - `get_deviation_trend()`：首次记录返回 "first_iteration"、偏差缩小返回 "shrinking"、不变返回 "stable"、增加返回 "growing"
  - `should_continue_loop()`：
    - 偏差缩小且迭代次数 < max_loops 返回 True
    - 偏差不变或增大返回 False（即使未超 max_loops）
    - 超过 max_loops 返回 False
  - `to_feedback_signal()` 输出合法的 FeedbackSignal 结构，signal_type 为 "loop_deviation"
  - 测试使用临时文件（`tempfile`），不污染实际 `harness/state/` 目录

**TST-4: generate_rule_evolution.py 脚本运行测试**

- 文件：`tests/test_generate_rule_evolution.py`
- 覆盖功能点：
  - 无重复模式时 stdout 输出 "No repeated patterns detected."，退出码 0
  - 存在一个 rule_ref >= 3 次时生成 `rule-evolution-proposal.md`，含：生成时间戳、变更理由、支持证据、状态标记 `待确认`
  - 已存在 proposal 时：已有 pattern 不重复生成，新 pattern 追加到末尾
  - script 退出码为 0（即使有重复模式产生 proposal）
  - 测试使用临时目录作为 `harness/feedback/` 和 `harness/state/`，通过 monkeypatch 或参数注入路径

## 3. 依赖关系

```
IMP-1 (FeedbackSignal 数据模型)
  ├── IMP-2 (FeedbackEngine) -- 依赖 IMP-1
  │     ├── IMP-4 (generate_rule_evolution.py) -- 依赖 IMP-2
  │     │     └── IMP-8 (Planner agent 升级) -- 依赖 IMP-4（文件路径引用）
  │     └── TST-2 (FeedbackEngine 测试) -- 依赖 IMP-2
  ├── IMP-3 (WorkflowState) -- 依赖 IMP-1
  │     ├── IMP-7 (命令入口文件升级) -- 依赖 IMP-3
  │     └── TST-3 (WorkflowState 测试) -- 依赖 IMP-3
  ├── TST-1 (FeedbackSignal 测试) -- 依赖 IMP-1
  └── TST-4 (generate_rule_evolution 测试) -- 依赖 IMP-4

IMP-5 (check_structure.py) -- 独立（仅依赖目录存在，可在 IMP-1 完成后立即执行）
IMP-6 (.gitignore) -- 独立（无条件依赖）
IMP-9 (project-map 文档) -- 依赖 IMP-1~IMP-4 全部完成后（反映最终文件结构）

并行组：
  Group A (顺序): IMP-1
  Group B (IMP-1 完成后可并行): IMP-2, IMP-3
  Group C (IMP-2/3 完成后可并行): IMP-4, IMP-5, IMP-6, IMP-7
  Group D (IMP-4 完成后): IMP-8
  Group E (IMP-1~IMP-4 全部完成后): IMP-9
  Group TST (对应 IMP 完成后按需执行): TST-1, TST-2, TST-3, TST-4
```

## 4. 风险点

1. **偏差量化代理指标不够精准** -- Explorer 的 `blocking_issues_count` 和 Tester 的 `failed_test_count` 作为偏差量代理指标，可能存在"同样的阻塞问题用不同措辞描述导致计数值波动"。决策：v0.1 使用关键词计数作为代理，后续版本可引入更精细量化。编排器提取偏差量时使用简单规则（搜索 "阻塞" / "FAILED" 关键词计数），不要求子 Agent 修改输出格式。

2. **JSON 写入并发冲突** -- 当前系统为单工作流串行执行，v0.1 不处理并发。原子写入（.tmp + os.replace）提供基本安全。

3. **`harness/state/` JSON 文件膨胀** -- `current-workflow.json` 随迭代累积历史记录，`feedback-signals.json` 持续追加。v0.1 不做归档。后续版本需引入归档策略（spec 已标记）。

4. **规则演化建议可能被忽略** -- 生成的 proposal 需人工确认才生效。缓解：Planner 启动时强制注入未处理建议到上下文（IMP-8）。

5. **命令入口文件修改影响现有工作流行为** -- 这是本次变更最高风险区域。4 个 `.claude/commands/workflow/*.md` 是主会话逐行执行的实际入口，修改回环决策逻辑时：
   - YAML frontmatter 完全不变（name/description/category/tags 保持原样）
   - 只升级正文中的编排器执行指令（Python 脚本调用 + 偏差趋势判断替换硬编码"最多 2 次"）
   - 每个命令文件必须自包含完整逻辑，不再使用 "同 full-cycle" 这类跨文件引用
   - quick-fix.md 只加 Tester 回环逻辑（其 Explorer 阻塞后直接报告用户并终止，不走回环）
   - `harness/workflow/*.md` 的 YAML frontmatter 仍被命令文件读取作为 stages 数据源，但正文完全不被读取

6. **coding-rules #4 命中** -- 每个新建 Python 脚本（feedback_signal.py、feedback_engine.py、workflow_state.py、generate_rule_evolution.py、__init__.py）必须在文件头 3 行内包含用途注释。

7. **coding-rules #1 命中** -- 新增模块前必须在 `module-map.md` 中登记（IMP-9 覆盖）。

8. **coding-rules #6 命中** -- 新增数据结构后必须同步更新 `data-flow.md`（IMP-9 覆盖）。

9. **coding-rules #2 命中** -- 新增 `harness/state/` 目录后必须在 `directory-map.md` 中更新（IMP-9 覆盖）。

10. **不引入第三方依赖** -- 所有功能使用 Python 标准库实现（`json`、`dataclasses`、`os`、`pathlib`、`datetime`、`shutil`）。测试可使用 `pytest` 和 `tempfile`（均为标准库/已安装）。

11. **IMP-7 编排器执行 Python 脚本需确保 sandbox 不阻止** -- 编排器通过 Bash 工具运行 Python 脚本。需确保工作目录正确，路径使用绝对路径或基于 `__file__` 的相对路径解析。`check_structure.py` 的 PROJECT_ROOT 计算方式（`__file__` 上溯 3 级）可作为参考。

12. **IMP-7 中 WorkflowState.stages 参数** -- full-cycle 和 implement 的 init() 传 `['explorer', 'tester']`（两个回环点），quick-fix 和 review-fix 仅传 `['tester']`（只有 Tester 回环）。WorkflowState.init() 实现需支持任意 stages 列表，不硬编码特定 stage id。
