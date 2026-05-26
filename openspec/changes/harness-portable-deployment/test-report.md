## 测试报告

### 结论: 通过

所有 55 个新增测试用例全部通过，零失败。现有回归测试 365 个全部通过，结构检查 52/52 PASS。

### 测试概况

- 新增用例: 55
- 通过: 55
- 失败: 0
- 跳过: 0

### 失败详情

无。

### 失败分类

| 类别 | 数量 | 处理方式 |
| ---- | ---- | ---- |
| 测试自身问题 | 0 | - |
| 代码 bug | 0 | - |

### 覆盖情况

| 模块/类 | 测试点 | 状态 |
| ---- | ---- | ---- |
| TestCliBasics (TST-1) | --help 输出、不存在路径报错、缺参数报错、无 harness 目录提示、-h 短选项 | 7/7 PASS |
| TestDetectProjectFeatures (TST-2a) | JS(package.json)、Go(go.mod)、Rust(Cargo.toml)、Python、空目录 unknown、字段完整性、harness/.claude 排除 | 7/7 PASS |
| TestParseAdaptableZones (TST-2b) | 单 zone 提取、多 zone 提取、无 zone 返回原始 | 3/3 PASS |
| TestAdaptWorkflowContent (TST-2c) | {{test_command}}/{{project_name}}等占位符替换、前端 skip 标记、Go/Python/Rust 不 skip、无 frontmatter 不崩溃、frontmatter 外内容保留 | 9/9 PASS |
| TestGenerateAdaptedProjectYaml (TST-2d) | domain/description/entry_point 字段存在、值非空、YAML 有效性验证 | 6/6 PASS |
| TestGenerateAdaptedClaudeMd (TST-2e) | 项目名称、描述、项目地图入口表 | 3/3 PASS |
| TestCheckConsistency (TST-2f) | 残留占位符检测、残留 zone marker 检测、干净文件通过、非.md/.yaml/.txt 跳过 | 4/4 PASS |
| TestAtomicWrite (TST-2g) | 创建文件、覆盖已有文件、自动创建父目录 | 3/3 PASS |
| TestTryFindEntryPoint (TST-2h) | Python 入口 main.py、Go 入口 main.go、无可返回空串 | 3/3 PASS |
| TestCollectDirectorySummary (TST-2i) | 非空目录返回非空摘要、. 开头目录排除 | 2/2 PASS |
| TestProjectYamlNewFields (TST-3) | domain/description/entry_point 存在、值非空、YAML 合法、全字段可解析 | 8/8 PASS |

### 回归检查

| 检查项 | 结果 |
| ---- | ---- |
| 现有测试套件 (15 个文件, 365 个用例) | 365/365 PASS |
| harness/scripts/check_structure.py | 52/52 PASS |

### 与计划任务的对照

| 计划任务 | 测试用例覆盖 | 状态 |
| ---- | ---- | ---- |
| TST-1: CLI 基础测试 | TestCliBasics (7 个用例) | 完成 |
| TST-2: 检测逻辑 + 模板替换 | TestDetectProjectFeatures + TestParseAdaptableZones + TestAdaptWorkflowContent + TestGenerateAdaptedProjectYaml + TestGenerateAdaptedClaudeMd + TestCheckConsistency + TestAtomicWrite + TestTryFindEntryPoint + TestCollectDirectorySummary (40 个用例) | 完成 |
| TST-3: project.yaml 新增字段 | TestProjectYamlNewFields (8 个用例) | 完成 |

### 修正记录

| 轮次 | 问题 | 类型 | 处理 |
| ---- | ---- | ---- | ---- |
| 1 | 路径字符串包含未转义反斜杠导致 SyntaxError | 测试自身问题 | 改为 Unix 风格路径 |
| 1 | subprocess stderr 编码 GBK vs UTF-8 导致 result.stderr 为 None | 测试自身问题 | subprocess.run 添加 errors="replace" |
| 1 | Rust fixture 将 src 创建为文件又尝试创建为目录导致 FileExistsError | 测试自身问题 | 移除错误文件创建 |
