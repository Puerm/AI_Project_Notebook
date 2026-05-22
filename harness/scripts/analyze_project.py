# analyze_project.py — 智能项目分析引擎 v0.5 渐进式披露 + digest 全量三维分析

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HARNESS_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(HARNESS_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.analyzer.guiding_files import collect_guiding_files, generate_directory_summary
from app.analyzer.domain_analyzer import analyze_business_domains
from app.analyzer.map_writer import generate_progressive_overview
from app.analyzer.llm_assistant import check_api_key_available


def main():
    parser = argparse.ArgumentParser(
        description="智能项目分析引擎 v0.5 — 渐进式披露 + --digest 全量文件三维度分析",
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
        help="启用 codebase-digest 全量文件收集 + LLM 三维度分析 (架构/用户故事/风险)"
    )
    parser.add_argument(
        "--max-size", type=int, default=10240,
        help="digest 最大输出大小(KB), 默认 10240 (10 MB)"
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
        from app.analyzer.digest_collector import collect_digest
        from app.analyzer.dimension_analyzer import (
            analyze_architecture, analyze_user_stories, analyze_risk,
        )

        # Step D1: Digest collection
        if not args.quiet:
            print("[digest/1] 收集全量文件...")
        digest_result = collect_digest(target_path, max_size_kb=args.max_size)
        if digest_result["status"] == "ok":
            digest_text = digest_result["text"]
            if not args.quiet:
                print(f"  收集到 {digest_result['stats']['files']} 个文件, "
                      f"{len(digest_text)} 字符")
        elif digest_result["status"] == "cdigest_unavailable":
            print("警告: codebase-digest 未安装，回退到引导文件模式。", file=sys.stderr)
            print("  安装: pip install codebase-digest", file=sys.stderr)
            digest_text = None
        else:
            print(f"警告: digest 收集失败 ({digest_result.get('error', 'unknown')})，"
                  "回退到引导文件模式。", file=sys.stderr)
            digest_text = None

        # Step D2: Business domain analysis (always run, same as non-digest)
        if not args.quiet:
            print("[digest/2] 业务板块识别...")
        try:
            guiding_result = collect_guiding_files(target_path)
        except Exception as e:
            print(f"[digest/2] 引导文件收集失败: {type(e).__name__}: {e}", file=sys.stderr)
            guiding_result = {"found": [], "missing": []}

        try:
            dir_summary = generate_directory_summary(target_path)
        except Exception as e:
            print(f"[digest/2] 目录摘要生成失败: {type(e).__name__}: {e}", file=sys.stderr)
            dir_summary = f"项目根: {project_name}\n(目录摘要生成失败)"

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

        # Step D3: Generate project-overview.md
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

        # Step D4-D6: Three-dimension analysis (only if digest succeeded)
        if digest_text:
            # D4: Architecture analysis
            if not args.quiet:
                print("[digest/4] 架构分析...")
            arch_result = analyze_architecture(
                digest_text, project_name, target_path, enable_dotenv=True,
            )
            if not args.quiet:
                print(f"  {arch_result['status']}: {arch_result['file_path']}")
            arch_content = arch_result["content"]

            # D5: User stories analysis
            if not args.quiet:
                print("[digest/5] 用户故事重建...")
            stories_result = analyze_user_stories(
                digest_text, arch_content, project_name, target_path, enable_dotenv=True,
            )
            if not args.quiet:
                print(f"  {stories_result['status']}: {stories_result['file_path']}")
            stories_content = stories_result["content"]

            # D6: Risk analysis
            if not args.quiet:
                print("[digest/6] 风险分析...")
            risk_result = analyze_risk(
                digest_text, arch_content, stories_content,
                project_name, target_path, enable_dotenv=True,
            )
            if not args.quiet:
                print(f"  {risk_result['status']}: {risk_result['file_path']}")

        if not args.quiet:
            print(f"\n分析完成，输出到 {output_dir}")
            print(f"  - project-overview.md")
            if digest_text:
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

    # Step 2: LLM business domain analysis
    if not args.quiet:
        print("[2/3] LLM 业务板块识别...")
    try:
        domain_result = analyze_business_domains(
            guiding_result, dir_summary, project_name,
            enable_dotenv=True,
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
