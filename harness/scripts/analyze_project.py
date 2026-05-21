# analyze_project.py — 智能项目分析引擎，自动生成 project-map 文件

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HARNESS_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(HARNESS_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.analyzer.scanner import scan_directory, detect_source_roots
from app.analyzer.parser import parse_file
from app.analyzer.overview import analyze_overview
from app.analyzer.map_writer import generate_all


def main():
    parser = argparse.ArgumentParser(
        description="智能项目分析引擎 — 自动扫描项目目录、解析源码、生成 project-map 文件",
        epilog=(
            "环境变量 (LLM 模式需要):\n"
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
        "--llm", action="store_true", default=False,
        help="启用 LLM 语义增强"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", default=False,
        help="精简输出模式"
    )
    parser.add_argument(
        "--depth", type=int, default=3,
        help="目录树展开深度 (默认: 3)"
    )
    parser.add_argument(
        "--source-root", type=str, default=None,
        help="手动指定源码根目录 (单个)，覆盖自动检测"
    )

    args = parser.parse_args()

    target_path = os.path.abspath(args.target_path)
    output_dir = args.output_dir or os.path.join(target_path, "harness", "project-map")

    if not os.path.exists(target_path):
        print(f"错误: 目标路径不存在: {target_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(target_path):
        print(f"错误: 目标路径不是目录: {target_path}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"分析目标: {target_path}")
        print(f"输出目录: {output_dir}")

    # Step 1: Scan directory
    if not args.quiet:
        print("[1/4] 扫描目录结构...")
    try:
        scan_result = scan_directory(target_path)
    except Exception as e:
        print(f"[1/4] 扫描失败: {type(e).__name__}: {e}", file=sys.stderr)
        scan_result = {"root": target_path, "tree": None, "files": [], "stats": {"total_dirs": 0, "source_files": 0}}

    if not scan_result.get("files"):
        print("目标路径为空目录或无可分析的源码文件。")
        sys.exit(0)

    # Step 1.5: Detect source roots (multi)
    if args.source_root:
        source_roots = [args.source_root]
    else:
        source_roots = detect_source_roots(target_path, scan_result["files"])
    if not source_roots:
        source_roots = ["."]
    if not args.quiet:
        roots_display = ", ".join(source_roots)
        print(f"  源码根: {roots_display}")

    # Step 2: Parse source files
    if not args.quiet:
        print("[2/4] 解析源代码...")
    modules = []
    all_imports = {}
    lang_counts = {}

    for file_path in scan_result["files"]:
        abs_path = os.path.join(target_path, file_path)
        try:
            parsed = parse_file(abs_path)
        except Exception as e:
            print(f"  解析失败 {file_path}: {type(e).__name__}: {e}", file=sys.stderr)
            parsed = {"imports": [], "functions": [], "classes": [], "language": "unknown"}

        lang = parsed.get("language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

        modules.append({
            "file": file_path,
            "description": _module_snippet(parsed),
            "functions": parsed.get("functions", []),
            "classes": parsed.get("classes", []),
        })

        if parsed.get("imports"):
            all_imports[file_path] = parsed["imports"]

    if not args.quiet:
        lang_parts = [f"{lang}: {count}" for lang, count in sorted(lang_counts.items())]
        print(f"  发现 {len(scan_result['files'])} 个源码文件 ({', '.join(lang_parts)})")

    # Step 2.5: Group modules by each source root, merge with source_root field
    from app.analyzer.map_writer import _group_modules_by_directory, _compute_module_dependencies, _infer_module_description
    all_dir_modules = []
    for sr in source_roots:
        dir_modules_raw = _group_modules_by_directory(modules, sr)
        module_deps = _compute_module_dependencies(dir_modules_raw, all_imports, sr, target_path)
        for dir_name, file_mods in dir_modules_raw.items():
            all_funcs = []
            all_classes = []
            for fm in file_mods:
                all_funcs.extend(fm.get("functions", []))
                all_classes.extend(fm.get("classes", []))
            desc = _infer_module_description(dir_name,
                                             [fm["file"] for fm in file_mods],
                                             all_funcs, all_classes)
            deps = module_deps.get(dir_name, [])
            all_dir_modules.append({
                "dir": dir_name,
                "source_root": sr,
                "description": desc,
                "functions": all_funcs,
                "classes": all_classes,
                "dependencies": deps,
                "file_count": len(file_mods),
                "files": [fm["file"] for fm in file_mods],
            })

    if not args.quiet:
        print(f"  模块分组: {len(all_dir_modules)} 个模块 (跨 {len(source_roots)} 个源码根)")

    # Step 3: Analyze overview (rule-based with tech features gathering)
    if not args.quiet:
        print("[3/4] 分析项目概览...")
    try:
        overview_result = analyze_overview(target_path)
    except Exception as e:
        print(f"[3/4] 概览分析失败: {type(e).__name__}: {e}", file=sys.stderr)
        overview_result = {"name": os.path.basename(target_path), "description": "",
                           "tech_stack": [], "project_type": "通用项目", "entry_files": [],
                           "tech_features": {}}

    entry_functions = []
    llm_data_flow = None

    # Step 3.5: LLM enhancement or non-LLM fallback
    if args.llm:
        from app.analyzer.llm_assistant import (
            check_api_key_available, enhance_project_description,
            enhance_module_descriptions_batch, detect_entry_functions,
            enhance_data_flow_llm, enhance_tech_stack_llm,
        )
        key_ok, guidance = check_api_key_available()
        if not key_ok:
            print(guidance, file=sys.stderr)
            if not args.quiet:
                print("[LLM] API Key 不可用，跳过 LLM 增强")
        else:
            if not args.quiet:
                print("[LLM] LLM 语义增强...")
            try:
                # a. Enhance module descriptions per source root
                llm_descriptions = enhance_module_descriptions_batch(
                    all_dir_modules, overview_result["name"], source_roots[0])
                for i, desc in enumerate(llm_descriptions):
                    if i < len(all_dir_modules):
                        all_dir_modules[i]["description"] = desc
                if not args.quiet:
                    print(f"  模块描述增强: {len(all_dir_modules)} 个模块")

                # b. Detect entry functions
                entry_functions = detect_entry_functions(
                    target_path, scan_result["files"], source_roots)
                if not args.quiet:
                    print(f"  入口函数检测: {len(entry_functions)} 个")

                # c. Data flow inference
                if entry_functions:
                    # Build module_deps from all_dir_modules for LLM context
                    module_deps_for_llm = {}
                    for m in all_dir_modules:
                        deps = [d for d in m.get("dependencies", [])]
                        module_deps_for_llm[m.get("dir", "?")] = deps
                    llm_data_flow = enhance_data_flow_llm(
                        entry_functions, all_dir_modules,
                        module_deps_for_llm, overview_result["name"])
                    if llm_data_flow and not args.quiet:
                        print("  数据流推断: LLM 已生成")

                # d. Tech stack enhancement
                tech_features = overview_result.get("tech_features", {})
                llm_tech = enhance_tech_stack_llm(
                    tech_features,
                    overview_result.get("tech_stack", []),
                    overview_result.get("project_type", "通用项目"),
                )
                if llm_tech:
                    overview_result["tech_stack"] = llm_tech.get("tech_stack", overview_result.get("tech_stack", []))
                    overview_result["project_type"] = llm_tech.get("project_type", overview_result.get("project_type", "通用项目"))
                    if not args.quiet:
                        print(f"  技术栈推断: {llm_tech.get('tech_stack', [])} / {llm_tech.get('project_type', '')}")

                # e. Project description enhancement
                llm_desc = enhance_project_description(
                    overview_result["name"],
                    overview_result["tech_stack"],
                    overview_result["project_type"],
                )
                if llm_desc.get("enhanced"):
                    overview_result["description"] = llm_desc["description"]
                    if not args.quiet:
                        print(f"  LLM 描述: {llm_desc['description']}")

            except Exception as e:
                print(f"[LLM] LLM 增强失败，使用规则推断: {type(e).__name__}: {e}", file=sys.stderr)
    else:
        # No --llm: detect entry functions for data-flow fallback
        from app.analyzer.llm_assistant import detect_entry_functions
        try:
            entry_functions = detect_entry_functions(
                target_path, scan_result["files"], source_roots)
        except Exception as e:
            print(f"[入口检测] 失败: {type(e).__name__}: {e}", file=sys.stderr)
            entry_functions = []

    # Step 4: Generate project-map files
    if not args.quiet:
        print("[4/4] 生成 project-map 文件...")
    try:
        results = {
            "name": overview_result.get("name", os.path.basename(target_path)),
            "description": overview_result.get("description", ""),
            "tech_stack": overview_result.get("tech_stack", []),
            "project_type": overview_result.get("project_type", "通用项目"),
            "entry_files": overview_result.get("entry_files", []),
            "tree": scan_result.get("tree"),
            "modules": modules,
            "dir_modules": all_dir_modules,
            "imports": all_imports,
            "llm_data_flow": llm_data_flow,
        }
        generate_all(results, output_dir, max_depth=args.depth,
                     source_root=source_roots[0] if source_roots else None,
                     entry_functions=entry_functions,
                     source_roots=source_roots)
    except Exception as e:
        print(f"[4/4] 文件生成失败: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"\n分析完成，已生成 4 个 project-map 文件到 {output_dir}")
        print(f"  - overview.md")
        print(f"  - directory-map.md")
        print(f"  - module-map.md")
        print(f"  - data-flow.md")


def _module_snippet(parsed):
    """根据解析结果生成模块的一句话片段描述。"""
    funcs = parsed.get("functions", [])
    classes = parsed.get("classes", [])
    imports = parsed.get("imports", [])
    parts = []
    if funcs:
        parts.append(f"{len(funcs)} 个函数")
    if classes:
        parts.append(f"{len(classes)} 个类")
    if imports:
        parts.append(f"{len(imports)} 个导入")
    if not parts:
        return "无函数/类"
    return "，".join(parts)


if __name__ == "__main__":
    main()
