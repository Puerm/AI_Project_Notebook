# test_analyze_project.py — 测试智能项目分析引擎各模块及 CLI 集成

import os
import sys
import json
import subprocess
import tempfile
import shutil

# Ensure project root is on path for imports
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

CLI_SCRIPT = os.path.join(_PROJECT_ROOT, "harness", "scripts", "analyze_project.py")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_file(dir_path, filename, content):
    """Create file at dir_path/filename with content. Auto-creates dirs."""
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, filename), "w", encoding="utf-8") as f:
        f.write(content)


def _make_tmpdir():
    """Create and return a temp directory."""
    return tempfile.mkdtemp()


# ===========================================================================
# TST-1  ScannerTest — 目录扫描器
# ===========================================================================

class TestScanner:
    """测试 scanner.py — 目录扫描引擎"""

    def test_scan_directory_standard_labels(self):
        """标准目录名识别：src→源代码, tests→测试, docs→文档"""
        from app.analyzer.scanner import scan_directory

        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, "src"))
            os.makedirs(os.path.join(tmp, "tests"))
            os.makedirs(os.path.join(tmp, "docs"))
            # Ensure at least one source file so the dirs are not pruned
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
        """非标准目录基于文件扩展名分布推断用途"""
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
        """排除列表生效: .git / node_modules / __pycache__ 等"""
        from app.analyzer.scanner import scan_directory

        tmp = _make_tmpdir()
        try:
            os.makedirs(os.path.join(tmp, ".git"))
            os.makedirs(os.path.join(tmp, "node_modules"))
            os.makedirs(os.path.join(tmp, "__pycache__"))
            # A regular source dir to make result non-empty
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
        """空目录处理：无源码文件"""
        from app.analyzer.scanner import scan_directory

        tmp = _make_tmpdir()
        try:
            result = scan_directory(tmp)
            assert result["files"] == []
            assert result["stats"]["source_files"] == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_scan_directory_non_source_only(self):
        """仅含非源码文件的目录：无 .py/.js/.ts 文件"""
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
        """传入文件路径返回 error 标记"""
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


# ===========================================================================
# TST-2  ParserTest — 代码解析器
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


class TestParser:
    """测试 parser.py — 代码解析引擎"""

    def test_parse_python_imports(self):
        """Python AST 正确提取 import 语句"""
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
        """Python AST 正确提取函数定义"""
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
        """Python AST 正确提取类定义"""
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
        """JS 正则降级模式正确提取 import/require"""
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
        """JS 正则降级正确提取函数声明"""
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
        """JS 正则降级正确提取类声明"""
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
        """Python 语法错误文件不崩溃，返回空列表"""
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
        """空文件不崩溃，返回空结果"""
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
        """不存在的文件不崩溃，返回空结果"""
        from app.analyzer.parser import parse_file

        result = parse_file("/nonexistent/path/test.py")
        assert result["imports"] == []
        assert result["functions"] == []
        assert result["classes"] == []

    def test_parse_file_unknown_extension(self):
        """不支持的文件扩展名返回 language=unknown"""
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
        """check_nodejs 返回布尔值（不崩溃）"""
        from app.analyzer.parser import check_nodejs

        result = check_nodejs()
        assert isinstance(result, bool)

    def test_check_js_parser_returns_tuple(self):
        """check_js_parser 返回三元组 (parser_name, available, hint)"""
        from app.analyzer.parser import check_js_parser

        result = check_js_parser()
        assert len(result) == 3
        parser_name, available, hint = result
        assert parser_name is None or isinstance(parser_name, str)
        assert isinstance(available, bool)
        # hint 可能为 None 或字符串
        if available:
            assert hint is None
        else:
            assert isinstance(hint, str) or hint is None


# ===========================================================================
# TST-3  OverviewTest — 项目概览检测
# ===========================================================================

class TestOverview:
    """测试 overview.py — 项目概览检测"""

    def test_analyze_overview_python_detected(self):
        """检测 requirements.txt → tech_stack 含 Python"""
        from app.analyzer.overview import analyze_overview

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "requirements.txt", "flask==2.0\n")
            result = analyze_overview(tmp)
            assert "Python" in result["tech_stack"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_nodejs_detected(self):
        """检测 package.json → tech_stack 含 Node.js"""
        from app.analyzer.overview import analyze_overview

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "package.json", '{"name": "test"}')
            result = analyze_overview(tmp)
            assert "Node.js" in result["tech_stack"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_typescript_detected(self):
        """检测 tsconfig.json → tech_stack 含 TypeScript"""
        from app.analyzer.overview import analyze_overview

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "tsconfig.json", '{"compilerOptions": {}}')
            result = analyze_overview(tmp)
            assert "TypeScript" in result["tech_stack"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_web_app_express(self):
        """package.json 含 express → project_type 为 Web 应用"""
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
        """package.json 含 commander → project_type 为 CLI 工具"""
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
        """检测到 main.py → entry_files 包含"""
        from app.analyzer.overview import analyze_overview

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "main.py", "print(1)")
            result = analyze_overview(tmp)
            assert any("main.py" in f for f in result["entry_files"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_entry_files_src_index_js(self):
        """检测 src/index.js → entry_files 包含"""
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
        """缺少所有标志文件时返回合理默认值"""
        from app.analyzer.overview import analyze_overview

        tmp = _make_tmpdir()
        try:
            result = analyze_overview(tmp)
            assert result["tech_stack"] == []
            assert result["project_type"] == "通用项目"
            assert result["entry_files"] == []
            # description based on dir name
            assert len(result["description"]) > 0
            assert len(result["name"]) > 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_analyze_overview_not_a_directory(self):
        """传入文件路径返回 name 和空数据"""
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
        """README.md 第一行标题作为描述"""
        from app.analyzer.overview import analyze_overview

        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "README.md", "# My Awesome Project\nSome content")
            result = analyze_overview(tmp)
            assert result["description"] == "My Awesome Project"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# TST-4  LLMAssistantTest — LLM 语义增强
# ===========================================================================

class TestLLMAssistant:
    """测试 llm_assistant.py — LLM 语义增强及降级"""

    def test_enhance_description_no_api_key(self):
        """未设置 API Key 时直接走降级，不崩溃"""
        # Ensure no API key in env
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        try:
            from app.analyzer.llm_assistant import enhance_description
            result = enhance_description("test module", enable_dotenv=False)
            assert result["enhanced"] is False
            assert result["source"] == "template"
            assert len(result["description"]) > 0
        finally:
            for k, v in saved.items():
                os.environ[k] = v

    def test_template_dir_description_known(self):
        """模板目录描述：已知目录名返回正确标注"""
        from app.analyzer.llm_assistant import _template_dir_description

        result = _template_dir_description("src", ["main.py", "utils.py"])
        assert result["enhanced"] is False
        assert result["source"] == "template"
        assert "源" in result["description"]

        result = _template_dir_description("tests", ["test_main.py"])
        assert "测试" in result["description"]

        result = _template_dir_description("docs", ["readme.md"])
        assert "文档" in result["description"]

    def test_template_dir_description_empty(self):
        """模板目录描述：空目录返回 '空目录'"""
        from app.analyzer.llm_assistant import _template_dir_description

        result = _template_dir_description("unknown", [])
        assert result["description"] == "空目录"

    def test_template_module_description_with_functions(self):
        """模板模块描述：函数名拼接进描述"""
        from app.analyzer.llm_assistant import _template_module_description

        result = _template_module_description(
            "utils", ["parse", "format", "validate"], [])
        assert "parse" in result["description"] or "parse" in str(result)
        assert result["enhanced"] is False

    def test_template_module_description_with_classes(self):
        """模板模块描述：类名拼接进描述"""
        from app.analyzer.llm_assistant import _template_module_description

        result = _template_module_description(
            "models", [], ["User", "Product"])
        assert "User" in result["description"]
        assert result["source"] == "template"

    def test_template_module_description_empty(self):
        """模板模块描述：空模块"""
        from app.analyzer.llm_assistant import _template_module_description

        result = _template_module_description("empty", [], [])
        assert result["description"] == "模块 empty"
        assert result["source"] == "template"

    def test_template_project_description(self):
        """模板项目描述：名称+技术栈+类型 拼接"""
        from app.analyzer.llm_assistant import _template_project_description

        result = _template_project_description("MyApp", ["Python"], "Web 应用")
        assert "MyApp" in result["description"]
        assert "Python" in result["description"]
        assert "Web 应用" in result["description"]
        assert result["enhanced"] is False

    def test_enhance_description_with_invalid_api_key(self):
        """无效 API Key 时静默降级，返回 template 模式"""
        saved = {}
        for k in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "LLM_API_BASE", "LLM_MODEL"):
            if k in os.environ:
                saved[k] = os.environ.pop(k)

        os.environ["LLM_API_KEY"] = "invalid-key-000000"

        try:
            from app.analyzer.llm_assistant import enhance_description
            result = enhance_description("test content")
            # Either LLM call fails (template) or unlikely success — both acceptable
            assert result["source"] in ("template", "llm")
            assert len(result["description"]) > 0
        finally:
            os.environ.pop("LLM_API_KEY", None)
            for k, v in saved.items():
                os.environ[k] = v


# ===========================================================================
# TST-5  MapWriterTest — 地图文件生成器
# ===========================================================================

class TestMapWriter:
    """测试 map_writer.py — 项目地图文件生成"""

    def test_generate_all_creates_four_files(self):
        """generate_all 生成完整的 4 个 project-map 文件"""
        from app.analyzer.map_writer import generate_all

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "harness", "project-map")
            results = {
                "name": "test-project",
                "description": "A test project",
                "tech_stack": ["Python"],
                "project_type": "CLI 工具",
                "entry_files": ["main.py"],
                "tree": None,
                "modules": [],
                "imports": {},
            }
            generate_all(results, output_dir)

            assert os.path.isfile(os.path.join(output_dir, "overview.md"))
            assert os.path.isfile(os.path.join(output_dir, "directory-map.md"))
            assert os.path.isfile(os.path.join(output_dir, "module-map.md"))
            assert os.path.isfile(os.path.join(output_dir, "data-flow.md"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_overview_contains_expected_sections(self):
        """overview.md 包含项目名称和技术栈"""
        from app.analyzer.map_writer import generate_overview

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            results = {
                "tech_stack": ["Python", "Node.js"],
                "project_type": "Web 应用",
                "entry_files": ["src/app.py"],
                "description": "测试项目",
            }
            generate_overview(results, "my-proj", output_dir)

            file_path = os.path.join(output_dir, "overview.md")
            assert os.path.isfile(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "my-proj" in content
            assert "Python" in content
            assert "Node.js" in content
            assert "Web 应用" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_atomic_write_no_tmp_leftover(self):
        """原子写入：写入后没有 .tmp 残留文件"""
        from app.analyzer.map_writer import generate_all

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "map")
            results = {
                "name": "test", "description": "", "tech_stack": [],
                "project_type": "通用项目", "entry_files": [],
                "tree": None, "modules": [], "imports": {},
            }
            generate_all(results, output_dir)

            # No .tmp files should remain
            tmp_files = [f for f in os.listdir(output_dir) if f.endswith(".tmp")]
            assert len(tmp_files) == 0, f"Leftover .tmp files: {tmp_files}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_output_dir_auto_created(self):
        """目标目录不存在时自动创建（嵌套路径）"""
        from app.analyzer.map_writer import generate_all

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "deeply", "nested", "output")
            results = {
                "name": "test", "description": "", "tech_stack": [],
                "project_type": "通用项目", "entry_files": [],
                "tree": None, "modules": [], "imports": {},
            }
            generate_all(results, output_dir)
            assert os.path.isdir(output_dir)
            assert len(os.listdir(output_dir)) >= 4
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_merge_preserves_manual_section(self):
        """MANUAL 标记的段落合并后保留"""
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
        # Auto section should be updated
        assert "这是新的自动内容" in merged
        # Manual section should be preserved (old content)
        assert "这是手动内容" in merged

    def test_generate_data_flow_without_llm_shows_guidance(self):
        """无 LLM 时 data-flow.md 显示入口函数检测引导模板"""
        from app.analyzer.map_writer import generate_data_flow

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            all_imports = {
                "src/main.py": [
                    {"name": "os", "from": None},
                    {"name": "utils", "from": ".utils"},
                ],
                "src/utils.py": [
                    {"name": "json", "from": None},
                ],
            }
            generate_data_flow(all_imports, output_dir)

            file_path = os.path.join(output_dir, "data-flow.md")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "未检测到入口函数" in content
            assert "--llm" in content
            # 无入口函数时不出现逐条 import 列表
            assert "main.py" not in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_generate_data_flow_empty_shows_guidance(self):
        """空依赖时 data-flow.md 显示入口函数检测引导模板"""
        from app.analyzer.map_writer import generate_data_flow

        tmp = _make_tmpdir()
        try:
            output_dir = os.path.join(tmp, "output")
            generate_data_flow({}, output_dir)

            file_path = os.path.join(output_dir, "data-flow.md")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "未检测到入口函数" in content
            assert "--llm" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ===========================================================================
# TST-6  CLIIntegrationTest — CLI 入口集成测试
# ===========================================================================

# Helper: subprocess environment forcing UTF-8 on Windows
_SUBPROCESS_ENV = os.environ.copy()
_SUBPROCESS_ENV["PYTHONIOENCODING"] = "utf-8"
_SUBPROCESS_ENV["PYTHONUTF8"] = "1"


def _run_cli(*args):
    """Run analyze_project.py with forced UTF-8 encoding. Returns CompletedProcess."""
    return subprocess.run(
        [sys.executable, CLI_SCRIPT] + list(args),
        capture_output=True, encoding="utf-8", env=_SUBPROCESS_ENV,
    )


class TestCLIIntegration:
    """测试 analyze_project.py — CLI 入口集成"""

    def test_help_output(self):
        """--help 输出完整，包含 v0.3.1 新参数和 LLM 环境变量说明"""
        result = _run_cli("--help")
        assert result.returncode == 0
        assert "target_path" in result.stdout
        assert "--output-dir" in result.stdout
        assert "--llm" in result.stdout
        assert "--quiet" in result.stdout
        # v0.3.1 新增参数
        assert "--depth" in result.stdout
        assert "--source-root" in result.stdout
        # v0.3.1 环境变量说明
        assert "ANTHROPIC_API_KEY" in result.stdout
        assert ".env" in result.stdout

    def test_invalid_path_exits_one(self):
        """不存在的目标路径退出码为 1"""
        result = _run_cli("/nonexistent/path/xyz")
        assert result.returncode == 1
        assert "不存在" in result.stderr

    def test_invalid_path_not_a_directory(self):
        """目标路径是文件时退出码为 1"""
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

    def test_empty_directory_exits_zero(self):
        """空目录优雅退出，退出码为 0"""
        tmp = _make_tmpdir()
        try:
            result = _run_cli(tmp)
            assert result.returncode == 0
            assert "无" in result.stdout or "空" in result.stdout
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_valid_project_generates_files(self):
        """有效项目路径完成分析并生成 4 个文件"""
        tmp = _make_tmpdir()
        try:
            # Create a minimal Python project structure
            os.makedirs(os.path.join(tmp, "src"))
            _write_file(tmp, "src/main.py", "import os\n\ndef main():\n    print('hi')\n")
            _write_file(tmp, "src/utils.py", "def helper():\n    pass\n")
            _write_file(tmp, "requirements.txt", "click==8.0\n")

            result = _run_cli(tmp)
            assert result.returncode == 0, f"stderr: {result.stderr}"
            assert "分析完成" in result.stdout

            map_dir = os.path.join(tmp, "harness", "project-map")
            assert os.path.isfile(os.path.join(map_dir, "overview.md"))
            assert os.path.isfile(os.path.join(map_dir, "directory-map.md"))
            assert os.path.isfile(os.path.join(map_dir, "module-map.md"))
            assert os.path.isfile(os.path.join(map_dir, "data-flow.md"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_valid_project_quiet_mode(self):
        """--quiet 模式下仅精简输出"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "main.py", "print(1)\n")

            result = _run_cli(tmp, "--quiet")
            assert result.returncode == 0, f"stderr: {result.stderr}"
            # Quiet mode should not print step-by-step
            assert "[1/4]" not in result.stdout
            assert "分析完成" not in result.stdout
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_valid_project_custom_output_dir(self):
        """--output-dir 自定义输出目录生效"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "app.py", "print(1)\n")
            custom_dir = os.path.join(tmp, "custom", "maps")

            result = _run_cli(tmp, "--output-dir", custom_dir)
            assert result.returncode == 0, f"stderr: {result.stderr}"
            assert os.path.isfile(os.path.join(custom_dir, "overview.md"))
            assert os.path.isfile(os.path.join(custom_dir, "module-map.md"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_llm_is_default(self):
        """--no-llm 为默认行为，不尝试 LLM 调用"""
        tmp = _make_tmpdir()
        try:
            _write_file(tmp, "main.py", "print(1)\n")

            result = _run_cli(tmp)
            assert result.returncode == 0
            # Default output should not mention LLM
            assert "[LLM]" not in result.stdout
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
