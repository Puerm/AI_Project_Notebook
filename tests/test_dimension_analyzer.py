# test_dimension_analyzer.py — TST-2: 三维度代码分析引擎（架构/用户故事/风险）

import os
import sys
import tempfile
import shutil
from unittest.mock import patch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _make_tmpdir():
    return tempfile.mkdtemp()


def _mock_llm_config():
    return {
        "api_key": "sk-test-123",
        "api_base": None,
        "model": "gpt-4o-mini",
        "provider": "openai",
    }


# ===========================================================================
# 降级模式（无 LLM Key）
# ===========================================================================


class TestDegradedArchitecture:
    """_degraded_architecture / analyze_architecture 降级"""

    def test_degraded_content_has_key_sections(self):
        from app.analyzer.dimension_analyzer import _degraded_architecture
        content = _degraded_architecture("TestProject")
        assert "架构风格" in content or "分层说明" in content
        assert "降级" in content
        assert "app/" in content
        assert "TestProject" in content

    def test_analyze_architecture_degraded_when_no_key(self):
        from app.analyzer.dimension_analyzer import analyze_architecture
        tmp = _make_tmpdir()
        try:
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(False, {"api_key": None})):
                result = analyze_architecture("code text", "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert "降级" in result["content"]
            assert os.path.isfile(result["file_path"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestDegradedUserStories:
    """_degraded_user_stories / analyze_user_stories 降级"""

    def test_degraded_content_has_entry_files(self):
        from app.analyzer.dimension_analyzer import _degraded_user_stories
        content = _degraded_user_stories("TestProject")
        assert "入口文件" in content
        assert "降级" in content

    def test_degraded_content_crossrefs_architecture(self):
        from app.analyzer.dimension_analyzer import _degraded_user_stories
        content = _degraded_user_stories("TestProject")
        assert "architecture.md" in content

    def test_analyze_user_stories_degraded_when_no_key(self):
        from app.analyzer.dimension_analyzer import analyze_user_stories
        tmp = _make_tmpdir()
        try:
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(False, {"api_key": None})):
                result = analyze_user_stories("code", "arch", "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert "降级" in result["content"]
            assert os.path.isfile(result["file_path"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestDegradedRisk:
    """_degraded_risk / analyze_risk 降级"""

    def test_degraded_content_has_static_check(self):
        from app.analyzer.dimension_analyzer import _degraded_risk
        content = _degraded_risk("TestProject")
        assert "静态检查" in content
        assert "降级" in content

    def test_degraded_content_crossrefs_both(self):
        from app.analyzer.dimension_analyzer import _degraded_risk
        content = _degraded_risk("TestProject")
        assert "architecture.md" in content
        assert "user-stories.md" in content

    def test_analyze_risk_degraded_when_no_key(self):
        from app.analyzer.dimension_analyzer import analyze_risk
        tmp = _make_tmpdir()
        try:
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(False, {"api_key": None})):
                result = analyze_risk("code", "arch", "stories", "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert "降级" in result["content"]
            assert os.path.isfile(result["file_path"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# LLM 增强模式（有 API Key）
# ===========================================================================


class TestArchitectureLLM:
    """analyze_architecture LLM 增强"""

    def test_llm_path_writes_architecture_file(self):
        from app.analyzer.dimension_analyzer import analyze_architecture
        tmp = _make_tmpdir()
        try:
            filtered = [{"path": "src/main.py", "content": "print('hello')"}]
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(True, _mock_llm_config())):
                with patch("app.analyzer.dimension_analyzer._call_llm",
                           return_value="## 架构分层\n\n这是测试的架构分析输出。"):
                    result = analyze_architecture(filtered, "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "llm"
            assert os.path.isfile(result["file_path"])
            with open(result["file_path"], "r", encoding="utf-8") as f:
                content = f.read()
            assert "架构分析" in content
            assert "架构分层" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_llm_call_fails_falls_back_to_degraded(self):
        from app.analyzer.dimension_analyzer import analyze_architecture
        tmp = _make_tmpdir()
        try:
            filtered = [{"path": "src/main.py", "content": "print('hello')"}]
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(True, _mock_llm_config())):
                with patch("app.analyzer.dimension_analyzer._call_llm",
                           return_value=None):
                    result = analyze_architecture(filtered, "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert "降级" in result["content"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestUserStoriesLLM:
    """analyze_user_stories LLM 增强"""

    def test_llm_path_writes_stories_with_crossref(self):
        from app.analyzer.dimension_analyzer import analyze_user_stories
        tmp = _make_tmpdir()
        try:
            filtered = [{"path": "src/main.py", "content": "print('hello')"}]
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(True, _mock_llm_config())):
                with patch("app.analyzer.dimension_analyzer._call_llm",
                           return_value="## 核心用户故事\n\n- 作为用户，我想登录。"):
                    result = analyze_user_stories(filtered, "arch text", "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "llm"
            assert os.path.isfile(result["file_path"])
            with open(result["file_path"], "r", encoding="utf-8") as f:
                content = f.read()
            assert "用户故事" in content
            assert "architecture.md" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_llm_call_fails_falls_back_to_degraded(self):
        from app.analyzer.dimension_analyzer import analyze_user_stories
        tmp = _make_tmpdir()
        try:
            filtered = [{"path": "src/main.py", "content": "print('hello')"}]
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(True, _mock_llm_config())):
                with patch("app.analyzer.dimension_analyzer._call_llm",
                           return_value=None):
                    result = analyze_user_stories(filtered, "arch", "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestRiskLLM:
    """analyze_risk LLM 增强"""

    def test_llm_path_writes_risk_with_crossrefs(self):
        from app.analyzer.dimension_analyzer import analyze_risk
        tmp = _make_tmpdir()
        try:
            filtered = [{"path": "src/main.py", "content": "print('hello')"}]
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(True, _mock_llm_config())):
                with patch("app.analyzer.dimension_analyzer._call_llm",
                           return_value="## 安全风险\n\n- 高风险：硬编码密钥。"):
                    result = analyze_risk(filtered, "arch", "stories", "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "llm"
            assert os.path.isfile(result["file_path"])
            with open(result["file_path"], "r", encoding="utf-8") as f:
                content = f.read()
            assert "风险分析" in content
            assert "architecture.md" in content
            assert "user-stories.md" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_llm_call_fails_falls_back_to_degraded(self):
        from app.analyzer.dimension_analyzer import analyze_risk
        tmp = _make_tmpdir()
        try:
            filtered = [{"path": "src/main.py", "content": "print('hello')"}]
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(True, _mock_llm_config())):
                with patch("app.analyzer.dimension_analyzer._call_llm",
                           return_value=None):
                    result = analyze_risk(filtered, "arch", "stories", "TestProject", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# _write_analysis_file 文件输出
# ===========================================================================


class TestWriteAnalysisFile:
    """_write_analysis_file 原子写入和目录管理"""

    def test_atomic_write_no_tmp_leftover(self):
        from app.analyzer.dimension_analyzer import _write_analysis_file
        tmp = _make_tmpdir()
        try:
            _write_analysis_file(tmp, "test.md", "# Test Content")
            analysis_dir = os.path.join(tmp, "analysis")
            tmp_files = [f for f in os.listdir(analysis_dir) if f.endswith(".tmp")]
            assert len(tmp_files) == 0, f"Leftover .tmp files: {tmp_files}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analysis_dir_auto_created(self):
        from app.analyzer.dimension_analyzer import _write_analysis_file
        tmp = _make_tmpdir()
        try:
            analysis_dir = os.path.join(tmp, "analysis")
            assert not os.path.exists(analysis_dir)
            _write_analysis_file(tmp, "test.md", "# Test")
            assert os.path.isdir(analysis_dir)
            assert os.path.isfile(os.path.join(analysis_dir, "test.md"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_write_overwrites_existing_file(self):
        from app.analyzer.dimension_analyzer import _write_analysis_file
        tmp = _make_tmpdir()
        try:
            path1 = _write_analysis_file(tmp, "test.md", "old content")
            with open(path1, "r", encoding="utf-8") as f:
                assert f.read() == "old content"
            path2 = _write_analysis_file(tmp, "test.md", "new content")
            with open(path2, "r", encoding="utf-8") as f:
                assert f.read() == "new content"
            assert path1 == path2
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_returns_correct_file_path(self):
        from app.analyzer.dimension_analyzer import _write_analysis_file
        tmp = _make_tmpdir()
        try:
            file_path = _write_analysis_file(tmp, "architecture.md", "# Test")
            expected = os.path.join(tmp, "analysis", "architecture.md")
            assert file_path == expected
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# TST-3 新增: 聚焦分析签名验证 + filtered_files 降级测试
# ===========================================================================


class TestDimensionAnalyzerSignatures:
    """v0.5.1 公开函数签名：第一参数为 filtered_files 而非 digest_text"""

    def test_architecture_first_param_is_filtered_files(self):
        import inspect
        from app.analyzer.dimension_analyzer import analyze_architecture
        sig = inspect.signature(analyze_architecture)
        params = list(sig.parameters.keys())
        assert "filtered_files" in params, (
            f"Expected 'filtered_files' in signature, got {params}"
        )
        assert "digest_text" not in params, (
            f"'digest_text' should be removed from signature, got {params}"
        )

    def test_user_stories_first_param_is_filtered_files(self):
        import inspect
        from app.analyzer.dimension_analyzer import analyze_user_stories
        sig = inspect.signature(analyze_user_stories)
        params = list(sig.parameters.keys())
        assert "filtered_files" in params, (
            f"Expected 'filtered_files' in signature, got {params}"
        )
        assert "digest_text" not in params, (
            f"'digest_text' should be removed from signature, got {params}"
        )

    def test_risk_first_param_is_filtered_files(self):
        import inspect
        from app.analyzer.dimension_analyzer import analyze_risk
        sig = inspect.signature(analyze_risk)
        params = list(sig.parameters.keys())
        assert "filtered_files" in params, (
            f"Expected 'filtered_files' in signature, got {params}"
        )
        assert "digest_text" not in params, (
            f"'digest_text' should be removed from signature, got {params}"
        )


class TestDimensionAnalyzerDegradedWithFilteredFiles:
    """聚焦分析降级模式：传入 filtered_files 列表正常降级，不崩溃"""

    def test_architecture_degraded_with_empty_filtered(self):
        from app.analyzer.dimension_analyzer import analyze_architecture
        tmp = _make_tmpdir()
        try:
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(False, {"api_key": None})):
                result = analyze_architecture([], "Proj", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert "降级" in result["content"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_user_stories_degraded_with_empty_filtered(self):
        from app.analyzer.dimension_analyzer import analyze_user_stories
        tmp = _make_tmpdir()
        try:
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(False, {"api_key": None})):
                result = analyze_user_stories([], "arch", "Proj", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert "降级" in result["content"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_risk_degraded_with_empty_filtered(self):
        from app.analyzer.dimension_analyzer import analyze_risk
        tmp = _make_tmpdir()
        try:
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(False, {"api_key": None})):
                result = analyze_risk([], "arch", "stories", "Proj", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert "降级" in result["content"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_architecture_with_fake_key_using_files_list(self):
        """假 Key + filtered_files 列表：LLM 调用失败回退到降级，不崩溃"""
        from app.analyzer.dimension_analyzer import analyze_architecture
        tmp = _make_tmpdir()
        try:
            filtered = [
                {"path": "src/main.py", "content": "print('hello')"},
                {"path": "config.json", "content": "{}"},
            ]
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(True, _mock_llm_config())):
                with patch("app.analyzer.dimension_analyzer._call_llm",
                           return_value=None):
                    result = analyze_architecture(filtered, "Proj", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert os.path.isfile(result["file_path"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_user_stories_with_fake_key_using_files_list(self):
        """假 Key + filtered_files 列表：LLM 调用失败回退到降级，不崩溃"""
        from app.analyzer.dimension_analyzer import analyze_user_stories
        tmp = _make_tmpdir()
        try:
            filtered = [{"path": "README.md", "content": "# Project"}]
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(True, _mock_llm_config())):
                with patch("app.analyzer.dimension_analyzer._call_llm",
                           return_value=None):
                    result = analyze_user_stories(filtered, "arch", "Proj", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert os.path.isfile(result["file_path"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_risk_with_fake_key_using_files_list(self):
        """假 Key + filtered_files 列表：LLM 调用失败回退到降级，不崩溃"""
        from app.analyzer.dimension_analyzer import analyze_risk
        tmp = _make_tmpdir()
        try:
            filtered = [{"path": "requirements.txt", "content": "flask==2.0"}]
            with patch("app.analyzer.dimension_analyzer._check_llm_available",
                       return_value=(True, _mock_llm_config())):
                with patch("app.analyzer.dimension_analyzer._call_llm",
                           return_value=None):
                    result = analyze_risk(filtered, "arch", "stories", "Proj", tmp, enable_dotenv=False)
            assert result["status"] == "degraded"
            assert os.path.isfile(result["file_path"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
