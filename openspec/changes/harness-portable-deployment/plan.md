# Plan: Harness 框架个性化部署

## 1. 变更范围

### 需要新增的文件

| 文件 | 改动意图 |
| ---- | -------- |
| `harness/scripts/harness_deploy.py` | 主入口命令。LLM 驱动的项目检测 → 适配建议生成 → 交互式逐项确认流程。覆盖 spec 功能 A/B/C/D/E |

### 需要修改的文件

| 文件 | 改动意图 | 对应 spec 章节 |
| ---- | -------- | -------------- |
| `.claude/agents/pm.md` | 添加可适配区标记 `<!-- ADAPTABLE_ZONE_START/END -->`，将示例代码片段和语言特定约束包裹在可适配区 | 功能 B + 风险 2 |
| `.claude/agents/planner.md` | 同上 | 功能 B + 风险 2 |
| `.claude/agents/explorer.md` | 同上 | 功能 B + 风险 2 |
| `.claude/agents/generator.md` | 同上 | 功能 B + 风险 2 |
| `.claude/agents/reviewer.md` | 同上 | 功能 B + 风险 2 |
| `.claude/agents/tester.md` | 同上 | 功能 B + 风险 2 |
| `.claude/agents/harness_maintainer.md` | 同上 | 功能 B + 风险 2 |
| `harness/config/project.yaml` | 新增 `domain`、`description`、`entry_point` 三个字段 | 功能 A |
| `harness/scripts/help.py` | 注册 `harness_deploy` 命令 | 功能 A (命令入口) |
| `harness/scripts/check_structure.py` | REQUIRED_FILES 新增 `harness/scripts/harness_deploy.py` | 编码规则 8 |
| `harness/project-map/command-map.md` | 登记 `harness_deploy` 命令 | 编码规则 5 |
| `harness/project-map/module-map.md` | 登记 `harness_deploy.py` 模块 | 编码规则 1 |
| `harness/project-map/directory-map.md` | 更新 `harness/scripts/` 目录树（新增 harness_deploy.py） | 编码规则 2 |
| `harness/project-map/data-flow.md` | 新增 harness-deploy 数据流（LLM 检测 → 适配生成 → 交互确认） | 编码规则 6 |
| `harness/project-map/change-map.md` | 记录本次变更 | 工作流规则 14 |
| `harness/project-map/overview.md` | 版本号更新为 v0.10，下一步计划更新 | 工作流规则 14 |
| `README.md` | 新增 `harness_deploy` 使用说明，版本号更新 | 编码规则 5 |
| `CLAUDE.md` | 更新项目定位描述 | 功能 A |

---

## 2. 任务列表

### 实现任务 (-> Generator)

**IMP-1: 在 7 个 agent 文件中添加可适配区标记**

- 涉及文件：
  - `.claude/agents/pm.md`
  - `.claude/agents/planner.md`
  - `.claude/agents/explorer.md`
  - `.claude/agents/generator.md`
  - `.claude/agents/reviewer.md`
  - `.claude/agents/tester.md`
  - `.claude/agents/harness_maintainer.md`
- 操作：在每个 agent 文件中，将包含语言特定命令引用（如 `{{test_command}}`）、示例代码片段、语言特定约束（如 `snake_case.py` / `kebab-case.md`）的内容段落用 `<!-- ADAPTABLE_ZONE_START -->` 和 `<!-- ADAPTABLE_ZONE_END -->` 包裹。agent 的通用定位描述、角色职责、抽象行为逻辑等保留在标记外（通用区）。
- 参考 spec：功能 B（Agent 定义适配）+ 风险 2（通用区/可适配区分离）
- 完成标准：每个 agent 文件至少含有一对适配区标记，标记外的通用逻辑和标记内的可适配内容语义正确
- 验证命令：`python harness/scripts/check_structure.py`

**IMP-2: project.yaml 新增 domain / description / entry_point 字段**

- 涉及文件：`harness/config/project.yaml`
- 操作：在现有字段后追加三行：
  ```yaml
  domain: "AI 辅助开发工具"
  description: "面向 AI 辅助开发的项目理解与 Harness 反馈工作台"
  entry_point: "app/analyze_project.py"
  ```
- 参考 spec：功能 A（项目背景自动填充的目标字段）
- 完成标准：新增字段存在且 YAML 解析有效
- 验证命令：`python -c "import yaml; d=yaml.safe_load(open('harness/config/project.yaml')); assert 'domain' in d; assert 'description' in d; assert 'entry_point' in d; print('OK')"`

**IMP-3: 创建 harness_deploy.py 主脚本**

- 涉及文件：`harness/scripts/harness_deploy.py` (新建)
- 脚本职责与实现要点：

  **Phase 1: 项目检测 (LLM 增强 + 静态降级)**
  - 扫描目标项目目录结构（复用 `init_project.py` 的 `scan_tree` / `_detect_project_features` 静态检测逻辑作为降级路径）
  - 收集引导文件内容（README.md, package.json/go.mod/Cargo.toml 等配置文件，入口源文件前 100 行）
  - 构造 LLM prompt，要求输出：`languages`、`framework`、`domain`、`description`、`entry_point`
  - LLM 调用参考 `diagnose_and_fix.py` 的 API 调用方式（`_load_dotenv`, `_call_llm`），max_tokens=1024, timeout=60s
  - LLM 不可用时降级为静态检测（复用 `_detect_project_features`）
  - 输出"检测摘要"展示给用户作为第一个确认项（对应 spec 风险 1 缓解措施）

  **Phase 2: 适配建议生成**
  - 遍历 `harness/` 和 `.claude/` 下所有 .md / .yaml / .txt 文件
  - 对 agent 文件（`.claude/agents/*.md`）：解析 `<!-- ADAPTABLE_ZONE_START -->` / `<!-- ADAPTABLE_ZONE_END -->` 标记，提取可适配区内容，将项目特征 + 原始内容发送给 LLM 生成适配版本，适配内容包括：替换命令引用（如 `python -m pytest` -> `npx jest`）、替换示例代码片段语言、调整语言特定约束描述
  - 对 workflow 文件（`harness/workflow/*.md`）：根据项目类型（如纯前端项目无后端测试时跳过 tester 阶段）调整 stages 配置
  - 对规则文件（`harness/rules/*.md`）：LLM 根据新项目技术栈重写语言特定部分（如 TypeScript 项目生成 ESLint/tsconfig 相关规则、Go 项目生成 gofmt 相关规则），保留通用规则语义
  - 对 `harness/config/project.yaml`：填入 Phase 1 检测到的值
  - 对根目录 `CLAUDE.md`：根据检测结果生成项目定位描述和项目地图入口表

  **Phase 3: 交互式确认**
  - 逐项展示适配内容（检测摘要 -> project.yaml -> CLAUDE.md -> 各 agent -> 各 workflow -> 各 rules）
  - 每项展示格式：文件路径 + 修改前后 diff 视图 + 当前适配后的内容
  - 用户输入选项：`y` 确认应用 / `n` 跳过此修改 / `e` 打开编辑器手动修改
  - `e` 模式：将适配后内容写入临时文件，读取 `EDITOR` 环境变量启动编辑器，等待编辑器关闭后回读内容，重新展示 diff 供二次确认
  - 所有确认完成后执行原子写入（.tmp + os.replace）

- 参考 spec：功能 A（项目背景自动填充）、功能 B（Agent 定义适配）、功能 C（工作流适配）、功能 D（规则文件适配）、功能 E（交互式确认流程）、风险 1（检测摘要作为首个确认项）、风险 2（只修改可适配区）、风险 3（一致性检查）
- 完成标准：`python harness/scripts/harness_deploy.py --help` 输出用法信息，`python harness/scripts/harness_deploy.py <目标路径>` 启动交互流程
- 验证命令：`python harness/scripts/check_structure.py`

**IMP-4: 注册命令到 help.py / check_structure.py / command-map.md**

- 涉及文件：
  - `harness/scripts/help.py`
  - `harness/scripts/check_structure.py`
  - `harness/project-map/command-map.md`
- 操作：
  - `help.py`：在 CLI 命令表中新增一行 `| python harness/scripts/harness_deploy.py <目标路径> | Harness 框架个性化部署 — LLM 检测新项目并生成适配建议，交互式确认 | harness/scripts/harness_deploy.py |`
  - `check_structure.py`：在 REQUIRED_FILES 列表追加 `"harness/scripts/harness_deploy.py"`
  - `command-map.md`：在 CLI 命令表中新增一行
- 参考 spec：功能 A（命令注册）
- 完成标准：help.py 输出包含新命令，check_structure.py PASS
- 验证命令：`python harness/scripts/help.py` (确认新命令出现)，`python harness/scripts/check_structure.py`

**IMP-5: 更新 project-map 文档**

- 涉及文件：
  - `harness/project-map/module-map.md`
  - `harness/project-map/directory-map.md`
  - `harness/project-map/data-flow.md`
  - `harness/project-map/change-map.md`
  - `harness/project-map/overview.md`
- 操作：
  - `module-map.md`：在现有注册表末尾新增一行 `harness/scripts/harness_deploy.py | Harness 框架个性化部署 — LLM 检测 + 适配建议生成 + 交互式确认 | main | -`
  - `directory-map.md`：在 `harness/scripts/` 目录树下新增 `harness_deploy.py` 条目
  - `data-flow.md`：新增"harness-deploy 数据流"章节，描述 Phase 1/2/3 的数据流转路径（项目扫描 -> LLM 检测 -> 适配生成 -> 交互确认 -> 原子写入）
  - `change-map.md`：按记录规则新增本次变更条目（日期 2026-05-26、新功能、范围 1 新建 + 18 修改）
  - `overview.md`：
    - 当前版本 v0.9 -> v0.10
    - 核心能力新增第 7 项："Harness 框架个性化部署 — LLM 自动检测新项目 + 适配建议生成 + 交互式确认流程"
    - 当前状态表：版本 v0.10，最近变更 2026-05-26: Harness 框架个性化部署
    - 下一步计划更新为"在实际项目中验证 harness-deploy 的适配准确率"
- 参考 spec：编码规则 1/2/5/6，工作流规则 14
- 完成标准：所有文档更新完成，内容一致
- 验证命令：`python harness/scripts/check_structure.py`

**IMP-6: 更新 README.md 和 CLAUDE.md**

- 涉及文件：
  - `README.md`
  - `CLAUDE.md`
- 操作：
  - `README.md`：
    - 版本号 v0.9 -> v0.10
    - 新增一条版本历史：`| v0.10 | Harness 框架个性化部署 — LLM 检测新项目 + 适配建议生成 + 交互式确认 |`
    - 快速开始区域新增 `harness_deploy` 使用示例：
      ```bash
      # Harness 框架个性化部署（LLM 驱动）
      python harness/scripts/harness_deploy.py <目标项目路径>
      ```
    - 版本描述更新为 "v0.10"
    - 目录结构中 `harness/scripts/` 下新增 `harness_deploy.py` 条目
  - `CLAUDE.md`：
    - 项目定位描述更新为 "AI Project Notebook — 项目理解与知识沉淀工作台。v0.10 命令行版本。"
- 参考 spec：编码规则 5，工作流规则 15
- 完成标准：文档内容正确反映新功能
- 验证命令：`python harness/scripts/check_structure.py`

---

### 测试任务 (-> Tester)

**TST-1: harness_deploy.py CLI 基础测试**

- 涉及文件：`tests/test_harness_deploy.py` (新建)
- 覆盖功能点：
  - `harness_deploy.py --help` 输出包含用法说明（spec 功能 A 验收标准）
  - `harness_deploy.py <不存在的路径>` 正确报错退出码非零
  - `harness_deploy.py <存在的路径>` 启动交互流程（不会卡死在等待输入，能在 pipe 模式下正确输出检测摘要）
- 验证命令：`python -m pytest tests/test_harness_deploy.py -v`

**TST-2: 检测逻辑 + 模板占位符替换测试**

- 涉及文件：`tests/test_harness_deploy.py`
- 覆盖功能点：
  - 对包含 `package.json` 的测试 fixture 目录，静态检测逻辑正确识别为 javascript/typescript（spec 功能 A）
  - 对包含 `go.mod` 的测试 fixture 目录，正确识别为 go
  - `_fill_templates` 逻辑正确替换 `{{test_command}}` / `{{project_name}}` 等占位符（验证不会留下未替换的占位符）
  - zone marker 解析逻辑：能正确提取 `<!-- ADAPTABLE_ZONE_START -->` 到 `<!-- ADAPTABLE_ZONE_END -->` 之间的内容
- 验证命令：`python -m pytest tests/test_harness_deploy.py -v`

**TST-3: project.yaml 新增字段测试**

- 涉及文件：`tests/test_harness_deploy.py`
- 覆盖功能点：
  - `project.yaml` 包含 `domain`、`description`、`entry_point` 字段
  - 默认值不为空
  - YAML 结构有效（spec 功能 A 验收标准）
- 验证命令：`python -m pytest tests/test_harness_deploy.py -v`

---

## 3. 依赖关系

```
IMP-1 (agent 可适配区标记)     IMP-2 (project.yaml 新字段)
         │                              │
         └──────────┬───────────────────┘
                    │
                    ▼
              IMP-3 (harness_deploy.py 主脚本)
                    │
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
     IMP-4      IMP-5      IMP-6
  (命令注册)  (project-map) (README/CLAUDE)
         │          │          │
         └──────────┼──────────┘
                    │
                    ▼
            TST-1, TST-2, TST-3 (测试)
```

- IMP-1 和 IMP-2 可并行执行
- IMP-3 依赖 IMP-1 和 IMP-2 完成（脚本引用 zone 标记和 project.yaml 新字段）
- IMP-4、IMP-5、IMP-6 可并行执行（全部依赖 IMP-3 完成后文件路径确定）
- 所有 TST 任务依赖所有 IMP 任务完成

---

## 4. 风险点

1. **LLM 检测准确率（spec 风险 1 对应措施）**
   - 缓解：Phase 1 的"检测摘要"作为用户确认的第一个环节，后续所有适配都基于确认后的项目画像；静态检测逻辑作为 LLM 不可用时的降级路径
   - 注意：LLM prompt 中要求输出结构化 JSON，解析失败时降级为静态检测结果

2. **Agent 文件适配后丢失通用约束（spec 风险 2）**
   - 关键约束：`harness_deploy.py` 的适配逻辑严格只修改 `<!-- ADAPTABLE_ZONE_START -->` 到 `<!-- ADAPTABLE_ZONE_END -->` 之间的内容，不触碰标记外区域
   - IMP-1 的标记划分是此风险的前置防线，需要仔细审查每个 agent 文件中哪些内容是语言特定的（可适配）vs 通用的（不可修改）

3. **模板变量替换不完整（spec 风险 3）**
   - 缓解：自动化一致性检查 — `harness_deploy.py` 完成所有写入后，扫描所有目标文件确认不存在残留的 `{{...}}` 占位符和 `<!-- ADAPTABLE_ZONE_* -->` 标记

4. **交互式确认的编辑器触发方式（spec 未决问题）**
   - v0.1 实施策略：读取 `EDITOR` 环境变量，Windows 下默认 `notepad`，Unix 下默认 `vi`；将适配后内容写入临时文件 -> 打开编辑器 -> 等待进程退出 -> 回读并重新展示 diff
   - 若 `EDITOR` 未设置且默认编辑器不存在，降级为直接在终端展示修改内容并要求用户手动输入修改后的文本

5. **harness_deploy.py 的 LLM API Key 依赖**
   - `harness_deploy.py` 运行在目标项目上，目标项目可能没有 `.env` 文件
   - 在脚本启动时检查 API Key，不可用时告知用户并进入纯静态模式（跳过 LLM 增强的 B/C/D 阶段，只执行静态检测 + 模板填充）
   - 纯静态模式下在交互确认中标注"静态检测结果，建议配置 LLM 以获得更准确的适配"

6. **CLAUDE.md 写入范围控制**
   - `harness_deploy.py` 写入目标项目的 `CLAUDE.md`，但 `CLAUDE.md` 作为项目入口文件可能有用户自定义内容
   - 如果文件已存在，只更新"项目定位"和"项目地图入口"两个区块，其他内容保持不动（基于区块标题匹配做增量更新而非全量覆盖）
