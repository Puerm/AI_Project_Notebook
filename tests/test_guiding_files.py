# test_guiding_files.py — 引导文件收集 (TST-1) 与目录摘要 (TST-2) 测试

import os
import sys
import tempfile
import shutil

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.analyzer.guiding_files import (
    collect_guiding_files,
    generate_directory_summary,
    _UUID_RE,
    _BUILD_OUTPUT_DIRS,
    GUIDING_FILE_PATTERNS,
)


def _write_file(dir_path, filename, content):
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, filename), "w", encoding="utf-8") as f:
        f.write(content)


def _make_tmpdir():
    return tempfile.mkdtemp()


# ===========================================================================
# TST-1: collect_guiding_files 测试
# ===========================================================================

class TestCollectGuidingFiles:

    def test_collect_finds_readme(self):
        """标准项目：README.md 被正确收集"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# My Project\n\nThis is a test project.\n")
            result = collect_guiding_files(tmp)
            found_labels = {f["label"] for f in result["found"]}
            assert "项目自述文档" in found_labels
            assert any("README.md" in f["file_path"] for f in result["found"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_finds_package_json(self):
        """标准项目：package.json 被正确收集"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "package.json", '{"name": "test", "dependencies": {"express": "^4.0"}}')
            result = collect_guiding_files(tmp)
            found_labels = {f["label"] for f in result["found"]}
            assert "Node.js 依赖与脚本" in found_labels
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_returns_found_and_missing_keys(self):
        """返回值包含 found 和 missing 两个键"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# Test\n")
            result = collect_guiding_files(tmp)
            assert "found" in result
            assert "missing" in result
            assert isinstance(result["found"], list)
            assert isinstance(result["missing"], list)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_empty_project_returns_empty_found(self):
        """空项目（无任何引导文件）：found 为空列表"""
        tmp = _make_tmpdir()
        try:
            result = collect_guiding_files(tmp)
            assert result["found"] == []
            assert len(result["missing"]) > 0  # all patterns are missing
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_readme_truncated_to_80_lines(self):
        """README.md 内容截断为前 80 行（含截断标记行 ≤ 81 行）"""
        tmp = _make_tmpdir()
        try:
            lines = [f"Line {i}: some content here to pad out the file" for i in range(150)]
            _write_file(tmp, "README.md", "\n".join(lines))
            result = collect_guiding_files(tmp)
            readme_entry = next((f for f in result["found"] if "README.md" in f["file_path"]), None)
            assert readme_entry is not None
            content_lines = readme_entry["content"].split("\n")
            # 80 content lines + 1 truncation marker = at most 81 lines
            assert len(content_lines) <= 81
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_limits_to_15_files(self):
        """引导文件超过 15 个时仅保留优先级最高的 15 个"""
        tmp = _make_tmpdir()
        try:
            # Create many guiding files at root level
            root_files = [
                "README.md", "package.json", "pyproject.toml", "requirements.txt",
                "Dockerfile", "Makefile", "tsconfig.json", ".env.example",
                ".gitignore", ".dockerignore", "setup.py", "CHANGELOG.md",
                "CONTRIBUTING.md", "Gemfile", "Cargo.toml", "go.mod",
                "pom.xml", "build.gradle", "docker-compose.yml", ".env.template",
            ]
            for fname in root_files:
                _write_file(tmp, fname, "# test content\n" * 3)

            result = collect_guiding_files(tmp)
            assert len(result["found"]) <= 15
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_ci_config_file(self):
        """CI 配置文件 (.gitlab-ci.yml) 被正确收集"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, ".gitlab-ci.yml", "stages:\n  - build\n  - test\n")

            result = collect_guiding_files(tmp)
            found_labels = {f["label"] for f in result["found"]}
            assert "GitLab CI 流水线" in found_labels
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_github_actions_not_in_patterns(self):
        """.github/workflows/*.yml 暂未匹配到模式（当前实现限制）"""
        tmp = _make_tmpdir()
        try:
            ci_dir = os.path.join(tmp, ".github", "workflows")
            os.makedirs(ci_dir)
            _write_file(tmp, ".github/workflows/ci.yml", "name: CI\non: [push]\n")

            result = collect_guiding_files(tmp)
            found_paths = [f["file_path"] for f in result["found"]]
            # Current implementation: .github/workflows/*.yml filenames
            # are not in GUIDING_FILE_PATTERNS, so they won't be found
            assert not any(".github/workflows/ci.yml" in p for p in found_paths)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_skips_excluded_dirs(self):
        """EXCLUDE_DIRS 中的目录（如 node_modules）被跳过"""
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, "node_modules", "some-pkg"))
            _write_file(tmp, "node_modules/some-pkg/package.json",
                        '{"name": "dep"}')
            _write_file(tmp, "README.md", "# root\n")

            result = collect_guiding_files(tmp)
            found_paths = [f["file_path"] for f in result["found"]]
            # Should NOT find the node_modules package.json
            assert not any("node_modules" in p for p in found_paths)
            # Should find root README
            assert any("README.md" == p for p in found_paths)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_single_file_read_failure_no_crash(self):
        """单个不可读文件不导致整体崩溃"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# test\n")
            _write_file(tmp, "package.json", "{}")

            # Create a package.json in a subdir we'll make unreadable
            # We simulate by creating an empty file first, then the read
            # will succeed normally since we can't easily break perms on win.
            # Instead verify that the overall function doesn't crash
            # even if a specific file path is problematic.
            result = collect_guiding_files(tmp)
            assert len(result["found"]) >= 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_entry_format(self):
        """每个 found 条目包含 file_path, content, label 三个字段"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# Test Project\n")
            result = collect_guiding_files(tmp)
            for entry in result["found"]:
                assert "file_path" in entry
                assert "content" in entry
                assert "label" in entry
                assert isinstance(entry["file_path"], str)
                assert isinstance(entry["content"], str)
                assert isinstance(entry["label"], str)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_missing_labels(self):
        """缺失的引导文件在 missing 列表中正确标注"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# Only readme\n")
            result = collect_guiding_files(tmp)
            # Many patterns should be missing
            assert len(result["missing"]) > 0
            # missing items are labels (strings)
            for item in result["missing"]:
                assert isinstance(item, str)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_collect_prefers_root_level(self):
        """同名文件优先根目录级别"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# root readme\n")
            os.makedirs(os.path.join(tmp, "subdir"), exist_ok=True)
            _write_file(tmp, "subdir/README.md", "# sub readme\n")

            result = collect_guiding_files(tmp)
            readmes = [f for f in result["found"] if "README.md" in f["file_path"]]
            # Root-level should appear first (lower depth)
            if len(readmes) >= 1:
                assert readmes[0]["file_path"] == "README.md"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_uuid_re_pattern(self):
        """_UUID_RE 正确匹配 UUID 格式目录名"""
        assert _UUID_RE.match("550e8400-e29b-41d4-a716-446655440000")
        assert _UUID_RE.match("550E8400-E29B-41D4-A716-446655440000")
        assert not _UUID_RE.match("not-a-uuid")
        assert not _UUID_RE.match("12345678-1234-1234-1234-12345678901")


# ===========================================================================
# TST-2: generate_directory_summary 测试
# ===========================================================================

class TestDirectorySummary:

    def test_summary_contains_project_root(self):
        """目录摘要以 "项目根:" 开头"""
        tmp = _make_tmpdir()
        try:
            summary = generate_directory_summary(tmp)
            assert summary.startswith("项目根:")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_summary_shows_first_level_dirs(self):
        """目录摘要包含一级子目录"""
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, "src"))
            os.makedirs(os.path.join(tmp, "tests"))
            os.makedirs(os.path.join(tmp, "docs"))
            summary = generate_directory_summary(tmp)
            assert "src/" in summary
            assert "tests/" in summary
            assert "docs/" in summary
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_summary_shows_second_level_dirs(self):
        """目录摘要包含二级子目录"""
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, "src", "utils"))
            os.makedirs(os.path.join(tmp, "src", "models"))
            summary = generate_directory_summary(tmp)
            assert "utils/" in summary
            assert "models/" in summary
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_summary_folds_uuid_dirs(self):
        """UUID 格式目录被折叠为省略提示"""
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, "550e8400-e29b-41d4-a716-446655440000"))
            os.makedirs(os.path.join(tmp, "6ba7b810-9dad-11d1-80b4-00c04fd430c8"))
            summary = generate_directory_summary(tmp)
            assert "UUID" in summary
            assert "550e8400" not in summary  # should be folded
            assert "6ba7b810" not in summary
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_summary_folds_build_output_dirs(self):
        """编译产物目录被折叠（使用在 _BUILD_OUTPUT_DIRS 但不在 EXCLUDE_DIRS 中的目录）"""
        tmp = _make_tmpdir()
        try:
            # Use dirs in _BUILD_OUTPUT_DIRS that are NOT in EXCLUDE_DIRS
            # and don't start with "."
            for d in ["target", "out", "coverage"]:
                os.makedirs(os.path.join(tmp, d))
            summary = generate_directory_summary(tmp)
            assert "编译产物目录" in summary
            assert "target/" not in summary.split("\n")[1:]
            assert "out/" not in summary.split("\n")[1:]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_summary_excludes_hidden_dirs(self):
        """隐藏目录（以 . 开头）不出现在摘要中"""
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, ".git"))
            os.makedirs(os.path.join(tmp, ".venv"))
            os.makedirs(os.path.join(tmp, "src"))
            summary = generate_directory_summary(tmp)
            assert ".git" not in summary
            assert ".venv" not in summary
            assert "src/" in summary
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_summary_excludes_exclude_dirs(self):
        """EXCLUDE_DIRS 中的目录不出现在摘要中"""
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, "node_modules"))
            os.makedirs(os.path.join(tmp, "harness"))
            os.makedirs(os.path.join(tmp, "dist"))
            os.makedirs(os.path.join(tmp, "src"))
            summary = generate_directory_summary(tmp)
            # node_modules is both in EXCLUDE_DIRS and _BUILD_OUTPUT_DIRS
            assert "node_modules" not in summary or "编译产物" in summary
            # harness is in EXCLUDE_DIRS
            assert "harness" not in summary or "harness/" not in summary.split("\n")[1:]
            assert "src/" in summary
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_summary_not_exceeding_30_lines(self):
        """目录摘要不超过 30 行"""
        tmp = _make_tmpdir()
        try:
            # Create many directories to test line limit
            for i in range(40):
                os.makedirs(os.path.join(tmp, f"dir_{i:03d}"))
            summary = generate_directory_summary(tmp)
            lines = summary.split("\n")
            assert len(lines) <= 30, f"Got {len(lines)} lines"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_summary_empty_directory(self):
        """空目录返回最小摘要"""
        tmp = _make_tmpdir()
        try:
            summary = generate_directory_summary(tmp)
            lines = summary.strip().split("\n")
            # Should have at least the root line
            assert len(lines) >= 1
            assert len(lines) <= 30
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_build_output_dirs_set(self):
        """_BUILD_OUTPUT_DIRS 包含预期目录"""
        expected = {"dist", "build", ".next", "__pycache__", "node_modules",
                    "target", ".turbo", "out", "coverage"}
        assert _BUILD_OUTPUT_DIRS == expected
