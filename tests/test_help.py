# test_help.py — 测试帮助脚本

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


def test_help_lists_all_commands():
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert "help.py" in result.stdout
    assert "init_project.py" in result.stdout
    assert "check_structure.py" in result.stdout
    assert "search_notes.py" in result.stdout
    assert "export_report.py" in result.stdout
