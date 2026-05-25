# test_generate_rule_evolution.py — 规则演化建议脚本测试 (TST-4)
"""测试 generate_rule_evolution.py 的无模式/有模式/追加行为。"""

import os
import sys
import json
import tempfile
import shutil
import io
from unittest.mock import patch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from harness.state.feedback_engine import FeedbackEngine
from harness.state.feedback_signal import FeedbackSignal
from harness.scripts.generate_rule_evolution import main, _project_path


def _make_signal(**kwargs):
    """快捷构造 FeedbackSignal，提供合理的默认值。"""
    defaults = {
        "signal_type": "rule_violation",
        "severity": "blocking",
        "rule_ref": "test-rule.md#1",
        "source": "test",
    }
    defaults.update(kwargs)
    return FeedbackSignal(**defaults)


class TestGenerateRuleEvolutionNoPatterns:
    """测试无重复模式时的脚本行为。"""

    def test_no_patterns_prints_message(self):
        """无重复模式时 stdout 输出 'No repeated patterns detected.'。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            engine = FeedbackEngine(signals_file=signals_file)
            # 不添加任何信号 → detect_patterns() 返回 []

            stdout_capture = io.StringIO()

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                with patch.object(sys, "stdout", stdout_capture):
                    # main() 直接执行，无异常
                    main()

            output = stdout_capture.getvalue()
            assert "No repeated patterns detected." in output
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_patterns_exits_zero(self):
        """无重复模式时脚本不抛异常（退出码 0）。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                # 应正常完成，不抛异常
                main()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_patterns_does_not_create_proposal_file(self):
        """无重复模式时不创建 proposal 文件。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            proposal_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(proposal_dir, exist_ok=True)
            proposal_path = os.path.join(proposal_dir, "rule-evolution-proposal.md")

            engine = FeedbackEngine(signals_file=signals_file)

            def _fake_project_path(rel):
                return os.path.join(tmp, rel)

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                with patch(
                    "harness.scripts.generate_rule_evolution._project_path",
                    side_effect=_fake_project_path,
                ):
                    main()

            # proposal 文件不应该被创建（没有重复模式）
            assert not os.path.exists(proposal_path), (
                f"no patterns 时不应创建 proposal 文件: {proposal_path}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestGenerateRuleEvolutionWithPatterns:
    """测试存在重复模式时生成 proposal 文件。"""

    def test_generates_proposal_when_pattern_exists(self):
        """存在 >=3 次重复模式时生成 rule-evolution-proposal.md。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            proposal_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(proposal_dir, exist_ok=True)
            proposal_path = os.path.join(proposal_dir, "rule-evolution-proposal.md")

            engine = FeedbackEngine(signals_file=signals_file)
            # 添加 3 次同一 rule_ref 触发重复模式
            for _ in range(3):
                engine.add_signal(_make_signal(rule_ref="coding-rules.md#4"))

            def _fake_project_path(rel):
                return os.path.join(tmp, rel)

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                with patch(
                    "harness.scripts.generate_rule_evolution._project_path",
                    side_effect=_fake_project_path,
                ):
                    main()

            # 验证 proposal 文件已创建
            assert os.path.exists(proposal_path), (
                f"应生成 proposal 文件: {proposal_path}"
            )

            with open(proposal_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 包含生成时间戳
            assert "生成时间" in content or "自动生成" in content
            # 包含变更理由
            assert "变更理由" in content
            # 包含支持证据
            assert "支持证据" in content
            # 包含状态标记 "待确认"
            assert "待确认" in content
            # 包含规则引用
            assert "coding-rules.md#4" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_proposal_contains_correct_pattern_count(self):
        """proposal 中包含正确的出现次数。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            proposal_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(proposal_dir, exist_ok=True)
            proposal_path = os.path.join(proposal_dir, "rule-evolution-proposal.md")

            engine = FeedbackEngine(signals_file=signals_file)
            for _ in range(5):
                engine.add_signal(
                    _make_signal(rule_ref="workflow-rules.md#3", severity="non_blocking")
                )

            def _fake_project_path(rel):
                return os.path.join(tmp, rel)

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                with patch(
                    "harness.scripts.generate_rule_evolution._project_path",
                    side_effect=_fake_project_path,
                ):
                    main()

            with open(proposal_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "5 次" in content, f"应包含 5 次，内容: {content[:500]}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_script_exits_zero_even_with_patterns(self):
        """存在重复模式时脚本正常完成（退出码 0）。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            proposal_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(proposal_dir, exist_ok=True)

            engine = FeedbackEngine(signals_file=signals_file)
            for _ in range(3):
                engine.add_signal(_make_signal(rule_ref="rule.md#1"))

            def _fake_project_path(rel):
                return os.path.join(tmp, rel)

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                with patch(
                    "harness.scripts.generate_rule_evolution._project_path",
                    side_effect=_fake_project_path,
                ):
                    # 应正常完成不抛异常
                    main()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_stdout_message_when_patterns_generated(self):
        """生成 proposal 时 stdout 输出成功信息。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            proposal_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(proposal_dir, exist_ok=True)

            engine = FeedbackEngine(signals_file=signals_file)
            for _ in range(4):
                engine.add_signal(_make_signal(rule_ref="coding-rules.md#4"))

            stdout_capture = io.StringIO()

            def _fake_project_path(rel):
                return os.path.join(tmp, rel)

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                with patch(
                    "harness.scripts.generate_rule_evolution._project_path",
                    side_effect=_fake_project_path,
                ):
                    with patch.object(sys, "stdout", stdout_capture):
                        main()

            output = stdout_capture.getvalue()
            assert "Generated" in output
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestGenerateRuleEvolutionAppend:
    """测试已有 proposal 时的追加行为。"""

    def test_existing_pattern_not_duplicated(self):
        """已有 proposal 中的 pattern 不重复生成。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            proposal_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(proposal_dir, exist_ok=True)
            proposal_path = os.path.join(proposal_dir, "rule-evolution-proposal.md")

            # 创建已有 proposal 文件，包含 rule-a 的建议
            existing_content = (
                "# 规则演化建议\n\n"
                "> 自动生成于 2026-05-25T00:00:00+00:00\n\n"
                "---\n\n"
                "## 建议 1: `rule-a.md#1` -- 重复模式 (3 次)\n\n"
                "> 生成时间: 2026-05-25T00:00:00+00:00\n"
                "> 状态: 待确认\n\n"
                "**变更理由**: 旧建议\n\n"
            )
            with open(proposal_path, "w", encoding="utf-8") as f:
                f.write(existing_content)

            # 创建 engine：rule-a 3 次（已有）+ rule-b 4 次（新增）
            engine = FeedbackEngine(signals_file=signals_file)
            for _ in range(3):
                engine.add_signal(_make_signal(rule_ref="rule-a.md#1"))
            for _ in range(4):
                engine.add_signal(_make_signal(rule_ref="rule-b.md#2"))

            def _fake_project_path(rel):
                return os.path.join(tmp, rel)

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                with patch(
                    "harness.scripts.generate_rule_evolution._project_path",
                    side_effect=_fake_project_path,
                ):
                    main()

            with open(proposal_path, "r", encoding="utf-8") as f:
                content = f.read()

            # rule-a 只出现一次（原有）
            assert content.count("rule-a.md#1") == 1, (
                f"已有 pattern rule-a 不应重复，出现次数: {content.count('rule-a.md#1')}"
            )
            # rule-b 出现（新增）
            assert "rule-b.md#2" in content, "新 pattern rule-b 应被追加"
            # 包含分隔线
            assert "---" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_duplicate_when_all_existing(self):
        """所有 pattern 都已存在时不生成重复建议。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            proposal_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(proposal_dir, exist_ok=True)
            proposal_path = os.path.join(proposal_dir, "rule-evolution-proposal.md")

            existing_content = (
                "# 规则演化建议\n\n"
                "> 自动生成于 2026-05-25T00:00:00+00:00\n\n"
                "---\n\n"
                "## 建议 1: `rule-x.md#1` -- 重复模式 (3 次)\n\n"
                "> 生成时间: 2026-05-25T00:00:00+00:00\n"
                "> 状态: 待确认\n\n"
            )
            with open(proposal_path, "w", encoding="utf-8") as f:
                f.write(existing_content)

            engine = FeedbackEngine(signals_file=signals_file)
            for _ in range(3):
                engine.add_signal(_make_signal(rule_ref="rule-x.md#1"))

            stdout_capture = io.StringIO()

            def _fake_project_path(rel):
                return os.path.join(tmp, rel)

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                with patch(
                    "harness.scripts.generate_rule_evolution._project_path",
                    side_effect=_fake_project_path,
                ):
                    with patch.object(sys, "stdout", stdout_capture):
                        main()

            output = stdout_capture.getvalue()
            assert "No new repeated patterns" in output

            with open(proposal_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 只出现一次 rule-x
            assert content.count("rule-x.md#1") == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_new_pattern_appended_after_separator(self):
        """新 pattern 通过分隔线追加到文件末尾。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "feedback-signals.json")
            proposal_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(proposal_dir, exist_ok=True)
            proposal_path = os.path.join(proposal_dir, "rule-evolution-proposal.md")

            existing_content = "## 建议 1: `old-rule.md#1` -- 重复模式 (3 次)\n"
            with open(proposal_path, "w", encoding="utf-8") as f:
                f.write(existing_content)

            engine = FeedbackEngine(signals_file=signals_file)
            for _ in range(3):
                engine.add_signal(_make_signal(rule_ref="new-rule.md#5"))

            def _fake_project_path(rel):
                return os.path.join(tmp, rel)

            with patch(
                "harness.state.feedback_engine.FeedbackEngine",
                return_value=engine,
            ):
                with patch(
                    "harness.scripts.generate_rule_evolution._project_path",
                    side_effect=_fake_project_path,
                ):
                    main()

            with open(proposal_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 原内容保留
            assert "old-rule.md#1" in content
            # 新内容追加
            assert "new-rule.md#5" in content
            # 新内容在原内容之后
            old_pos = content.index("old-rule.md#1")
            new_pos = content.index("new-rule.md#5")
            assert new_pos > old_pos, "新 pattern 应在原有内容之后追加"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
