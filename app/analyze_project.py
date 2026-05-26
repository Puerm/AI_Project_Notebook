# analyze_project.py — 智能项目分析引擎 v0.5.1 渐进式披露 + digest 聚焦三维度分析
# 入口文件：app/analyze_project.py

import argparse
import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.analyzer.guiding_files import collect_guiding_files, generate_directory_summary
from app.analyzer.domain_analyzer import analyze_business_domains
from app.analyzer.map_writer import generate_progressive_overview
from app.analyzer.llm_assistant import check_api_key_available, _get_llm_config, _call_llm_with_tools


# CodeGraph tool definition for LLM function calling
_CODEGRAPH_TOOL_DEF = [{
    "type": "function",
    "function": {
        "name": "query_codegraph",
        "description": "执行只读 SQL 查询探索 CodeGraph 符号知识图谱。"
                       "可用于查询符号列表、函数调用关系、模块依赖等。"
                       "仅支持 SELECT 语句。",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "要执行的 SQL SELECT 查询语句",
                },
            },
            "required": ["sql"],
        },
    },
}]

# Anthropic 兼容格式：使用顶层 "name" 字段
_CODEGRAPH_TOOL_DEF_ANTHROPIC = [
    {
        "name": "query_codegraph",
        "description": "执行只读 SQL 查询探索 CodeGraph 符号知识图谱。"
                       "可用于查询符号列表、函数调用关系、模块依赖等。"
                       "仅支持 SELECT 语句。",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "要执行的 SQL SELECT 查询语句",
                },
            },
            "required": ["sql"],
        },
    },
]


def _run_codegraph_exploration(target_path, quiet=False):
    """运行 CodeGraph 探索阶段：检测 db -> 提取 schema -> LLM tool-use 多轮探索，返回探索结果文本或 None。"""
    from app.analyzer.codegraph import (
        detect_codegraph_db, connect_codegraph_db,
        extract_schema_summary, execute_query, format_schema_for_llm,
    )

    # 检测数据库
    db_path = detect_codegraph_db(target_path)
    if not db_path:
        if not quiet:
            print("  CodeGraph: 未检测到 .codegraph/codegraph.db")
            print("  建议安装 CodeGraph (https://github.com/..."
                  ") 并运行索引后重试")
        return None

    if not quiet:
        print(f"  CodeGraph: 检测到数据库 {db_path}")

    # 连接并提取 schema
    try:
        conn = connect_codegraph_db(db_path)
        schema = extract_schema_summary(conn)
        schema_text = format_schema_for_llm(schema)
        conn.close()
    except Exception as e:
        print(f"  CodeGraph: Schema 提取失败: {e}", file=sys.stderr)
        return None

    if not quiet:
        table_count = len(schema.get("tables", []))
        print(f"  CodeGraph: 提取到 {table_count} 个表的 schema")

    # LLM tool-use 多轮探索
    config = _get_llm_config(enable_dotenv=True)

    if config["provider"] == "anthropic":
        tools_def = _CODEGRAPH_TOOL_DEF_ANTHROPIC
    else:
        tools_def = _CODEGRAPH_TOOL_DEF

    def tool_handler(tool_name, arguments):
        if tool_name == "query_codegraph":
            sql = arguments.get("sql", "")
            # 重新连接（只读）
            conn2 = connect_codegraph_db(db_path)
            try:
                rows = execute_query(conn2, sql)
            finally:
                conn2.close()
            return json.dumps(rows, ensure_ascii=False, indent=2)
        return f"未知工具: {tool_name}"

    system_prompt = (
        "你是一位代码分析专家，可以通过 query_codegraph 工具查询 CodeGraph 符号知识图谱。\n"
        "目标：深入理解项目结构，发现关键符号（函数、类、模块）及其调用关系。\n"
        "策略建议：先了解有哪些类型的符号和表结构，再查关键函数的调用链，最后确认入口函数和核心依赖。\n"
        "每次查询后根据结果决定下一步，逐步深入，达到 3-5 轮探索后给出总结。"
    )

    user_prompt = (
        f"以下是目标项目的 CodeGraph 知识图谱 Schema 摘要，请探索该项目的关键符号关系:\n\n"
        f"{schema_text}\n\n"
        f"请通过 query_codegraph 工具逐步查询，最终给出项目的符号级关系总结。"
    )

    if not quiet:
        print("  CodeGraph: LLM 多轮探索中...")

    exploration_result = _call_llm_with_tools(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tools_def=tools_def,
        tool_handler=tool_handler,
        config=config,
        max_rounds=5,
        timeout=120,
    )

    return exploration_result


def main():
    parser = argparse.ArgumentParser(
        description="智能项目分析引擎 v0.5.1 — 渐进式披露 + --digest 聚焦三维度分析",
        epilog=(
            "环境变量 (LLM 必需):\n"
            "  ANTHROPIC_API_KEY   Anthropic API Key\n"
            "  LLM_API_KEY         OpenAI 兼容 API Key\n"
            "  LLM_API_BASE        自定义 API 地址 (可选)\n"
            "  LLM_MODEL           模型名称 (可选, 默认: gpt-4o-mini)\n\n"
            "也可在项目根目录创建 .env 文件配置以上变量。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target_path", nargs="?", default=".",
        help="目标项目路径 (默认: 当前目录)"
    )
    parser.add_argument(
        "--output-dir", "-o", default=None,
        help="输出目录 (默认: <target_path>/harness/project-map/)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", default=False,
        help="精简输出模式"
    )
    parser.add_argument(
        "--digest", action="store_true", default=False,
        help="启用聚焦三维度分析 (架构/用户故事/风险)，每维度仅传入相关文件子集"
    )
    parser.add_argument(
        "--max-size", type=int, default=10240,
        help="digest 最大输出大小(KB), 默认 10240 (10 MB)"
    )
    parser.add_argument(
        "--codegraph", action="store_true", default=False,
        help="启用 CodeGraph 图谱增强分析 (需预先安装 CodeGraph 并完成索引)"
    )

    args = parser.parse_args()

    target_path = os.path.abspath(args.target_path)
    output_dir = args.output_dir or os.path.join(target_path, "harness", "project-map")
    project_name = os.path.basename(target_path) or "unknown"

    if not os.path.exists(target_path):
        print(f"错误: 目标路径不存在: {target_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(target_path):
        print(f"错误: 目标路径不是目录: {target_path}", file=sys.stderr)
        sys.exit(1)

    # API Key 检查（LLM 是强制依赖）
    key_ok, guidance = check_api_key_available()
    if not key_ok:
        print("错误: LLM API Key 未配置。\n", file=sys.stderr)
        print(guidance, file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"分析目标: {target_path}")
        print(f"输出目录: {output_dir}")

    # ── Digest 模式 ──
    if args.digest:
        from app.analyzer.digest_collector import (
            collect_digest,
            filter_for_architecture,
            filter_for_user_stories,
            filter_for_risk,
        )
        from app.analyzer.dimension_analyzer import (
            analyze_architecture, analyze_user_stories, analyze_risk,
        )

        # [digest/1] Guiding file overview (same as non-digest Step 1)
        if not args.quiet:
            print("[digest/1] 收集引导文件...")
        try:
            guiding_result = collect_guiding_files(target_path)
        except Exception as e:
            print(f"[digest/1] 引导文件收集失败: {type(e).__name__}: {e}", file=sys.stderr)
            guiding_result = {"found": [], "missing": []}
        try:
            dir_summary = generate_directory_summary(target_path)
        except Exception as e:
            print(f"[digest/1] 目录摘要生成失败: {type(e).__name__}: {e}", file=sys.stderr)
            dir_summary = f"项目根: {project_name}\n(目录摘要生成失败)"
        if not args.quiet:
            print(f"  收集到 {len(guiding_result['found'])} 个引导文件")

        # [digest/2] Business domain analysis (now with two-level structure)
        if not args.quiet:
            print("[digest/2] 业务板块识别（两级：主板块 + 子板块）...")
        try:
            domain_result = analyze_business_domains(
                guiding_result, dir_summary, project_name,
                enable_dotenv=True,
            )
        except Exception as e:
            print(f"[digest/2] 板块识别失败: {type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)
        if not args.quiet:
            domains_count = len(domain_result.get("domains", []))
            print(f"  识别到 {domains_count} 个业务板块")

        # [digest/3] Generate project-overview.md
        if not args.quiet:
            print("[digest/3] 生成项目概览...")
        try:
            generate_progressive_overview(
                domain_result, output_dir,
                project_name=project_name,
                llm_enabled=True,
            )
        except Exception as e:
            print(f"[digest/3] 文件生成失败: {type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)

        # [digest/3.5] CodeGraph exploration (only if --codegraph enabled)
        codegraph_context = None
        if args.codegraph:
            if not args.quiet:
                print("[digest/3.5] CodeGraph 图谱探索...")
            codegraph_context = _run_codegraph_exploration(target_path, quiet=args.quiet)
            if codegraph_context:
                if not args.quiet:
                    print(f"  CodeGraph 探索完成 ({len(codegraph_context)} 字符)")
            else:
                if not args.quiet:
                    print("  CodeGraph 探索跳过（无可用数据库或探索失败）")

        # [digest/4] Digest file pool collection (collect files only, no LLM text)
        if not args.quiet:
            print("[digest/4] digest 文件池收集...")
        digest_result = collect_digest(target_path, max_size_kb=args.max_size)
        if digest_result["status"] == "ok":
            digest_files = digest_result["files"]
            if not args.quiet:
                print(f"  收集到 {len(digest_files)} 个文件")
        elif digest_result["status"] == "cdigest_unavailable":
            print("警告: codebase-digest 未安装，跳过聚焦分析。", file=sys.stderr)
            print("  安装: pip install codebase-digest", file=sys.stderr)
            digest_files = None
        else:
            print(f"警告: digest 收集失败 ({digest_result.get('error', 'unknown')})，"
                  "跳过聚焦分析。", file=sys.stderr)
            digest_files = None

        # Three-dimension focused analysis (only if digest files are available)
        if digest_files:
            # [digest/5] Architecture focused analysis
            if not args.quiet:
                print("[digest/5] 架构聚焦分析...")
            arch_filtered = filter_for_architecture(digest_files)
            if not args.quiet:
                print(f"  筛选出 {len(arch_filtered)} 个架构相关文件")
            arch_result = analyze_architecture(
                arch_filtered, project_name, target_path, enable_dotenv=True,
                codegraph_context=codegraph_context,
            )
            if not args.quiet:
                print(f"  {arch_result['status']}: {arch_result['file_path']}")
            arch_content = arch_result["content"]

            # Rate limit avoidance: pause between API calls
            time.sleep(3)

            # [digest/6] User stories focused analysis
            if not args.quiet:
                print("[digest/6] 用户故事聚焦分析...")
            stories_filtered = filter_for_user_stories(digest_files)
            if not args.quiet:
                print(f"  筛选出 {len(stories_filtered)} 个用户故事相关文件")
            stories_result = analyze_user_stories(
                stories_filtered, arch_content, project_name, target_path, enable_dotenv=True,
                codegraph_context=codegraph_context,
            )
            if not args.quiet:
                print(f"  {stories_result['status']}: {stories_result['file_path']}")
            stories_content = stories_result["content"]

            # Rate limit avoidance: pause between API calls
            time.sleep(3)

            # [digest/7] Risk focused analysis
            if not args.quiet:
                print("[digest/7] 风险聚焦分析...")
            risk_filtered = filter_for_risk(digest_files)
            if not args.quiet:
                print(f"  筛选出 {len(risk_filtered)} 个风险相关文件")
            risk_result = analyze_risk(
                risk_filtered, arch_content, stories_content,
                project_name, target_path, enable_dotenv=True,
                codegraph_context=codegraph_context,
            )
            if not args.quiet:
                print(f"  {risk_result['status']}: {risk_result['file_path']}")

        if not args.quiet:
            print(f"\n分析完成，输出到 {output_dir}")
            print(f"  - project-overview.md")
            if digest_files:
                analysis_dir = os.path.join(target_path, "analysis")
                print(f"  - {analysis_dir}/architecture.md")
                print(f"  - {analysis_dir}/user-stories.md")
                print(f"  - {analysis_dir}/risk-analysis.md")

        return

    # ── 非 digest 模式（保持现有流程不变）──

    # Step 1: Collect guiding files + directory summary
    if not args.quiet:
        print("[1/3] 收集引导文件 + 目录摘要...")
    try:
        guiding_result = collect_guiding_files(target_path)
    except Exception as e:
        print(f"[1/3] 引导文件收集失败: {type(e).__name__}: {e}", file=sys.stderr)
        guiding_result = {"found": [], "missing": []}

    try:
        dir_summary = generate_directory_summary(target_path)
    except Exception as e:
        print(f"[1/3] 目录摘要生成失败: {type(e).__name__}: {e}", file=sys.stderr)
        dir_summary = f"项目根: {project_name}\n(目录摘要生成失败)"

    if not args.quiet:
        print(f"  收集到 {len(guiding_result['found'])} 个引导文件")
        print(f"  目录摘要: {len(dir_summary.splitlines())} 行")

    # Step 1.5: CodeGraph exploration (only if --codegraph enabled)
    codegraph_context = None
    if args.codegraph:
        if not args.quiet:
            print("[1.5/3.5] CodeGraph 图谱探索...")
        codegraph_context = _run_codegraph_exploration(target_path, quiet=args.quiet)
        if codegraph_context:
            if not args.quiet:
                print(f"  CodeGraph 探索完成 ({len(codegraph_context)} 字符)")
        else:
            if not args.quiet:
                print("  CodeGraph 探索跳过（无可用数据库或探索失败）")

    # Step 2: LLM business domain analysis
    if not args.quiet:
        print("[2/3] LLM 业务板块识别...")
    try:
        domain_result = analyze_business_domains(
            guiding_result, dir_summary, project_name,
            enable_dotenv=True,
            codegraph_context=codegraph_context,
        )
    except Exception as e:
        print(f"[2/3] 板块识别失败: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        domains_count = len(domain_result.get("domains", []))
        print(f"  识别到 {domains_count} 个业务板块")

    # Step 3: Generate progressive overview
    if not args.quiet:
        print("[3/3] 生成项目概览...")
    try:
        output_path = generate_progressive_overview(
            domain_result, output_dir,
            project_name=project_name,
            llm_enabled=True,
        )
    except Exception as e:
        print(f"[3/3] 文件生成失败: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"\n分析完成，已生成项目概览到 {output_dir}")
        print(f"  - project-overview.md")


if __name__ == "__main__":
    main()
