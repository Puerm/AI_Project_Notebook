# Coding Rules

可执行的编码规则，非口号。每条规则必须可验证。

## 文件与目录

1. 新增模块前必须在 `harness/project-map/module-map.md` 中登记模块名称、用途、依赖
2. 新增目录后必须在 `harness/project-map/directory-map.md` 中更新目录结构
3. 文件命名遵循项目约定的命名规范
4. 每个 Python 脚本必须在文件头 3 行内包含一行描述其用途的注释

## 代码变更

5. 修改 CLI 命令后必须同步更新 `README.md` 和 `harness/project-map/command-map.md`
6. 修改数据结构（类字段、文件格式）后必须同步更新 `harness/project-map/data-flow.md`
7. 修改公开函数签名后必须更新 `harness/project-map/module-map.md` 中对应的接口说明
8. 任何代码修改后必须运行项目配置的结构验证命令

## 测试

9. 新增功能必须在 `tests/` 下添加对应的测试文件
10. 测试文件命名：`test_<模块名>.py`
11. 修改代码后必须运行相关测试：{{test_command}}

## 注释

12. 仅在 WHY 不明显时写注释——解释为什么这样做，而不是这段代码做了什么
13. 不要写多行 docstring，一行描述即可
14. 不要写"由 XX 调用"、"用于 YY 场景"之类的注释——这些信息在 commit message 或 PR 描述中
