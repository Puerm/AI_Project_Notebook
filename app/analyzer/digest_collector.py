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


def format_digest_for_llm(preprocessed):
    """将预处理后的文件列表格式化为 LLM 可消费的纯文本。"""
    parts = []
    for f in preprocessed:
        path = f["path"]
        content = f["content"]
        parts.append(f"### File: {path}\n```\n{content}\n```\n")
    return "\n".join(parts)


def collect_digest(target_path, max_size_kb=10240):
    """编排函数：可用性检查 → 收集 → 预处理 → 格式化。"""
    if not is_cdigest_available():
        return {
            "text": "",
            "status": "cdigest_unavailable",
            "stats": {"files": 0, "total_tokens": 0},
        }

    raw = run_digest_collection(target_path, max_size_kb)
    if raw["status"] != "ok":
        return {
            "text": "",
            "status": raw["status"],
            "stats": {"files": 0, "total_tokens": 0},
        }

    preprocessed = preprocess_digest(raw, max_size_kb)
    text = format_digest_for_llm(preprocessed)

    return {
        "text": text,
        "status": "ok",
        "stats": {
            "files": len(preprocessed),
            "total_tokens": raw.get("total_tokens", 0),
        },
    }
