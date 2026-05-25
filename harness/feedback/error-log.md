# Error Log

记录开发和使用过程中遇到的错误，供后续分析和规则改进。

## 格式

```
### YYYY-MM-DD HH:MM — 错误简述

- **现象**: 发生了什么
- **触发**: 执行了什么操作
- **根因**: 为什么会发生（如果已知）
- **解决**: 如何修复的
- **关联规则**: 涉及 `harness/rules/` 下哪条规则
```

## 记录

### 2026-05-22 — v0.1.5 digest BioTec 实测：全量文件导致 LLM 架构分析严重失焦

- **现象**: digest 全量文件收集后，`architecture.md` 只分析了 `back/python/paper_agent/` 一个 CLI 脚本的 argparse 参数，完全忽略了 NestJS 后端（`back/src/` 十几模块）、React 前端（`front/`）、Worker 集群（AlphaFold/AutoDock/PyRosetta 等 10+ 个计算 worker）。而 v0.4 引导文件模式产出的 `project-overview.md` 正确识别了 10 个业务板块、技术栈、板块间关系。
- **触发**: `python harness/scripts/analyze_project.py "C:\Users\21093\Desktop\BioTec" --digest --quiet`
- **根因**: 
  1. 全量代码 dump 给 LLM 后，`paper_agent/main.py` 的巨大 argparse（20+ 参数）吸引了 LLM 全部注意力，被误判为"主入口"
  2. Architecture Prompt 没有"先全局扫描再深入"的两阶段设计——LLM 应该先列出所有顶级目录和模块角色，再选择关键模块深入
  3. digest 的全量文件淹没了 README.md、docker-compose.yml、package.json 等天然承载高层视角的引导文件——这些文件在 v0.4 中正是正确识别业务板块的关键信号
  4. `node_modules` 虽然被 digest 默认忽略，但 `back/dist/` 编译产物仍然混入，增加了噪声
- **解决**: 待修复。改进方向：(a) Architecture Prompt 增加"阶段一：全局组件识别"；(b) 两轮 LLM 调用——第一轮识别所有模块，第二轮深入分析；(c) digest 输出中保留引导文件的优先位置（放在 prompt 最前面）
- **关联规则**: `harness/rules/coding-rules.md` — LLM Prompt 设计缺少"全局→局部"的渐进式分析约束
- **严重程度**: **重大** — digest 集成核心价值（"帮助用户全面了解新项目"）未达成，全量数据反而比引导文件摘要效果更差

### 2026-05-21 — v0.3.2 BioTec --llm 实测：data-flow LLM 超时 + 多源码根串扰 + 模块粒度过粗

- **现象**: 
  1. data-flow 的 LLM 调用超时（Read operation timed out），降级为入口函数列表而非 LLM 推断的调用链
  2. `front` 源码根下面出现了 `back` 模块，`back` 源码根下面有 `front` 模块——多源码根模块划分互相串扰
  3. `back/python` 整个被当做一个模块，`paper_agent/` 下面的 8 个子模块（adapters/orchestrator/models...）没拆出来
  4. directory-map 仍有 Notebook 部署的 `app/analyzer/` 残留
- **触发**: `python harness/scripts/analyze_project.py "C:\Users\21093\Desktop\BioTec" --llm --depth 3`
- **根因**: 
  1. `_call_llm()` 硬编码 10 秒超时，data-flow 的 prompt 包含完整模块依赖 JSON + 12 个入口函数，DeepSeek 处理超时
  2. `detect_source_roots()` 将 `back/` 和 `front/` 都识别为源码根，但 `back/` 下也有 `front/` 子目录、`front/` 下也有 `back/` 子目录，模块分组时交叉污染
  3. 源码根检测只找到顶层 `back/`，没有进一步发现 `back/python/paper_agent/` 是更精准的 Python 源码根
  4. EXCLUDE_DIRS 缺少 `app/`，init_project 部署的 harness 被扫入
- **解决**: 已临时修复 data-flow 超时（分批 + 30 秒超时）；多源码根串扰、模块粒度过粗、目录残留待系统性修复
- **关联规则**: `harness/rules/coding-rules.md` — LLM 调用未考虑超时差异化；Spec 未定义多源码根去重/父子过滤逻辑

### 2026-05-21 — v0.3.1 --llm 实测：LLM 只增强了 overview 一句话，模块描述和数据流完全未走 LLM

### 2026-05-21 — v0.3.1 --llm 实测：LLM 只增强了 overview 一句话，模块描述和数据流完全未走 LLM

- **现象**: 对 BioTec 运行 `analyze_project.py --llm --depth 3`，module-map 中两个模块描述为"包含 576 个文件的 back 模块"（模板）、data-flow 显示"LLM 未启用"、技术栈仍为"通用"
- **触发**: `python harness/scripts/analyze_project.py "C:\Users\21093\Desktop\BioTec" --llm --depth 3`
- **根因**: 三个独立问题：
  1. `analyze_project.py` 第 163-184 行 LLM 调用只增强 `overview_result["description"]`（一句话概述），从未调用 LLM 增强模块描述或数据流
  2. `_infer_module_description()` 是 map_writer 的纯模板函数，不调用 LLM
  3. `generate_data_flow()` 在无 LLM 数据流参数时输出"LLM 未启用"模板，但 analyze_project.py 从未生成 LLM 数据流
  4. `detect_source_root()` 返回了项目根目录而非 `back/python/paper_agent/`，模块只有 back/front 两个
  5. `analyze_overview()` 的技术栈检测只搜根目录，没搜到深层目录里的 pyproject.toml 和 tsconfig.json
- **解决**: v0.3.2 已修复 — analyze_project.py 重构编排流程，新增 enhance_module_descriptions_batch()、enhance_data_flow_llm()、enhance_tech_stack_llm() 三个 LLM 增强函数
- **关联规则**: Spec 明确要求 LLM 增强模块描述和数据流，Generator 只实现了一部分
- **状态**: 已修复

### 2026-05-21 — v0.3 BioTec 输出：directory-map 在深度折叠下仍然包含自身 harness 目录

- **现象**: directory-map 在深度折叠后仍包含 `app/analyzer/` 等 harness 自身目录
- **触发**: init_project.py 部署后 directory-map 扫描到 harness 自身
- **根因**: EXCLUDE_DIRS 缺少 `harness`
- **解决**: 已修复 — v0.3 审查反馈修复中 scanner.py EXCLUDE_DIRS 增加 `harness`
- **关联规则**: `harness/rules/coding-rules.md`
- **状态**: 已修复

### 2026-05-20 16:22 — check_structure.py 用 Notebook 自身结构标准检查目标项目

- **现象**: 对 BioTec（NestJS+React 项目）运行 `check_structure.py`，报告 13 项缺失（`app/`、`data/`、`tests/`、`openspec/`、`.claude/agents/`、`CLAUDE.md` 等），必然 FAIL
- **触发**: `python harness/scripts/check_structure.py` 在目标项目 BioTec 下执行
- **根因**: `check_structure.py` 的检查清单硬编码了 AI_Project_Notebook 自身结构。它检查的是"运行它的项目有没有长成 Notebook 的样子"，而不是检查 harness 骨架自身是否完整
- **解决**: 已修复 — `check_structure.py` 的 REQUIRED_DIRS 移除了 `.claude/`、`.claude/agents/`、`.claude/commands/`、`.claude/skills/`，只检查 harness 骨架完整性
- **关联规则**: `harness/rules/workflow-rules.md` 第 7 条
- **状态**: 已修复

---

> 每当遇到错误，在此文件顶部（标题下方）添加一条记录。

---

### 2026-05-25T07:25:58.407383+00:00 — [sandbox_verify_failed] worktree 验证失败 (1 项)

```json
{
  "failures": [
    "pytest 异常: Command '['C:\\\\Python314\\\\python.exe', '-m', 'pytest', 'tests/', '-v']' timed out after 120 seconds"
  ]
}
```

---

### 2026-05-25T07:28:42.157415+00:00 — [sandbox_verify_failed] worktree 验证失败 (1 项)

```json
{
  "failures": [
    "pytest 异常: Command '['C:\\\\Python314\\\\python.exe', '-m', 'pytest', 'tests/', '-v']' timed out after 120 seconds"
  ]
}
```
