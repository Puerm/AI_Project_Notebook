# scanner.py — 递归扫描目标项目目录树，识别目录用途，收集源码文件列表

import os

EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", "dist", "build", "harness",
}

STANDARD_DIR_LABELS = {
    "src": "源代码",
    "tests": "测试",
    "test": "测试",
    "docs": "文档",
    "doc": "文档",
    "lib": "库文件",
    "libs": "库文件",
    "bin": "可执行文件",
    "config": "配置文件",
    "configs": "配置文件",
    "scripts": "脚本",
    "data": "数据",
    "assets": "静态资源",
    "static": "静态资源",
    "templates": "模板",
    "examples": "示例",
    "tools": "工具",
    "utils": "工具",
    "plugins": "插件",
    "extensions": "扩展",
    "logs": "日志",
    "output": "输出",
    "public": "公开资源",
}

SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx"}

EXTENSION_CATEGORY_MAP = {
    ".py": "Python 源码",
    ".js": "JavaScript 源码",
    ".jsx": "JavaScript 源码",
    ".ts": "TypeScript 源码",
    ".tsx": "TypeScript 源码",
    ".html": "前端资源",
    ".css": "前端资源",
    ".scss": "前端资源",
    ".less": "前端资源",
    ".md": "文档",
    ".json": "配置/数据",
    ".yaml": "配置/数据",
    ".yml": "配置/数据",
    ".toml": "配置/数据",
    ".xml": "配置/数据",
}


def _infer_dir_label(dir_path, children_names):
    """非标准目录基于文件扩展名分布推断用途。"""
    ext_counts = {}
    for name in children_names:
        full = os.path.join(dir_path, name)
        if os.path.isfile(full):
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

    if not ext_counts:
        return None

    dominant_ext = max(ext_counts, key=ext_counts.get)
    total = sum(ext_counts.values())
    ratio = ext_counts[dominant_ext] / total

    if ratio >= 0.5:
        return EXTENSION_CATEGORY_MAP.get(dominant_ext)

    source_count = sum(c for e, c in ext_counts.items() if e in SOURCE_EXTENSIONS)
    if source_count / total >= 0.5:
        return "源码"

    return None


def scan_directory(target_path):
    """扫描目录结构，返回目录树和源码文件列表。"""
    target = os.path.abspath(target_path)
    if not os.path.isdir(target):
        return {"root": target, "tree": None, "files": [], "stats": {"error": "not_a_directory"}}

    files = []
    excluded = []

    def walk(path, depth=0):
        node = {
            "name": os.path.basename(path) or os.path.basename(target),
            "path": os.path.relpath(path, target) if path != target else ".",
            "type": "dir",
            "label": None,
            "children": [],
        }

        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            node["label"] = "(权限不足)"
            return node

        dir_entries = []
        file_entries = []

        for name in entries:
            full = os.path.join(path, name)
            if name.startswith("."):
                if name not in (".git", ".venv", ".idea", ".vscode"):
                    continue  # skip hidden items except known exclude dirs
                # known exclude dirs fall through to exclusion check below

            if name in EXCLUDE_DIRS:
                excluded.append(name)
                continue

            if os.path.isdir(full):
                dir_entries.append((name, full))
            else:
                file_entries.append(name)

                ext = os.path.splitext(name)[1].lower()
                if ext in SOURCE_EXTENSIONS:
                    files.append(os.path.relpath(full, target))

        # Build children for directories
        for name, full in dir_entries:
            child = walk(full, depth + 1)
            node["children"].append(child)

        # Infer label for this directory
        if node["name"] in STANDARD_DIR_LABELS:
            node["label"] = STANDARD_DIR_LABELS[node["name"]]
        else:
            node["label"] = _infer_dir_label(path, file_entries)

        # Add file nodes
        for fname in file_entries:
            node["children"].append({
                "name": fname,
                "path": os.path.relpath(os.path.join(path, fname), target),
                "type": "file",
            })

        return node

    tree = walk(target)

    stats = {
        "total_dirs": _count_dirs(tree),
        "total_files": len(files),
        "source_files": len(files),
        "excluded_dirs": excluded,
    }

    return {
        "root": target,
        "tree": tree,
        "files": files,
        "stats": stats,
    }


def _count_dirs(node):
    count = 1  # this node
    for child in node.get("children", []):
        if child.get("type") == "dir":
            count += _count_dirs(child)
    return count


def _common_ancestor(paths):
    """Find the deepest common ancestor directory of all given absolute paths."""
    if not paths:
        return None
    if len(paths) == 1:
        return paths[0]

    parts_list = []
    for p in paths:
        norm = os.path.normpath(p).replace("\\", "/")
        parts_list.append(norm.split("/"))

    min_len = min(len(parts) for parts in parts_list)
    common = []
    for i in range(min_len):
        part = parts_list[0][i]
        if all(parts[i] == part for parts in parts_list):
            common.append(part)
        else:
            break

    if not common:
        return None

    result = os.sep.join(common)
    drive = os.path.splitdrive(paths[0])[0]
    if drive and not result.startswith(drive):
        result = drive + os.sep + result

    return os.path.abspath(result)


def detect_source_root(target_path, files):
    """Auto-detect the source root directory from a list of source files.

    Returns the relative path from target_path to the source root, or None
    if the project root itself is the source root (no clear sub-root).
    (Compatibility wrapper, delegates to detect_source_roots.)
    """
    roots = detect_source_roots(target_path, files)
    return roots[0] if roots else None


def detect_source_roots(target_path, files):
    """Detect multiple source root directories from a list of source files.

    Returns a list of relative paths (from target_path) to source roots,
    sorted shallow-first with parent-child containment resolved (children removed).
    """
    if not files:
        return []

    target = os.path.abspath(target_path)

    # Collect directories containing project markers
    init_py_dirs = set()
    pkg_json_dirs = set()
    tsconfig_dirs = set()

    for root, _, dir_files in os.walk(target):
        for fname in dir_files:
            if fname == "__init__.py":
                init_py_dirs.add(os.path.abspath(root))
            elif fname == "package.json":
                pkg_json_dirs.add(os.path.abspath(root))
            elif fname == "tsconfig.json":
                tsconfig_dirs.add(os.path.abspath(root))

    # Check if project root itself has markers -> project root is sole source root
    if target in init_py_dirs or target in pkg_json_dirs:
        return ["."]

    candidates = set()

    for f in files:
        ext = os.path.splitext(f)[1].lower()
        abs_path = os.path.join(target, f)
        abs_dir = os.path.dirname(os.path.abspath(abs_path))

        if ext == ".py":
            # Walk up to find nearest __init__.py ancestor
            current = abs_dir
            while current and current != target:
                if current in init_py_dirs:
                    candidates.add(current)
                    break
                parent = os.path.dirname(current)
                if parent == current:
                    break
                current = parent
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            # Walk up to find nearest package.json or tsconfig.json ancestor
            current = abs_dir
            while current and current != target:
                if current in pkg_json_dirs or current in tsconfig_dirs:
                    candidates.add(current)
                    break
                parent = os.path.dirname(current)
                if parent == current:
                    break
                current = parent

    if not candidates:
        # Fallback: common ancestor of all source file dirs
        abs_dirs = []
        for f in files:
            abs_path = os.path.join(target, f)
            abs_dirs.append(os.path.dirname(os.path.abspath(abs_path)))
        common = _common_ancestor(abs_dirs)
        if common and common != target:
            candidates.add(common)

    # Convert to relative paths, sort shallow-first
    rel_candidates = sorted(
        [os.path.relpath(c, target).replace("\\", "/") for c in candidates],
        key=lambda p: len(p.split("/"))
    )

    # Filter: remove child paths whose parent is also in the list
    result = []
    for c in rel_candidates:
        c_parts = c.split("/")
        is_child = False
        for r in result:
            r_parts = r.split("/")
            if len(c_parts) > len(r_parts) and c_parts[:len(r_parts)] == r_parts:
                is_child = True
                break
        if not is_child:
            result.append(c)

    return result
