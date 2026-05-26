# Change Summary: Harness 框架个性化部署

## 完成状态

全部 6 个 IMP 任务完成，验证通过 (52/52)。

## 实现内容

- **IMP-1**: 7 个 agent 文件添加 `ADAPTABLE_ZONE_START/END` 可适配区标记
- **IMP-2**: `project.yaml` 新增 `domain`/`description`/`entry_point` 字段
- **IMP-3**: 新建 `harness_deploy.py`（三阶段：LLM 检测 + 适配生成 + 交互确认）
- **IMP-4**: `help.py`/`check_structure.py`/`command-map.md` 注册命令
- **IMP-5**: 5 个 project-map 文档更新（module/directory/data-flow/change/overview）
- **IMP-6**: `README.md`/`CLAUDE.md` 版本 v0.9→v0.10，新增使用说明

## 验证结果

`python harness/scripts/check_structure.py` — 52/52 PASS
`python harness/scripts/harness_deploy.py --help` — 正确输出用法信息

## 审查修复 (generator-fix)

Reviewer 发现 3 个问题，已全部修复：

1. **`_adapt_workflow_content` L452 — `{{project_name}}` 替换值来源错误**
   - 修复：`os.path.basename(os.getcwd())` 改为 `features.get("project_name", os.path.basename(os.getcwd()))`
   - 现在 `{{project_name}}` 使用 Phase 1 检测到的项目名而非当前工作目录名

2. **`_adapt_workflow_content` L442-444 — `is_frontend_only`/`is_go_only`/`is_rust_only` 死代码**
   - 修复：三个变量现在用于确定需要标记为 skip 的阶段 id 集合
   - `is_frontend_only` -> 跳过 `tester`/`generator-fix`/`generator-test-fix` 阶段
   - `is_go_only`/`is_rust_only` -> 所有阶段适用，但不做跳过（显式判断消除死代码）

3. **`_adapt_workflow_content` 未实现项目类型条件适配（计划 SPEC 功能 C）**
   - 修复：在 YAML frontmatter 解析后，对不适用阶段添加 `skip: true` 标记
   - 满足 Spec 功能 C 验收标准："不适用阶段被移除或标记为 skip"
   - 使用 `yaml.safe_load` + `yaml.dump` 安全操作 frontmatter，异常时静默降级（不破坏原内容）

验证：`python harness/scripts/check_structure.py` — 52/52 PASS
功能测试：前端项目正确标记 skip，Go/Python 项目不标记 skip，模板占位符正确替换

## 待 Tester 执行

TST-1 至 TST-3 测试任务（tests/test_harness_deploy.py 新建）。
