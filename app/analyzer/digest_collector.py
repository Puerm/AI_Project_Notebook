# digest_collector.py — codebase-digest 集成与全量文件收集，含噪声过滤和大小截断

import os
import sys
from io import StringIO


def is_cdigest_available():
    """检查 codebase_digest 包是否可用。"""
    try:
        import codebase_digest.app  # noqa: F401
        return True
    except ImportError:
        return False


def run_digest_collection(target_path, max_size_kb=10240):
    """调用 codebase_digest 收集全量文本文件，返回原始结果。"""
    try:
        from codebase_digest.app import analyze_directory, generate_content_string
    except ImportError:
        return {"files": [], "total_tokens": 0, "status": "cdigest_unavailable"}

    target_path = os.path.abspath(target_path)
    if not os.path.isdir(target_path):
        return {"files": [], "total_tokens": 0, "status": "error", "error": "目标路径不是目录"}

    ignore_patterns = [
        ".git", "__pycache__", "*.pyc", "*.pyo", "*.pyd",
        "node_modules", ".pytest_cache", "*.egg-info",
        ".venv", "venv", "env", ".env",
        "dist", "build", ".tox", ".mypy_cache", ".ruff_cache",
        "coverage", "htmlcov",
    ]

    # 风险对策：analyze_directory 使用 print() 输出调试信息，临时重定向 stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        result = analyze_directory(target_path, ignore_patterns=ignore_patterns, base_path=target_path)
        raw_files = generate_content_string(result)
        total_tokens = result.get("total_tokens", 0)
    except Exception as e:
        sys.stdout = old_stdout
        return {"files": [], "total_tokens": 0, "status": "error", "error": str(e)}
    finally:
        sys.stdout = old_stdout

    if not isinstance(raw_files, list):
        return {"files": [], "total_tokens": 0, "status": "error", "error": "generate_content_string 返回格式异常"}

    return {"files": raw_files, "total_tokens": total_tokens, "status": "ok"}


def preprocess_digest(raw_result, max_size_kb):
    """后处理：过滤噪声、折叠编译产物标注、截断超大内容。"""
    files = raw_result.get("files", [])
    max_size_bytes = max_size_kb * 1024

    # 过滤 [Non-text file] 内容
    cleaned = []
    for f in files:
        content = f.get("content", "")
        path = f.get("path", "")
        if content == "[Non-text file]":
            continue
        # 折叠编译产物目录标注
        if _is_build_artifact_dir(path):
            continue
        cleaned.append({"path": path, "content": content})

    # 按文件优先级排序：优先保留小文件、入口文件
    cleaned.sort(key=lambda f: _file_priority(f["path"], f["content"]))

    # 截断超大内容
    result = []
    total_bytes = 0
    for f in cleaned:
        content = f["content"]
        remaining = max_size_bytes - total_bytes
        if remaining <= 0:
            break
        if len(content.encode("utf-8")) > remaining:
            content = _truncate_text(content, remaining)
        result.append({"path": f["path"], "content": content})
        total_bytes += len(content.encode("utf-8"))

    return result


def _is_build_artifact_dir(path):
    """判断路径是否属于编译产物目录。"""
    skip_dirs = {"__pycache__", "node_modules", ".git", ".pytest_cache",
                 "dist", "build", ".venv", "venv", "env", ".tox",
                 ".mypy_cache", ".ruff_cache", "coverage", "htmlcov",
                 ".egg-info"}
    parts = path.replace("\\", "/").split("/")
    return bool(set(parts) & skip_dirs)


def _file_priority(path, content):
    """计算文件优先级（越小越优先保留）。"""
    path_lower = path.lower()
    # 入口文件最高优先级
    entry_names = {"main", "app", "index", "server", "cli", "setup", "manage"}
    name = os.path.splitext(os.path.basename(path))[0].lower()
    if name in entry_names:
        return 0
    # 小文件优先
    content_len = len(content.encode("utf-8"))
    if content_len < 5000:
        return 1
    if content_len < 20000:
        return 2
    return 3


def _truncate_text(text, max_bytes):
    """按字节截断文本，保留完整 UTF-8 字符。"""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes]
    # 确保不截断多字节字符
    return truncated.decode("utf-8", errors="ignore") + "\n... (truncated)"


def format_digest_for_llm(preprocessed, max_tokens=None):
    """将预处理后的文件列表格式化为 LLM 可消费的纯文本（保留向后兼容）。"""
    return format_files_for_llm(preprocessed, max_tokens=max_tokens)


def estimate_tokens(text: str) -> int:
    """估算文本 token 数量。使用 len(text.encode("utf-8")) / 4 上取整 + 10% 安全余量。"""
    bytes_count = len(text.encode("utf-8"))
    base = -(-bytes_count // 4)  # ceiling division
    margin = max(1, base // 10) if base > 0 else 0
    return base + margin


def format_files_for_llm(files: list, max_tokens: int | None = None) -> str:
    """将文件列表格式化为 LLM 可消费的纯文本，可指定 token 预算上限。"""
    if max_tokens is None:
        parts = []
        for f in files:
            path = f["path"]
            content = f["content"]
            parts.append(f"### File: {path}\n```\n{content}\n```\n")
        return "\n".join(parts)

    TRUNCATION_BUDGET_BYTES = 500  # 预留字节给截断标注
    result_parts = []
    truncated = []
    current_bytes = 0
    budget_bytes = max_tokens * 4  # token 预算转字节估算

    for f in files:
        entry = f"### File: {f['path']}\n```\n{f['content']}\n```\n"
        entry_bytes = len(entry.encode("utf-8"))
        if current_bytes + entry_bytes > budget_bytes - TRUNCATION_BUDGET_BYTES:
            truncated.append(f["path"])
        else:
            result_parts.append(entry)
            current_bytes += entry_bytes

    result = "\n".join(result_parts)
    if truncated:
        result += f"\n\n> [截断] 已省略 {len(truncated)} 个文件：\n> - " + "\n> - ".join(truncated)

    return result


def filter_for_architecture(preprocessed: list) -> list:
    """筛选架构分析相关文件（目录结构、配置、入口、大型模块），上限 100 文件。"""
    MAX_ARCHITECTURE_FILES = 100

    result = []
    for f in preprocessed:
        path = f.get("path", "")
        content = f.get("content", "")
        path_lower = path.lower()
        basename = os.path.basename(path).lower()

        # 目录结构文件
        if basename == "__init__.py":
            result.append(f)
            continue

        # 配置文件
        if any(path_lower.endswith(ext) for ext in [".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".conf"]):
            result.append(f)
            continue

        # 入口文件
        entry_names = {"main", "app", "index", "server", "cli", "setup", "manage", "run"}
        name_no_ext = os.path.splitext(basename)[0].lower()
        if name_no_ext in entry_names:
            result.append(f)
            continue

        # 大型模块文件 (>3000 字符，可能是核心模块)
        if len(content) > 3000 and path_lower.endswith(".py"):
            result.append(f)
            continue

    total = len(result)
    if total > MAX_ARCHITECTURE_FILES:
        print(f"[filter] architecture: {total} 文件超出上限 {MAX_ARCHITECTURE_FILES}，"
              f"保留前 {MAX_ARCHITECTURE_FILES} 个", file=sys.stderr)
        result = result[:MAX_ARCHITECTURE_FILES]

    return result


def filter_for_user_stories(preprocessed: list) -> list:
    """筛选用户故事分析相关文件（README、文档、路由、handler/controller、测试），上限 150 文件。"""
    MAX_USER_STORIES_FILES = 150

    result = []
    for f in preprocessed:
        path = f.get("path", "")
        content = f.get("content", "")
        path_lower = path.lower()
        basename = os.path.basename(path).lower()

        # README 文件
        if basename.startswith("readme"):
            result.append(f)
            continue

        # 文档目录
        if any(part in path.replace("\\", "/").split("/") for part in ["docs", "doc", "documentation"]):
            result.append(f)
            continue

        # 路由文件
        if any(kw in path_lower for kw in ["route", "router", "urls", "endpoint"]):
            result.append(f)
            continue

        # Handler / Controller / View 文件
        if any(kw in path_lower for kw in ["handler", "controller", "view", "serializer", "schema"]):
            result.append(f)
            continue

        # 测试文件
        if basename.startswith("test_") or basename.endswith("_test.py") or "/tests/" in path.replace("\\", "/"):
            result.append(f)
            continue

    total = len(result)
    if total > MAX_USER_STORIES_FILES:
        print(f"[filter] user_stories: {total} 文件超出上限 {MAX_USER_STORIES_FILES}，"
              f"保留前 {MAX_USER_STORIES_FILES} 个", file=sys.stderr)
        result = result[:MAX_USER_STORIES_FILES]

    return result


def filter_for_risk(preprocessed: list) -> list:
    """筛选风险分析相关文件（安全关键词、错误处理、配置、依赖、脚本），按优先级排序并去重，上限 200。"""
    MAX_RISK_FILES = 200
    risk_keywords = ["secret", "password", "token", "api_key", "apikey", "private_key",
                     "credential", "auth", "permission", "role", "admin"]

    scored = {}  # path -> (priority, file_dict)

    for f in preprocessed:
        path = f.get("path", "")
        content = f.get("content", "")
        path_lower = path.lower()
        basename = os.path.basename(path).lower()
        content_lower = content.lower()

        priority = None

        # 依赖文件 (priority 0 — highest)
        if basename in {"requirements.txt", "package.json", "pyproject.toml", "setup.py",
                        "setup.cfg", "pom.xml", "build.gradle", "cargo.toml", "go.mod"}:
            priority = 0

        # 配置文件 (priority 1)
        elif any(basename == p for p in [".env", ".env.example", "config.py", "settings.py", "config.json",
                                          "config.yaml", "config.yml", ".editorconfig"]):
            priority = 1

        # 脚本文件 (priority 2)
        elif path_lower.endswith((".sh", ".bat", ".ps1", ".psm1")):
            priority = 2

        # 错误处理相关文件 (priority 3)
        elif any(kw in path_lower for kw in ["error", "exception", "logging", "logger"]):
            priority = 3

        # 包含安全/风险关键词的内容 (priority 4)
        elif any(kw in content_lower for kw in risk_keywords):
            priority = 4

        if priority is None:
            continue

        # 去重：保留最高优先级（数值最小）
        if path not in scored or priority < scored[path][0]:
            scored[path] = (priority, f)

    # 按优先级排序，同优先级按路径字典序稳定排序
    result = [f for _, f in sorted(scored.values(), key=lambda x: (x[0], x[1].get("path", "")))]

    total = len(result)
    if total > MAX_RISK_FILES:
        print(f"[filter] risk: {total} 文件超出上限 {MAX_RISK_FILES}，"
              f"保留前 {MAX_RISK_FILES} 个", file=sys.stderr)
        result = result[:MAX_RISK_FILES]

    return result


def collect_digest(target_path, max_size_kb=10240):
    """编排函数：可用性检查 → 收集 → 预处理，返回文件列表（不再格式化全量 LLM 文本）。"""
    if not is_cdigest_available():
        return {
            "text": "",
            "files": [],
            "status": "cdigest_unavailable",
            "stats": {"files": 0, "total_tokens": 0},
        }

    raw = run_digest_collection(target_path, max_size_kb)
    if raw["status"] != "ok":
        return {
            "text": "",
            "files": [],
            "status": raw["status"],
            "stats": {"files": 0, "total_tokens": 0},
        }

    preprocessed = preprocess_digest(raw, max_size_kb)

    return {
        "text": "",
        "files": preprocessed,
        "status": "ok",
        "stats": {
            "files": len(preprocessed),
            "total_tokens": raw.get("total_tokens", 0),
        },
    }
