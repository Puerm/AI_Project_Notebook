# Module Map

各模块的职责、接口和依赖关系。

## 当前模块

v0.1 初始化阶段，尚无应用模块。

### 框架脚本

| 模块 | 文件 | 职责 | 依赖 |
| ---- | ---- | ---- | ---- |
| check_structure | `harness/scripts/check_structure.py` | 检查项目目录和关键文件完整性 | Python 3 标准库 |
| export_report | `harness/scripts/export_report.py` | 合并 project-map 输出格式化报告 | Python 3 标准库 |
| search_notes | `harness/scripts/search_notes.py` | 在 project-map 和 feedback 中搜索关键词 | Python 3 标准库 |
| help | `harness/scripts/help.py` | 打印所有可用命令 | Python 3 标准库 |
| init_project | `harness/scripts/init_project.py` | 复制 harness 骨架、部署 .claude/ 配置、扫描目录结构；部署后删除自身 | Python 3 标准库 (shutil) |

## 登记规则

新模块登记时必须填写：
1. 模块名称（与文件名对应）
2. 文件路径
3. 一句话职责描述
4. 依赖列表（依赖哪些模块/库）

## 变更规则

- 新增模块后在此文件中新增一行
- 修改模块职责后更新对应描述
- 模块被移除后标记为 `~~已移除~~` 并在 `change-map.md` 中记录
