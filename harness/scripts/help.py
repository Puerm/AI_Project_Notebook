# help.py — 打印所有可用命令和一句话用途

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HARNESS_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(HARNESS_ROOT)

COMMANDS = [
    ("python harness/scripts/help.py", "打印所有可用命令"),
    ("python harness/scripts/init_project.py <目标路径>", "初始化项目地图 — 复制 harness 骨架并扫描目标目录结构"),
    ("python harness/scripts/search_notes.py <关键词>", "在 project-map 和 feedback 中搜索关键词"),
    ("python harness/scripts/export_report.py", "导出完整项目理解报告"),
    ("python harness/scripts/generate_rule_evolution.py", "扫描反馈信号，生成规则演化建议"),
    ("python harness/scripts/diagnose_and_fix.py", "自我升级引擎 — 扫描反馈信号的重复模式，自动诊断并应用修复"),
    ("", ""),
    ("--- 手工操作 ---", ""),
    ("cat harness/project-map/overview.md", "查看项目总览"),
    ("编辑 harness/project-map/module-map.md", "填写模块笔记"),
]


def _load_project_config():
    """从 project.yaml 加载项目名和版本，使用最小化 YAML 解析。"""
    config_path = os.path.join(PROJECT_ROOT, "harness", "config", "project.yaml")
    name = "Unknown Project"
    version = "v0.1"
    if not os.path.exists(config_path):
        return name, version
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return name, version
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("project_name:"):
            name = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        elif stripped.startswith("version:"):
            version = stripped.split(":", 1)[1].strip().strip('"').strip("'")
    return name, version


if __name__ == "__main__":
    project_name, version = _load_project_config()
    print(f"{project_name} {version} — 可用命令")
    print("=" * 50)
    for cmd, desc in COMMANDS:
        if cmd.startswith("---"):
            print(f"\n{cmd}")
        elif cmd == "":
            print("")
        else:
            print(f"  {cmd}")
            print(f"    {desc}")
