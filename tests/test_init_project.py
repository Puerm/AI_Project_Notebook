# test_init_project.py — 测试项目初始化脚本 (TST-2: 验证 IMP-5c + IMP-7)

import os
import sys
import subprocess
import tempfile
import shutil

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "harness", "scripts", "init_project.py",
)


def test_init_project_creates_harness_dir():
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0
        harness_dir = os.path.join(tmpdir, "harness")
        assert os.path.isdir(harness_dir)
        assert os.path.isdir(os.path.join(harness_dir, "rules"))
        assert os.path.isdir(os.path.join(harness_dir, "scripts"))
        assert os.path.isdir(os.path.join(harness_dir, "project-map"))
        assert os.path.isdir(os.path.join(harness_dir, "feedback"))
        assert os.path.isfile(os.path.join(harness_dir, "project-map", "directory-map.md"))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_project_generates_directory_map_with_tree():
    tmpdir = tempfile.mkdtemp()
    try:
        # 创建一些测试文件结构
        os.makedirs(os.path.join(tmpdir, "src", "utils"))
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("# test")

        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0

        dir_map_path = os.path.join(tmpdir, "harness", "project-map", "directory-map.md")
        with open(dir_map_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "README.md" in content
        assert "src/" in content
        assert "utils/" in content
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_project_refuses_existing_harness():
    tmpdir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmpdir, "harness"))
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_project_refuses_nonexistent_path():
    result = subprocess.run(
        [sys.executable, SCRIPT, "/nonexistent/path/xyz"], capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 1


def test_init_project_missing_argument_exits_one():
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 1


def test_init_project_scans_three_levels_deep():
    tmpdir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmpdir, "a", "b", "c"))
        with open(os.path.join(tmpdir, "a", "b", "deep.txt"), "w") as f:
            f.write("deep")

        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0

        dir_map_path = os.path.join(tmpdir, "harness", "project-map", "directory-map.md")
        with open(dir_map_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "a/" in content
        assert "b/" in content
        assert "c/" in content
        assert "deep.txt" in content
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ======== v0.2 新增测试 ========

EXPECTED_AGENTS = [
    "harness_maintainer.md", "pm.md", "planner.md", "explorer.md",
    "generator.md", "reviewer.md", "tester.md",
]

EXPECTED_WORKFLOW_COMMANDS = [
    "full-cycle.md", "implement.md", "quick-fix.md", "review-fix.md",
]


def test_init_project_does_not_deploy_itself():
    """TST-1: 验证目标项目 harness/scripts/ 下不含 init_project.py"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0
        init_py_path = os.path.join(tmpdir, "harness", "scripts", "init_project.py")
        assert not os.path.exists(init_py_path), (
            f"init_project.py 不应部署到目标项目，但仍存在于: {init_py_path}"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_deploys_claude_agents():
    """TST-2: 验证目标项目 .claude/agents/ 下存在全部 7 个 agent 文件"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0
        agents_dir = os.path.join(tmpdir, ".claude", "agents")
        assert os.path.isdir(agents_dir), f".claude/agents/ 目录缺失: {agents_dir}"
        for agent in EXPECTED_AGENTS:
            agent_path = os.path.join(agents_dir, agent)
            assert os.path.isfile(agent_path), f"agent 文件缺失: {agent_path}"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_deploys_claude_commands():
    """TST-3: 验证目标项目 .claude/commands/ 下含 pm/discuss.md 和 4 个 workflow 命令，不含 opsx/"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0
        commands_dir = os.path.join(tmpdir, ".claude", "commands")
        assert os.path.isdir(commands_dir), f".claude/commands/ 目录缺失: {commands_dir}"

        # 确认 pm/discuss.md 存在
        pm_discuss = os.path.join(commands_dir, "pm", "discuss.md")
        assert os.path.isfile(pm_discuss), f"pm/discuss.md 缺失: {pm_discuss}"

        # 确认 4 个 workflow 命令存在
        for cmd_file in EXPECTED_WORKFLOW_COMMANDS:
            cmd_path = os.path.join(commands_dir, "workflow", cmd_file)
            assert os.path.isfile(cmd_path), f"workflow 命令缺失: {cmd_path}"

        # 确认 opsx/ 不存在
        opsx_dir = os.path.join(commands_dir, "opsx")
        assert not os.path.exists(opsx_dir), (
            f"opsx/ 不应部署到目标项目，但仍存在于: {opsx_dir}"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_creates_empty_claude_skills():
    """TST-4: 验证目标项目 .claude/skills/ 存在且为空目录"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0
        skills_dir = os.path.join(tmpdir, ".claude", "skills")
        assert os.path.isdir(skills_dir), f".claude/skills/ 目录缺失: {skills_dir}"
        assert len(os.listdir(skills_dir)) == 0, (
            f".claude/skills/ 应为空目录，但包含: {os.listdir(skills_dir)}"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_deployed_project_passes_check_structure():
    """TST-5: 对部署后的目标项目运行 check_structure.py，验证返回 PASS"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, f"init_project 失败: {result.stderr}"

        check_script = os.path.join(tmpdir, "harness", "scripts", "check_structure.py")
        assert os.path.isfile(check_script), f"check_structure.py 缺失: {check_script}"

        result = subprocess.run(
            [sys.executable, check_script], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, (
            f"check_structure.py 应返回 PASS (0)，实际返回 {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ======== TST-2: IMP-7 project.yaml 部署和模板填充测试 ========

def test_init_deployed_project_has_project_yaml():
    """IMP-7: 部署后目标项目包含 harness/config/project.yaml。"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, f"init_project 失败: {result.stderr}"

        yaml_path = os.path.join(tmpdir, "harness", "config", "project.yaml")
        assert os.path.isfile(yaml_path), (
            f"project.yaml 缺失: {yaml_path}"
        )
        # 验证文件有内容
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "project_name:" in content
        assert "version:" in content
        assert "languages:" in content
        assert "test_command:" in content
        assert "package_manager:" in content
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_deployed_harness_rules_templates_filled():
    """IMP-7: 部署后 harness/rules/coding-rules.md 中的 {{test_command}} 已被替换。
    _fill_templates 的范围是 harness/ 目录。"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, f"init_project 失败: {result.stderr}"

        # 检查 harness/rules/coding-rules.md 中不应有 {{test_command}}
        cr_path = os.path.join(tmpdir, "harness", "rules", "coding-rules.md")
        assert os.path.isfile(cr_path), f"coding-rules.md 缺失: {cr_path}"
        with open(cr_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "{{test_command}}" not in content, (
            "harness/rules/coding-rules.md 中的 {{test_command}} 应已被替换为实际测试命令"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_deployed_claude_agents_filled():
    """修复验证: _fill_templates 现在遍历 harness/ 和 .claude/ 两个目录。
    部署后 .claude/agents/tester.md 中的 {{test_command}} 应已被替换。"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, f"init_project 失败: {result.stderr}"

        tester_path = os.path.join(tmpdir, ".claude", "agents", "tester.md")
        with open(tester_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "{{test_command}}" not in content, (
            ".claude/agents/tester.md 中的 {{test_command}} 应已被替换为实际测试命令。"
            f"当前内容包含占位符未填充。"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_deployed_generator_filled():
    """修复验证: .claude/agents/generator.md 中的 {{test_command}} 应已被填充。"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, f"init_project 失败: {result.stderr}"

        generator_path = os.path.join(tmpdir, ".claude", "agents", "generator.md")
        with open(generator_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "{{test_command}}" not in content, (
            ".claude/agents/generator.md 中的 {{test_command}} 应已被替换为实际测试命令。"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_deployed_tester_filled():
    """修复验证: .claude/agents/tester.md 中的 {{test_command}} 应已被填充。"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, f"init_project 失败: {result.stderr}"

        tester_path = os.path.join(tmpdir, ".claude", "agents", "tester.md")
        with open(tester_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "{{test_command}}" not in content, (
            ".claude/agents/tester.md 中的 {{test_command}} 应已被替换为实际测试命令。"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_deployed_no_app_analyzer_dir():
    """IMP-5c: 部署后目标项目不创建 app/analyzer/ 目录。"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, f"init_project 失败: {result.stderr}"

        # init_project.py 不应在目标项目中创建 app/analyzer/
        # app/analyzer/ 是 Notebook 自身的应用代码目录
        app_dir = os.path.join(tmpdir, "app")
        assert not os.path.exists(app_dir), (
            f"init_project.py 不应创建 app/ 目录，目标项目中发现: {app_dir}"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_command_map_no_check_structure():
    """IMP-5c: 部署后的 command-map.md 不含 check_structure.py 条目。"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, f"init_project 失败: {result.stderr}"

        cm_path = os.path.join(tmpdir, "harness", "project-map", "command-map.md")
        with open(cm_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "check_structure.py" not in content, (
            "deployed command-map.md should not reference check_structure.py"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_init_command_map_no_analyze_project():
    """IMP-5c: 部署后的 command-map.md 不含 analyze_project.py 条目。"""
    tmpdir = tempfile.mkdtemp()
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, tmpdir], capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, f"init_project 失败: {result.stderr}"

        cm_path = os.path.join(tmpdir, "harness", "project-map", "command-map.md")
        with open(cm_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "analyze_project.py" not in content, (
            "deployed command-map.md should not reference analyze_project.py"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
