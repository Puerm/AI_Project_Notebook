# guiding_files.py — 引导文件收集与目录摘要，为 LLM 业务板块识别提供上下文

import os
import re
from app.analyzer.scanner import EXCLUDE_DIRS

GUIDING_FILE_PATTERNS = {
    # 文档类
    "README.md": "项目自述文档",
    "README.rst": "项目自述文档",
    "README": "项目自述文档",
    "CHANGELOG.md": "变更日志",
    "CONTRIBUTING.md": "贡献指南",
    # 依赖清单
    "package.json": "Node.js 依赖与脚本",
    "pyproject.toml": "Python 项目配置",
    "setup.py": "Python 打包配置",
    "requirements.txt": "Python 依赖清单",
    "Pipfile": "Python Pipenv 依赖",
    "Gemfile": "Ruby 依赖",
    "Cargo.toml": "Rust 依赖与配置",
    "go.mod": "Go 模块定义",
    "pom.xml": "Maven 项目配置",
    "build.gradle": "Gradle 构建配置",
    # 容器/部署
    "Dockerfile": "Docker 镜像定义",
    "docker-compose.yml": "Docker 编排配置",
    "docker-compose.yaml": "Docker 编排配置",
    # CI/CD
    ".gitlab-ci.yml": "GitLab CI 流水线",
    "Jenkinsfile": "Jenkins 流水线",
    # 构建/任务
    "Makefile": "Make 构建任务",
    "GNUmakefile": "GNU Make 构建任务",
    # 框架配置
    "tsconfig.json": "TypeScript 编译配置",
    "next.config.js": "Next.js 配置 (JS)",
    "next.config.ts": "Next.js 配置 (TS)",
    "next.config.mjs": "Next.js 配置 (MJS)",
    "nest-cli.json": "NestJS CLI 配置",
    "vite.config.js": "Vite 配置 (JS)",
    "vite.config.ts": "Vite 配置 (TS)",
    "webpack.config.js": "Webpack 配置",
    "angular.json": "Angular 配置",
    # 环境提示
    ".env.example": "环境变量示例",
    ".env.template": "环境变量模板",
    ".gitignore": "Git 忽略规则",
    ".dockerignore": "Docker 忽略规则",
}

# CI/CD glob patterns under .github/workflows/
_CI_GLOB = ".github/workflows"
_CI_EXTS = (".yml", ".yaml")

# UUID-like directory pattern (hex segments with hyphens)
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

# Build output directories to fold
_BUILD_OUTPUT_DIRS = {"dist", "build", ".next", "__pycache__", "node_modules",
                      "target", ".turbo", "out", "coverage"}


def collect_guiding_files(target_path):
    """扫描目标项目，收集关键引导文件的内容。

    Returns:
        dict: {"found": [{file_path, content, label}], "missing": [label]}
    """
    target = os.path.abspath(target_path)
    found = []
    found_labels = set()

    # Collect all file paths in root and one level subdirectories
    all_candidates = {}
    for root, dirs, files in os.walk(target):
        depth = root.replace(target, "").count(os.sep)
        if depth > 1:
            dirs.clear()
            continue

        dirs[:] = [d for d in sorted(dirs) if d not in EXCLUDE_DIRS
                   and not d.startswith(".")]
        # Also skip hidden dirs (except .github for CI)
        dirs[:] = [d for d in dirs if not d.startswith(".") or d == ".github"]

        for fname in files:
            rel_path = os.path.relpath(os.path.join(root, fname), target)
            basename = os.path.basename(fname)
            all_candidates.setdefault(basename, []).append((rel_path, root, depth))

    # Second pass: collect CI files under .github/workflows/
    ci_dir = os.path.join(target, ".github", "workflows")
    if os.path.isdir(ci_dir):
        try:
            for fname in sorted(os.listdir(ci_dir)):
                if fname.lower().endswith(_CI_EXTS):
                    rel_path = os.path.relpath(os.path.join(ci_dir, fname), target)
                    all_candidates.setdefault(fname, []).append((rel_path, ci_dir, 2))
        except OSError:
            pass

    # Collect files matching GUIDING_FILE_PATTERNS
    def _read_file(rel_path, max_lines=100):
        abs_path = os.path.join(target, rel_path)
        try:
            if not os.path.isfile(abs_path):
                return None
            size = os.path.getsize(abs_path)
            if size == 0:
                return "(空文件)"
            if size > 50 * 1024:
                return f"(文件过大: {size // 1024} KB)"
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"... (截断，共 {size // 1024} KB)")
                        break
                    # Skip very long lines
                    if len(line) > 500:
                        lines.append(line[:500] + "... (行过长已截断)")
                    else:
                        lines.append(line.rstrip("\n").rstrip("\r"))
                return "\n".join(lines)
        except OSError:
            return None

    for basename, label in GUIDING_FILE_PATTERNS.items():
        candidates = all_candidates.get(basename, [])
        if not candidates:
            continue

        # Prefer root-level candidates
        candidates.sort(key=lambda c: c[2])
        # Take up to 3 per basename
        for rel_path, _, _ in candidates[:3]:
            if "README" in basename.upper() and basename.endswith(".md"):
                content = _read_file(rel_path, max_lines=80)
            elif basename in ("Dockerfile",):
                content = _read_file(rel_path, max_lines=100)
            elif basename.startswith("."):
                content = _read_file(rel_path, max_lines=50)
            else:
                content = _read_file(rel_path, max_lines=100)

            if content is not None:
                found.append({
                    "file_path": rel_path,
                    "content": content,
                    "label": label,
                })
                found_labels.add(label)

    # Limit to 15, prioritize root-level
    found.sort(key=lambda f: f["file_path"].count(os.sep))
    if len(found) > 15:
        found = found[:15]

    missing = [lbl for pat, lbl in GUIDING_FILE_PATTERNS.items()
               if lbl not in found_labels]

    return {"found": found, "missing": missing}


def generate_directory_summary(target_path):
    """生成目录结构摘要（≤30 行纯文本）。

    Returns:
        str: 目录摘要文本
    """
    target = os.path.abspath(target_path)
    lines = [f"项目根: {os.path.basename(target)}"]
    uuid_count = 0
    build_dirs_folded = set()

    def _walk(root, prefix, depth):
        nonlocal uuid_count
        if depth > 2:
            return

        try:
            entries = sorted(os.listdir(root))
        except PermissionError:
            lines.append(f"{prefix}(权限不足)")
            return

        dirs = []
        for name in entries:
            full = os.path.join(root, name)
            if not os.path.isdir(full):
                continue
            if name in EXCLUDE_DIRS:
                continue
            if name.startswith("."):
                continue
            dirs.append(name)

        for i, name in enumerate(dirs):
            is_last = (i == len(dirs) - 1)
            connector = "└── " if is_last else "├── "
            next_prefix = "    " if is_last else "│   "

            # Check UUID pattern
            if _UUID_RE.match(name):
                uuid_count += 1
                continue

            # Check build output dir
            if name in _BUILD_OUTPUT_DIRS:
                build_dirs_folded.add(name)
                continue

            if depth < 2:
                lines.append(prefix + connector + name + "/")
                full_path = os.path.join(root, name)
                _walk(full_path, prefix + next_prefix, depth + 1)

    _walk(target, "", 0)

    # Add fold summaries
    if uuid_count > 0:
        lines.append(f"  ... UUID 目录 ({uuid_count} 个)")
    for bd in sorted(build_dirs_folded):
        lines.append(f"  ... {bd}/ (编译产物目录，已折叠)")

    # Truncate to 30 lines
    if len(lines) > 30:
        lines = lines[:29]
        lines.append(f"  ... (共 {uuid_count + len(build_dirs_folded)} 个目录被折叠)")

    return "\n".join(lines)
