# init_project.py — 在新项目中初始化 harness 骨架并扫描目录结构

import os
import sys
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HARNESS_ROOT = os.path.dirname(SCRIPT_DIR)  # harness/
PROJECT_ROOT = os.path.dirname(HARNESS_ROOT)  # AI_Project_Notebook/

EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", "dist", "build", "harness", ".claude",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def scan_tree(path, depth=0, max_depth=3):
    """扫描目录结构，返回树形节点列表。max_depth 从 1 开始计数。"""
    if depth >= max_depth:
        return []
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return [{"name": "(权限不足)", "type": "error", "children": []}]

    nodes = []
    for name in entries:
        full = os.path.join(path, name)
        if name in EXCLUDE_DIRS:
            continue
        if name.startswith("."):
            continue
        if os.path.isdir(full):
            children = scan_tree(full, depth + 1, max_depth)
            nodes.append({"name": name, "type": "dir", "children": children})
        else:
            nodes.append({"name": name, "type": "file", "children": []})
    return nodes


def format_tree(nodes, prefix=""):
    """将树节点格式化为目录树字符串列表。"""
    lines = []
    for i, node in enumerate(nodes):
        is_last = (i == len(nodes) - 1)
        connector = "└── " if is_last else "├── "
        name = node["name"] + ("/" if node["type"] == "dir" else "")
        lines.append(prefix + connector + name)

        if node["children"]:
            child_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(format_tree(node["children"], child_prefix))
    return lines


def generate_directory_map(target_path, project_name):
    """生成 directory-map.md 内容。"""
    nodes = scan_tree(target_path, depth=0, max_depth=3)
    tree_lines = format_tree(nodes)

    lines = ["# Directory Map", "", "项目完整目录结构及每个目录的职责说明。", "", "```text",
             f"{project_name}/"]
    lines.extend(tree_lines)
    lines.append("```")
    lines.append("")
    lines.append("## 变更规则")
    lines.append("")
    lines.append("- 新增/删除/重命名目录后必须更新本文档")
    lines.append("- 修改目录职责说明后检查 `overview.md` 是否需要同步")
    return "\n".join(lines)


def make_template_overview(project_name):
    return f"""# Project Overview

## 项目名称

{project_name}

## 一句话描述

（待填写）

## 当前版本

v0.1

## 核心概念

- **项目地图 (project-map/)** — 项目的结构化知识库，包含目录、模块、命令、数据流、变更记录
- **规则 (rules/)** — 可执行的开发约束
- **反馈 (feedback/)** — 从错误和改进中沉淀的经验
- **脚本 (scripts/)** — 自动化检查与维护工具

## 当前状态

| 指标 | 状态 |
| ---- | ---- |
| 版本 | v0.1 |
| 应用代码 | 待分析 |
| 测试 | 待确认 |
| 最近变更 | 项目地图初始化 |
"""


def make_template_module_map():
    return """# Module Map

各模块的职责、接口和依赖关系。

## 当前模块

| 模块 | 文件 | 职责 | 依赖 |
| ---- | ---- | ---- | ---- |
| （待填写） | | | |

## 登记规则

新模块登记时必须填写：
1. 模块名称（与文件名对应）
2. 文件路径
3. 一句话职责描述
4. 依赖列表（依赖哪些模块/库）

## 变更规则

- 新增模块后在此文件中新增一行
- 修改模块职责后更新对应描述
- 模块被移除后标记为 `~~已移除~~` 并在 `change-map.md` 中记录
"""


def make_template_command_map():
    return """# Command Map

所有可执行命令索引。

## CLI 命令

| 命令 | 用途 | 来源文件 |
| ---- | ---- | ---- |
| `python harness/scripts/help.py` | 打印所有可用命令 | `harness/scripts/help.py` |
| `python harness/scripts/check_structure.py` | 检查项目结构完整性 | `harness/scripts/check_structure.py` |
| `python harness/scripts/search_notes.py <关键词>` | 搜索笔记 | `harness/scripts/search_notes.py` |
| `python harness/scripts/export_report.py` | 导出项目理解报告 | `harness/scripts/export_report.py` |
| `python harness/scripts/init_project.py <目标路径>` | 初始化新项目地图 | `harness/scripts/init_project.py` |

## 变更规则

- 新增命令后必须在本文档中登记
- 修改命令参数后必须更新对应行
"""


def make_template_data_flow():
    return """# Data Flow

项目中数据的产生、存储、流转路径。

## 数据流图

（待填写）

## 数据文件格式

| 目录 | 文件格式 | 编码 |
| ---- | ---- | ---- |
| （待填写） | | |

## 变更规则

- 增加新的数据文件格式后必须更新本文档
- 增加新的数据流路径后必须更新上图
"""


def make_template_change_map():
    return """# Change Map

记录每次变更的摘要，保持项目演化历史可追溯。

## 变更记录

### 项目地图初始化

- **类型**: 初始化
- **范围**: 全项目
- **摘要**: 通过 `init_project.py` 初始化 harness 项目地图骨架
- **验证**: `python harness/scripts/check_structure.py` 通过

---

## 记录规则

每次变更必须记录：
1. 日期和变更名称
2. 变更类型（初始化/新功能/修复/重构/规则更新）
3. 影响范围（哪些文件/模块）
4. 摘要
5. 验证命令及其结果
"""


TEMPLATES = {
    "overview.md": lambda name: make_template_overview(name),
    "module-map.md": lambda _: make_template_module_map(),
    "command-map.md": lambda _: make_template_command_map(),
    "data-flow.md": lambda _: make_template_data_flow(),
    "change-map.md": lambda _: make_template_change_map(),
}


def init_project(target_path):
    target = os.path.abspath(target_path)
    if not os.path.isdir(target):
        print(f"错误: 目标路径不存在或不是目录: {target}", file=sys.stderr)
        return 1

    target_harness = os.path.join(target, "harness")
    if os.path.exists(target_harness):
        print(f"错误: 目标路径下已存在 harness 目录: {target_harness}", file=sys.stderr)
        return 1

    project_name = os.path.basename(target)

    shutil.copytree(HARNESS_ROOT, target_harness)
    print(f"已复制 harness 骨架到: {target_harness}")

    # IMP-1: 删除目标项目中的 init_project.py
    init_py = os.path.join(target_harness, "scripts", "init_project.py")
    if os.path.exists(init_py):
        os.remove(init_py)
        print(f"已删除目标项目中的 init_project.py")

    # IMP-2: 部署 .claude/agents/ 到目标项目
    claude_src = os.path.join(PROJECT_ROOT, ".claude")
    target_claude = os.path.join(target, ".claude")
    os.makedirs(target_claude, exist_ok=True)
    shutil.copytree(os.path.join(claude_src, "agents"), os.path.join(target_claude, "agents"), dirs_exist_ok=True)
    print(f"已部署 .claude/agents/ 到目标项目")

    # IMP-3: 部署 .claude/commands/pm/ 和 .claude/commands/workflow/ (排除 opsx/)
    for subdir in ["pm", "workflow"]:
        shutil.copytree(
            os.path.join(claude_src, "commands", subdir),
            os.path.join(target_claude, "commands", subdir),
            dirs_exist_ok=True
        )
    print(f"已部署 .claude/commands/ (pm + workflow) 到目标项目")

    # IMP-4: 创建空的 .claude/skills/ 目录
    os.makedirs(os.path.join(target_claude, "skills"), exist_ok=True)
    print(f"已创建空的 .claude/skills/ 目录")

    dir_map_content = generate_directory_map(target, project_name)
    dir_map_path = os.path.join(target_harness, "project-map", "directory-map.md")
    with open(dir_map_path, "w", encoding="utf-8") as f:
        f.write(dir_map_content)
    print(f"已生成 directory-map.md（{project_name} 目录结构）")

    project_map_dir = os.path.join(target_harness, "project-map")
    for filename, template_fn in TEMPLATES.items():
        if filename == "directory-map.md":
            continue  # 上面已生成
        filepath = os.path.join(project_map_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(template_fn(project_name))
    print(f"已初始化 project-map 模板文件")

    print(f"\n初始化完成。运行以下命令开始:")
    print(f"  cd {target}")
    print(f"  python harness/scripts/help.py")

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python harness/scripts/init_project.py <目标路径>", file=sys.stderr)
        sys.exit(1)
    sys.exit(init_project(sys.argv[1]))
