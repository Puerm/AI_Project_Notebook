# help.py — 打印所有可用命令和一句话用途

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMMANDS = [
    ("python harness/scripts/help.py", "打印所有可用命令"),
    ("python harness/scripts/init_project.py <目标路径>", "初始化项目地图 — 复制 harness 骨架并扫描目标目录结构"),
    ("python harness/scripts/check_structure.py", "检查项目目录和关键文件完整性"),
    ("python harness/scripts/search_notes.py <关键词>", "在 project-map 和 feedback 中搜索关键词"),
    ("python harness/scripts/export_report.py", "导出完整项目理解报告"),
    ("python harness/scripts/analyze_project.py <目标路径>", "智能项目分析引擎 (v0.5.1 --digest 聚焦三维度分析（架构/用户故事/风险）)"),
    ("", ""),
    ("--- 手工操作 ---", ""),
    ("cat harness/project-map/overview.md", "查看项目总览"),
    ("编辑 harness/project-map/module-map.md", "填写模块笔记"),
]

if __name__ == "__main__":
    print("AI Project Notebook v0.5.1 — 可用命令")
    print("=" * 50)
    for cmd, desc in COMMANDS:
        if cmd.startswith("---"):
            print(f"\n{cmd}")
        elif cmd == "":
            print("")
        else:
            print(f"  {cmd}")
            print(f"    {desc}")
