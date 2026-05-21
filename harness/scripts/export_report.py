# export_report.py — 合并 project-map 下所有 Markdown 文件输出格式化报告

import os
import sys
from datetime import datetime

# Windows 控制台默认用 gbk，中文 Markdown 是 UTF-8，不重配置会乱码或崩溃
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PROJECT_MAP_DIR = os.path.join(PROJECT_ROOT, "harness", "project-map")
PROJECT_NAME = os.path.basename(PROJECT_ROOT)


def export_report():
    if not os.path.isdir(PROJECT_MAP_DIR):
        print(f"错误: project-map 目录不存在: {PROJECT_MAP_DIR}", file=sys.stderr)
        return 1

    md_files = sorted(
        [f for f in os.listdir(PROJECT_MAP_DIR) if f.endswith(".md")]
    )
    if not md_files:
        print("错误: project-map 目录下没有 .md 文件", file=sys.stderr)
        return 1

    print("=" * 50)
    print(f"项目理解报告: {PROJECT_NAME}")
    print(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    for i, filename in enumerate(md_files, 1):
        filepath = os.path.join(PROJECT_MAP_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"\n[{i}] {filename}")
        print("-" * 40)
        print(content.rstrip())

    return 0


if __name__ == "__main__":
    sys.exit(export_report())
