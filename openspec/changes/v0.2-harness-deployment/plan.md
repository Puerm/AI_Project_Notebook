# Implementation Plan: v0.2 Harness 部署范围修正 + 工作流系统部署

## 1. 变更范围

### 需要修改的文件

| 文件 | 改动意图 |
| ---- | ---- |
| `harness/scripts/init_project.py` | 新增 `.claude/` 部署逻辑 (agents/commands/skills)；部署后删除目标项目中的自身 |
| `harness/scripts/check_structure.py` | `REQUIRED_DIRS`/`REQUIRED_FILES` 加回 `.claude/` 相关条目；移除 `init_project.py`（目标项目不包含它）；与部署行为一致 |
| `tests/test_init_project.py` | 新增 5 个测试用例覆盖新部署行为 |
| `harness/project-map/change-map.md` | 记录本次变更 |
| `harness/project-map/directory-map.md` | 无需修改（Notebook 自身目录结构未变，仅部署逻辑变） |

### 不需要修改但需注意

- `.claude/agents/` (7 个 agent 定义文件): 本次不修改内容，仅作为部署源
- `.claude/commands/opsx/` (4 个 OpenSpec 命令): 不部署到目标项目，不纳入检查清单
- `.claude/skills/` (4 个 OpenSpec 技能): 不部署到目标项目，目标项目的 `skills/` 创建为空目录
- `harness/skills/README.md`: 通过 harness copytree 正常部署，不受影响

---

## 2. 任务列表

### 实现任务 (-> Generator)

#### IMP-1: init_project.py — 部署后删除目标项目中的 init_project.py

- **涉及文件**: `harness/scripts/init_project.py`
- **改动内容**: 在 `shutil.copytree(HARNESS_ROOT, target_harness)` 之后，追加删除目标路径 `harness/scripts/init_project.py` 的逻辑
- **具体做法**:
  1. 构造目标脚本路径: `os.path.join(target_harness, "scripts", "init_project.py")`
  2. 若文件存在则 `os.remove()` 并打印确认消息
- **完成标准**: 部署后目标项目 `harness/scripts/` 下不含 `init_project.py`
- **验证命令**: `python -m pytest tests/test_init_project.py::test_init_project_does_not_deploy_itself -v`

---

#### IMP-2: init_project.py — 部署 .claude/agents/ 到目标项目

- **涉及文件**: `harness/scripts/init_project.py`
- **改动内容**: 在 `init_project()` 函数中，将 Notebook 的 `.claude/agents/` 完整复制到目标项目
- **具体做法**:
  1. 定义源路径: `claude_src = os.path.join(PROJECT_ROOT, ".claude")`
  2. 确保目标 `.claude/` 目录存在: `os.makedirs(os.path.join(target, ".claude"), exist_ok=True)`
  3. 使用 `shutil.copytree(claude_src/agents/, target/.claude/agents/, dirs_exist_ok=True)`
  4. 打印确认消息
- **完成标准**: 目标项目 `.claude/agents/` 下含 7 个 agent `.md` 文件 (harness_maintainer, pm, planner, explorer, generator, reviewer, tester)
- **验证命令**: `python -m pytest tests/test_init_project.py::test_init_deploys_claude_agents -v`

---

#### IMP-3: init_project.py — 部署 .claude/commands/ 到目标项目 (仅 pm + workflow)

- **涉及文件**: `harness/scripts/init_project.py`
- **改动内容**: 将 `.claude/commands/pm/` 和 `.claude/commands/workflow/` 复制到目标项目，排除 `opsx/`
- **具体做法**:
  1. 对 `["pm", "workflow"]` 循环调用 `shutil.copytree`，源为 `claude_src/commands/{subdir}`，目标为 `target/.claude/commands/{subdir}`，带 `dirs_exist_ok=True`
  2. 打印确认消息
- **完成标准**: 目标项目 `.claude/commands/` 下含 `pm/` (1 文件) 和 `workflow/` (4 文件)，不含 `opsx/`
- **验证命令**: `python -m pytest tests/test_init_project.py::test_init_deploys_claude_commands -v`

---

#### IMP-4: init_project.py — 创建空的 .claude/skills/ 目录

- **涉及文件**: `harness/scripts/init_project.py`
- **改动内容**: 在目标项目中创建空的 `.claude/skills/` 目录
- **具体做法**:
  1. `os.makedirs(os.path.join(target, ".claude", "skills"), exist_ok=True)`
  2. 打印确认消息
- **完成标准**: 目标项目 `.claude/skills/` 存在且为空
- **验证命令**: `python -m pytest tests/test_init_project.py::test_init_creates_empty_claude_skills -v`

---

#### IMP-5: check_structure.py — 加回 .claude/ 目录和关键文件检查，移除 init_project.py

- **涉及文件**: `harness/scripts/check_structure.py`
- **改动内容**: 在 `REQUIRED_DIRS` 中加入 `.claude/`、`.claude/agents/`、`.claude/commands/`、`.claude/skills/`；在 `REQUIRED_FILES` 中加入 7 个 agent 文件 + 5 个 pm/workflow command 文件；**从 REQUIRED_FILES 中移除 `"harness/scripts/init_project.py"`**
- **具体做法**:
  1. `REQUIRED_DIRS` 追加 4 项: `".claude"`, `".claude/agents"`, `".claude/commands"`, `".claude/skills"`
  2. `REQUIRED_FILES` 追加 12 项:
     - `.claude/agents/harness_maintainer.md`, `pm.md`, `planner.md`, `explorer.md`, `generator.md`, `reviewer.md`, `tester.md`
     - `.claude/commands/pm/discuss.md`
     - `.claude/commands/workflow/full-cycle.md`, `implement.md`, `quick-fix.md`, `review-fix.md`
  3. `REQUIRED_FILES` 移除 1 项: `"harness/scripts/init_project.py"` — 该文件仅在 Notebook 源码项目中存在，目标项目部署后会删除它（IMP-1），因此不可在检查清单中要求它。Notebook 自身仍包含该文件，但从清单中移除后，Notebook 运行 check_structure.py 时不会检查它（额外文件不触发缺失告警，仍为 PASS）。
  4. **注意**: 不要求 `.claude/commands/opsx/` 也不要求 `.claude/skills/` 下的文件——这些是 Notebook 自身开发用的 OpenSpec 能力，不属于部署范围
- **完成标准**: Notebook 自身运行 `check_structure.py` 输出 PASS；部署到目标项目后也 PASS
- **验证命令**: `python harness/scripts/check_structure.py` (预期 PASS)

---

### 测试任务 (-> Tester)

#### TST-1: test_init_project_does_not_deploy_itself

- **涉及文件**: `tests/test_init_project.py`
- **覆盖功能点**: 验证 `init_project.py` 在目标项目的 `harness/scripts/` 下不存在
- **验证命令**: `python -m pytest tests/test_init_project.py::test_init_project_does_not_deploy_itself -v`

#### TST-2: test_init_deploys_claude_agents

- **涉及文件**: `tests/test_init_project.py`
- **覆盖功能点**: 验证目标项目 `.claude/agents/` 下存在全部 7 个 agent 文件
- **验证命令**: `python -m pytest tests/test_init_project.py::test_init_deploys_claude_agents -v`

#### TST-3: test_init_deploys_claude_commands

- **涉及文件**: `tests/test_init_project.py`
- **覆盖功能点**: 验证目标项目 `.claude/commands/` 下存在 `pm/discuss.md` 和 4 个 workflow 命令，不存在 `opsx/`
- **验证命令**: `python -m pytest tests/test_init_project.py::test_init_deploys_claude_commands -v`

#### TST-4: test_init_creates_empty_claude_skills

- **涉及文件**: `tests/test_init_project.py`
- **覆盖功能点**: 验证目标项目 `.claude/skills/` 存在且为空目录
- **验证命令**: `python -m pytest tests/test_init_project.py::test_init_creates_empty_claude_skills -v`

#### TST-5: test_init_deployed_project_passes_check_structure

- **涉及文件**: `tests/test_init_project.py`
- **覆盖功能点**: 对部署后的目标项目运行 `check_structure.py` 验证 PASS
- **验证命令**: `python -m pytest tests/test_init_project.py::test_init_deployed_project_passes_check_structure -v`

---

## 3. 依赖关系

```
IMP-1 ──┐
IMP-2 ──┼── 并行 (均修改 init_project.py 不同位置，但需在同一函数内顺序执行)
IMP-3 ──┤
IMP-4 ──┘
         │
         ▼
IMP-5 (独立，不依赖 IMP-1~4)
```

- **实现任务**: IMP-1 到 IMP-4 均修改同一个函数 `init_project()`，应在一次编辑中完成（按上述顺序）。IMP-5 独立修改 `check_structure.py`，可与 IMP-1~4 并行。
- **测试任务**: 全部 5 个 TST 任务依赖 IMP-1~4 完成。TST-1~5 均修改 `test_init_project.py`，可在一个文件中按顺序编写。TST-1~5 之间无相互依赖，可在同一轮测试中全部运行。
- **Tester 启动条件**: Generator 完成 IMP-1~5 后，Tester 才开始执行 TST-1~5。

---

## 4. 风险点

| 风险 | 应对 |
| ---- | ---- |
| 目标项目可能已有 `.claude/` 配置 (如 BioTec 的 `settings.local.json`) | 使用 `os.makedirs(exist_ok=True)` + 仅拷贝子目录，不触碰 `.claude/` 根目录文件。冲突处理暂不实现（spec 明确推迟） |
| `shutil.copytree` 的 `dirs_exist_ok` 需要 Python 3.8+ | 项目已在 Python 3 环境下运行，确认满足 |
| agent 定义包含 Notebook 特定版本约束 | spec 明确本次不改 agent 定义，后续版本处理 |
| `check_structure.py` 在目标项目跑会检查 12 个 `.claude/` 文件 | 与部署行为一致——部署了这些文件，检查它们存在是合理的。Notebook 自身因有额外 opsx/skills 内容，检查也 PASS（额外文件不触发缺失告警） |
| `init_project.py` 需从 REQUIRED_FILES 中移除，否则目标项目 check_structure 会 FAIL | **已在 IMP-5 中处理**：从 `REQUIRED_FILES` 移除 `"harness/scripts/init_project.py"`。Notebook 自身仍保留该文件，但 check_structure 不再要求它（额外文件不触发 FAIL） |
