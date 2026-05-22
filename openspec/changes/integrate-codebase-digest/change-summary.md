# Change Summary: 集成 Codebase Digest (v0.1.5)

## 完成状态

全部 6 个实现任务 (IMP-1 ~ IMP-6) 已完成。

## 完成摘要

- **IMP-1**: 新建 `app/analyzer/digest_collector.py` — 封装 codebase-digest API（可用性检测、全量文件收集、噪声过滤、max-size 截断、LLM 文本格式化），stdout 重定向抑制调试输出，优雅降级返回 `cdigest_unavailable` 状态
- **IMP-2**: 新建 `app/analyzer/dimension_analyzer.py` — 三维度分析引擎（arch/user-stories/risk），每维度含 LLM prompt + 降级函数 + 原子写入，输出到 `analysis/` 目录
- **IMP-3**: 修改 `analyze_project.py` — 新增 `--digest` / `--max-size` CLI 参数，digest 模式 6 步流程（收集→领域→概览→架构→故事→风险），非 digest 模式完全保持不变
- **IMP-4**: 修改 `help.py` — 版本号 v0.4 → v0.5，命令描述更新
- **IMP-5**: 修改 `module-map.md` — 登记 2 个新模块
- **IMP-6**: 修改 `command-map.md`、`data-flow.md`、`change-map.md`、`README.md` — 文档同步更新

## 验证结果

- `python harness/scripts/check_structure.py`: **46/46 PASS**
- `python -m pytest tests/test_analyze_project.py -v`: **50/51 PASS** (1 失败：`test_help_output` 因版本号 v0.4→v0.5 变更，待 Tester 在 TST-3 更新)
- 手动验证：
  - `collect_digest('.')` → status=ok, 91 files, 367727 chars
  - `_degraded_architecture/ user_stories/ risk()` → 均返回合理内容
  - `help.py` → 输出含 v0.5 和 --digest 描述

## generator-fix: 审查反馈修复

全部 4 个审查问题已修复：

- **FIX-1**: `digest_collector.py` — 4 个函数 (run_digest_collection / preprocess_digest / format_digest_for_llm / collect_digest) 多行 docstring 改为单行描述
- **FIX-2**: `dimension_analyzer.py` — 3 个函数 (analyze_architecture / analyze_user_stories / analyze_risk) 多行 docstring 改为单行描述
- **FIX-3**: `analyze_project.py` — 移除非 digest 模式下的重复 print 语句（行 189-191）
- **FIX-4**: `directory-map.md` — `app/analyzer/` 目录树补充 digest_collector.py 和 dimension_analyzer.py

验证结果:
- `check_structure.py`: 46/46 PASS
- `pytest test_analyze_project.py`: 50/51 PASS (1 失败为预存 test_help_output 问题)

## 遗留给 Tester 的任务

- **TST-1**: 新建 `tests/test_digest_collector.py` (6 个测试用例)
- **TST-2**: 新建 `tests/test_dimension_analyzer.py` (7 个测试用例)
- **TST-3**: 更新 `tests/test_analyze_project.py` (6 个测试用例，包括修复 `test_help_output` 版本号断言)
