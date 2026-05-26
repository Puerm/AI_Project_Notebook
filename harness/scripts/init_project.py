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
| `python harness/scripts/search_notes.py <关键词>` | 搜索笔记 | `harness/scripts/search_notes.py` |
| `python harness/scripts/init_project.py <目标路径>` | 初始化新项目地图 | `harness/scripts/init_project.py` |
| `python harness/scripts/export_report.py` | 导出项目理解报告 | `harness/scripts/export_report.py` |

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
- **验证**: 运行项目配置的结构验证命令通过

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


# ============================================================
# LLM 项目检测 (IMP-7)
# ============================================================

CONFIG_PATTERNS = {
    "python": [
        ("pyproject.toml", "pip"),
        ("setup.py", "pip"),
        ("setup.cfg", "pip"),
        ("requirements.txt", "pip"),
        ("Pipfile", "pipenv"),
        ("poetry.lock", "poetry"),
    ],
    "javascript": [
        ("package.json", "npm"),
        ("yarn.lock", "yarn"),
        ("pnpm-lock.yaml", "pnpm"),
        ("bun.lockb", "bun"),
    ],
    "typescript": [
        ("package.json", "npm"),
        ("yarn.lock", "yarn"),
        ("tsconfig.json", "npm"),
    ],
    "go": [
        ("go.mod", "go"),
    ],
    "rust": [
        ("Cargo.toml", "cargo"),
    ],
}

TEST_PATTERNS = {
    "python": {
        "pytest": ("import pytest", "pytest", "python -m pytest tests/ -v"),
        "unittest": ("import unittest", "unittest", "python -m unittest discover tests/"),
    },
    "javascript": {
        "jest": (r'jest|"jest"', "jest", "npx jest"),
        "vitest": ("vitest", "vitest", "npx vitest"),
        "mocha": ("mocha", "mocha", "npx mocha"),
    },
    "typescript": {
        "jest": (r'jest|"jest"', "jest", "npx jest"),
        "vitest": ("vitest", "vitest", "npx vitest"),
        "mocha": ("mocha", "mocha", "npx mocha"),
    },
    "go": {
        "go_test": ("testing", "go test", "go test ./..."),
    },
    "rust": {
        "cargo_test": ("#[test]", "cargo test", "cargo test"),
    },
}

DEFAULT_TEST_COMMANDS = {
    "python": "python -m pytest tests/ -v",
    "javascript": "npm test",
    "typescript": "npm test",
    "go": "go test ./...",
    "rust": "cargo test",
}

DEFAULT_PACKAGE_MANAGERS = {
    "python": "pip",
    "javascript": "npm",
    "typescript": "npm",
    "go": "go",
    "rust": "cargo",
}

VALIDATION_COMMANDS = {
    "python": "python harness/scripts/check_structure.py",
    "javascript": "node harness/scripts/check_structure.js",
    "typescript": "node harness/scripts/check_structure.js",
    "go": "go run harness/scripts/check_structure.go",
    "rust": "cargo run --manifest-path harness/scripts/check_structure.toml",
}


def _detect_project_features(target_path):
    """LLM 降级: 纯静态检测项目语言、包管理器、测试框架。

    扫描目标目录的文件后缀统计 -> 语言列表，
    检测已知配置文件推断包管理器和测试框架。
    返回 dict 含 languages / test_framework / test_command / package_manager。
    """
    ext_count = {}
    config_found = {}
    test_framework = None
    test_command = None
    package_manager = None
    languages = []

    # 扫描文件后缀和配置文件
    for root, _dirs, files in os.walk(target_path):
        # 跳过隐藏目录和常见排除目录
        dirs_to_skip = set()
        for d in _dirs:
            if d.startswith(".") or d in EXCLUDE_DIRS:
                dirs_to_skip.add(d)
        _dirs[:] = [d for d in _dirs if d not in dirs_to_skip]

        for fname in files:
            # 统计后缀
            _, ext = os.path.splitext(fname)
            if ext:
                ext = ext.lower()
                ext_count[ext] = ext_count.get(ext, 0) + 1

            # 检测配置文件
            for lang, patterns in CONFIG_PATTERNS.items():
                for cfg_file, pkg_mgr in patterns:
                    if fname == cfg_file:
                        config_found[lang] = pkg_mgr

        # 限制扫描深度
        if root.count(os.sep) - target_path.count(os.sep) > 3:
            _dirs[:] = []

    # 确定主语言
    ext_to_lang = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
    }

    lang_count = {}
    for ext, count in ext_count.items():
        lang = ext_to_lang.get(ext)
        if lang:
            lang_count[lang] = lang_count.get(lang, 0) + count

    # 按文件数量排序，取前 2 个
    sorted_langs = sorted(lang_count.items(), key=lambda x: x[1], reverse=True)
    languages = [lang for lang, _ in sorted_langs[:2]]

    if not languages:
        languages = ["unknown"]

    primary_lang = languages[0]

    # 包管理器
    if primary_lang in config_found:
        package_manager = config_found[primary_lang]
    else:
        package_manager = DEFAULT_PACKAGE_MANAGERS.get(primary_lang, "unknown")

    # 测试框架
    if primary_lang in TEST_PATTERNS:
        # 简单检测: 默认使用第一个
        test_info = list(TEST_PATTERNS[primary_lang].values())[0]
        test_framework = test_info[1]
        test_command = test_info[2]
    else:
        test_framework = "unknown"
        test_command = DEFAULT_TEST_COMMANDS.get(primary_lang, "echo 'no tests configured'")

    return {
        "languages": languages,
        "test_framework": test_framework,
        "test_command": test_command,
        "package_manager": package_manager,
    }


def _generate_project_yaml(features, project_name):
    """根据检测到的项目特征生成 project.yaml 内容。"""
    version = "0.1"
    yaml_lines = [
        "# project.yaml — 项目模板变量定义，所有占位符 {{...}} 的单一数据源",
        "# 由 init_project.py 自动生成",
        "",
        f"project_name: {project_name}",
        f'version: "{version}"',
        "languages:",
    ]
    for lang in features["languages"]:
        yaml_lines.append(f"  - {lang}")
    yaml_lines.append(f"test_framework: {features['test_framework']}")
    yaml_lines.append(f"test_command: {features['test_command']}")
    yaml_lines.append(f"package_manager: {features['package_manager']}")
    # 验证命令: 优先使用语言特定的默认值
    primary_lang = features["languages"][0] if features["languages"] else "unknown"
    validation_command = VALIDATION_COMMANDS.get(primary_lang, "")
    yaml_lines.append(f"validation_command: {validation_command}")
    return "\n".join(yaml_lines) + "\n"


def _fill_template_placeholders(content, config):
    """替换模板中的 {{...}} 占位符。"""
    replacements = {
        "{{project_name}}": config.get("project_name", "Unknown Project"),
        "{{version}}": config.get("version", "0.1"),
        "{{test_command}}": config.get("test_command", ""),
        "{{test_framework}}": config.get("test_framework", "unknown"),
        "{{package_manager}}": config.get("package_manager", "unknown"),
        "{{validation_command}}": config.get("validation_command", ""),
    }
    result = content
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def _fill_templates(target_harness, config):
    """遍历 harness 下所有 .md/.yaml/.txt 文件，填充占位符。"""
    for root, _dirs, files in os.walk(target_harness):
        for fname in files:
            if not (fname.endswith(".md") or fname.endswith(".yaml") or fname.endswith(".txt")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    original = f.read()
            except OSError:
                continue

            if "{{" not in original:
                continue

            filled = _fill_template_placeholders(original, config)
            if filled != original:
                tmp_path = fpath + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(filled)
                os.replace(tmp_path, fpath)


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

    # LLM 检测项目特征（降级为纯静态检测）
    print("[1/4] 检测项目特征...")
    features = _detect_project_features(target)
    print(f"  语言: {', '.join(features['languages'])}")
    print(f"  包管理器: {features['package_manager']}")
    print(f"  测试框架: {features['test_framework']}")
    print(f"  测试命令: {features['test_command']}")

    # 复制 harness 骨架（IMP-1~4 部署逻辑保持不变）
    print("[2/4] 复制 harness 骨架...")
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

    # 生成 project.yaml
    print("[3/4] 生成 project.yaml...")
    yaml_content = _generate_project_yaml(features, project_name)
    config_dir = os.path.join(target_harness, "config")
    os.makedirs(config_dir, exist_ok=True)
    yaml_path = os.path.join(config_dir, "project.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    print(f"已生成 harness/config/project.yaml")

    # 填充模板占位符
    config_for_fill = {
        "project_name": project_name,
        "version": "0.1",
        "test_command": features["test_command"],
        "test_framework": features["test_framework"],
        "package_manager": features["package_manager"],
        "validation_command": VALIDATION_COMMANDS.get(features["languages"][0] if features["languages"] else "unknown", ""),
    }
    _fill_templates(target_harness, config_for_fill)
    _fill_templates(target_claude, config_for_fill)

    # 生成 directory-map.md
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

    # 模板填充完成后删除 target 中的 project.yaml (不暴露 Notebook 自身的值)
    # project.yaml 是在 copy 之后生成的，所以已经是目标项目的值

    print(f"\n[4/4] 初始化完成。运行以下命令开始:")
    print(f"  cd {target}")
    print(f"  python harness/scripts/help.py")

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python harness/scripts/init_project.py <目标路径>", file=sys.stderr)
        sys.exit(1)
    sys.exit(init_project(sys.argv[1]))
