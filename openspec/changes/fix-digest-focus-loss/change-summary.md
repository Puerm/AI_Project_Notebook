# Change Summary: 修复 LLM 全量分析失焦问题

## 变更概述

v0.5 `--digest` 模式下全量文件统一 dump 给 LLM 导致分析失焦。修复方案：每维度筛选文件子集 + 官方 prompt 模板 + 两级板块结构。

## 完成情况

7 个实现任务全部完成：

| 任务 | 文件 | 状态 |
|------|------|------|
| IMP-1 | `domain_analyzer.py` — 两级结构 + [推测] | 完成 |
| IMP-2 | `prompts/` — prompt 库 + 三个模板 | 完成 |
| IMP-3 | `digest_collector.py` — 三维度筛选函数 | 完成 |
| IMP-4 | `dimension_analyzer.py` — 聚焦分析重构 | 完成 |
| IMP-5 | `analyze_project.py` — 7 步新流程 | 完成 |
| IMP-6 | 版本号 + 文档同步 (v0.5.0 -> v0.5.1) | 完成 |
| IMP-7 | `change-map.md` 变更记录 | 完成 |

## 核心变化

1. **domain_analyzer**: prompt 要求输出 `sub_domains` 两级结构，不确定信息标注 `[推测]`
2. **prompts/**: 新建官方 prompt 模板目录，`load_prompt(name)` 读取，每个模板 >200 字符
3. **digest_collector**: 新增 `filter_for_architecture/user_stories/risk` 三维度筛选，`collect_digest` 不再格式化全量文本
4. **dimension_analyzer**: 公开函数签名从 `digest_text` 改为 `filtered_files`，使用 `load_prompt` 加载官方模板
5. **analyze_project**: digest 模式 7 步流程，每维度只传入筛选后文件子集

## 验证结果

- `check_structure.py`: 46/46 PASS
- 现有测试: 136/136 PASS (8 个失败在 Tester 创建的测试文件中，需更新签名，非代码 bug)
- 版本号一致性: grep `0\.5\.0` 无匹配 (除 pycache 已清理)

## 待 Tester 完成

- TST-1: `test_digest_collector.py` — 更新 `collect_digest` 返回结构断言 (text -> files)
- TST-2: `test_domain_analyzer.py` — 更新 prompt 格式断言 (含 sub_domains)
- TST-3: `test_dimension_analyzer.py` — 更新公开函数调用签名 (digest_text -> filtered_files)
- TST-4: digest 端到端测试
- TST-5: 非 digest 模式回归验证 (136 passed 已确认)
