# test_help.py — 测试帮助脚本 (TST-1: 验证 IMP-2 通用化)

import os
import sys
import subprocess

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "harness", "scripts", "help.py",
)


def test_help_runs_and_returns_zero():
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 0


def test_help_lists_all_expected_commands():
    """IMP-2: 验证 help 列出正确的命令列表，不含 check_structure.py 和 analyze_project.py。"""
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert "help.py" in result.stdout
    assert "init_project.py" in result.stdout
    assert "search_notes.py" in result.stdout
    assert "export_report.py" in result.stdout
    assert "generate_rule_evolution.py" in result.stdout
    assert "diagnose_and_fix.py" in result.stdout


def test_help_no_check_structure():
    """IMP-2: verify help output does NOT list check_structure.py."""
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert "check_structure.py" not in result.stdout, (
        f"help.py should not list check_structure.py, but output was:\n{result.stdout}"
    )


def test_help_no_analyze_project():
    """IMP-2: verify help output does NOT list analyze_project.py."""
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert "analyze_project.py" not in result.stdout, (
        f"help.py should not list analyze_project.py, but output was:\n{result.stdout}"
    )


def test_help_no_ai_project_notebook_hardcoded_in_source():
    """IMP-2/IMP-8: verify help.py SOURCE does not hardcode 'AI Project Notebook'.
    The name must come from project.yaml, not be a string literal in help.py."""
    with open(SCRIPT, "r", encoding="utf-8") as f:
        source = f.read()
    assert "AI Project Notebook" not in source, (
        "help.py should not contain hardcoded 'AI Project Notebook' string literal"
    )


def test_help_reads_version_from_project_yaml():
    """IMP-2: verify help.py reads version from project.yaml.
    The version string '0.9' should appear in output."""
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    # project.yaml version is "0.9", help should display it
    assert "0.9" in result.stdout, (
        f"help.py should display version '0.9' from project.yaml, but output was:\n{result.stdout}"
    )
