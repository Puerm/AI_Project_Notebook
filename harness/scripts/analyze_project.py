# analyze_project.py — 智能项目分析引擎 v0.4 渐进式披露

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
        description="智能项目分析引擎 v0.4 — 渐进式披露：引导文件 → LLM 业务板块识别 → 输出概览",
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
