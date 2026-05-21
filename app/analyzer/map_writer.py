# map_writer.py — 项目地图文件生成：overview / directory-map / module-map / data-flow

import os

MANUAL_MARKER = "<!-- MANUAL -->"


def _format_tree(node, prefix="", is_last=True, in_tree=True, max_depth=3, current_depth=0):
    """将目录树节点格式化为 ASCII 树形字符串列表。max_depth 控制展开深度。"""
    lines = []
    if in_tree:
        connector = "└── " if is_last else "├── "
        name = node.get("name", "?")
        suffix = "/" if node.get("type") == "dir" else ""
        label = node.get("label", "")
        label_str = f"  # {label}" if label else ""
        lines.append(prefix + connector + name + suffix + label_str)

        child_prefix = prefix + ("    " if is_last else "│   ")
    else:
        name = node.get("name", "?")
        lines.append(name + "/")
        child_prefix = prefix

    children = node.get("children", [])
    is_dir = node.get("type") == "dir"

    if is_dir and current_depth >= max_depth and children:
        # Folded summary line
        file_extensions = {}
        subdir_count = 0
        for child in children:
            if child.get("type") == "dir":
                subdir_count += 1
            else:
                ext = os.path.splitext(child.get("name", ""))[1].lower()
                if ext:
                    file_extensions[ext] = file_extensions.get(ext, 0) + 1

        non_dir_files = len(children) - subdir_count

        if subdir_count == 0 and len(file_extensions) == 1:
            ext = list(file_extensions.keys())[0]
            cat = "Python 源码" if ext == ".py" else (
                "JavaScript 源码" if ext in (".js", ".jsx") else
                "TypeScript 源码" if ext in (".ts", ".tsx") else
                f"{ext} 文件"
            )
            lines.append(child_prefix + f"... {cat}目录，{non_dir_files} 个文件")
        else:
            parts = []
            if subdir_count > 0:
                parts.append(f"{subdir_count} 个子目录")
            if non_dir_files > 0:
                parts.append(f"{non_dir_files} 个文件")
            lines.append(child_prefix + "... " + "，".join(parts) if parts else "... (空)")
    else:
        for i, child in enumerate(children):
            child_is_last = (i == len(children) - 1)
            lines.extend(_format_tree(child, child_prefix, child_is_last,
                                       max_depth=max_depth, current_depth=current_depth + 1))

    return lines


def _build_directory_tree_lines(tree, root_name, max_depth=3):
    """构建目录树文本。"""
    if tree is None:
        return [f"{root_name}/", "  (空目录)"]
    lines = [root_name + "/"]
    children = tree.get("children", [])
    for i, child in enumerate(children):
        is_last = (i == len(children) - 1)
        lines.extend(_format_tree(child, "", is_last, max_depth=max_depth))
    return lines


def _atomic_write(file_path, content):
    """原子写入：先写临时文件，再 rename 覆盖。"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, file_path)


def _read_existing(file_path):
    """读取已有文件内容。"""
    if not os.path.isfile(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _split_by_sections(content):
    """按 ## 标题将内容分割为段落字典。返回 {heading_text: section_body}。"""
    if not content:
        return {}
    lines = content.split("\n")
    sections = {}
    current_heading = None
    current_lines = []
    in_code_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            current_lines.append(line)
            continue
        if not in_code_fence and line.startswith("## ") and not line.startswith("### "):
            if current_heading is not None or current_lines:
                sections[current_heading or "__preamble__"] = "\n".join(current_lines)
            current_heading = stripped
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_heading is not None or current_lines:
        sections[current_heading or "__preamble__"] = "\n".join(current_lines)
    return sections


def _merge_sections(existing_content, new_content, section_headers=None):
    """按 ## 段落合并：保留 MANUAL 标记段落，更新非标记段落，追加新增段落。"""
    if not existing_content:
        return new_content

    existing_sections = _split_by_sections(existing_content)
    new_sections = _split_by_sections(new_content)

    result_parts = []
    used_headings = set()

    # Process new sections in order
    for heading, new_body in new_sections.items():
        if heading in existing_sections:
            existing_body = existing_sections[heading]
            used_headings.add(heading)
            if MANUAL_MARKER in existing_body:
                result_parts.append(existing_body)
            else:
                result_parts.append(new_body)
        else:
            result_parts.append(new_body)

    # Preserve old-only sections that have MANUAL marker
    for heading, existing_body in existing_sections.items():
        if heading not in used_headings and MANUAL_MARKER in existing_body:
            result_parts.append(existing_body)

    return "\n\n".join(result_parts)


def _parse_module_table_rows(existing_content):
    """从已有 module-map.md 中提取旧表格行。返回 {file_path: row_text}。"""
    rows_map = {}
    in_table = False
    after_header_sep = False
    for line in existing_content.split("\n"):
        stripped = line.strip()
        has_table_header = (stripped.startswith("|") and "模块描述" in stripped
                           and ("文件路径" in stripped or "模块路径" in stripped or "源码根" in stripped))
        if has_table_header:
            in_table = True
            continue
        if in_table and stripped.startswith("|") and stripped.count("-") >= 3:
            after_header_sep = True
            continue
        if after_header_sep and stripped.startswith("|"):
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) >= 2:
                fp = parts[1]
                if fp and fp not in ("文件路径", "模块路径", "源码根"):
                    rows_map[fp] = line
        elif after_header_sep and not stripped.startswith("|"):
            break
    return rows_map


def _line_has_manual(existing_content, target_line):
    """检查 target_line 及其前后两行是否包含 MANUAL_MARKER。"""
    all_lines = existing_content.split("\n")
    try:
        idx = all_lines.index(target_line)
    except ValueError:
        return False
    start = max(0, idx - 1)
    end = min(len(all_lines), idx + 3)
    for i in range(start, end):
        if MANUAL_MARKER in all_lines[i]:
            return True
    return False


def _group_modules_by_directory(modules, source_root):
    """Group file-level modules by their first-level directory under source_root."""
    grouped = {}
    for mod in modules:
        fp = mod.get("file", "")
        if not fp:
            continue
        parts = fp.replace("\\", "/").split("/")
        if source_root:
            # Find relative path from source_root
            src_parts = source_root.replace("\\", "/").split("/")
            if parts[:len(src_parts)] == src_parts:
                parts = parts[len(src_parts):]
        if parts:
            dir_name = parts[0] if len(parts) > 1 else "."
            if dir_name not in grouped:
                grouped[dir_name] = []
            grouped[dir_name].append(mod)
        else:
            if "." not in grouped:
                grouped["."] = []
            grouped["."].append(mod)
    return grouped


def _infer_module_description(dir_name, file_list, all_functions, all_classes):
    """Infer module description from directory name and content patterns."""
    func_names = [f["name"] if isinstance(f, dict) else f for f in all_functions]
    cls_names = [c["name"] if isinstance(c, dict) else c for c in all_classes]

    # Rule-based inference
    if dir_name == "adapters":
        has_adapter = any("adapter" in f.lower() for f in file_list)
        if has_adapter:
            return "适配器模块，集成外部数据源"
        return "适配器模块"
    if dir_name == "models":
        if cls_names:
            return "数据模型层"
    if dir_name == "services":
        return "业务服务层"
    if dir_name in ("controllers", "routes"):
        return "路由/控制器层"
    if dir_name in ("utils", "helpers"):
        return "工具函数模块"
    if dir_name == "config":
        return "配置管理模块"
    if dir_name == "tests":
        return "测试代码"
    if dir_name == "app":
        return "应用程序主模块"
    if dir_name == "src":
        return "源代码主目录"
    if dir_name == "lib":
        return "库文件模块"
    if dir_name == "scripts":
        return "脚本工具模块"
    if dir_name == "harness":
        return "项目工具链模块"
    if dir_name == "docs":
        return "文档目录"

    # Fallback
    return f"包含 {len(file_list)} 个文件的 {dir_name} 模块"


# Known stdlib module names for filtering
_STDLIB_NAMES = frozenset({
    "sys", "os", "json", "re", "ast", "subprocess", "pathlib", "typing",
    "collections", "itertools", "functools", "datetime", "logging", "unittest",
    "io", "hashlib", "uuid", "copy", "math", "random", "string", "textwrap",
    "argparse", "shutil", "tempfile", "urllib", "http", "socket", "ssl",
    "email", "csv", "xml", "html", "configparser", "dataclasses", "abc",
    "enum", "asyncio", "threading", "multiprocessing", "queue", "concurrent",
    "traceback", "warnings", "weakref", "inspect", "types", "importlib",
    "pkgutil", "atexit", "signal", "getpass", "getopt", "platform",
    "sysconfig", "builtins", "contextlib", "glob", "fnmatch", "fileinput",
    "codecs", "struct", "binascii", "zlib", "gzip", "bz2", "lzma",
    "zipfile", "tarfile", "sqlite3", "pickle", "shelve", "marshal",
    "readline", "rlcompleter", "code", "pdb", "profile", "timeit",
    "doctest", "pkg_resources", "setuptools", "distutils", "ensurepip",
    "venv", "zipapp", "zipimport", "runpy", "site", "dis", "opcode",
    "symtable", "token", "keyword", "tokenize", "tabnanny", "py_compile",
    "compileall", "modulefinder", "pydoc", "antigravity", "this",
})


def _compute_module_dependencies(modules_by_dir, all_imports, source_root, target_path):
    """Compute inter-module dependencies between directory groups."""
    # Build a mapping: file_path -> dir_name
    file_to_dir = {}
    for dir_name, file_mods in modules_by_dir.items():
        for fm in file_mods:
            file_to_dir[fm["file"]] = dir_name

    deps = {}
    for dir_name in modules_by_dir:
        deps[dir_name] = set()

    for file_path, imports in all_imports.items():
        from_dir = file_to_dir.get(file_path)
        if from_dir is None:
            continue
        for imp in imports:
            imp_name = imp.get("name", "")
            if not imp_name:
                continue
            # Skip stdlib
            top_level = imp_name.split(".")[0]
            if top_level in _STDLIB_NAMES:
                continue
            # Check if this import refers to a file in another dir group
            for target_file, target_dir in file_to_dir.items():
                if target_dir == from_dir:
                    continue
                # Match: imp_name could be like "utils.helper" and target_file "utils.py"
                target_base = os.path.splitext(os.path.basename(
                    target_file.replace("\\", "/")))[0]
                if imp_name == target_base or imp_name.startswith(target_base + "."):
                    deps[from_dir].add(target_dir)
                    break

    return {k: sorted(v) for k, v in deps.items() if v}


def _build_table_section(modules, existing_content):
    """构建 module-map 的表格段落。自动检测目录级/文件级模块格式。"""
    if not modules:
        return """## 自动分析模块

| 模块路径 | 模块描述 | 主要函数/类 | 模块依赖 |
| ---- | ---- | ---- | ---- |
| （无模块） | | | |"""

    is_dir_level = "dir" in modules[0] if isinstance(modules[0], dict) else False
    if is_dir_level:
        return _build_dir_table_section(modules, existing_content)
    else:
        return _build_file_table_section(modules, existing_content)


def _build_dir_table_section(dir_modules, existing_content):
    """Build table for directory-level modules (new format) with source root column."""
    new_rows = []
    for mod in dir_modules:
        dir_name = mod.get("dir", "?")
        src_root = mod.get("source_root", "-")
        desc = mod.get("description", "")
        funcs = mod.get("functions", [])
        classes = mod.get("classes", [])
        deps = mod.get("dependencies", [])
        func_names = [f["name"] if isinstance(f, dict) else f for f in funcs[:3]]
        cls_names = [c["name"] if isinstance(c, dict) else c for c in classes[:3]]
        combined = ", ".join(func_names + cls_names) if (func_names or cls_names) else "-"
        deps_str = ", ".join(deps) if deps else "-"
        new_rows.append((dir_name, f"| {src_root} | {dir_name} | {desc} | {combined} | {deps_str} |"))

    if existing_content:
        old_rows_map = _parse_module_table_rows(existing_content)
        manual_keys = {k for k, row in old_rows_map.items() if _line_has_manual(existing_content, row)}
        merged_rows = []
        seen = set()
        for key, row_text in new_rows:
            seen.add(key)
            if key in manual_keys and key in old_rows_map:
                merged_rows.append(old_rows_map[key])
            else:
                merged_rows.append(row_text)
        for key, row_text in old_rows_map.items():
            if key not in seen and key in manual_keys:
                merged_rows.append(row_text)
        table = "\n".join(merged_rows) if merged_rows else "| - | （无模块） | | | |"
    else:
        table = "\n".join(row for _, row in new_rows)

    return f"""## 自动分析模块

| 源码根 | 模块路径 | 模块描述 | 主要函数/类 | 模块依赖 |
| ---- | ---- | ---- | ---- | ---- |
{table}"""


def _build_file_table_section(modules, existing_content):
    """Build table for file-level modules (legacy format)."""
    new_rows = []
    for mod in modules:
        fp = mod.get("file", "")
        desc = mod.get("description", "")
        functions = mod.get("functions", [])
        classes = mod.get("classes", [])
        func_names = ", ".join(f["name"] for f in functions[:5]) if functions else "-"
        cls_names = ", ".join(c["name"] for c in classes[:5]) if classes else "-"
        new_rows.append((fp, f"| {fp} | {desc} | {func_names} | {cls_names} |"))

    if existing_content:
        old_rows_map = _parse_module_table_rows(existing_content)
        manual_files = {fp for fp, row in old_rows_map.items() if _line_has_manual(existing_content, row)}
        merged_rows = []
        seen_files = set()
        for fp, row_text in new_rows:
            seen_files.add(fp)
            if fp in manual_files and fp in old_rows_map:
                merged_rows.append(old_rows_map[fp])
            else:
                merged_rows.append(row_text)
        for fp, row_text in old_rows_map.items():
            if fp not in seen_files and fp in manual_files:
                merged_rows.append(row_text)
        table = "\n".join(merged_rows) if merged_rows else "| （无模块） | | | |"
    else:
        table = "\n".join(row for _, row in new_rows) if new_rows else "| （无模块） | | | |"

    return f"""## 自动分析模块

| 文件路径 | 模块描述 | 主要函数 | 主要类 |
| ---- | ---- | ---- | ---- |
{table}"""


def generate_overview(results, project_name, output_dir):
    """生成 overview.md。"""
    tech_stack = results.get("tech_stack", [])
    project_type = results.get("project_type", "通用项目")
    entry_files = results.get("entry_files", [])
    description = results.get("description", "")

    tech_str = ", ".join(tech_stack) if tech_stack else "通用"
    entries_str = ", ".join(entry_files) if entry_files else "未检测到"

    content = f"""# Project Overview

## 项目名称

{project_name}

## 一句话描述

{description}

## 技术栈

{tech_str}

## 项目类型

{project_type}

## 入口文件

{entries_str}

## 当前版本

v0.1 — 由 analyze_project 自动分析生成
"""

    file_path = os.path.join(output_dir, "overview.md")
    existing = _read_existing(file_path)
    final = _merge_sections(existing, content, [])
    _atomic_write(file_path, final)


def generate_directory_map(tree, project_name, output_dir, max_depth=3):
    """生成 directory-map.md。"""
    tree_lines = _build_directory_tree_lines(tree, project_name, max_depth=max_depth)
    tree_text = "\n".join("    " + line for line in tree_lines)

    content = f"""# Directory Map

项目完整目录结构及每个目录的职责说明。

```
{tree_text}
```

## 变更规则

- 新增/删除/重命名目录后必须更新本文档
- 修改目录职责说明后检查 `overview.md` 是否需要同步
"""

    file_path = os.path.join(output_dir, "directory-map.md")
    existing = _read_existing(file_path)
    final = _merge_sections(existing, content, [])
    _atomic_write(file_path, final)


def generate_module_map(dir_modules, output_dir):
    """生成 module-map.md，接收目录级模块列表，支持增量更新。"""
    file_path = os.path.join(output_dir, "module-map.md")
    existing = _read_existing(file_path)

    table_section = _build_table_section(dir_modules, existing)

    new_content = f"""# Module Map

各模块的职责、接口和依赖关系。

{table_section}

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

    final = _merge_sections(existing, new_content) if existing else new_content
    _atomic_write(file_path, final)


def _generate_data_flow_template(source_root, entry_functions=None):
    """Generate data-flow content: LLM-inferred or entry function fallback list."""
    if entry_functions:
        rows = []
        for ef in entry_functions:
            fname = ef.get("name", "?")
            ffile = ef.get("file", "?")
            fmodule = ef.get("module_dir", "?")
            rows.append(f"| {fname} | {ffile} | {fmodule} |")
        table = "\n".join(rows)
        return f"""# Data Flow

项目中数据的产生、存储、流转路径。

> LLM 未启用，已自动检测到 {len(entry_functions)} 个入口函数。
> 请使用 `--llm` 参数重新运行分析以启用 LLM 数据流推断。

## 检测到的入口函数

| 函数名 | 文件 | 所属模块 |
| ---- | ---- | ---- |
{table}

以上入口函数是数据流的起点，可据此手动追踪数据流转路径。

## 变更规则

- 增加新的数据文件格式后必须更新本文档
- 增加新的数据流路径后必须更新上图
"""
    else:
        source_note = f" 源码根: `{source_root}`" if source_root else ""
        return f"""# Data Flow

项目中数据的产生、存储、流转路径。

> 未检测到入口函数，无法自动推断数据流路径。
> 请使用 `--llm` 参数重新运行分析以启用 LLM 语义推断。
> 或在此手动填写数据流分析内容。

## 待分析的数据流{source_note}

- 入口函数 -> 处理节点 -> 数据变换路径
- （使用 --llm 自动生成，或手动填写）

## 变更规则

- 增加新的数据文件格式后必须更新本文档
- 增加新的数据流路径后必须更新上图
"""


def generate_data_flow(all_imports, output_dir, entry_functions=None, source_root=None):
    """生成 data-flow.md。有 LLM 数据时写入推断内容，否则生成引导模板。"""
    content = _generate_data_flow_template(source_root, entry_functions=entry_functions)

    file_path = os.path.join(output_dir, "data-flow.md")
    existing = _read_existing(file_path)
    final = _merge_sections(existing, content, [])
    _atomic_write(file_path, final)


def generate_all(results, output_dir, max_depth=3, source_root=None, entry_functions=None, source_roots=None):
    """生成全部 4 个 project-map 文件。"""
    project_name = results.get("name", "unknown")
    tree = results.get("tree")
    modules = results.get("dir_modules", results.get("modules", []))
    all_imports = results.get("imports", {})
    llm_data_flow = results.get("llm_data_flow", None)

    overview_data = {
        "tech_stack": results.get("tech_stack", []),
        "project_type": results.get("project_type", "通用项目"),
        "entry_files": results.get("entry_files", []),
        "description": results.get("description", ""),
    }

    # If llm_data_flow is present, write it directly and skip entry_functions fallback
    if llm_data_flow:
        df_content = llm_data_flow
        df_path = os.path.join(output_dir, "data-flow.md")
        existing = _read_existing(df_path)
        final = _merge_sections(existing, df_content, [])
        _atomic_write(df_path, final)
    else:
        generate_data_flow(all_imports, output_dir,
                           entry_functions=entry_functions, source_root=source_root)

    generate_overview(overview_data, project_name, output_dir)
    generate_directory_map(tree, project_name, output_dir, max_depth=max_depth)
    generate_module_map(modules, output_dir)
