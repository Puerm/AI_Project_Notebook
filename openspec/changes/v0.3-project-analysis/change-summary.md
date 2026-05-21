# Change Summary: v0.3 智能项目分析引擎

## 完成状态

**全部 8 个 IMP 任务已完成。**

## 新增文件 (6)

| 文件 | 说明 |
| ---- | ---- |
| `app/analyzer/__init__.py` | 包初始化，版本号 0.3.0 |
| `app/analyzer/scanner.py` | 目录扫描引擎，标准目录标注 + 内容推断，排除非源码目录，EXCLUDE_DIRS 与 init_project.py 对齐 |
| `app/analyzer/parser.py` | Python AST 解析 + JS/TS 解析（acorn 子进程优先，不可用时正则降级） |
| `app/analyzer/overview.py` | 技术栈检测、入口文件检测、项目类型推断、一句话描述生成 |
| `app/analyzer/llm_assistant.py` | LLM 语义增强（环境变量配置，urllib.request 调用，不可用时静默降级） |
| `app/analyzer/map_writer.py` | 生成 4 个 project-map 文件，原子写入，MANUAL 标记合并策略 |
| `harness/scripts/analyze_project.py` | CLI 入口命令，argparse 参数解析，4 步编排流水线 + 进度输出 |

## 修改文件 (9)

| 文件 | 改动 |
| ---- | ---- |
| `harness/scripts/check_structure.py` | REQUIRED_DIRS +`app/analyzer/`，REQUIRED_FILES +`analyze_project.py` (46/46) |
| `harness/scripts/help.py` | 版本号 v0.3，注册 `analyze_project.py` 命令 |
| `harness/scripts/init_project.py` | 部署时创建 `app/analyzer/` 目录骨架 |
| `harness/project-map/overview.md` | 版本 v0.2，新增分析引擎概念，更新下一步计划 |
| `harness/project-map/module-map.md` | 新增 6 个 analyzer 子模块 + analyze_project 命令模块登记 |
| `harness/project-map/command-map.md` | CLI 命令表新增 `analyze_project.py` 行 |
| `harness/project-map/directory-map.md` | 目录树新增 `app/analyzer/` + 标注"智能项目分析引擎" |
| `harness/project-map/data-flow.md` | 新增分析引擎数据流图 + 模块间依赖表 |
| `harness/project-map/change-map.md` | 记录 v0.3 变更摘要 |
| `README.md` | 版本号 v0.3，快速开始新增分析命令，目录树更新 |

## 验证结果

- `python harness/scripts/check_structure.py` — **PASS (46/46)**
- `python -m pytest tests/ -v` — **20 passed** (无回归)
- `python harness/scripts/analyze_project.py --help` — 正常输出
- `python harness/scripts/analyze_project.py .` — 正常生成 4 个文件
