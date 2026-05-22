# dimension_analyzer.py — 三维度代码分析引擎（架构/用户故事/风险），含 LLM 增强和降级模式

import os
import sys

from app.analyzer.llm_assistant import _get_llm_config, _call_llm


def _check_llm_available(enable_dotenv=True):
    """检查 LLM API Key 是否可用。"""
    config = _get_llm_config(enable_dotenv=enable_dotenv)
    return bool(config["api_key"]), config


def _write_analysis_file(output_dir, filename, content):
    """原子写入分析文件到 analysis/ 目录。"""
    analysis_dir = os.path.join(output_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    file_path = os.path.join(analysis_dir, filename)
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, file_path)
    return file_path


def _build_architecture_prompt(digest_text, project_name, max_chars=6000):
    """构造架构分析 LLM prompt。"""
    truncated = digest_text[:max_chars]
    if len(digest_text) > max_chars:
        truncated += "\n\n...(codebase digest truncated, total within limit)"

    return f"""# 项目名称
{project_name}

# 代码库摘要（codebase-digest 全量文件收集）
```
{truncated}
```

# 输出要求
请分析该项目的架构分层，输出一份 Markdown 格式的架构分析报告。

报告结构：
1. **架构风格** — 识别使用的架构模式（如 MVC、微服务、分层架构等）
2. **分层说明** — 每层的职责、关键目录、主要模块
3. **技术选型** — 使用的框架、库、中间件
4. **关键设计决策** — 重要的架构决策点
5. **改进建议** — 架构层面的改进空间

约束：
- 只分析能从代码中确认的内容
- 不确定的部分标注 [推测]
- 报告用中文编写
- 输出完整的 Markdown 文档，标题以 # 开始
"""


def _build_stories_prompt(digest_text, arch_text, project_name, max_chars=6000):
    """构造用户故事分析 LLM prompt。"""
    truncated = digest_text[:max_chars]
    if len(digest_text) > max_chars:
        truncated += "\n\n...(truncated)"

    arch_summary = arch_text[:2000] if arch_text else "(架构分析不可用)"

    return f"""# 项目名称
{project_name}

# 架构分析摘要
```
{arch_summary}
```

# 代码库摘要（codebase-digest 全量文件收集）
```
{truncated}
```

# 输出要求
请基于代码库和架构分析，反向重建该项目的用户故事。输出一份 Markdown 格式的用户故事文档。

报告结构：
1. **核心用户故事** — 按优先级排列的用户故事列表（格式：作为 <角色>，我想要 <目标>，以便 <价值>）
2. **功能模块映射** — 每个故事对应的代码模块路径
3. **故事依赖关系** — 故事之间的先后顺序和依赖
4. **技术支持故事** — 非功能性需求对应的故事（性能、安全、可维护性等）

约束：
- 每个故事必须有代码证据支撑
- 引用架构分析（architecture.md）作为上下文
- 不确定的功能标注 [推测]
- 用中文编写
"""


def _build_risk_prompt(digest_text, arch_text, stories_text, project_name, max_chars=6000):
    """构造风险分析 LLM prompt。"""
    truncated = digest_text[:max_chars]
    if len(digest_text) > max_chars:
        truncated += "\n\n...(truncated)"

    arch_summary = arch_text[:1500] if arch_text else "(架构分析不可用)"
    stories_summary = stories_text[:1500] if stories_text else "(用户故事分析不可用)"

    return f"""# 项目名称
{project_name}

# 架构分析摘要
```
{arch_summary}
```

# 用户故事分析摘要
```
{stories_summary}
```

# 代码库摘要（codebase-digest 全量文件收集）
```
{truncated}
```

# 输出要求
请分析该项目的潜在错误和风险，输出一份 Markdown 格式的风险分析报告。

报告结构：
1. **安全风险** — 硬编码密钥、注入风险、权限问题等
2. **稳定性风险** — 错误处理缺失、资源泄漏、并发问题等
3. **可维护性风险** — 代码重复、耦合度高、缺少文档等
4. **技术债务** — 过时依赖、不推荐使用的模式等
5. **缓解建议** — 具体可行的改进方案

约束：
- 引用架构分析（architecture.md）和用户故事分析（user-stories.md）作为上下文
- 只分析代码中能确认的风险
- 风险按严重程度排序（高/中/低）
- 用中文编写
"""


def _degraded_architecture(project_name):
    """无 LLM Key 时的降级架构分析。"""
    return f"""# {project_name} — 架构分析（降级）

> 未配置 LLM API Key，以下为基于目录结构的降级分析。

## 架构风格
（无法自动识别，请配置 LLM 后重新分析）

## 分层说明
基于项目目录结构的分层推断：

- **应用层**: `app/` 目录包含核心业务逻辑
- **脚本层**: `harness/scripts/` 包含命令行工具入口
- **配置层**: 项目根目录和 `.claude/` 下的配置文件
- **数据层**: `data/` 和 `harness/project-map/` 包含数据文件

## 技术选型
（请使用 `--digest` 参数并配置 LLM 以获取详细技术选型分析）

## 关键设计决策
（无法自动分析）

## 改进建议
1. 配置 LLM API Key (ANTHROPIC_API_KEY) 以获取完整的架构分析
2. 使用 `python harness/scripts/analyze_project.py <路径> --digest` 重新分析
"""


def _degraded_user_stories(project_name):
    """无 LLM Key 时的降级用户故事分析。"""
    return f"""# {project_name} — 用户故事（降级）

> 未配置 LLM API Key，以下为基于入口文件的降级分析。

## 核心用户故事
（无法自动重建，请配置 LLM 后重新分析）

## 入口文件列表
以下为检测到的入口文件（可能对应主要功能）：

- `harness/scripts/help.py` — 打印可用命令
- `harness/scripts/check_structure.py` — 检查项目结构
- `harness/scripts/analyze_project.py` — 项目分析引擎
- `harness/scripts/search_notes.py` — 搜索笔记
- `harness/scripts/export_report.py` — 导出报告
- `harness/scripts/init_project.py` — 初始化项目

## 故事依赖关系
（无法自动分析）

## 技术支持故事
1. 配置 LLM API Key 以获取完整的用户故事重建
2. 使用 `python harness/scripts/analyze_project.py <路径> --digest` 重新分析

> 上下文引用: 参见 [architecture.md](architecture.md) 了解项目架构概览。
"""


def _degraded_risk(project_name):
    """无 LLM Key 时的降级风险分析。"""
    return f"""# {project_name} — 风险分析（降级）

> 未配置 LLM API Key，以下为基础静态检查结果。

## 静态检查结果

### .env 文件
- 检查 .env 是否存在于项目根目录
- 确保 .gitignore 包含 .env 规则

### 代码结构
- 检查是否有过大的单一文件（>2000 行）
- 检查是否有空的 `__init__.py`

### 依赖管理
- 检查是否有 requirements.txt 或 pyproject.toml

## 安全风险
（无法自动分析，请配置 LLM 后重新分析）

## 稳定性风险
（无法自动分析）

## 可维护性风险
（无法自动分析）

## 技术债务
（无法自动分析）

## 缓解建议
1. 配置 LLM API Key (ANTHROPIC_API_KEY) 以获取完整的风险分析
2. 使用 `python harness/scripts/analyze_project.py <路径> --digest` 重新分析

> 上下文引用: 参见 [architecture.md](architecture.md) 和 [user-stories.md](user-stories.md) 了解项目上下文。
"""


def analyze_architecture(digest_text, project_name, output_dir, enable_dotenv=True):
    """LLM 架构分层分析，写入 analysis/architecture.md。"""
    available, config = _check_llm_available(enable_dotenv)

    if not available:
        content = _degraded_architecture(project_name)
        file_path = _write_analysis_file(output_dir, "architecture.md", content)
        return {"file_path": file_path, "status": "degraded", "content": content}

    prompt = _build_architecture_prompt(digest_text, project_name)
    result = _call_llm(
        system_prompt="你是一位资深软件架构师，擅长从代码中识别架构模式并生成结构化的架构分析报告。输出完整的 Markdown 文档。",
        user_prompt=prompt,
        config=config,
        max_tokens=4096,
        timeout=120,
    )

    if result is None:
        content = _degraded_architecture(project_name)
        file_path = _write_analysis_file(output_dir, "architecture.md", content)
        return {"file_path": file_path, "status": "degraded", "content": content}

    full_content = f"# {project_name} — 架构分析\n\n{result}"
    file_path = _write_analysis_file(output_dir, "architecture.md", full_content)
    return {"file_path": file_path, "status": "llm", "content": full_content}


def analyze_user_stories(digest_text, arch_md_text, project_name, output_dir, enable_dotenv=True):
    """LLM 反向重建用户故事，写入 analysis/user-stories.md。"""
    available, config = _check_llm_available(enable_dotenv)

    if not available:
        content = _degraded_user_stories(project_name)
        file_path = _write_analysis_file(output_dir, "user-stories.md", content)
        return {"file_path": file_path, "status": "degraded", "content": content}

    prompt = _build_stories_prompt(digest_text, arch_md_text, project_name)
    result = _call_llm(
        system_prompt="你是一位资深产品经理，擅长从代码仓库中反向重建用户故事。每个故事必须有代码证据。输出完整的 Markdown 文档。",
        user_prompt=prompt,
        config=config,
        max_tokens=4096,
        timeout=120,
    )

    if result is None:
        content = _degraded_user_stories(project_name)
        file_path = _write_analysis_file(output_dir, "user-stories.md", content)
        return {"file_path": file_path, "status": "degraded", "content": content}

    full_content = f"# {project_name} — 用户故事\n\n{result}\n\n> 上下文引用: 参见 [architecture.md](architecture.md) 了解项目架构概览。"
    file_path = _write_analysis_file(output_dir, "user-stories.md", full_content)
    return {"file_path": file_path, "status": "llm", "content": full_content}


def analyze_risk(digest_text, arch_md_text, stories_md_text, project_name, output_dir, enable_dotenv=True):
    """LLM 错误与风险分析，写入 analysis/risk-analysis.md。"""
    available, config = _check_llm_available(enable_dotenv)

    if not available:
        content = _degraded_risk(project_name)
        file_path = _write_analysis_file(output_dir, "risk-analysis.md", content)
        return {"file_path": file_path, "status": "degraded", "content": content}

    prompt = _build_risk_prompt(digest_text, arch_md_text, stories_md_text, project_name)
    result = _call_llm(
        system_prompt="你是一位资深代码审查专家和安全工程师，擅长发现代码中的潜在错误和安全风险。输出完整的 Markdown 文档。",
        user_prompt=prompt,
        config=config,
        max_tokens=4096,
        timeout=120,
    )

    if result is None:
        content = _degraded_risk(project_name)
        file_path = _write_analysis_file(output_dir, "risk-analysis.md", content)
        return {"file_path": file_path, "status": "degraded", "content": content}

    full_content = f"# {project_name} — 风险分析\n\n{result}\n\n> 上下文引用: 参见 [architecture.md](architecture.md) 和 [user-stories.md](user-stories.md) 了解项目上下文。"
    file_path = _write_analysis_file(output_dir, "risk-analysis.md", full_content)
    return {"file_path": file_path, "status": "llm", "content": full_content}
