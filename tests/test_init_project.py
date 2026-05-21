# test_init_project.py — 测试项目初始化脚本

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
