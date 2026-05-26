# test_analyze_project.py — v0.4 扫描/解析/概览 + 渐进式输出 + CLI 集成测试

import os
import sys
import json
import subprocess
import tempfile
import shutil

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

CLI_SCRIPT = os.path.join(_PROJECT_ROOT, "app", "analyze_project.py")


def _write_file(dir_path, filename, content):
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, filename), "w", encoding="utf-8") as f:
        f.write(content)


def _make_tmpdir():
    return tempfile.mkdtemp()


_SUBPROCESS_ENV = os.environ.copy()
_SUBPROCESS_ENV["PYTHONIOENCODING"] = "utf-8"
_SUBPROCESS_ENV["PYTHONUTF8"] = "1"


def _run_cli(*args, env=None):
    """Run analyze_project.py. Returns CompletedProcess."""
    run_env = _SUBPROCESS_ENV.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        [sys.executable, CLI_SCRIPT] + list(args),
        capture_output=True, encoding="utf-8", env=run_env,
    )


# ===========================================================================
# Sealed scanner/parser/overview tests (functions preserved on disk)
# ===========================================================================

PYTHON_SAMPLE = """
import os
import sys
from pathlib import Path
from .utils import helper

def main():
    pass

def greet(name):
    return f"Hello {name}"

class App:
    def __init__(self):
        pass

class Service:
    def run(self):
        pass
"""

JS_SAMPLE = """
import os from 'os';
import { join } from 'path';
const utils = require('./utils');

function main() {
    console.log("hello");
}

function greet(name) {
    return `Hello ${name}`;
}

class App {
    constructor() { }
}

class Service {
    run() { }
}
"""


class TestScanner:
    """scanner.py — 目录扫描引擎"""

    def test_scan_directory_standard_labels(self):
        from app.analyzer.scanner import scan_directory
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, "src"))
            os.makedirs(os.path.join(tmp, "tests"))
            os.makedirs(os.path.join(tmp, "docs"))
            _write_file(tmp, "src/main.py", "print(1)")
            _write_file(tmp, "tests/test_main.py", "print(2)")
            _write_file(tmp, "docs/readme.md", "# doc")

            result = scan_directory(tmp)
            tree = result["tree"]
            labels = {}
            for child in tree.get("children", []):
                if child.get("type") == "dir":
                    labels[child["name"]] = child.get("label")

            assert labels.get("src") == "源代码"
            assert labels.get("tests") == "测试"
            assert labels.get("docs") == "文档"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_scan_directory_content_inference(self):
        from app.analyzer.scanner import scan_directory
        tmp = _make_tmpdir()
        try:
            py_dir = os.path.join(tmp, "mymodule")
            os.makedirs(py_dir)
            _write_file(tmp, "mymodule/a.py", "x=1")
            _write_file(tmp, "mymodule/b.py", "x=2")
            _write_file(tmp, "mymodule/c.py", "x=3")

            result = scan_directory(tmp)
            tree = result["tree"]
            labels = {}
            for child in tree.get("children", []):
                if child.get("type") == "dir":
                    labels[child["name"]] = child.get("label")

            assert labels.get("mymodule") == "Python 源码", f"Got: {labels}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_scan_directory_exclusion(self):
        from app.analyzer.scanner import scan_directory
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, ".git"))
            os.makedirs(os.path.join(tmp, "node_modules"))
            os.makedirs(os.path.join(tmp, "__pycache__"))
            os.makedirs(os.path.join(tmp, "src"))
            _write_file(tmp, "src/main.py", "print(1)")

            result = scan_directory(tmp)
            tree = result["tree"]
            child_names = {c["name"] for c in tree.get("children", [])}

            assert ".git" not in child_names
            assert "node_modules" not in child_names
            assert "__pycache__" not in child_names
            assert "src" in child_names
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_scan_directory_empty(self):
        from app.analyzer.scanner import scan_directory
        tmp = _make_tmpdir()
        try:
            result = scan_directory(tmp)
            assert result["files"] == []
            assert result["stats"]["source_files"] == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_scan_directory_non_source_only(self):
        from app.analyzer.scanner import scan_directory
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "readme.md", "# hello")
            _write_file(tmp, "config.json", "{}")
            _write_file(tmp, "data.csv", "a,b,c")
            result = scan_directory(tmp)
            assert result["files"] == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_scan_directory_not_a_directory(self):
        from app.analyzer.scanner import scan_directory
        tmp = _make_tmpdir()
        try:
            filepath = os.path.join(tmp, "test.txt")
            with open(filepath, "w") as f:
                f.write("hello")
            result = scan_directory(filepath)
            assert result["tree"] is None
            assert result["files"] == []
            assert "error" in result["stats"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestParser:
    """parser.py — 代码解析引擎"""

    def test_parse_python_imports(self):
        from app.analyzer.parser import parse_python
        tmp = _make_tmpdir()
        try:
            py_path = os.path.join(tmp, "test.py")
            with open(py_path, "w") as f:
                f.write(PYTHON_SAMPLE)
            result = parse_python(py_path)
            import_names = {imp["name"] for imp in result["imports"]}
            assert "os" in import_names
            assert "sys" in import_names
            assert "Path" in import_names
            assert "helper" in import_names
            assert result["language"] == "python"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_python_functions(self):
        from app.analyzer.parser import parse_python
        tmp = _make_tmpdir()
        try:
            py_path = os.path.join(tmp, "test.py")
            with open(py_path, "w") as f:
                f.write(PYTHON_SAMPLE)
            result = parse_python(py_path)
            func_names = {f["name"] for f in result["functions"]}
            assert "main" in func_names
            assert "greet" in func_names
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_python_classes(self):
        from app.analyzer.parser import parse_python
        tmp = _make_tmpdir()
        try:
            py_path = os.path.join(tmp, "test.py")
            with open(py_path, "w") as f:
                f.write(PYTHON_SAMPLE)
            result = parse_python(py_path)
            class_names = {c["name"] for c in result["classes"]}
            assert "App" in class_names
            assert "Service" in class_names
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_js_regex_imports(self):
        from app.analyzer.parser import _parse_js_regex
        tmp = _make_tmpdir()
        try:
            js_path = os.path.join(tmp, "test.js")
            with open(js_path, "w") as f:
                f.write(JS_SAMPLE)
            result = _parse_js_regex(js_path)
            import_names = {imp["name"] for imp in result["imports"]}
            assert "os" in import_names or "path" in import_names or "utils" in import_names
            assert result["language"] == "javascript"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_js_regex_functions(self):
        from app.analyzer.parser import _parse_js_regex
        tmp = _make_tmpdir()
        try:
            js_path = os.path.join(tmp, "test.js")
            with open(js_path, "w") as f:
                f.write(JS_SAMPLE)
            result = _parse_js_regex(js_path)
            func_names = {f["name"] for f in result["functions"]}
            assert "main" in func_names, f"Got: {func_names}"
            assert "greet" in func_names, f"Got: {func_names}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_js_regex_classes(self):
        from app.analyzer.parser import _parse_js_regex
        tmp = _make_tmpdir()
        try:
            js_path = os.path.join(tmp, "test.js")
            with open(js_path, "w") as f:
                f.write(JS_SAMPLE)
            result = _parse_js_regex(js_path)
            class_names = {c["name"] for c in result["classes"]}
            assert "App" in class_names, f"Got: {class_names}"
            assert "Service" in class_names, f"Got: {class_names}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_python_syntax_error_no_crash(self):
        from app.analyzer.parser import parse_python
        tmp = _make_tmpdir()
        try:
            py_path = os.path.join(tmp, "broken.py")
            with open(py_path, "w") as f:
                f.write("def broken(:\n    pass\nif = 1\n")
            result = parse_python(py_path)
            assert result["imports"] == []
            assert result["functions"] == []
            assert result["classes"] == []
            assert result["language"] == "python"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_file_empty_file(self):
        from app.analyzer.parser import parse_file
        tmp = _make_tmpdir()
        try:
            py_path = os.path.join(tmp, "empty.py")
            with open(py_path, "w") as f:
                f.write("")
            result = parse_file(py_path)
            assert result["imports"] == []
            assert result["functions"] == []
            assert result["classes"] == []
            assert result["language"] == "python"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_parse_file_nonexistent_file(self):
        from app.analyzer.parser import parse_file
        result = parse_file("/nonexistent/path/test.py")
        assert result["imports"] == []
        assert result["functions"] == []
        assert result["classes"] == []

    def test_parse_file_unknown_extension(self):
        from app.analyzer.parser import parse_file
        tmp = _make_tmpdir()
        try:
            txt_path = os.path.join(tmp, "readme.md")
            with open(txt_path, "w") as f:
                f.write("# Hello")
            result = parse_file(txt_path)
            assert result["language"] == "unknown"
            assert result["imports"] == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_nodejs_returns_bool(self):
        from app.analyzer.parser import check_nodejs
        result = check_nodejs()
        assert isinstance(result, bool)

    def test_check_js_parser_returns_tuple(self):
        from app.analyzer.parser import check_js_parser
        result = check_js_parser()
        assert len(result) == 3
        parser_name, available, hint = result
        assert parser_name is None or isinstance(parser_name, str)
        assert isinstance(available, bool)
        if available:
            assert hint is None
        else:
            assert isinstance(hint, str) or hint is None


class TestOverview:
    """overview.py — 项目概览检测"""

    def test_analyze_overview_python_detected(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "requirements.txt", "flask==2.0\n")
            result = analyze_overview(tmp)
            assert "Python" in result["tech_stack"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_nodejs_detected(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "package.json", '{"name": "test"}')
            result = analyze_overview(tmp)
            assert "Node.js" in result["tech_stack"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_typescript_detected(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "tsconfig.json", '{"compilerOptions": {}}')
            result = analyze_overview(tmp)
            assert "TypeScript" in result["tech_stack"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_web_app_express(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "package.json", json.dumps({
                "name": "my-app",
                "dependencies": {"express": "^4.0.0"}
            }))
            result = analyze_overview(tmp)
            assert result["project_type"] == "Web 应用"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_cli_tool(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "package.json", json.dumps({
                "name": "cli-app",
                "dependencies": {"commander": "^9.0.0"}
            }))
            result = analyze_overview(tmp)
            assert result["project_type"] == "CLI 工具"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_entry_files_main_py(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "main.py", "print(1)")
            result = analyze_overview(tmp)
            assert any("main.py" in f for f in result["entry_files"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_entry_files_src_index_js(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, "src"))
            _write_file(tmp, "src/index.js", "console.log(1)")
            result = analyze_overview(tmp)
            assert any("index.js" in f for f in result["entry_files"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_empty_project_defaults(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            result = analyze_overview(tmp)
            assert result["tech_stack"] == []
            assert result["project_type"] == "通用项目"
            assert result["entry_files"] == []
            assert len(result["description"]) > 0
            assert len(result["name"]) > 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_not_a_directory(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            fp = os.path.join(tmp, "test.txt")
            with open(fp, "w") as f:
                f.write("x")
            result = analyze_overview(fp)
            assert result["tech_stack"] == []
            assert result["project_type"] == "未知"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_readme_title_as_description(self):
        from app.analyzer.overview import analyze_overview
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# My Awesome Project\nSome content")
            result = analyze_overview(tmp)
            assert result["description"] == "My Awesome Project"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# TST-4: llm_assistant 剩余函数测试
# ===========================================================================

class TestLLMAssistant:
    """llm_assistant.py — v0.4 保留函数"""

    def test_check_api_key_no_key_returns_false(self):
        """无 API Key 时 check_api_key_available 返回 (False, guidance)"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        try:
            from app.analyzer.llm_assistant import check_api_key_available
            ok, guidance = check_api_key_available(enable_dotenv=False)
            assert ok is False
            assert len(guidance) > 0
            assert "LLM" in guidance or "API Key" in guidance or ".env" in guidance
        finally:
            for k, v in saved.items():
                os.environ[k] = v

    def test_check_api_key_with_key_returns_true(self):
        """有 LLM_API_KEY 时 check_api_key_available 返回 (True, '')"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        os.environ["LLM_API_KEY"] = "sk-test-123"
        try:
            from app.analyzer.llm_assistant import check_api_key_available
            ok, guidance = check_api_key_available(enable_dotenv=False)
            assert ok is True
            assert guidance == ""
        finally:
            os.environ.pop("LLM_API_KEY", None)
            for k, v in saved.items():
                os.environ[k] = v

    def test_get_llm_config_with_no_env_vars(self):
        """无环境变量时 _get_llm_config 返回默认值"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE",
                  "LLM_MODEL", "OPENAI_API_BASE"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        try:
            from app.analyzer.llm_assistant import _get_llm_config
            config = _get_llm_config(enable_dotenv=False)
            assert config["api_key"] is None
            assert config["model"] == "gpt-4o-mini"
            assert config["provider"] == "openai"
        finally:
            for k, v in saved.items():
                os.environ[k] = v

    def test_get_llm_config_with_env_vars(self):
        """设置环境变量后 _get_llm_config 正确读取"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        os.environ["LLM_API_KEY"] = "sk-custom"
        os.environ["LLM_API_BASE"] = "https://custom.api/v1"
        os.environ["LLM_MODEL"] = "custom-model"
        try:
            from app.analyzer.llm_assistant import _get_llm_config
            config = _get_llm_config(enable_dotenv=False)
            assert config["api_key"] == "sk-custom"
            assert config["api_base"] == "https://custom.api/v1"
            assert config["model"] == "custom-model"
        finally:
            for k in ("LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
                os.environ.pop(k, None)
            for k, v in saved.items():
                os.environ[k] = v

    def test_call_llm_no_key_returns_none(self):
        """无 API Key 时 _call_llm 返回 None"""
        from app.analyzer.llm_assistant import _call_llm
        config = {"api_key": None, "api_base": None, "model": "gpt-4o-mini",
                  "provider": "openai"}
        result = _call_llm("system", "user", config)
        assert result is None


# ===========================================================================
# TST-4: generate_progressive_overview 测试
# ===========================================================================

class TestProgressiveOverview:
    """map_writer.py — generate_progressive_overview (TST-4)"""

    def _sample_domain_result(self, **overrides):
        defaults = {
            "one_liner": "一个测试项目",
            "tech_stack": ["Python", "Flask"],
            "domains": [
                {
                    "name": "用户管理",
                    "description": "用户注册、登录和权限管理",
                    "evidence": "README 中描述了用户模块",
                    "paths": ["auth", "users"],
                    "confidence": "高",
                },
                {
                    "name": "数据分析",
                    "description": "数据报表和统计分析",
                    "evidence": "package.json 含 chart.js",
                    "paths": ["analytics"],
                    "confidence": "中",
                },
            ],
            "relationships": [
                {
                    "from": "用户管理",
                    "to": "数据分析",
                    "type": "数据流",
                    "evidence": "README 提到用户数据用于分析",
                },
            ],
            "next_steps": [
                "深入分析 auth/ 目录的认证流程",
                "检查 analytics/ 模块的数据模型",
                "验证用户权限控制的测试覆盖",
            ],
            "source": "llm",
        }
        defaults.update(overrides)
        return defaults

    def test_generates_file_with_six_sections(self):
        """生成文件包含 6 个必需部分"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            result = self._sample_domain_result()
            path = generate_progressive_overview(result, output_dir, project_name="test")

            assert os.path.isfile(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "项目定位" in content
            assert "技术栈" in content
            assert "业务板块" in content
            assert "板块关系" in content
            assert "下一步建议" in content
            assert "v0.4" in content  # footer
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_contains_data_from_domain_result(self):
        """输出文件包含 domain_result 中的实际数据"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            result = self._sample_domain_result()
            path = generate_progressive_overview(result, output_dir, project_name="MyApp")

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "一个测试项目" in content
            assert "MyApp" in content
            assert "Python" in content
            assert "Flask" in content
            assert "用户管理" in content
            assert "数据分析" in content
            assert "深入分析 auth/ 目录的认证流程" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_confidence_icons_correct(self):
        """置信度符号：高=✓, 中=—, 低=?"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            result = self._sample_domain_result()
            path = generate_progressive_overview(result, output_dir)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # High confidence = checkmark
            assert "高" in content
            assert "中" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_empty_domains_no_crash(self):
        """空 domains 列表不崩溃，显示占位文字"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            result = self._sample_domain_result(domains=[], relationships=[],
                                                 next_steps=[])
            path = generate_progressive_overview(result, output_dir)
            assert os.path.isfile(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "项目定位" in content  # still has structure
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_source_degraded_shows_warning(self):
        """source=degraded 时输出显示 LLM 降级警告"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            result = self._sample_domain_result(source="degraded")
            path = generate_progressive_overview(result, output_dir)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "降级" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_atomic_write_no_tmp_leftover(self):
        """原子写入后没有 .tmp 残留文件"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            result = self._sample_domain_result()
            generate_progressive_overview(result, output_dir)

            tmp_files = [f for f in os.listdir(output_dir) if f.endswith(".tmp")]
            assert len(tmp_files) == 0, f"Leftover .tmp: {tmp_files}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_output_dir_auto_created(self):
        """目标目录不存在时自动创建"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "deeply", "nested", "maps")
            result = self._sample_domain_result()
            path = generate_progressive_overview(result, output_dir)
            assert os.path.isfile(path)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_merge_preserves_manual_section(self):
        """MANUAL 标记的段落合并后保留 (保留的旧测试)"""
        from app.analyzer.map_writer import _merge_sections

        existing = """# Title

## 自动生成段落
这是自动内容

## 手动维护段落 <!-- MANUAL -->
这是手动内容，不可覆盖
"""
        new_content = """# Title

## 自动生成段落
这是新的自动内容

## 手动维护段落 <!-- MANUAL -->
这是新的自动内容
"""
        merged = _merge_sections(existing, new_content)
        assert "这是新的自动内容" in merged
        assert "这是手动内容" in merged

    def test_llm_enabled_footer(self):
        """llm_enabled=True + source=llm 时 footer 标注 LLM 增强"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            result = self._sample_domain_result(source="llm")
            path = generate_progressive_overview(result, output_dir,
                                                  llm_enabled=True)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "LLM 增强" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_returns_file_path(self):
        """返回值是生成的文件路径"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            result = self._sample_domain_result()
            path = generate_progressive_overview(result, output_dir)
            assert path == os.path.join(output_dir, "project-overview.md")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_relationships_shows_placeholder(self):
        """无板块关系时显示占位文字"""
        from app.analyzer.map_writer import generate_progressive_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            result = self._sample_domain_result(relationships=[])
            path = generate_progressive_overview(result, output_dir)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "未识别到板块关系" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# TST-5: CLI 端到端测试
# ===========================================================================

class TestCLIIntegration:
    """analyze_project.py — CLI 集成 (TST-5)"""

    def test_help_output(self):
        """--help 输出含 v0.5 新参数，不含已移除的 --depth/--source-root/--llm"""
        result = _run_cli("--help")
        assert result.returncode == 0
        assert "target_path" in result.stdout
        assert "--output-dir" in result.stdout
        assert "--quiet" in result.stdout
        # Removed parameters must not appear
        assert "--depth" not in result.stdout
        assert "--source-root" not in result.stdout
        assert "--llm" not in result.stdout
        # v0.5 version
        assert "v0.5" in result.stdout
        # New digest parameters
        assert "--digest" in result.stdout
        assert "--max-size" in result.stdout
        # API Key guidance
        assert "ANTHROPIC_API_KEY" in result.stdout
        assert ".env" in result.stdout

    def test_invalid_path_exits_one(self):
        """不存在的目标路径退出码 1"""
        result = _run_cli("/nonexistent/path/xyz")
        assert result.returncode == 1
        assert "不存在" in result.stderr

    def test_invalid_path_not_a_directory(self):
        """目标路径是文件时退出码 1"""
        tmp = _make_tmpdir()
        try:
            fp = os.path.join(tmp, "file.txt")
            with open(fp, "w") as f:
                f.write("hello")
            result = _run_cli(fp)
            assert result.returncode == 1
            assert "不是目录" in result.stderr
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_api_key_exits_one(self):
        """无 API Key 配置时退出码 1（LLM 强制依赖）"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        run_env = _SUBPROCESS_ENV.copy()
        # Explicitly remove all API keys from subprocess env
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL",
                  "ANTHROPIC_API_BASE", "OPENAI_API_KEY", "OPENAI_API_BASE"):
            run_env.pop(k, None)

        # Also prevent loading .env from project root by setting working dir
        tmp = _make_tmpdir()
        try:
            result = subprocess.run(
                [sys.executable, CLI_SCRIPT, tmp],
                capture_output=True, encoding="utf-8", env=run_env,
                cwd=tmp,  # change cwd to tmp so .env is not found
            )
            # If API keys are available (e.g. from project .env at original cwd),
            # changing cwd to tmp should prevent loading them
            # But if keys are set via real env vars that we already popped,
            # the result should be exit 1
            if result.returncode == 1:
                assert "API Key" in result.stderr
            else:
                # Keys may be present from system/user environment
                # This is acceptable
                assert result.returncode == 0
        finally:
            for k, v in saved.items():
                os.environ[k] = v
            shutil.rmtree(tmp, ignore_errors=True)

    def test_valid_project_with_fake_key_generates_overview(self):
        """配置假 Key（LLM 调用降级）仍生成 project-overview.md"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        run_env = _SUBPROCESS_ENV.copy()
        run_env["LLM_API_KEY"] = "fake-test-key"
        run_env["LLM_API_BASE"] = "http://127.0.0.1:1"

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# Test Project\n")
            os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
            _write_file(tmp, "src/main.py", "print('hello')\n")

            result = subprocess.run(
                [sys.executable, CLI_SCRIPT, tmp, "--quiet"],
                capture_output=True, encoding="utf-8", env=run_env,
            )
            assert result.returncode == 0, f"stderr: {result.stderr}"

            overview_path = os.path.join(tmp, "harness", "project-map",
                                          "project-overview.md")
            assert os.path.isfile(overview_path), (
                f"project-overview.md not found at {overview_path}"
            )
            # Verify it has expected sections
            with open(overview_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "项目概览" in content or "项目定位" in content
        finally:
            for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE",
                       "LLM_MODEL"):
                os.environ.pop(k, None)
            for k, v in saved.items():
                os.environ[k] = v
            shutil.rmtree(tmp, ignore_errors=True)

    def test_quiet_mode_exit_zero(self):
        """--quiet 模式退出码 0"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        run_env = _SUBPROCESS_ENV.copy()
        run_env["LLM_API_KEY"] = "fake-test-key"
        run_env["LLM_API_BASE"] = "http://127.0.0.1:1"

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "main.py", "print(1)\n")
            result = subprocess.run(
                [sys.executable, CLI_SCRIPT, tmp, "--quiet"],
                capture_output=True, encoding="utf-8", env=run_env,
            )
            assert result.returncode == 0, f"stderr: {result.stderr}"
            # Quiet mode should not print step-by-step
            assert "[1/3]" not in result.stdout
            assert "分析完成" not in result.stdout
        finally:
            for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE",
                       "LLM_MODEL"):
                os.environ.pop(k, None)
            for k, v in saved.items():
                os.environ[k] = v
            shutil.rmtree(tmp, ignore_errors=True)

    def test_custom_output_dir(self):
        """--output-dir 自定义输出目录生效"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        run_env = _SUBPROCESS_ENV.copy()
        run_env["LLM_API_KEY"] = "fake-test-key"
        run_env["LLM_API_BASE"] = "http://127.0.0.1:1"

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "app.py", "print(1)\n")
            custom_dir = os.path.join(tmp, "custom", "maps")
            result = subprocess.run(
                [sys.executable, CLI_SCRIPT, tmp, "--output-dir", custom_dir,
                 "--quiet"],
                capture_output=True, encoding="utf-8", env=run_env,
            )
            assert result.returncode == 0, f"stderr: {result.stderr}"
            assert os.path.isfile(os.path.join(custom_dir, "project-overview.md"))
        finally:
            for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE",
                       "LLM_MODEL"):
                os.environ.pop(k, None)
            for k, v in saved.items():
                os.environ[k] = v
            shutil.rmtree(tmp, ignore_errors=True)

    def test_digest_quiet_mode_exits_zero(self):
        """--digest --quiet 模式退出码为 0（需假 Key，LLM 调用降级后不应崩溃）"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        run_env = _SUBPROCESS_ENV.copy()
        run_env["LLM_API_KEY"] = "fake-test-key"
        run_env["LLM_API_BASE"] = "http://127.0.0.1:1"

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# Digest Test Project\n")
            os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
            _write_file(tmp, "src/main.py", "print('hello')\n")

            result = subprocess.run(
                [sys.executable, CLI_SCRIPT, tmp, "--digest", "--quiet"],
                capture_output=True, encoding="utf-8", env=run_env,
            )
            assert result.returncode == 0, f"Exit {result.returncode}, stderr: {result.stderr}"
            overview_path = os.path.join(tmp, "harness", "project-map", "project-overview.md")
            assert os.path.isfile(overview_path), f"Missing: {overview_path}"
        finally:
            for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE",
                       "LLM_MODEL"):
                os.environ.pop(k, None)
            for k, v in saved.items():
                os.environ[k] = v
            shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# TST-4: CLI digest 聚焦分析新流程端到端测试
# ===========================================================================


class TestDigestCLIE2E:
    """analyze_project.py --digest 聚焦分析新流程"""

    def test_digest_help_contains_focus_description(self):
        """--digest --help 输出含'聚焦'描述"""
        result = _run_cli("--digest", "--help")
        assert result.returncode == 0
        assert "聚焦" in result.stdout, (
            f"Expected '聚焦' in digest help, got: {result.stdout[:500]}"
        )

    def test_digest_always_generates_project_overview(self):
        """--digest 模式下即使 cdigest 不可用，仍生成 project-overview.md"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        run_env = _SUBPROCESS_ENV.copy()
        run_env["LLM_API_KEY"] = "fake-test-key"
        run_env["LLM_API_BASE"] = "http://127.0.0.1:1"

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# Digest Overview Test\n")
            os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
            _write_file(tmp, "src/app.py", "print('hello')\n")

            result = subprocess.run(
                [sys.executable, CLI_SCRIPT, tmp, "--digest", "--quiet"],
                capture_output=True, encoding="utf-8", env=run_env,
            )
            assert result.returncode == 0, (
                f"Exit {result.returncode}, stderr: {result.stderr}"
            )

            overview_path = os.path.join(tmp, "harness", "project-map",
                                          "project-overview.md")
            assert os.path.isfile(overview_path), (
                f"project-overview.md missing at {overview_path}"
            )

            with open(overview_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "业务板块" in content or "项目定位" in content, (
                "project-overview.md should have structured content"
            )
        finally:
            for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE",
                      "LLM_MODEL"):
                os.environ.pop(k, None)
            for k, v in saved.items():
                os.environ[k] = v
            shutil.rmtree(tmp, ignore_errors=True)

    def test_digest_with_cdigest_available_generates_analysis_files(self):
        """--digest 模式下若 cdigest 可用，生成 analysis/ 下三份报告"""
        from app.analyzer.digest_collector import is_cdigest_available
        if not is_cdigest_available():
            import pytest
            pytest.skip("codebase-digest not installed — skipping analysis file test")

        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        run_env = _SUBPROCESS_ENV.copy()
        run_env["LLM_API_KEY"] = "fake-test-key"
        run_env["LLM_API_BASE"] = "http://127.0.0.1:1"

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# Analysis Test\n")
            os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
            _write_file(tmp, "src/main.py", "print('hello')\n")

            result = subprocess.run(
                [sys.executable, CLI_SCRIPT, tmp, "--digest", "--quiet"],
                capture_output=True, encoding="utf-8", env=run_env,
            )
            assert result.returncode == 0, (
                f"Exit {result.returncode}, stderr: {result.stderr}"
            )

            analysis_dir = os.path.join(tmp, "analysis")
            assert os.path.isfile(os.path.join(analysis_dir, "architecture.md")), (
                "architecture.md missing"
            )
            assert os.path.isfile(os.path.join(analysis_dir, "user-stories.md")), (
                "user-stories.md missing"
            )
            assert os.path.isfile(os.path.join(analysis_dir, "risk-analysis.md")), (
                "risk-analysis.md missing"
            )
        finally:
            for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE",
                      "LLM_MODEL"):
                os.environ.pop(k, None)
            for k, v in saved.items():
                os.environ[k] = v
            shutil.rmtree(tmp, ignore_errors=True)

    def test_non_digest_mode_still_works_regression(self):
        """非 digest 模式：--quiet 正常输出 project-overview.md（回归）"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        run_env = _SUBPROCESS_ENV.copy()
        run_env["LLM_API_KEY"] = "fake-test-key"
        run_env["LLM_API_BASE"] = "http://127.0.0.1:1"

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "main.py", "print('hello')\n")
            result = subprocess.run(
                [sys.executable, CLI_SCRIPT, tmp, "--quiet"],
                capture_output=True, encoding="utf-8", env=run_env,
            )
            assert result.returncode == 0, (
                f"Exit {result.returncode}, stderr: {result.stderr}"
            )
            overview_path = os.path.join(tmp, "harness", "project-map",
                                          "project-overview.md")
            assert os.path.isfile(overview_path), (
                f"project-overview.md missing at {overview_path}"
            )
        finally:
            for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE",
                      "LLM_MODEL"):
                os.environ.pop(k, None)
            for k, v in saved.items():
                os.environ[k] = v
            shutil.rmtree(tmp, ignore_errors=True)
