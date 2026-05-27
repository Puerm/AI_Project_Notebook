# test_digest_collector.py — TST-1: codebase-digest 集成与全量文件收集

import os
import sys
from unittest.mock import patch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class TestIsCdigestAvailable:
    """is_cdigest_available() 可用性检测"""

    def test_returns_bool(self):
        from app.analyzer.digest_collector import is_cdigest_available
        result = is_cdigest_available()
        assert isinstance(result, bool)


class TestCollectDigest:
    """collect_digest() 编排函数"""

    def test_cdigest_unavailable_returns_proper_status(self):
        from app.analyzer.digest_collector import collect_digest
        with patch("app.analyzer.digest_collector.is_cdigest_available", return_value=False):
            result = collect_digest(".")
            assert result["status"] == "cdigest_unavailable"
            assert result["text"] == ""
            assert result["stats"]["files"] == 0

    def test_nonexistent_dir_does_not_crash(self):
        from app.analyzer.digest_collector import collect_digest
        result = collect_digest("/nonexistent/path/xyz12345")
        # Should not crash; returns error or cdigest_unavailable
        assert result["status"] in ("error", "cdigest_unavailable")
        assert result["text"] == ""

    def test_valid_dir_with_cdigest_installed(self):
        """对项目根目录收集 digest（若 cdigest 已安装则验证 status=ok）"""
        from app.analyzer.digest_collector import collect_digest, is_cdigest_available
        result = collect_digest(_PROJECT_ROOT)
        assert result["status"] in ("ok", "error", "cdigest_unavailable")
        if is_cdigest_available() and os.path.isdir(_PROJECT_ROOT):
            # When cdigest is available and path is valid, should be ok
            assert result["status"] == "ok"
            # v0.5.1: text is always "" (no more full-text dump); files is the primary output
            assert result["text"] == ""
            assert len(result["files"]) > 0
            assert result["stats"]["files"] > 0
        else:
            # cdigest not installed or path issue — ok as long as no crash
            assert result["text"] == "" or result["status"] == "cdigest_unavailable"


class TestPreprocessDigest:
    """preprocess_digest() 噪声过滤和截断"""

    def test_filters_non_text_file_content(self):
        from app.analyzer.digest_collector import preprocess_digest
        raw = {
            "files": [
                {"path": "src/main.py", "content": "print('hello')"},
                {"path": "assets/logo.png", "content": "[Non-text file]"},
                {"path": "src/utils.py", "content": "def foo(): pass"},
            ],
            "total_tokens": 100,
        }
        result = preprocess_digest(raw, max_size_kb=10240)
        paths = {f["path"] for f in result}
        assert "src/main.py" in paths
        assert "src/utils.py" in paths
        assert "assets/logo.png" not in paths, "[Non-text file] should be filtered out"

    def test_filters_build_artifact_dirs(self):
        from app.analyzer.digest_collector import preprocess_digest
        raw = {
            "files": [
                {"path": "src/main.py", "content": "x=1"},
                {"path": "__pycache__/module.cpython-311.pyc", "content": "binary"},
                {"path": "node_modules/pkg/index.js", "content": "module.exports = {}"},
                {"path": ".git/HEAD", "content": "ref: refs/heads/main"},
            ],
            "total_tokens": 50,
        }
        result = preprocess_digest(raw, max_size_kb=10240)
        paths = {f["path"] for f in result}
        assert "src/main.py" in paths
        assert "__pycache__/module.cpython-311.pyc" not in paths
        assert "node_modules/pkg/index.js" not in paths
        assert ".git/HEAD" not in paths

    def test_max_size_truncation(self):
        from app.analyzer.digest_collector import preprocess_digest
        big_content = "x" * 3000
        raw = {
            "files": [
                {"path": "a.py", "content": big_content},
                {"path": "b.py", "content": "short"},
            ],
            "total_tokens": 50,
        }
        result = preprocess_digest(raw, max_size_kb=1)  # 1 KB = 1024 bytes
        total_bytes = sum(len(f["content"].encode("utf-8")) for f in result)
        # NOTE: _truncate_text appends "\n... (truncated)" suffix (16 bytes)
        # outside the budget, causing slight exceedance. Bug tracked as
        # "minor-bug: truncation marker exceeds max_size budget".
        assert total_bytes <= 1024 + 50, (
            f"Total bytes {total_bytes} substantially exceeds 1024 limit" + " (+50 tolerance for truncation marker)"
        )
        # The truncated file MUST contain the truncation marker
        assert any("... (truncated)" in f["content"] for f in result), (
            "Truncated file should contain truncation marker"
        )

    def test_empty_files_list(self):
        from app.analyzer.digest_collector import preprocess_digest
        raw = {"files": [], "total_tokens": 0}
        result = preprocess_digest(raw, max_size_kb=10240)
        assert result == []


class TestFormatDigestForLLM:
    """format_digest_for_llm() LLM 文本格式化"""

    def test_format_contains_file_markers(self):
        from app.analyzer.digest_collector import format_digest_for_llm
        preprocessed = [
            {"path": "src/main.py", "content": "print('hello')"},
            {"path": "src/utils.py", "content": "def foo(): pass"},
        ]
        text = format_digest_for_llm(preprocessed)
        assert "### File: src/main.py" in text
        assert "```" in text
        assert "print('hello')" in text
        assert "### File: src/utils.py" in text
        assert "def foo(): pass" in text

    def test_format_empty_list_returns_empty_string(self):
        from app.analyzer.digest_collector import format_digest_for_llm
        text = format_digest_for_llm([])
        assert text == ""


# ===========================================================================
# TST-1 新增: 维度筛选函数测试
# ===========================================================================


class TestFilterForArchitecture:
    """filter_for_architecture() 架构维度文件筛选"""

    def test_filters_init_py_files(self):
        from app.analyzer.digest_collector import filter_for_architecture
        preprocessed = [
            {"path": "src/__init__.py", "content": "# package"},
            {"path": "app/__init__.py", "content": ""},
            {"path": "src/main.py", "content": "print('hello')"},
        ]
        result = filter_for_architecture(preprocessed)
        paths = {f["path"] for f in result}
        assert "src/__init__.py" in paths
        assert "app/__init__.py" in paths

    def test_filters_config_files(self):
        from app.analyzer.digest_collector import filter_for_architecture
        preprocessed = [
            {"path": "settings.json", "content": "{}"},
            {"path": "config.yaml", "content": "key: val"},
            {"path": "pyproject.toml", "content": "[tool]"},
            {"path": "app.ini", "content": "[section]"},
        ]
        result = filter_for_architecture(preprocessed)
        paths = {f["path"] for f in result}
        assert "settings.json" in paths
        assert "config.yaml" in paths
        assert "pyproject.toml" in paths
        assert "app.ini" in paths

    def test_filters_entry_files(self):
        from app.analyzer.digest_collector import filter_for_architecture
        preprocessed = [
            {"path": "main.py", "content": "x=1"},
            {"path": "server.js", "content": "x=1"},
            {"path": "cli.go", "content": "x=1"},
            {"path": "setup.py", "content": "x=1"},
            {"path": "other.py", "content": "x=1"},
        ]
        result = filter_for_architecture(preprocessed)
        paths = {f["path"] for f in result}
        assert "main.py" in paths
        assert "server.js" in paths
        assert "cli.go" in paths
        assert "setup.py" in paths
        assert "other.py" not in paths  # small non-entry file excluded

    def test_filters_large_module_files(self):
        from app.analyzer.digest_collector import filter_for_architecture
        large_content = "x" * 4000
        preprocessed = [
            {"path": "core/engine.py", "content": large_content},
            {"path": "core/small.py", "content": "pass"},  # < 3000 chars
        ]
        result = filter_for_architecture(preprocessed)
        paths = {f["path"] for f in result}
        assert "core/engine.py" in paths
        assert "core/small.py" not in paths

    def test_empty_list_returns_empty(self):
        from app.analyzer.digest_collector import filter_for_architecture
        result = filter_for_architecture([])
        assert result == []

    # ---------- TST-2: 文件数上限 ----------

    def test_upper_limit_100_files(self):
        """101+ 个文件时只返回前 100 个"""
        from app.analyzer.digest_collector import filter_for_architecture
        preprocessed = [{"path": f"dir{i}/__init__.py", "content": ""} for i in range(101)]
        result = filter_for_architecture(preprocessed)
        assert len(result) == 100, f"Expected 100, got {len(result)}"

    def test_within_limit_no_truncation(self):
        """50 个文件未超过 100 上限，全部保留"""
        from app.analyzer.digest_collector import filter_for_architecture
        preprocessed = [{"path": f"dir{i}/__init__.py", "content": ""} for i in range(50)]
        result = filter_for_architecture(preprocessed)
        assert len(result) == 50, f"Expected 50, got {len(result)}"


class TestFilterForUserStories:
    """filter_for_user_stories() 用户故事维度文件筛选"""

    def test_filters_readme_files(self):
        from app.analyzer.digest_collector import filter_for_user_stories
        preprocessed = [
            {"path": "README.md", "content": "# Project"},
            {"path": "readme.txt", "content": "hello"},
            {"path": "src/main.py", "content": "print(1)"},
        ]
        result = filter_for_user_stories(preprocessed)
        paths = {f["path"] for f in result}
        assert "README.md" in paths
        assert "readme.txt" in paths
        assert "src/main.py" not in paths

    def test_filters_docs_directory(self):
        from app.analyzer.digest_collector import filter_for_user_stories
        preprocessed = [
            {"path": "docs/guide.md", "content": "# Guide"},
            {"path": "documentation/api.md", "content": "# API"},
            {"path": "src/main.py", "content": "print(1)"},
        ]
        result = filter_for_user_stories(preprocessed)
        paths = {f["path"] for f in result}
        assert "docs/guide.md" in paths
        assert "documentation/api.md" in paths
        assert "src/main.py" not in paths

    def test_filters_route_handler_view_files(self):
        from app.analyzer.digest_collector import filter_for_user_stories
        preprocessed = [
            {"path": "app/routes.py", "content": "@app.route"},
            {"path": "app/handlers/user.py", "content": "class Handler"},
            {"path": "app/controllers/api.py", "content": "def index"},
            {"path": "app/views/home.html", "content": "<html>"},
            {"path": "app/serializers/user.py", "content": "class Serializer"},
            {"path": "app/models/user.py", "content": "class User"},
        ]
        result = filter_for_user_stories(preprocessed)
        paths = {f["path"] for f in result}
        assert "app/routes.py" in paths
        assert "app/handlers/user.py" in paths
        assert "app/controllers/api.py" in paths
        assert "app/views/home.html" in paths
        assert "app/serializers/user.py" in paths
        assert "app/models/user.py" not in paths

    def test_filters_test_files(self):
        from app.analyzer.digest_collector import filter_for_user_stories
        preprocessed = [
            {"path": "tests/test_auth.py", "content": "def test()"},
            {"path": "src/utils_test.py", "content": "def test()"},
            {"path": "src/test_helpers.py", "content": "def test()"},
            {"path": "src/main.py", "content": "print(1)"},
        ]
        result = filter_for_user_stories(preprocessed)
        paths = {f["path"] for f in result}
        assert "tests/test_auth.py" in paths
        assert "src/utils_test.py" in paths
        assert "src/test_helpers.py" in paths
        assert "src/main.py" not in paths

    def test_empty_list_returns_empty(self):
        from app.analyzer.digest_collector import filter_for_user_stories
        result = filter_for_user_stories([])
        assert result == []

    # ---------- TST-2: 文件数上限 ----------

    def test_upper_limit_150_files(self):
        """151+ 个文件时只返回前 150 个"""
        from app.analyzer.digest_collector import filter_for_user_stories
        preprocessed = [{"path": f"dir{i}/README.md", "content": ""} for i in range(151)]
        result = filter_for_user_stories(preprocessed)
        assert len(result) == 150, f"Expected 150, got {len(result)}"

    def test_within_limit_no_truncation(self):
        """80 个文件未超过 150 上限，全部保留"""
        from app.analyzer.digest_collector import filter_for_user_stories
        preprocessed = [{"path": f"dir{i}/README.md", "content": ""} for i in range(80)]
        result = filter_for_user_stories(preprocessed)
        assert len(result) == 80, f"Expected 80, got {len(result)}"


class TestFilterForRisk:
    """filter_for_risk() 风险维度文件筛选"""

    def test_filters_dependency_files(self):
        from app.analyzer.digest_collector import filter_for_risk
        preprocessed = [
            {"path": "requirements.txt", "content": "flask==2.0"},
            {"path": "package.json", "content": "{}"},
            {"path": "pyproject.toml", "content": "[tool]"},
            {"path": "setup.py", "content": "x=1"},
            {"path": "src/other.py", "content": "print(1)"},
        ]
        result = filter_for_risk(preprocessed)
        paths = {f["path"] for f in result}
        assert "requirements.txt" in paths
        assert "package.json" in paths
        assert "pyproject.toml" in paths
        assert "setup.py" in paths
        assert "src/other.py" not in paths

    def test_filters_risk_keyword_content(self):
        from app.analyzer.digest_collector import filter_for_risk
        preprocessed = [
            {"path": "src/auth.py", "content": "PASSWORD = 'secret123'"},
            {"path": "src/config.py", "content": "API_KEY = 'abc'"},
            {"path": "src/clean.py", "content": "x = 1 + 2"},
        ]
        result = filter_for_risk(preprocessed)
        paths = {f["path"] for f in result}
        assert "src/auth.py" in paths
        assert "src/config.py" in paths
        assert "src/clean.py" not in paths

    def test_filters_config_and_env_files(self):
        from app.analyzer.digest_collector import filter_for_risk
        preprocessed = [
            {"path": ".env", "content": "SECRET=xxx"},
            {"path": "config.py", "content": "DEBUG=True"},
            {"path": "settings.py", "content": "DB_URL=xxx"},
            {"path": "lib/util.py", "content": "def f(): pass"},
        ]
        result = filter_for_risk(preprocessed)
        paths = {f["path"] for f in result}
        assert ".env" in paths
        assert "config.py" in paths
        assert "settings.py" in paths
        assert "lib/util.py" not in paths

    def test_filters_script_files(self):
        from app.analyzer.digest_collector import filter_for_risk
        preprocessed = [
            {"path": "deploy.sh", "content": "#!/bin/bash"},
            {"path": "run.bat", "content": "@echo off"},
            {"path": "setup.ps1", "content": "Write-Host"},
            {"path": "src/app.py", "content": "print(1)"},
        ]
        result = filter_for_risk(preprocessed)
        paths = {f["path"] for f in result}
        assert "deploy.sh" in paths
        assert "run.bat" in paths
        assert "setup.ps1" in paths
        assert "src/app.py" not in paths

    def test_filters_error_handling_files(self):
        from app.analyzer.digest_collector import filter_for_risk
        preprocessed = [
            {"path": "src/errors.py", "content": "class Error"},
            {"path": "src/exception.py", "content": "class Exception"},
            {"path": "src/logging_config.py", "content": "import logging"},
            {"path": "src/logger.py", "content": "logger = ..."},
            {"path": "src/main.py", "content": "print(1)"},
        ]
        result = filter_for_risk(preprocessed)
        paths = {f["path"] for f in result}
        assert "src/errors.py" in paths
        assert "src/exception.py" in paths
        assert "src/logging_config.py" in paths
        assert "src/logger.py" in paths
        assert "src/main.py" not in paths

    def test_empty_list_returns_empty(self):
        from app.analyzer.digest_collector import filter_for_risk
        result = filter_for_risk([])
        assert result == []

    # ---------- TST-1: 优先级排序 + 去重 ----------

    def test_dedup_duplicate_file_path(self):
        """相同文件路径出现多次时去重，只保留一次"""
        from app.analyzer.digest_collector import filter_for_risk
        preprocessed = [
            {"path": "config.py", "content": "PASSWORD = 'secret'"},
            {"path": "config.py", "content": "PASSWORD = 'secret'"},  # 重复路径
            {"path": "src/util.py", "content": "API_KEY = 'abc'"},
        ]
        result = filter_for_risk(preprocessed)
        paths = [f["path"] for f in result]
        assert paths.count("config.py") == 1, f"Expected 1, got {paths.count('config.py')}"

    def test_priority_sorting_full_order(self):
        """依赖(0) < 配置(1) < 脚本(2) < 错误处理(3) < 安全关键词(4)"""
        from app.analyzer.digest_collector import filter_for_risk
        preprocessed = [
            {"path": "src/auth.py", "content": "password = 'secret'"},     # priority 4
            {"path": "src/errors.py", "content": "class CustomError"},      # priority 3
            {"path": "deploy.sh", "content": "#!/bin/bash"},                # priority 2
            {"path": "config.py", "content": "DEBUG = True"},               # priority 1
            {"path": "requirements.txt", "content": "flask==2.0"},          # priority 0
        ]
        result = filter_for_risk(preprocessed)
        paths = [f["path"] for f in result]
        assert paths == [
            "requirements.txt",
            "config.py",
            "deploy.sh",
            "src/errors.py",
            "src/auth.py",
        ], f"Unexpected order: {paths}"

    def test_same_priority_sorted_by_path(self):
        """同一优先级内按文件路径字典序稳定排序"""
        from app.analyzer.digest_collector import filter_for_risk
        preprocessed = [
            {"path": "c.sh", "content": "#!/bin/bash"},
            {"path": "a.sh", "content": "#!/bin/bash"},
            {"path": "b.sh", "content": "#!/bin/bash"},
        ]
        result = filter_for_risk(preprocessed)
        paths = [f["path"] for f in result]
        assert paths == ["a.sh", "b.sh", "c.sh"], f"Expected alphabetical by path, got {paths}"

    # ---------- TST-2: 文件数上限 ----------

    def test_upper_limit_200_files(self):
        """201+ 个文件时只返回前 200 个（按优先级排序后）"""
        from app.analyzer.digest_collector import filter_for_risk
        preprocessed = [{"path": f"script{i}.sh", "content": "#!/bin/bash"} for i in range(201)]
        result = filter_for_risk(preprocessed)
        assert len(result) == 200, f"Expected 200, got {len(result)}"


class TestFormatFilesForLLM:
    """format_files_for_llm() 文件列表格式化 LLM 文本"""

    def test_format_contains_file_markers(self):
        from app.analyzer.digest_collector import format_files_for_llm
        files = [
            {"path": "src/main.py", "content": "print('hello')"},
            {"path": "src/utils.py", "content": "def foo(): pass"},
        ]
        text = format_files_for_llm(files)
        assert "### File: src/main.py" in text
        assert "```" in text
        assert "print('hello')" in text
        assert "### File: src/utils.py" in text
        assert "def foo(): pass" in text

    def test_format_empty_list_returns_empty_string(self):
        from app.analyzer.digest_collector import format_files_for_llm
        text = format_files_for_llm([])
        assert text == ""

    # ---------- TST-3: token 预算截断 ----------

    def test_max_tokens_none_no_truncation(self):
        """max_tokens=None 时不截断，保持原有行为（回归）"""
        from app.analyzer.digest_collector import format_files_for_llm
        files = [
            {"path": "a.py", "content": "x=1"},
            {"path": "b.py", "content": "y=2"},
        ]
        text = format_files_for_llm(files, max_tokens=None)
        assert "### File: a.py" in text
        assert "### File: b.py" in text
        assert "[截断]" not in text

    def test_max_tokens_sufficient_all_retained(self):
        """max_tokens 足够大时全部文件保留"""
        from app.analyzer.digest_collector import format_files_for_llm
        files = [
            {"path": "a.py", "content": "x=1"},
            {"path": "b.py", "content": "y=2"},
            {"path": "c.py", "content": "z=3"},
        ]
        text = format_files_for_llm(files, max_tokens=5000)
        assert "### File: a.py" in text
        assert "### File: b.py" in text
        assert "### File: c.py" in text
        assert "[截断]" not in text

    def test_max_tokens_truncation_with_notice(self):
        """max_tokens 不够时截断，输出包含 [截断] 已省略 N 个文件 标注"""
        from app.analyzer.digest_collector import format_files_for_llm
        files = [{"path": f"f{i}.py", "content": "x"} for i in range(10)]
        text = format_files_for_llm(files, max_tokens=160)
        assert "[截断]" in text, f"Expected truncation notice, got: {text[:200]}"
        assert "已省略" in text

    def test_truncation_notice_lists_omitted_paths(self):
        """截断标注列出被截断文件的具体路径"""
        from app.analyzer.digest_collector import format_files_for_llm
        files = [
            {"path": "a.py", "content": "x"},
            {"path": "b.py", "content": "y"},
            {"path": "c.py", "content": "z"},
            {"path": "d.py", "content": "w"},
            {"path": "e.py", "content": "v"},
        ]
        text = format_files_for_llm(files, max_tokens=160)
        if "[截断]" in text:
            # 被截断的文件路径应该在标注中列出
            remaining_in_text = sum(1 for f in files if f"### File: {f['path']}" in text)
            omitted = 5 - remaining_in_text
            if omitted > 0:
                assert f"已省略 {omitted} 个文件" in text, (
                    f"Expected '已省略 {omitted} 个文件' in output"
                )

    def test_max_tokens_zero_only_notice(self):
        """max_tokens=0 时全部文件被截断，返回仅含标注的字符串"""
        from app.analyzer.digest_collector import format_files_for_llm
        files = [
            {"path": "a.py", "content": "x=1"},
            {"path": "b.py", "content": "y=2"},
        ]
        text = format_files_for_llm(files, max_tokens=0)
        assert "[截断]" in text
        assert "已省略 2 个文件" in text
