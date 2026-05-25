# Change Summary: Harness 自我升级引擎 v0.1

## 概述

实现 Harness 框架自我升级系统 v0.1。该系统在工作流收尾阶段自动扫描反馈信号中的重复模式，通过 LLM 根因诊断生成修复方案，在 git worktree 沙盒中验证后合并或降级输出。

## 实现文件

### 新建 (3)

| 文件 | 用途 |
| ---- | ---- |
| `harness/config/self-upgrade.yaml` | 自动程度配置（glob 匹配 auto/semi-auto/disabled）+ 安全边界 + 去重窗口 |
| `harness/prompts/diagnosis.txt` | LLM 诊断 prompt 模板 v1.0.0，宽上下文分析指令 + JSON 输出格式 |
| `harness/scripts/diagnose_and_fix.py` | 自我升级主引擎：反馈信号扫描 → 24h 去重 → LLM 诊断 → 安全边界 → git worktree 验证 → 合并/降级 |

### 修改 (11)

| 文件 | 变更 |
| ---- | ---- |
| `.gitignore` | 追加 `harness/state/upgrade-history.json` |
| `harness/scripts/check_structure.py` | REQUIRED_DIRS +2 (`harness/config`, `harness/prompts`), REQUIRED_FILES +3 |
| `.claude/commands/workflow/full-cycle.md` | 收尾阶段追加 `diagnose_and_fix.py` 触发指令 |
| `.claude/commands/workflow/implement.md` | 同上 |
| `.claude/commands/workflow/quick-fix.md` | 同上 |
| `.claude/commands/workflow/review-fix.md` | 同上 |
| `harness/project-map/directory-map.md` | 目录树新增 `config/` 和 `prompts/` |
| `harness/project-map/module-map.md` | 登记 `diagnose_and_fix.py` 模块 |
| `harness/project-map/command-map.md` | 登记 `diagnose_and_fix.py` 命令 |
| `harness/project-map/data-flow.md` | 新增自我升级数据流章节 |
| `harness/project-map/change-map.md` | 记录本次变更 |

## 核心流程

```
feedback-signals.json → detect_patterns (>=3次) → 24h去重
  → auto_level匹配 (auto/semi-auto/disabled)
  → LLM诊断 (宽上下文: 目标文件 + funnel关联 + 历史信号)
  → 安全边界检查 (insert≤50行, replace≤20行, delete需确认)
  → git worktree沙盒验证 (check_structure + pytest + agent YAML)
  → 合并或降级到 rule-evolution-proposal.md
  → 写入 upgrade-history.json
```

## 验证结果

- `python harness/scripts/check_structure.py` → **52/52 PASS** (15 dirs + 37 files)
- IMP-1: self-upgrade.yaml 存在
- IMP-2: diagnosis.txt 1713 字符，包含版本标记
- IMP-3: 所有核心函数可导入
- IMP-6: 4 个 workflow 命令文件均包含 `diagnose_and_fix.py` 触发指令

## 未实现项（计划为 Tester 职责）

以下 IMP-3 中的功能点由 Tester 通过测试验证，不在 Generator 实现范围内：
- dry-run 模式的端到端行为测试
- worktree 在各种失败场景下的清理逻辑验证
- semi-auto 交互超时的行为测试
- 24h 去重边界条件测试
