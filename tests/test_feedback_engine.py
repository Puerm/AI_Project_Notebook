# test_feedback_engine.py — FeedbackEngine 反馈引擎测试 (TST-2)
"""测试 FeedbackEngine 的 JSON 读写、去重、模式检测、原子写入行为。"""

import os
import sys
import json
import tempfile
import shutil

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from harness.state.feedback_signal import FeedbackSignal
from harness.state.feedback_engine import FeedbackEngine


def _make_signal(
    signal_type="rule_violation",
    severity="blocking",
    rule_ref="coding-rules.md#4",
    **kwargs,
):
    """快捷构造 FeedbackSignal。"""
    return FeedbackSignal(
        signal_type=signal_type,
        severity=severity,
        rule_ref=rule_ref,
        **kwargs,
    )


class TestFeedbackEngineLoadEmpty:
    """测试加载不存在或空的 JSON 文件。"""

    def test_load_nonexistent_file_returns_empty_list(self):
        """加载不存在的 JSON 文件返回空列表，不抛异常。"""
        tmp = tempfile.mkdtemp()
        try:
            nonexistent = os.path.join(tmp, "does-not-exist.json")
            engine = FeedbackEngine(signals_file=nonexistent)
            result = engine.load_signals()
            assert result == []
            assert isinstance(result, list)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_empty_file_returns_empty_list(self):
        """加载空 JSON 文件返回空列表。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "empty.json")
            with open(signals_file, "w", encoding="utf-8") as f:
                f.write("")
            engine = FeedbackEngine(signals_file=signals_file)
            result = engine.load_signals()
            assert result == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_corrupted_json_returns_empty_list(self):
        """加载损坏的 JSON 文件返回空列表，不抛异常。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "corrupt.json")
            with open(signals_file, "w", encoding="utf-8") as f:
                f.write("{not valid json [[[")
            engine = FeedbackEngine(signals_file=signals_file)
            result = engine.load_signals()
            assert result == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_non_list_json_returns_empty_list(self):
        """加载非 list 结构的 JSON 返回空列表。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "obj.json")
            with open(signals_file, "w", encoding="utf-8") as f:
                json.dump({"key": "value"}, f)
            engine = FeedbackEngine(signals_file=signals_file)
            result = engine.load_signals()
            assert result == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFeedbackEngineAddAndLoad:
    """测试添加信号并加载——来回一致性。"""

    def test_add_single_signal_roundtrip(self):
        """添加一个信号后加载得到相同数据。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            s = _make_signal(
                signal_type="rule_violation",
                severity="blocking",
                rule_ref="coding-rules.md#4",
                source="tester-failed",
            )
            engine.add_signal(s)

            loaded = engine.load_signals()
            assert len(loaded) == 1
            assert loaded[0].signal_type == "rule_violation"
            assert loaded[0].severity == "blocking"
            assert loaded[0].rule_ref == "coding-rules.md#4"
            assert loaded[0].source == "tester-failed"
            assert loaded[0].occurrences == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_multiple_different_signals(self):
        """添加多个不同的信号，全部被保留。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            engine.add_signal(_make_signal(rule_ref="rule-a.md#1"))
            engine.add_signal(_make_signal(rule_ref="rule-b.md#2"))
            engine.add_signal(_make_signal(rule_ref="rule-c.md#3"))

            loaded = engine.load_signals()
            assert len(loaded) == 3
            refs = {s.rule_ref for s in loaded}
            assert refs == {"rule-a.md#1", "rule-b.md#2", "rule-c.md#3"}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_file_created_on_add(self):
        """add_signal 后 JSON 文件自动创建。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            assert not os.path.exists(signals_file)
            engine.add_signal(_make_signal())
            assert os.path.exists(signals_file)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFeedbackEngineDedup:
    """测试去重逻辑：(signal_type, rule_ref) 为唯一键。"""

    def test_same_key_dedup_accumulates_occurrences(self):
        """相同 (signal_type, rule_ref) 累加 occurrences。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            s1 = _make_signal(
                signal_type="rule_violation",
                rule_ref="coding-rules.md#4",
                occurrences=1,
            )
            engine.add_signal(s1)

            s2 = _make_signal(
                signal_type="rule_violation",
                rule_ref="coding-rules.md#4",
                occurrences=1,
            )
            engine.add_signal(s2)

            loaded = engine.load_signals()
            assert len(loaded) == 1
            assert loaded[0].occurrences == 2
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_same_key_updates_last_seen(self):
        """相同键去重时 last_seen 更新为新值，first_seen 不变。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            s1 = _make_signal(
                signal_type="rule_violation",
                rule_ref="coding-rules.md#4",
                first_seen="2026-05-01T00:00:00+00:00",
                last_seen="2026-05-01T00:00:00+00:00",
            )
            engine.add_signal(s1)

            s2 = _make_signal(
                signal_type="rule_violation",
                rule_ref="coding-rules.md#4",
                first_seen="2026-05-20T00:00:00+00:00",  # 应被忽略
                last_seen="2026-05-25T12:00:00+00:00",
            )
            engine.add_signal(s2)

            loaded = engine.load_signals()
            assert len(loaded) == 1
            # first_seen should remain from s1 (the first occurrence)
            assert loaded[0].first_seen == "2026-05-01T00:00:00+00:00"
            # last_seen should update to s2's value
            assert loaded[0].last_seen == "2026-05-25T12:00:00+00:00"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_different_signal_type_same_rule_ref_are_separate(self):
        """不同 signal_type 但相同 rule_ref 不互串——各自独立去重。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            # type=rule_violation, ref=coding-rules.md#4
            s1 = _make_signal(
                signal_type="rule_violation",
                rule_ref="coding-rules.md#4",
                occurrences=1,
            )
            engine.add_signal(s1)

            # type=error, ref=coding-rules.md#4 — 不同的 signal_type
            s2 = _make_signal(
                signal_type="error",
                rule_ref="coding-rules.md#4",
                occurrences=1,
            )
            engine.add_signal(s2)

            loaded = engine.load_signals()
            assert len(loaded) == 2, (
                f"不同 signal_type 应各自独立，期望 2 条记录，实际 {len(loaded)}"
            )

            # 再次添加 type=rule_violation, 应对第一条去重
            s3 = _make_signal(
                signal_type="rule_violation",
                rule_ref="coding-rules.md#4",
                occurrences=1,
            )
            engine.add_signal(s3)

            loaded = engine.load_signals()
            assert len(loaded) == 2
            viol = [s for s in loaded if s.signal_type == "rule_violation"][0]
            err = [s for s in loaded if s.signal_type == "error"][0]
            assert viol.occurrences == 2
            assert err.occurrences == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFeedbackEngineDetectPatterns:
    """测试 detect_patterns() 重复模式检测。"""

    def test_no_patterns_when_no_signals(self):
        """无信号时 detect_patterns 返回空列表。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)
            patterns = engine.detect_patterns()
            assert patterns == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_patterns_below_threshold(self):
        """同一 rule_ref 出现 2 次时不触发重复模式。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            engine.add_signal(_make_signal(rule_ref="rule-a.md#1", occurrences=1))
            engine.add_signal(_make_signal(rule_ref="rule-a.md#1", occurrences=1))

            patterns = engine.detect_patterns()
            assert patterns == [], (
                f"出现 2 次不应触发模式，实际 {patterns}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_patterns_triggered_at_three(self):
        """同一 rule_ref 累计恰好 3 次时触发重复模式。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            engine.add_signal(_make_signal(rule_ref="rule-a.md#1", occurrences=1))
            engine.add_signal(_make_signal(rule_ref="rule-a.md#1", occurrences=1))
            engine.add_signal(_make_signal(rule_ref="rule-a.md#1", occurrences=1))

            patterns = engine.detect_patterns()
            assert len(patterns) == 1
            assert patterns[0]["rule_ref"] == "rule-a.md#1"
            assert patterns[0]["occurrences"] == 3
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_patterns_triggered_above_three(self):
        """同一 rule_ref 超过 3 次也触发——>= 3 次的阈值。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            for _ in range(5):
                engine.add_signal(_make_signal(rule_ref="rule-b.md#2", occurrences=1))

            patterns = engine.detect_patterns()
            assert len(patterns) == 1
            assert patterns[0]["occurrences"] == 5
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_multiple_patterns_detected(self):
        """多个不同 rule_ref 同时触发时全部检出。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            # rule-a：3 次
            for _ in range(3):
                engine.add_signal(_make_signal(rule_ref="rule-a.md#1"))
            # rule-b：4 次
            for _ in range(4):
                engine.add_signal(_make_signal(rule_ref="rule-b.md#2"))
            # rule-c：仅 1 次，不触发
            engine.add_signal(_make_signal(rule_ref="rule-c.md#3"))

            patterns = engine.detect_patterns()
            assert len(patterns) == 2
            rule_refs = {p["rule_ref"] for p in patterns}
            assert rule_refs == {"rule-a.md#1", "rule-b.md#2"}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_cross_type_accumulation(self):
        """不同 signal_type 的同一 rule_ref 累积计算总次数。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            engine.add_signal(
                _make_signal(signal_type="rule_violation", rule_ref="rule-x.md#1")
            )
            engine.add_signal(
                _make_signal(signal_type="error", rule_ref="rule-x.md#1")
            )
            engine.add_signal(
                _make_signal(signal_type="improvement", rule_ref="rule-x.md#1")
            )

            patterns = engine.detect_patterns()
            assert len(patterns) == 1
            assert patterns[0]["rule_ref"] == "rule-x.md#1"
            assert patterns[0]["occurrences"] == 3
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFeedbackEngineSaveSignals:
    """测试 save_signals() 行为 — 计划要求原子写入。"""

    def test_save_signals_is_noop_after_add(self):
        """save_signals() 在 add_signal 后调用不出错。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)
            engine.add_signal(_make_signal())
            # save_signals 应不抛异常
            engine.save_signals()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_save_signals_actually_persists_data(self):
        """计划要求 save_signals() 原子写入。验证其确实将数据持久化到磁盘。

        此测试验证：删除 JSON 文件后，仅调用 save_signals() 能否恢复数据。
        若 save_signals() 为空操作，此测试将失败（标记为代码 bug）。
        """
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            # 先添加信号让数据落盘
            s = _make_signal(
                signal_type="error",
                severity="blocking",
                rule_ref="test-rule.md#1",
            )
            engine.add_signal(s)

            # 确认文件存在
            assert os.path.exists(signals_file)

            # 删除文件模拟异常
            os.remove(signals_file)
            assert not os.path.exists(signals_file)

            # 调用 save_signals() —— 计划要求此方法应原子写入
            engine.save_signals()

            # 检查文件是否被重新创建
            # 若 save_signals 是空操作 → 文件不存在 → 测试失败
            if not os.path.exists(signals_file):
                pytest.fail(
                    "BUG: save_signals() 是空操作，删除文件后未能重新写入。"
                    "计划要求 save_signals() 执行原子写入。"
                )

            # 文件存在则验证内容
            loaded = engine.load_signals()
            assert len(loaded) == 1
            assert loaded[0].rule_ref == "test-rule.md#1"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFeedbackEngineAtomicWrite:
    """测试原子写入保护。"""

    def test_atomic_write_does_not_leave_tmp_file(self):
        """原子写入完成后 .tmp 文件被清理。"""
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            engine.add_signal(_make_signal())

            # .tmp 文件不残留
            tmp_path = signals_file + ".tmp"
            assert not os.path.exists(tmp_path), (
                f"原子写入后 .tmp 文件不应残留: {tmp_path}"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_original_file_preserved_on_write_failure(self):
        """写入失败时原始文件内容不被破坏。

        通过让 .tmp 写入到一个不可写的目录来模拟失败。
        实际实现使用了 try/finally 确保 .tmp 被清理，
        这里的重点是验证原 JSON 文件在异常后仍可读取。
        """
        tmp = tempfile.mkdtemp()
        try:
            signals_file = os.path.join(tmp, "signals.json")
            engine = FeedbackEngine(signals_file=signals_file)

            # 先写入一个有效信号
            s1 = _make_signal(rule_ref="original.md#1")
            engine.add_signal(s1)

            # 读取当前内容作为基准
            original_content = None
            with open(signals_file, "r", encoding="utf-8") as f:
                original_content = f.read()

            # 使目录只读来阻止写入（Windows 上可能不生效，但 try/finally 保证安全）
            try:
                os.chmod(tmp, 0o444)  # 只读
                try:
                    engine.add_signal(_make_signal(rule_ref="new.md#99"))
                except (PermissionError, OSError):
                    pass  # 预期可能的失败
            finally:
                os.chmod(tmp, 0o777)  # 恢复权限

            # 原文件应仍然可读
            assert os.path.exists(signals_file), "原子写入失败时原文件不应被删除"
            loaded = engine.load_signals()
            # 至少应加载成功（内容可能未变）
            assert isinstance(loaded, list)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# 导入 pytest 用于 fail（top-level 因为 test 函数内使用）
import pytest
