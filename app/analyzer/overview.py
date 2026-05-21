# overview.py — 项目概览检测：技术栈识别、入口文件检测、项目类型推断

import os

_EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", "dist", "build",
}

TECH_INDICATORS = {
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "Pipfile": "Python",
    "package.json": "Node.js",
    "tsconfig.json": "TypeScript",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
}

WEB_FRAMEWORKS_PYTHON = {"flask", "fastapi", "django", "starlette", "sanic", "tornado"}
WEB_FRAMEWORKS_NODE = {"express", "next", "koa", "nest", "fastify"}
CLI_FRAMEWORKS_PYTHON = {"click", "argparse", "typer", "fire"}
CLI_FRAMEWORKS_NODE = {"commander", "yargs", "oclif"}

ENTRY_NAMES = [
    "main.py", "app.py", "index.py", "run.py", "server.py",
    "index.js", "app.js", "server.js", "main.js",
]

ENTRY_SEARCH_DIRS = [".", "src", "src/app", "app"]


def _detect_tech_stack(root_path):
    """Deep-scan for tech indicator files up to 3 levels deep, respecting EXCLUDE_DIRS."""
    features = _gather_tech_features(root_path)
    tech = set()
    for indicator_file in features["indicator_files"]:
        fname = os.path.basename(indicator_file)
        label = TECH_INDICATORS.get(fname)
        if label:
            tech.add(label)
    return sorted(tech)


def _gather_tech_features(root_path):
    """Walk root_path up to 3 levels to collect tech-relevant features.

    Returns dict with:
      - indicator_files: list of relative paths to TECH_INDICATORS files found
      - python_deps: dict of deps extracted from pyproject.toml files
      - node_deps: dict of deps extracted from package.json files
      - dir_structure: list of top 2-level directory names under root
    """
    indicator_files = []
    python_deps = {}
    node_deps = {}
    dir_structure = []

    for current_root, dirs, files in os.walk(root_path):
        depth = os.path.relpath(current_root, root_path)
        depth_count = 0 if depth == "." else len(depth.replace("\\", "/").split("/"))

        if depth_count > 3:
            dirs.clear()
            continue

        # Exclude unwanted dirs
        dirs[:] = [d for d in dirs if d not in _EXCLUDE_DIRS]

        # Collect dir_structure for top 2 levels
        if depth_count <= 1:
            rel = os.path.relpath(current_root, root_path)
            if depth_count > 0:
                dir_structure.append(rel.replace("\\", "/"))

        for fname in files:
            if fname in TECH_INDICATORS:
                rel_path = os.path.relpath(
                    os.path.join(current_root, fname), root_path
                ).replace("\\", "/")
                indicator_files.append(rel_path)

            # Extract deps from package.json
            if fname == "package.json":
                abs_path = os.path.join(current_root, fname)
                node_deps.update(_read_package_json_from_path(abs_path))

            # Extract deps from pyproject.toml
            if fname == "pyproject.toml":
                abs_path = os.path.join(current_root, fname)
                python_deps.update(_read_pyproject_toml_from_path(abs_path))

    return {
        "indicator_files": sorted(indicator_files),
        "python_deps": python_deps,
        "node_deps": node_deps,
        "dir_structure": sorted(dir_structure),
    }


def _read_package_json_from_path(pkg_path):
    """Read package.json dependencies from a specific path."""
    import json
    try:
        with open(pkg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    deps = {}
    deps.update(data.get("dependencies", {}))
    deps.update(data.get("devDependencies", {}))
    return deps


def _read_pyproject_toml_from_path(pp_path):
    """Read pyproject.toml dependencies from a specific path."""
    import re
    deps = {}
    try:
        with open(pp_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return deps
    in_deps = False
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("[") and "dependencies" in line.lower():
            in_deps = True
            continue
        if line.startswith("[") and in_deps:
            in_deps = False
        if in_deps and "=" in line:
            name = line.split("=")[0].strip().strip('"').strip("'")
            deps[name.lower()] = line
    return deps


def _read_package_json(root_path):
    """读取 package.json 的 dependencies 字段。"""
    pkg_path = os.path.join(root_path, "package.json")
    if not os.path.isfile(pkg_path):
        return {}
    return _read_package_json_from_path(pkg_path)


def _read_pyproject_toml(root_path):
    """简化的 pyproject.toml 依赖读取。"""
    pp_path = os.path.join(root_path, "pyproject.toml")
    if not os.path.isfile(pp_path):
        return {}
    return _read_pyproject_toml_from_path(pp_path)


def _infer_project_type(root_path, tech_stack, features=None):
    """推断项目类型：Web 应用 / 库 / CLI / 通用项目。可传入预收集的 features。"""
    if features:
        node_deps = {k.lower() for k in features.get("node_deps", {})}
        python_deps = {k.lower() for k in features.get("python_deps", {})}

        if "Node.js" in tech_stack:
            if node_deps & WEB_FRAMEWORKS_NODE:
                return "Web 应用"
            if node_deps & CLI_FRAMEWORKS_NODE:
                return "CLI 工具"

        if "Python" in tech_stack:
            if python_deps & WEB_FRAMEWORKS_PYTHON:
                return "Web 应用"
            if python_deps & CLI_FRAMEWORKS_PYTHON:
                return "CLI 工具"
            if any(k in python_deps for k in ["setuptools", "poetry", "hatch", "flit"]):
                return "库"

        return "通用项目"

    # Fallback: use the old file-reading approach
    if "Node.js" in tech_stack:
        deps = _read_package_json(root_path)
        dep_names = {k.lower() for k in deps}
        if dep_names & WEB_FRAMEWORKS_NODE:
            return "Web 应用"
        if dep_names & CLI_FRAMEWORKS_NODE:
            return "CLI 工具"

    if "Python" in tech_stack:
        pp_path = os.path.join(root_path, "pyproject.toml")
        if os.path.isfile(pp_path):
            deps = _read_pyproject_toml(root_path)
            dep_names = {k.lower() for k in deps}
            if dep_names & WEB_FRAMEWORKS_PYTHON:
                return "Web 应用"
            if dep_names & CLI_FRAMEWORKS_PYTHON:
                return "CLI 工具"
            if any(k in dep_names for k in ["setuptools", "poetry", "hatch", "flit"]) and "scripts" not in deps:
                return "库"

        if os.path.isfile(os.path.join(root_path, "setup.py")):
            return "库"

    if any(fw in str(_read_package_json(root_path)).lower() for fw in WEB_FRAMEWORKS_NODE):
        return "Web 应用"

    return "通用项目"


def _detect_entry_files(root_path):
    """搜索常见入口文件。"""
    entries = []
    for search_dir in ENTRY_SEARCH_DIRS:
        dir_path = os.path.join(root_path, search_dir)
        if not os.path.isdir(dir_path):
            continue
        for name in ENTRY_NAMES:
            full = os.path.join(dir_path, name)
            if os.path.isfile(full):
                rel = os.path.relpath(full, root_path)
                entries.append(rel)
    return entries


def _generate_description(root_path, project_name, tech_stack, project_type):
    """生成一句话描述：README 第一行 + 技术栈 + 项目类型。"""
    readme_path = os.path.join(root_path, "README.md")
    title = None
    if os.path.isfile(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line.startswith("# "):
                    title = first_line[2:].strip()
        except OSError:
            pass

    if title:
        return title

    tech_str = "/".join(tech_stack) if tech_stack else "通用"
    return f"{project_name} — {tech_str} {project_type}"


def analyze_overview(target_path):
    """分析项目概览，返回统一结构。"""
    root = os.path.abspath(target_path)
    if not os.path.isdir(root):
        return {"name": os.path.basename(root), "description": "", "tech_stack": [],
                "project_type": "未知", "entry_files": [], "tech_features": {}}

    project_name = os.path.basename(root)
    tech_features = _gather_tech_features(root)
    tech_stack = _detect_tech_stack(root)
    project_type = _infer_project_type(root, tech_stack, features=tech_features)
    entry_files = _detect_entry_files(root)
    description = _generate_description(root, project_name, tech_stack, project_type)

    return {
        "name": project_name,
        "description": description,
        "tech_stack": tech_stack,
        "project_type": project_type,
        "entry_files": entry_files,
        "tech_features": tech_features,
    }
