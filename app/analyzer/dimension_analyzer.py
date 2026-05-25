# dimension_analyzer.py — 聚焦三维度分析引擎（架构/用户故事/风险），使用官方 prompt + 筛选文件子集

import os
import sys
import time

from app.analyzer.llm_assistant import _get_llm_config, _call_llm
from app.analyzer.prompts import load_prompt
from app.analyzer.digest_collector import format_files_for_llm

RETRY_MAX = 3
RETRY_BASE_DELAY = 2


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


def _build_architecture_prompt_from_files(filtered_files, project_name):
    """基于筛选后的文件子集构造架构分析用户 prompt。"""
    files_text = format_files_for_llm(filtered_files)
    return load_prompt("architecture").format(
        project_name=project_name,
        files_content=files_text,
    )


def _build_stories_prompt_from_files(filtered_files, arch_text, project_name):
    """基于筛选后的文件子集构造用户故事分析用户 prompt。"""
    files_text = format_files_for_llm(filtered_files)
    arch_context = arch_text[:2000] if arch_text else "(架构分析不可用)"
    prompt_template = load_prompt("user_stories")
    user_prompt = prompt_template.format(
        project_name=project_name,
        files_content=files_text,
    )
    user_prompt += f"\n\n# 架构分析摘要（作为上下文参考）\n```\n{arch_context}\n```\n"
    return user_prompt


def _build_risk_prompt_from_files(filtered_files, arch_text, stories_text, project_name):
    """基于筛选后的文件子集构造风险分析用户 prompt。"""
    files_text = format_files_for_llm(filtered_files)
    arch_summary = arch_text[:1500] if arch_text else "(架构分析不可用)"
    stories_summary = stories_text[:1500] if stories_text else "(用户故事分析不可用)"
    prompt_template = load_prompt("risk")
    user_prompt = prompt_template.format(
        project_name=project_name,
        files_content=files_text,
    )
    user_prompt += f"\n\n# 架构分析摘要（作为上下文参考）\n```\n{arch_summary}\n```\n"
    user_prompt += f"\n# 用户故事分析摘要（作为上下文参考）\n```\n{stories_summary}\n```\n"
    return user_prompt


def _call_llm_with_retry(system_prompt, user_prompt, config, max_tokens=4096, timeout=120):
    """调用 LLM，失败时自动重试（最多 3 次，指数退避）。"""
    for attempt in range(1, RETRY_MAX + 1):
        result = _call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            config=config,
            max_tokens=max_tokens,
            timeout=timeout,
            silent=True,
        )
        if result is not None:
            if attempt > 1:
                print(f"  [重试成功] 第 {attempt} 次调用成功", file=sys.stderr)
            return result
        if attempt < RETRY_MAX:
            delay = RETRY_BASE_DELAY ** attempt
            print(f"  [重试 {attempt}/{RETRY_MAX}] API 调用失败，{delay}s 后重试...", file=sys.stderr)
            time.sleep(delay)
    print(f"  [重试耗尽] {RETRY_MAX} 次重试后仍失败，降级处理", file=sys.stderr)
    return None


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


def analyze_architecture(filtered_files, project_name, output_dir, enable_dotenv=True):
    """聚焦架构分析，接收筛选后的文件子集，写入 analysis/architecture.md。"""
    available, config = _check_llm_available(enable_dotenv)

    if not available:
        content = _degraded_architecture(project_name)
        file_path = _write_analysis_file(output_dir, "architecture.md", content)
        return {"file_path": file_path, "status": "degraded", "content": content}

    user_prompt = _build_architecture_prompt_from_files(filtered_files, project_name)
    result = _call_llm_with_retry(
        system_prompt="你是一位资深软件架构师，擅长从代码中识别架构模式并生成结构化的架构分析报告。输出完整的 Markdown 文档。",
        user_prompt=user_prompt,
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


def analyze_user_stories(filtered_files, arch_md_text, project_name, output_dir, enable_dotenv=True):
    """聚焦用户故事重建，接收筛选后的文件子集，写入 analysis/user-stories.md。"""
    available, config = _check_llm_available(enable_dotenv)

    if not available:
        content = _degraded_user_stories(project_name)
        file_path = _write_analysis_file(output_dir, "user-stories.md", content)
        return {"file_path": file_path, "status": "degraded", "content": content}

    user_prompt = _build_stories_prompt_from_files(filtered_files, arch_md_text, project_name)
    result = _call_llm_with_retry(
        system_prompt="你是一位资深产品经理，擅长从代码仓库中反向重建用户故事。每个故事必须有代码证据。输出完整的 Markdown 文档。",
        user_prompt=user_prompt,
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


def analyze_risk(filtered_files, arch_md_text, stories_md_text, project_name, output_dir, enable_dotenv=True):
    """聚焦风险分析，接收筛选后的文件子集，写入 analysis/risk-analysis.md。"""
    available, config = _check_llm_available(enable_dotenv)

    if not available:
        content = _degraded_risk(project_name)
        file_path = _write_analysis_file(output_dir, "risk-analysis.md", content)
        return {"file_path": file_path, "status": "degraded", "content": content}

    user_prompt = _build_risk_prompt_from_files(filtered_files, arch_md_text, stories_md_text, project_name)
    result = _call_llm_with_retry(
        system_prompt="你是一位资深代码审查专家和安全工程师，擅长发现代码中的潜在错误和安全风险。输出完整的 Markdown 文档。",
        user_prompt=user_prompt,
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
