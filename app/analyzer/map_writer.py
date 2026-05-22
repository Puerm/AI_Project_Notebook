# map_writer.py — 项目地图文件生成，v0.4 渐进式概览输出

import os

MANUAL_MARKER = "<!-- MANUAL -->"


def _atomic_write(file_path, content):
    """原子写入：先写临时文件，再 rename 覆盖。"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, file_path)


def _read_existing(file_path):
    """读取已有文件内容。"""
    if not os.path.isfile(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _split_by_sections(content):
    """按 ## 标题将内容分割为段落字典。返回 {heading_text: section_body}。"""
    if not content:
        return {}
    lines = content.split("\n")
    sections = {}
    current_heading = None
    current_lines = []
    in_code_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            current_lines.append(line)
            continue
        if not in_code_fence and line.startswith("## ") and not line.startswith("### "):
            if current_heading is not None or current_lines:
                sections[current_heading or "__preamble__"] = "\n".join(current_lines)
            current_heading = stripped
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_heading is not None or current_lines:
        sections[current_heading or "__preamble__"] = "\n".join(current_lines)
    return sections


def _merge_sections(existing_content, new_content, section_headers=None):
    """按 ## 段落合并：保留 MANUAL 标记段落，更新非标记段落，追加新增段落。"""
    if not existing_content:
        return new_content

    existing_sections = _split_by_sections(existing_content)
    new_sections = _split_by_sections(new_content)

    result_parts = []
    used_headings = set()

    for heading, new_body in new_sections.items():
        if heading in existing_sections:
            existing_body = existing_sections[heading]
            used_headings.add(heading)
            if MANUAL_MARKER in existing_body:
                result_parts.append(existing_body)
            else:
                result_parts.append(new_body)
        else:
            result_parts.append(new_body)

    for heading, existing_body in existing_sections.items():
        if heading not in used_headings and MANUAL_MARKER in existing_body:
            result_parts.append(existing_body)

    return "\n\n".join(result_parts)


_CONFIDENCE_ICON = {"高": "✓", "中": "—", "低": "?"}


def generate_progressive_overview(domain_result, output_dir,
                                  project_name=None, llm_enabled=False):
    """生成渐进式项目概览（单一 project-overview.md 文件）。

    输出结构：定位 → 技术栈 → 板块表格 → 板块关系 → 下一步建议 → 页脚
    """
    os.makedirs(output_dir, exist_ok=True)

    one_liner = domain_result.get("one_liner", "")
    tech_stack = domain_result.get("tech_stack", [])
    domains = domain_result.get("domains", [])
    relationships = domain_result.get("relationships", [])
    next_steps = domain_result.get("next_steps", [])
    source = domain_result.get("source", "degraded")

    if project_name is None:
        project_name = "未命名项目"

    parts = []

    # Header
    parts.append(f"# {project_name} 项目概览\n")

    # LLM status notice — only when LLM call failed internally
    if source == "degraded":
        parts.append("> LLM 调用异常，以下为降级分析结果。请检查 API Key 和网络连接后重试。\n")

    # 定位
    parts.append("## 项目定位\n")
    if one_liner:
        parts.append(f"**{one_liner}**\n")
    else:
        parts.append("(待分析)\n")

    # 技术栈
    parts.append("## 技术栈\n")
    if tech_stack:
        parts.append(", ".join(tech_stack) + "\n")
    else:
        parts.append("(待分析)\n")

    # 业务板块表格
    parts.append("## 业务板块\n")
    if domains:
        header = "| 板块名称 | 板块描述 | 关联路径 | 置信度 | 证据来源 |"
        sep = "| ---- | ---- | ---- | ---- | ---- |"
        rows = [header, sep]
        for d in domains:
            name = d.get("name", "?")
            desc = d.get("description", "")
            paths = ", ".join(d.get("paths", [])) or "."
            confidence = d.get("confidence", "低")
            icon = _CONFIDENCE_ICON.get(confidence, "?")
            evidence = d.get("evidence", "")
            rows.append(f"| {name} | {desc} | {paths} | {icon} {confidence} | {evidence} |")
        parts.append("\n".join(rows) + "\n")
    else:
        parts.append("(未识别到业务板块)\n")

    # 板块关系
    parts.append("## 板块关系\n")
    if relationships:
        for r in relationships:
            frm = r.get("from", "?")
            to = r.get("to", "?")
            rtype = r.get("type", "关联")
            ev = r.get("evidence", "")
            parts.append(f"- **{frm}** → **{to}** ({rtype}) — {ev}\n")
    else:
        parts.append("(未识别到板块关系)\n")

    # 下一步建议
    parts.append("## 下一步建议\n")
    if next_steps:
        for i, step in enumerate(next_steps, 1):
            parts.append(f"{i}. {step}\n")
    else:
        parts.append("(无建议)\n")

    # Footer
    parts.append("---\n\n")
    if llm_enabled and source == "llm":
        parts.append("*v0.4 渐进式分析引擎生成 (LLM 增强)*\n")
    else:
        parts.append("*v0.4 渐进式分析引擎生成*\n")

    content = "\n".join(parts)

    file_path = os.path.join(output_dir, "project-overview.md")
    existing = _read_existing(file_path)
    final = _merge_sections(existing, content, [])
    _atomic_write(file_path, final)

    return file_path
