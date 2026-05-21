# test_export_report.py — 测试导出报告脚本

import os
import sys
import subprocess

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "harness", "scripts", "export_report.py",
)


def test_export_report_runs_and_returns_zero():
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 0


def test_export_report_contains_expected_sections():
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert "项目理解报告" in result.stdout
    assert "导出时间" in result.stdout
    assert "overview.md" in result.stdout
    assert "directory-map.md" in result.stdout
    assert "module-map.md" in result.stdout
    assert "change-map.md" in result.stdout


def test_export_report_sections_have_numbered_source_labels():
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 0
    assert "[1] " in result.stdout
    assert "---" in result.stdout
