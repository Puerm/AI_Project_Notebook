# test_project_yaml.py — project.yaml schema 验证和模板填充测试 (TST-4)
"""测试 project.yaml 字段完整性、语义正确性，以及 _fill_template_placeholders 函数。"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from harness.scripts.init_project import (
    _fill_template_placeholders,
    _generate_project_yaml,
    _detect_project_features,
)


class TestProjectYamlSchema:
    """TST-4a: project.yaml 字段完整性和语义正确性。"""

    def test_project_yaml_file_exists(self):
        """project.yaml 文件存在于 harness/config/ 下。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        assert os.path.isfile(yaml_path), f"project.yaml 缺失: {yaml_path}"

    def test_project_yaml_project_name_present(self):
        """project.yaml 包含 project_name 字段。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "project_name:" in content

    def test_project_yaml_version_present(self):
        """project.yaml 包含 version 字段。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "version:" in content

    def test_project_yaml_languages_present(self):
        """project.yaml 包含 languages 字段。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "languages:" in content

    def test_project_yaml_test_command_present(self):
        """project.yaml 包含 test_command 字段。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "test_command:" in content

    def test_project_yaml_package_manager_present(self):
        """project.yaml 包含 package_manager 字段。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "package_manager:" in content

    def test_project_yaml_validation_command_present(self):
        """project.yaml 包含 validation_command 字段。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "validation_command:" in content

    def test_project_yaml_version_is_semver_like(self):
        """version 字段值为 semver 格式（如 '0.9' 或 '0.1'）。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        import re
        match = re.search(r'version:\s*"?(\d+\.\d+(?:\.\d+)?)"?', content)
        assert match is not None, (
            f"project.yaml version 字段不是 semver 格式，内容: {content}"
        )
        version_value = match.group(1)
        parts = version_value.split(".")
        assert len(parts) >= 2, f"version '{version_value}' 至少需要 major.minor"
        for p in parts:
            assert p.isdigit(), f"version '{version_value}' 各部分应为数字"

    def test_project_yaml_languages_non_empty(self):
        """languages 是非空列表，至少包含一项。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 查找 languages 段落后应至少有一个 - <lang> 条目
        import re
        lang_items = re.findall(r'^\s*-\s+(\w+)', content, re.MULTILINE)
        assert len(lang_items) > 0, (
            f"project.yaml languages 列表不应为空，内容: {content}"
        )

    def test_project_yaml_test_command_not_empty(self):
        """test_command 不是空值。"""
        yaml_path = os.path.join(
            _PROJECT_ROOT, "harness", "config", "project.yaml"
        )
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        import re
        match = re.search(r'test_command:\s*"?([^"\n]+)"?', content)
        assert match is not None, "test_command 字段不存在"
        value = match.group(1).strip()
        assert len(value) > 0, "test_command 不应为空"


class TestGenerateProjectYaml:
    """TST-4b: _generate_project_yaml 生成内容格式正确。"""

    def test_generate_yaml_contains_all_fields(self):
        """生成的 YAML 包含所有必需字段。"""
        features = {
            "languages": ["python"],
            "test_framework": "pytest",
            "test_command": "python -m pytest tests/ -v",
            "package_manager": "pip",
        }
        yaml_text = _generate_project_yaml(features, "Test Project")
        assert "project_name: Test Project" in yaml_text
        assert "version:" in yaml_text
        assert "languages:" in yaml_text
        assert "- python" in yaml_text
        assert "test_framework: pytest" in yaml_text
        assert "test_command: python -m pytest tests/ -v" in yaml_text
        assert "package_manager: pip" in yaml_text
        assert "validation_command:" in yaml_text

    def test_generate_yaml_multiple_languages(self):
        """多语言项目 YAML 正确列出所有语言。"""
        features = {
            "languages": ["javascript", "typescript"],
            "test_framework": "jest",
            "test_command": "npx jest",
            "package_manager": "npm",
        }
        yaml_text = _generate_project_yaml(features, "JS Project")
        assert "- javascript" in yaml_text
        assert "- typescript" in yaml_text

    def test_generate_yaml_unknown_language_has_validation(self):
        """未知语言时 validation_command 为空字符串。"""
        features = {
            "languages": ["unknown"],
            "test_framework": "unknown",
            "test_command": "echo 'no tests configured'",
            "package_manager": "unknown",
        }
        yaml_text = _generate_project_yaml(features, "Mystery")
        # 应仍包含 validation_command 字段
        assert "validation_command:" in yaml_text


class TestDetectProjectFeatures:
    """TST-4c: _detect_project_features 静态检测逻辑。"""

    def test_detect_python_project(self):
        """包含 .py 文件的目录被识别为 python 项目。"""
        import tempfile
        import shutil
        tmp = tempfile.mkdtemp()
        try:
            # 创建 Python 项目特征
            with open(os.path.join(tmp, "main.py"), "w") as f:
                f.write("print('hello')")
            with open(os.path.join(tmp, "utils.py"), "w") as f:
                f.write("# util")

            features = _detect_project_features(tmp)
            assert "python" in features["languages"]
            assert features["test_framework"] in ("pytest", "unittest")
            assert features["package_manager"] in ("pip",)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detect_no_source_files_returns_unknown(self):
        """无源码文件的目录返回 ['unknown']。"""
        import tempfile
        import shutil
        tmp = tempfile.mkdtemp()
        try:
            # 仅有 README
            with open(os.path.join(tmp, "README.md"), "w") as f:
                f.write("# empty project")

            features = _detect_project_features(tmp)
            assert "unknown" in features["languages"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detect_returns_required_fields(self):
        """返回 dict 包含所有必需字段。"""
        import tempfile
        import shutil
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "main.py"), "w") as f:
                f.write("print('hello')")

            features = _detect_project_features(tmp)
            for key in ("languages", "test_framework", "test_command", "package_manager"):
                assert key in features, f"缺少字段: {key}"
            assert isinstance(features["languages"], list)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFillTemplatePlaceholders:
    """TST-4d: _fill_template_placeholders 正确替换所有占位符。"""

    def _config(self, **overrides):
        """构造 config dict 带默认值。"""
        defaults = {
            "project_name": "My Project",
            "version": "1.2.3",
            "test_command": "npm test",
            "test_framework": "jest",
            "package_manager": "npm",
            "validation_command": "node harness/scripts/check_structure.js",
        }
        defaults.update(overrides)
        return defaults

    def test_fill_project_name(self):
        """{{project_name}} 替换为 config 值。"""
        content = "Project: {{project_name}}"
        result = _fill_template_placeholders(content, self._config())
        assert result == "Project: My Project"

    def test_fill_version(self):
        """{{version}} 替换为 config 值。"""
        content = "Version: {{version}}"
        result = _fill_template_placeholders(content, self._config())
        assert result == "Version: 1.2.3"

    def test_fill_test_command(self):
        """{{test_command}} 替换为 config 值。"""
        content = "Run: {{test_command}}"
        result = _fill_template_placeholders(content, self._config())
        assert result == "Run: npm test"

    def test_fill_test_framework(self):
        """{{test_framework}} 替换为 config 值。"""
        content = "Framework: {{test_framework}}"
        result = _fill_template_placeholders(content, self._config())
        assert result == "Framework: jest"

    def test_fill_package_manager(self):
        """{{package_manager}} 替换为 config 值。"""
        content = "Package manager: {{package_manager}}"
        result = _fill_template_placeholders(content, self._config())
        assert result == "Package manager: npm"

    def test_fill_validation_command(self):
        """{{validation_command}} 替换为 config 值。"""
        content = "Validate: {{validation_command}}"
        result = _fill_template_placeholders(content, self._config())
        assert result == "Validate: node harness/scripts/check_structure.js"

    def test_fill_all_placeholders_at_once(self):
        """多个占位符在同一个字符串中被全部替换。"""
        content = (
            "# {{project_name}} v{{version}}\n"
            "测试: {{test_command}}\n"
            "验证: {{validation_command}}\n"
            "框架: {{test_framework}} | 包管理: {{package_manager}}"
        )
        result = _fill_template_placeholders(content, self._config())
        assert "My Project" in result
        assert "v1.2.3" in result
        assert "npm test" in result
        assert "jest" in result
        assert "npm" in result
        assert "node harness/scripts/check_structure.js" in result
        assert "{{" not in result, "所有占位符应被替换"

    def test_fill_no_replacement_for_unknown_placeholder(self):
        """未知占位符保持不变。"""
        content = "Value: {{unknown_placeholder}}"
        result = _fill_template_placeholders(content, self._config())
        assert result == content, (
            f"未知占位符应保持原样，但结果变为: {result}"
        )

    def test_fill_missing_config_key_uses_default(self):
        """config 中缺少某字段时使用默认值替换。"""
        content = "Project: {{project_name}}, test: {{test_command}}"
        # 空 config
        result = _fill_template_placeholders(content, {})
        assert "Project: Unknown Project" in result
        assert "test: " in result  # 空字符串

    def test_fill_no_placeholders_returns_original(self):
        """无占位符时返回原字符串。"""
        content = "No placeholders here."
        result = _fill_template_placeholders(content, self._config())
        assert result == content
