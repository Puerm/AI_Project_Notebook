# 侦察报告: v0.3-project-analysis

**严重程度: 无阻塞**

## 计划假设 vs 实际情况

| 文件 | 计划假设 | 实际情况 | 风险 |
| ---- | ---- | ---- | ---- |
| `app/analyzer/__init__.py` | 新文件，需创建 | `app/` 存在但为空（0 个文件，无子目录）。`app/analyzer/` 目录不存在。 | 需先创建目录（非阻塞） |
| `app/analyzer/scanner.py` | 新文件 | 不存在 | 无阻塞 |
| `app/analyzer/parser.py` | 新文件 | 不存在。Node.js v22.22.2 可用。`acorn` 和 `esprima` 均未全局安装。 | 无阻塞 |
| `app/analyzer/overview.py` | 新文件 | 不存在 | 无阻塞 |
| `app/analyzer/llm_assistant.py` | 新文件 | 不存在。Python stdlib `urllib.request` 可用。 | 无阻塞 |
| `app/analyzer/map_writer.py` | 新文件 | 不存在 | 无阻塞 |
| `harness/scripts/analyze_project.py` | 新文件 | 不存在 | 无阻塞 |
| `check_structure.py` | 修改：新增 app/analyzer/ 目录 + analyze_project.py 文件 | 当前 44 项（11 目录 + 33 文件）。IMP-8 后预期 46（12 目录 + 34 文件）。计划声称的"63/63"有误。 | Generator 应重新计算预期总计为 46 |
| `help.py` | 计划未提及 | 版本字符串硬编码为"v0.1"。COMMANDS 列表需新增 analyze_project.py 条目。 | 计划缺口：Generator 需一并修改 help.py |

## 基础设施可用性

| 依赖项 | 状态 | 备注 |
| ---- | ---- | ---- |
| Python | 3.14.3 | `ast`、`urllib.request`、`argparse` 均可用 |
| Node.js | v22.22.2 | JS 子进程运行时存在 |
| acorn (JS 解析器) | 未安装 | IMP-3 的检测+安装流程将触发 |
| esprima (JS 解析器) | 未安装 | 同上 |
| LLM API 密钥 | 未设置 | LLM 降级路径已覆盖 |
| `app/` 目录 | 存在，为空 | 非阻塞 |

## Spec 与计划对齐

- command-map 自动生成已标记为"暂不实现"（v0.4+），计划正确地将 map_writer 限制为 4 个文件
- LLM 配置方式：规范标记为"未决"，计划采用环境变量方案——无冲突

## 执行前提（给 Generator）

1. 修正 `check_structure.py` 的验证计数：当前基数 44，IMP-8 后应为 46
2. 一并修改 `help.py` 注册新命令
3. scanner 的排除列表需与 `init_project.py` 的 EXCLUDE_DIRS 对齐

## 可并行任务

IMP-1 到 IMP-6 无依赖，可并行进行。IMP-7 依赖 IMP-2~6。IMP-8 依赖 IMP-7。
