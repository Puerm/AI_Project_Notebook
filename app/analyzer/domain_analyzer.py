# domain_analyzer.py — LLM 业务板块识别，输出结构化领域分析结果

import json
import sys
from app.analyzer.llm_assistant import _get_llm_config, _call_llm


def analyze_business_domains(guiding_files_result, dir_summary, project_name,
                             enable_dotenv=True):
    """识别项目的业务板块（用户视角的功能领域）。

    Args:
        guiding_files_result: collect_guiding_files() 的返回值
        dir_summary: generate_directory_summary() 的返回值
        project_name: 项目名称
        enable_dotenv: 是否加载 .env 文件

    Returns:
        dict: {one_liner, tech_stack, domains, relationships, next_steps, source}
    """
    config = _get_llm_config(enable_dotenv=enable_dotenv)
    if not config["api_key"]:
        return _degraded_domain_result(project_name)

    prompt = _build_domain_analysis_prompt(
        guiding_files_result, dir_summary, project_name
    )

    result = _call_llm(
        system_prompt=(
            "你是一位资深软件架构师，擅长从代码仓库中识别用户可见的业务功能模块。"
            "你的分析基于引导文件（README、依赖清单、CI配置）和目录结构摘要。"
            "业务板块是用户视角的功能领域，不是代码目录名。"
            "必须注明每条信息的来源（哪个文件/目录）。禁止凭空编造。"
            "不确定时标注低置信度。板块数量控制在 5-20 个。"
            "只返回 JSON，不要任何额外文字。"
        ),
        user_prompt=prompt,
        config=config,
        max_tokens=2048,
        timeout=60,
    )

    if result is None:
        return _degraded_domain_result(project_name)

    parsed = _parse_domain_response(result)
    if parsed is None:
        return _degraded_domain_result(project_name)

    parsed["source"] = "llm"
    return parsed


def _build_domain_analysis_prompt(guiding_files_result, dir_summary, project_name):
    """构造业务板块分析的 LLM prompt。"""
    found_files = guiding_files_result.get("found", [])
    missing = guiding_files_result.get("missing", [])

    parts = [f"# 项目名称\n{project_name}\n"]

    # Guiding file contents
    parts.append("# 引导文件内容\n")
    if found_files:
        for f in found_files:
            parts.append(f"## {f['file_path']} ({f['label']})\n")
            parts.append(f"```\n{f['content']}\n```\n")
    else:
        parts.append("(未找到任何引导文件)\n")

    if missing:
        parts.append("# 缺失的引导文件\n")
        parts.append("- " + "\n- ".join(missing[:10]) + "\n")

    # Directory summary
    parts.append(f"# 目录结构摘要\n```\n{dir_summary}\n```\n")

    # Output format specification
    parts.append("""# 输出要求
只返回一个 JSON 对象，格式如下：

{
  "one_liner": "一句话描述项目定位（≤50字中文）",
  "tech_stack": ["技术栈1", "技术栈2", ...],
  "domains": [
    {
      "name": "业务板块简称（≤15字中文）",
      "description": "板块功能描述（≤60字）",
      "evidence": "判断依据：来源文件和关键内容",
      "paths": ["关联目录路径1", "关联目录路径2"],
      "confidence": "高" | "中" | "低"
    }
  ],
  "relationships": [
    {
      "from": "来源板块名",
      "to": "目标板块名",
      "type": "依赖" | "调用" | "数据流" | "配置",
      "evidence": "判断依据"
    }
  ],
  "next_steps": [
    "建议下一步分析动作1（≤40字）",
    "建议下一步分析动作2（≤40字）",
    "建议下一步分析动作3（≤40字）"
  ]
}

约束规则：
- 业务板块是用户视角的功能领域，不是代码目录名
- 每个板块必须注明 evidence（来源）
- 禁止凭空编造不存在的功能
- 板块数量 5-20 个
- 不确定时标低置信度
- 每个板块的 paths 必须是实际存在的目录路径
- next_steps 是给开发者的分析建议，不是代码修改建议
""")

    return "\n".join(parts)


def _parse_domain_response(text):
    """从 LLM 响应中提取 JSON 结构，处理各种格式异常。"""

    def _try_parse(s):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None

    # 1. Direct parse
    result = _try_parse(text)
    if result and isinstance(result, dict) and "domains" in result:
        return _normalize_result(result)

    # 2. Extract from ```json ... ``` block
    import re
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if m:
        result = _try_parse(m.group(1))
        if result and isinstance(result, dict) and "domains" in result:
            return _normalize_result(result)

    # 3. Find first JSON-like object
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        candidate = text[brace_start:brace_end + 1]
        result = _try_parse(candidate)
        if result and isinstance(result, dict):
            return _normalize_result(result)

    return None


def _normalize_result(result):
    """确保返回结果包含所有必需字段。"""
    defaults = {
        "one_liner": "",
        "tech_stack": [],
        "domains": [],
        "relationships": [],
        "next_steps": [],
    }
    for key, default in defaults.items():
        if key not in result:
            result[key] = default
    return result


def _degraded_domain_result(project_name):
    """无 LLM Key 时的降级分析结果。"""
    return {
        "one_liner": f"{project_name} — 未启用 LLM 分析",
        "tech_stack": [],
        "domains": [
            {
                "name": "项目整体",
                "description": "未启用 LLM，无法识别业务板块。请使用 --llm 参数重新分析。",
                "evidence": "降级分析",
                "paths": ["."],
                "confidence": "低",
            }
        ],
        "relationships": [],
        "next_steps": [
            "配置 LLM API Key 以启用业务板块分析",
            "使用 --llm 参数重新运行分析",
            "查看引导文件（README.md 等）了解项目概况",
        ],
        "source": "degraded",
    }
