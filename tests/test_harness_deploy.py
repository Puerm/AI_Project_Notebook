# test_harness_deploy.py — TST-1/TST-2/TST-3: harness_deploy 功能测试
"""
覆盖 spec 功能 A/B/C/D/E 的验收标准和 plan 定义的三个测试任务。
"""

import os
import sys
import subprocess
import tempfile
import shutil

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

SCRIPT = os.path.join(
    _PROJECT_ROOT, "harness", "scripts", "harness_deploy.py",
)

# ============================================================
# TST-1: CLI 基础测试
# ============================================================


class TestCliBasics:
    """TST-1: harness_deploy.py CLI 基础行为。"""

    def test_help_returns_zero(self):
        """--help 返回退出码 0。"""
        result = subprocess.run(
            [sys.executable, SCRIPT, "--help"],
            capture_output=True, encoding="utf-8",
        )
        assert result.returncode == 0, f"--help 应返回 0，实际 {result.returncode}"

    def test_help_shows_usage(self):
        """--help 输出包含用法说明（spec 功能 A 验收标准）。"""
        result = subprocess.run(
            [sys.executable, SCRIPT, "--help"],
            capture_output=True, encoding="utf-8",
        )
        assert "用法:" in result.stdout or "usage:" in result.stdout.lower(), (
            f"--help 应输出用法说明，实际:\n{result.stdout}"
        )
        assert "Phase 1" in result.stdout, "应包含 Phase 1 说明"
        assert "Phase 2" in result.stdout, "应包含 Phase 2 说明"
        assert "Phase 3" in result.stdout, "应包含 Phase 3 说明"

    def test_nonexistent_path_exits_nonzero(self):
        """<不存在的路径> 正确报错退出码非零。"""
        result = subprocess.run(
            [sys.executable, SCRIPT, "/nonexistent/path/to/nowhere_12345"],
            capture_output=True, encoding="utf-8",
        )
        assert result.returncode != 0, (
            f"不存在的路径应返回非零退出码，实际 {result.returncode}"
        )

    def test_nonexistent_path_error_message(self):
        """<不存在的路径> 输出错误信息。"""
        result = subprocess.run(
            [sys.executable, SCRIPT, "/nonexistent/path/to/nowhere_12345"],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        assert result.stderr is not None, "stderr 不应为 None（编码问题？）"
        assert result.returncode != 0, (
            f"不存在的路径应返回非零退出码，实际 {result.returncode}"
        )

    def test_missing_argument_exits_nonzero(self):
        """无参数运行时退出码非零。"""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, encoding="utf-8",
        )
        assert result.returncode != 0, (
            f"无参数应返回非零退出码，实际 {result.returncode}"
        )

    def test_existing_dir_without_harness_warns(self):
        """存在的目录但没有 harness 子目录时，提示先运行 init_project。"""
        tmpdir = tempfile.mkdtemp()
        try:
            result = subprocess.run(
                [sys.executable, SCRIPT, tmpdir],
                capture_output=True, encoding="utf-8", errors="replace",
            )
            assert result.returncode != 0, "缺 harness 目录时应返回非零"
            # stderr should contain a warning about missing harness dir
            assert result.stderr is not None, "应输出警告信息"
            assert len(result.stderr.strip()) > 0, "stderr 不应为空"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_help_with_h_flag(self):
        """-h 短选项也能输出帮助。"""
        result = subprocess.run(
            [sys.executable, SCRIPT, "-h"],
            capture_output=True, encoding="utf-8",
        )
        assert result.returncode == 0, f"-h 应返回 0，实际 {result.returncode}"
        assert "用法:" in result.stdout or "usage:" in result.stdout.lower()


# ============================================================
# TST-2: 检测逻辑 + 模板占位符替换测试
# ============================================================


class TestDetectProjectFeatures:
    """TST-2a: _detect_project_features 静态检测逻辑。"""

    def test_detect_js_with_package_json(self):
        """包含 package.json 的目录正确识别为 javascript（spec 功能 A）。"""
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "package.json"), "w") as f:
                f.write('{"name": "test"}')
            with open(os.path.join(tmp, "index.js"), "w") as f:
                f.write("console.log('hello')")

            from harness.scripts.harness_deploy import _detect_project_features
            features = _detect_project_features(tmp)
            assert "javascript" in features["languages"] or "typescript" in features["languages"], (
                f"package.json 项目应识别为 javascript/typescript，实际: {features['languages']}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detect_go_with_go_mod(self):
        """包含 go.mod 的目录正确识别为 go（spec 功能 A）。"""
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "go.mod"), "w") as f:
                f.write("module example.com/test\n\ngo 1.21\n")
            with open(os.path.join(tmp, "main.go"), "w") as f:
                f.write("package main\nfunc main() {}")

            from harness.scripts.harness_deploy import _detect_project_features
            features = _detect_project_features(tmp)
            assert "go" in features["languages"], (
                f"go.mod 项目应识别为 go，实际: {features['languages']}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detect_rust_with_cargo_toml(self):
        """包含 Cargo.toml 的目录正确识别为 rust。"""
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "Cargo.toml"), "w") as f:
                f.write('[package]\nname = "test"\n')
            os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
            with open(os.path.join(tmp, "src", "main.rs"), "w") as f:
                f.write("fn main() {}")

            from harness.scripts.harness_deploy import _detect_project_features
            features = _detect_project_features(tmp)
            assert "rust" in features["languages"], (
                f"Cargo.toml 项目应识别为 rust，实际: {features['languages']}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detect_python_project(self):
        """包含 .py 文件的目录正确识别为 python。"""
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "main.py"), "w") as f:
                f.write("print('hello')")

            from harness.scripts.harness_deploy import _detect_project_features
            features = _detect_project_features(tmp)
            assert "python" in features["languages"], (
                f".py 文件应识别为 python，实际: {features['languages']}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detect_returns_all_required_fields(self):
        """返回 dict 包含所有必需字段。"""
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "main.py"), "w") as f:
                f.write("print('hello')")

            from harness.scripts.harness_deploy import _detect_project_features
            features = _detect_project_features(tmp)
            required = ["languages", "framework", "domain", "description",
                        "entry_point", "test_framework", "test_command",
                        "package_manager", "source"]
            for key in required:
                assert key in features, f"缺少字段: {key}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detect_no_source_returns_unknown(self):
        """无源码文件返回 ['unknown']（降级行为）。"""
        tmp = tempfile.mkdtemp()
        try:
            from harness.scripts.harness_deploy import _detect_project_features
            features = _detect_project_features(tmp)
            assert "unknown" in features["languages"], (
                f"空目录应识别为 unknown，实际: {features['languages']}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detect_excludes_harness_and_dot_dirs(self):
        """harness/ 和 .claude/ 等目录不参与检测。"""
        tmp = tempfile.mkdtemp()
        try:
            # 在排除目录中放 .py 文件，根目录放 go 代码
            os.makedirs(os.path.join(tmp, "harness"))
            with open(os.path.join(tmp, "harness", "fake.py"), "w") as f:
                f.write("# this should be excluded")
            with open(os.path.join(tmp, "main.go"), "w") as f:
                f.write("package main")

            from harness.scripts.harness_deploy import _detect_project_features
            features = _detect_project_features(tmp)
            # 应该识别为 go（排除目录里的 .py 不算）
            assert "go" in features["languages"], (
                f"应忽略 harness/ 目录的文件，识别为 go，实际: {features['languages']}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestParseAdaptableZones:
    """TST-2b: _parse_adaptable_zones zone marker 解析逻辑。"""

    def test_extract_single_zone(self):
        """能正确提取单个 ADAPTABLE_ZONE 之间的内容。"""
        from harness.scripts.harness_deploy import _parse_adaptable_zones
        content = (
            "通用区内容\n"
            "<!-- ADAPTABLE_ZONE_START -->\n"
            "可适配区内容\n"
            "<!-- ADAPTABLE_ZONE_END -->\n"
            "更多通用内容"
        )
        general, zones = _parse_adaptable_zones(content)
        assert len(zones) == 1, f"应提取 1 个 zone，实际 {len(zones)}"
        assert "可适配区内容" in zones[0], f"zone 内容不正确: {zones[0]}"
        assert "通用区内容" in "".join(general), "通用区内容应保留"

    def test_extract_multiple_zones(self):
        """能正确提取多个 ADAPTABLE_ZONE。"""
        from harness.scripts.harness_deploy import _parse_adaptable_zones
        content = (
            "开头通用\n"
            "<!-- ADAPTABLE_ZONE_START -->\nzone1\n<!-- ADAPTABLE_ZONE_END -->\n"
            "中间通用\n"
            "<!-- ADAPTABLE_ZONE_START -->\nzone2\n<!-- ADAPTABLE_ZONE_END -->\n"
            "结尾通用"
        )
        general, zones = _parse_adaptable_zones(content)
        assert len(zones) == 2, f"应提取 2 个 zones，实际 {len(zones)}"
        assert "zone1" in zones[0]
        assert "zone2" in zones[1]
        assert "开头通用" in general[0]
        assert "中间通用" in general[1]
        assert "结尾通用" in general[2]

    def test_no_zone_returns_empty_and_original(self):
        """无 ADAPTABLE_ZONE 标记时返回空 zones 和原始内容作为通用区。"""
        from harness.scripts.harness_deploy import _parse_adaptable_zones
        content = "普通内容，无标记"
        general, zones = _parse_adaptable_zones(content)
        assert len(zones) == 0, "无标记时应返回空 zones"
        assert "普通内容" in "".join(general), "原始内容应包含在通用区"


class TestAdaptWorkflowContent:
    """TST-2c: _adapt_workflow_content 模板占位符替换和 skip 标记。"""

    def test_replaces_test_command_placeholder(self):
        """正确替换 {{test_command}} 占位符。"""
        from harness.scripts.harness_deploy import _adapt_workflow_content
        content = "运行: {{test_command}}"
        features = {"test_command": "go test ./...", "languages": ["go"]}
        result = _adapt_workflow_content(content, features)
        assert "{{test_command}}" not in result, "占位符应被替换"
        assert "go test ./..." in result, "应包含替换后的值"
        assert result == "运行: go test ./..."

    def test_replaces_project_name_placeholder(self):
        """正确替换 {{project_name}} 占位符。"""
        from harness.scripts.harness_deploy import _adapt_workflow_content
        content = "# {{project_name}}"
        features = {
            "test_command": "npm test", "languages": ["javascript"],
            "project_name": "MyJSProject",
        }
        result = _adapt_workflow_content(content, features)
        assert "{{project_name}}" not in result, "占位符应被替换"
        assert "MyJSProject" in result

    def test_replaces_multiple_placeholders(self):
        """所有已知占位符被正确替换，不留 {{...}} 残留。"""
        from harness.scripts.harness_deploy import _adapt_workflow_content
        content = (
            "Test: {{test_command}}\n"
            "Framework: {{test_framework}}\n"
            "Package: {{package_manager}}\n"
            "Validate: {{validation_command}}\n"
            "Project: {{project_name}} v{{version}}"
        )
        features = {
            "test_command": "npx jest",
            "test_framework": "jest",
            "package_manager": "npm",
            "validation_command": "npm run check",
            "project_name": "Frontend",
            "languages": ["typescript"],
        }
        result = _adapt_workflow_content(content, features)
        assert "{{" not in result, f"不应有残留占位符，实际: {result}"

    def test_frontend_only_marks_skip(self):
        """纯前端项目（javascript+typescript 无 python）标记 tester 等阶段为 skip。"""
        from harness.scripts.harness_deploy import _adapt_workflow_content
        content = """---
stages:
  - id: generator
    description: 生成代码
  - id: tester
    description: 测试
  - id: generator-fix
    description: 修复
  - id: generator-test-fix
    description: 测试修复
---
# Workflow
"""
        features = {
            "test_command": "npm test",
            "languages": ["javascript", "typescript"],
        }
        result = _adapt_workflow_content(content, features)
        assert "tester" in result
        # Check that skip: true was added for frontend-only stages
        # The yaml dump will have skip: true in the appropriate sections
        assert "skip: true" in result, (
            f"纯前端项目应标记阶段为 skip，实际:\n{result}"
        )

    def test_go_project_no_skip(self):
        """Go 项目不应标记任何阶段为 skip。"""
        from harness.scripts.harness_deploy import _adapt_workflow_content
        content = """---
stages:
  - id: generator
    description: 生成代码
  - id: tester
    description: 测试
---
# Workflow
"""
        features = {
            "test_command": "go test ./...",
            "languages": ["go"],
        }
        result = _adapt_workflow_content(content, features)
        assert "skip: true" not in result, (
            f"Go 项目不应标记 skip，实际:\n{result}"
        )

    def test_python_project_no_skip(self):
        """Python 项目不应标记任何阶段为 skip。"""
        from harness.scripts.harness_deploy import _adapt_workflow_content
        content = """---
stages:
  - id: generator
    description: 生成代码
  - id: tester
    description: 测试
---
# Workflow
"""
        features = {
            "test_command": "python -m pytest tests/ -v",
            "languages": ["python"],
        }
        result = _adapt_workflow_content(content, features)
        assert "skip: true" not in result, (
            f"Python 项目不应标记 skip，实际:\n{result}"
        )

    def test_no_frontmatter_no_crash(self):
        """无 YAML frontmatter 的内容不崩溃。"""
        from harness.scripts.harness_deploy import _adapt_workflow_content
        content = "# No frontmatter\nJust content"
        features = {"test_command": "npm test", "languages": ["javascript"]}
        result = _adapt_workflow_content(content, features)
        assert "Just content" in result, "无 frontmatter 时内容应不变（仅占位符替换）"

    def test_no_skip_for_rust_project(self):
        """Rust 项目不应标记任何阶段为 skip。"""
        from harness.scripts.harness_deploy import _adapt_workflow_content
        content = """---
stages:
  - id: tester
    description: 测试
---
# Workflow
"""
        features = {
            "test_command": "cargo test",
            "languages": ["rust"],
        }
        result = _adapt_workflow_content(content, features)
        assert "skip: true" not in result, (
            f"Rust 项目不应标记 skip，实际:\n{result}"
        )

    def test_preserves_content_outside_frontmatter(self):
        """frontmatter 外的内容保持不变（超出占位符替换）。"""
        from harness.scripts.harness_deploy import _adapt_workflow_content
        content = """---
stages:
  - id: tester
    description: 测试
---
# 工作流说明
请运行 {{test_command}}
"""
        features = {"test_command": "npm test", "languages": ["javascript"]}
        result = _adapt_workflow_content(content, features)
        assert "工作流说明" in result, "frontmatter 外内容应保留"
        assert "npm test" in result


class TestGenerateAdaptedProjectYaml:
    """TST-2d: _generate_adapted_project_yaml 生成 project.yaml 新内容。"""

    def test_contains_domain_field(self):
        """生成的 project.yaml 包含 domain 字段。"""
        from harness.scripts.harness_deploy import _generate_adapted_project_yaml
        features = {
            "project_name": "Test",
            "languages": ["python"],
            "test_framework": "pytest",
            "test_command": "pytest",
            "package_manager": "pip",
            "validation_command": "python check.py",
            "domain": "Web 后端",
            "description": "测试项目",
            "entry_point": "main.py",
        }
        result = _generate_adapted_project_yaml(features)
        assert 'domain:' in result, f"应包含 domain 字段，实际:\n{result}"

    def test_contains_description_field(self):
        """生成的 project.yaml 包含 description 字段。"""
        from harness.scripts.harness_deploy import _generate_adapted_project_yaml
        features = {
            "project_name": "Test",
            "languages": ["go"],
            "test_framework": "go test",
            "test_command": "go test ./...",
            "package_manager": "go",
            "validation_command": "",
            "domain": "CLI 工具",
            "description": "一个 Go CLI 工具",
            "entry_point": "main.go",
        }
        result = _generate_adapted_project_yaml(features)
        assert 'description:' in result, f"应包含 description 字段，实际:\n{result}"

    def test_contains_entry_point_field(self):
        """生成的 project.yaml 包含 entry_point 字段。"""
        from harness.scripts.harness_deploy import _generate_adapted_project_yaml
        features = {
            "project_name": "Test",
            "languages": ["typescript"],
            "test_framework": "jest",
            "test_command": "npx jest",
            "package_manager": "npm",
            "validation_command": "npm run check",
            "domain": "前端",
            "description": "React 前端",
            "entry_point": "src/index.ts",
        }
        result = _generate_adapted_project_yaml(features)
        assert 'entry_point:' in result, f"应包含 entry_point 字段，实际:\n{result}"

    def test_domain_field_non_empty(self):
        """domain 字段值不为空。"""
        from harness.scripts.harness_deploy import _generate_adapted_project_yaml
        features = {
            "project_name": "Test",
            "languages": ["python"],
            "test_framework": "pytest",
            "test_command": "pytest",
            "package_manager": "pip",
            "validation_command": "",
            "domain": "AI 辅助开发工具",
            "description": "desc",
            "entry_point": "",
        }
        result = _generate_adapted_project_yaml(features)
        assert 'domain: "' in result, "domain 应为带引号的字符串"
        # domain value should not be empty
        assert 'domain: ""' not in result, "domain 不应为空字符串"

    def test_description_field_non_empty(self):
        """description 字段值不为空。"""
        from harness.scripts.harness_deploy import _generate_adapted_project_yaml
        features = {
            "project_name": "Test",
            "languages": ["python"],
            "test_framework": "pytest",
            "test_command": "pytest",
            "package_manager": "pip",
            "validation_command": "",
            "domain": "Web",
            "description": "非空描述",
            "entry_point": "",
        }
        result = _generate_adapted_project_yaml(features)
        assert 'description: "' in result, "description 应为带引号的字符串"

    def test_generated_yaml_is_valid(self):
        """生成的 YAML 可以使用 yaml.safe_load 解析。"""
        import yaml
        from harness.scripts.harness_deploy import _generate_adapted_project_yaml
        features = {
            "project_name": "Test",
            "languages": ["javascript", "typescript"],
            "test_framework": "jest",
            "test_command": "npm test",
            "package_manager": "npm",
            "validation_command": "npm run check",
            "domain": "前端",
            "description": "React SPA",
            "entry_point": "src/index.tsx",
        }
        result = _generate_adapted_project_yaml(features)
        parsed = yaml.safe_load(result)
        assert parsed is not None, "生成的 YAML 应可解析"
        assert parsed["project_name"] == "Test"
        assert parsed["domain"] == "前端"
        assert parsed["description"] == "React SPA"
        assert parsed["entry_point"] == "src/index.tsx"
        assert parsed["languages"] == ["javascript", "typescript"]


class TestGenerateAdaptedClaudeMd:
    """TST-2e: _generate_adapted_claude_md 生成 CLAUDE.md。"""

    def test_contains_project_name(self):
        """生成的 CLAUDE.md 包含项目名称。"""
        from harness.scripts.harness_deploy import _generate_adapted_claude_md
        features = {
            "project_name": "MyGoProject",
            "description": "Go 微服务",
        }
        result = _generate_adapted_claude_md(features)
        assert "MyGoProject" in result, f"应包含项目名称，实际:\n{result}"

    def test_contains_description(self):
        """生成的 CLAUDE.md 包含项目描述。"""
        from harness.scripts.harness_deploy import _generate_adapted_claude_md
        features = {
            "project_name": "MyApp",
            "description": "一个测试应用",
        }
        result = _generate_adapted_claude_md(features)
        assert "测试应用" in result, f"应包含项目描述，实际:\n{result}"

    def test_contains_project_map_table(self):
        """生成的 CLAUDE.md 包含项目地图入口表。"""
        from harness.scripts.harness_deploy import _generate_adapted_claude_md
        features = {
            "project_name": "Test",
            "description": "desc",
        }
        result = _generate_adapted_claude_md(features)
        assert "overview.md" in result, "应包含项目地图入口表"


class TestCheckConsistency:
    """TST-2f: _check_consistency 一致性检查。"""

    def test_detects_residual_placeholder(self):
        """检测到残留 {{...}} 占位符。"""
        from harness.scripts.harness_deploy import _check_consistency
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "test.txt"), "w") as f:
                f.write("Run {{test_command}} to test")
            issues = _check_consistency(tmp)
            assert len(issues) > 0, "应检测到残留占位符"
            assert any("占位符" in i for i in issues), f"问题应提示残留占位符: {issues}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_detects_residual_zone_marker(self):
        """检测到残留 ADAPTABLE_ZONE 标记。"""
        from harness.scripts.harness_deploy import _check_consistency
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "agent.md"), "w") as f:
                f.write("<!-- ADAPTABLE_ZONE_START -->\ncontent\n<!-- ADAPTABLE_ZONE_END -->")
            issues = _check_consistency(tmp)
            assert len(issues) > 0, "应检测到残留适配标记"
            assert any("适配标记" in i for i in issues), f"问题应提示残留适配标记: {issues}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_clean_files_pass(self):
        """干净的文件通过一致性检查。"""
        from harness.scripts.harness_deploy import _check_consistency
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "clean.md"), "w") as f:
                f.write("# Clean file\nNo placeholders or zone markers.")
            with open(os.path.join(tmp, "config.yaml"), "w") as f:
                f.write("key: value\n")
            issues = _check_consistency(tmp)
            assert len(issues) == 0, f"干净文件不应有问题: {issues}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_only_checks_md_yaml_txt(self):
        """只检查 .md/.yaml/.txt 文件。"""
        from harness.scripts.harness_deploy import _check_consistency
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "script.py"), "w") as f:
                f.write("# {{placeholder}}")
            with open(os.path.join(tmp, "style.css"), "w") as f:
                f.write("/* {{placeholder}} */")
            issues = _check_consistency(tmp)
            assert len(issues) == 0, (
                f"非 .md/.yaml/.txt 文件不应被检查，实际 issues: {issues}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestAtomicWrite:
    """TST-2g: _atomic_write 原子写入。"""

    def test_atomic_write_creates_file(self):
        """_atomic_write 正确创建文件。"""
        from harness.scripts.harness_deploy import _atomic_write
        tmp = tempfile.mkdtemp()
        try:
            fpath = os.path.join(tmp, "output.txt")
            _atomic_write(fpath, "hello world")
            assert os.path.isfile(fpath), "文件应被创建"
            with open(fpath, "r", encoding="utf-8") as f:
                assert f.read() == "hello world"
            # tmp file should be removed after replace
            assert not os.path.exists(fpath + ".tmp"), "临时文件应被清理"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_atomic_write_overwrites_existing(self):
        """_atomic_write 正确覆盖已存在的文件。"""
        from harness.scripts.harness_deploy import _atomic_write
        tmp = tempfile.mkdtemp()
        try:
            fpath = os.path.join(tmp, "output.txt")
            with open(fpath, "w") as f:
                f.write("old content")
            _atomic_write(fpath, "new content")
            with open(fpath, "r", encoding="utf-8") as f:
                assert f.read() == "new content", "应覆盖为新内容"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_atomic_write_creates_parent_dirs(self):
        """_atomic_write 自动创建父目录。"""
        from harness.scripts.harness_deploy import _atomic_write
        tmp = tempfile.mkdtemp()
        try:
            fpath = os.path.join(tmp, "sub", "dir", "output.txt")
            _atomic_write(fpath, "deep content")
            assert os.path.isfile(fpath), "深层文件应被创建"
            with open(fpath, "r", encoding="utf-8") as f:
                assert f.read() == "deep content"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestTryFindEntryPoint:
    """TST-2h: _try_find_entry_point 入口文件检测。"""

    def test_finds_python_entry(self):
        """能找到 main.py 作为 Python 入口。"""
        from harness.scripts.harness_deploy import _try_find_entry_point
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "main.py"), "w") as f:
                f.write("print('hello')")
            result = _try_find_entry_point(tmp, ["python"])
            assert "main.py" in result, f"应找到 main.py，实际: {result}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_finds_go_entry(self):
        """能找到 main.go 作为 Go 入口。"""
        from harness.scripts.harness_deploy import _try_find_entry_point
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "main.go"), "w") as f:
                f.write("package main")
            result = _try_find_entry_point(tmp, ["go"])
            assert result == "main.go" or "main.go" in result, (
                f"应找到 main.go，实际: {result}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_returns_empty_for_no_match(self):
        """找不到入口文件时返回空字符串。"""
        from harness.scripts.harness_deploy import _try_find_entry_point
        tmp = tempfile.mkdtemp()
        try:
            result = _try_find_entry_point(tmp, ["python"])
            assert result == "", f"无入口文件时应返回空串，实际: {result}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestCollectDirectorySummary:
    """TST-2i: _collect_directory_summary 目录摘要收集。"""

    def test_returns_non_empty_for_populated_dir(self):
        """非空目录返回非空摘要。"""
        from harness.scripts.harness_deploy import _collect_directory_summary
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "README.md"), "w") as f:
                f.write("# test")
            summary = _collect_directory_summary(tmp)
            assert len(summary) > 0, "非空目录应返回非空摘要"
            assert "README.md" in summary, "摘要应包含文件列表"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_excludes_dot_dirs(self):
        """摘要排除 . 开头的目录。"""
        from harness.scripts.harness_deploy import _collect_directory_summary
        tmp = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmp, ".git"))
            os.makedirs(os.path.join(tmp, ".hidden_dir"))
            os.makedirs(os.path.join(tmp, "visible_dir"))
            summary = _collect_directory_summary(tmp)
            assert "visible_dir" in summary, "可见目录应出现在摘要中"
            assert ".git" not in summary, ".git 应被排除"
            assert ".hidden_dir" not in summary, ".hidden_dir 应被排除"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ============================================================
# TST-3: project.yaml 新增字段测试
# ============================================================


class TestProjectYamlNewFields:
    """TST-3: project.yaml 新增 domain/description/entry_point 字段（spec 功能 A 验收标准）。"""

    def test_project_yaml_has_domain(self):
        """project.yaml 包含 domain 字段。"""
        yaml_path = os.path.join(_PROJECT_ROOT, "harness", "config", "project.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "domain:" in content, f"project.yaml 缺少 domain 字段，内容:\n{content}"

    def test_project_yaml_has_description(self):
        """project.yaml 包含 description 字段。"""
        yaml_path = os.path.join(_PROJECT_ROOT, "harness", "config", "project.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "description:" in content, f"project.yaml 缺少 description 字段，内容:\n{content}"

    def test_project_yaml_has_entry_point(self):
        """project.yaml 包含 entry_point 字段。"""
        yaml_path = os.path.join(_PROJECT_ROOT, "harness", "config", "project.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "entry_point:" in content, f"project.yaml 缺少 entry_point 字段，内容:\n{content}"

    def test_domain_value_not_empty(self):
        """domain 字段值不为空。"""
        import yaml
        yaml_path = os.path.join(_PROJECT_ROOT, "harness", "config", "project.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "domain" in data, "domain 字段缺失"
        assert data["domain"] is not None, "domain 值不应为 None"
        assert len(str(data["domain"]).strip()) > 0, f"domain 值不应为空: {data['domain']}"

    def test_description_value_not_empty(self):
        """description 字段值不为空。"""
        import yaml
        yaml_path = os.path.join(_PROJECT_ROOT, "harness", "config", "project.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "description" in data, "description 字段缺失"
        assert data["description"] is not None, "description 值不应为 None"
        assert len(str(data["description"]).strip()) > 0, (
            f"description 值不应为空: {data['description']}"
        )

    def test_entry_point_value_not_empty(self):
        """entry_point 字段值不为空。"""
        import yaml
        yaml_path = os.path.join(_PROJECT_ROOT, "harness", "config", "project.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "entry_point" in data, "entry_point 字段缺失"
        assert data["entry_point"] is not None, "entry_point 值不应为 None"
        assert len(str(data["entry_point"]).strip()) > 0, (
            f"entry_point 值不应为空: {data['entry_point']}"
        )

    def test_yaml_structure_valid(self):
        """project.yaml YAML 结构有效（可被 yaml.safe_load 解析）。"""
        import yaml
        yaml_path = os.path.join(_PROJECT_ROOT, "harness", "config", "project.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None, "project.yaml 应可被解析为有效 YAML"
        assert isinstance(data, dict), "project.yaml 应解析为 dict"

    def test_all_fields_parsable(self):
        """project.yaml 所有字段都能正确解析。"""
        import yaml
        yaml_path = os.path.join(_PROJECT_ROOT, "harness", "config", "project.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        required = [
            "project_name", "version", "languages", "test_framework",
            "test_command", "package_manager", "validation_command",
            "domain", "description", "entry_point",
        ]
        for field in required:
            assert field in data, f"project.yaml 缺少字段: {field}"
