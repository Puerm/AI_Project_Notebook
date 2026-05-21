# test_search_notes.py — 测试搜索笔记脚本

import os
import sys
import subprocess

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "harness", "scripts", "search_notes.py",
)


def test_search_finds_matches():
    result = subprocess.run(
        [sys.executable, SCRIPT, "模块"], capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 0
    assert len(result.stdout.strip()) > 0


def test_search_no_match_shows_nothing():
    result = subprocess.run(
        [sys.executable, SCRIPT, "xyznonexistent12345"], capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 0
    assert "无匹配" in result.stdout


def test_search_missing_argument_exits_one():
    result = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 1


def test_search_output_format_contains_filename_colon_lineno():
    result = subprocess.run(
        [sys.executable, SCRIPT, "模块"], capture_output=True, encoding="utf-8"
    )
    assert result.returncode == 0
    for line in result.stdout.strip().split("\n"):
        if not line or line.startswith("("):
            continue
        assert ": " in line
        path_part, _, _ = line.partition(": ")
        assert "/" in path_part or "\\" in path_part
