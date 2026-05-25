# feedback_engine.py — 反馈信号持久化引擎
"""FeedbackEngine：JSON 文件读写、去重、重复模式检测。"""

import json
import os
import tempfile
from typing import Optional

from harness.state.feedback_signal import FeedbackSignal

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FeedbackEngine:
    """管理反馈信号的持久化存储，支持去重和模式检测。"""

    def __init__(self, signals_file: Optional[str] = None):
        if signals_file is None:
            signals_file = os.path.join(_PROJECT_ROOT, "harness", "state", "feedback-signals.json")
        self.signals_file = signals_file
        self._signals: Optional[list[FeedbackSignal]] = None

    def load_signals(self) -> list[FeedbackSignal]:
        """从 JSON 文件加载所有信号，文件不存在返回空列表。"""
        if not os.path.exists(self.signals_file):
            return []
        try:
            with open(self.signals_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(data, list):
            return []
        return [FeedbackSignal.from_dict(item) for item in data]

    def add_signal(self, signal: FeedbackSignal) -> None:
        """添加信号，若 (signal_type, rule_ref) 已存在则累加 occurrences。"""
        signals = self.load_signals()
        for existing in signals:
            if existing.signal_type == signal.signal_type and existing.rule_ref == signal.rule_ref:
                existing.occurrences += signal.occurrences if signal.occurrences else 1
                existing.last_seen = signal.last_seen
                break
        else:
            signals.append(signal)
        self._signals = signals
        self._write_signals(signals)

    def save_signals(self) -> None:
        """将当前内存中的信号列表原子写入磁盘。"""
        if self._signals is None:
            self._signals = self.load_signals()
        self._write_signals(self._signals)

    def detect_patterns(self) -> list[dict]:
        """查找同一 rule_ref 出现 >= 3 次的重复模式。"""
        signals = self.load_signals()
        rule_counts: dict[str, dict] = {}
        for s in signals:
            key = s.rule_ref
            if key not in rule_counts:
                rule_counts[key] = {"rule_ref": key, "occurrences": 0, "severity": s.severity}
            rule_counts[key]["occurrences"] += s.occurrences
        return [
            info
            for info in rule_counts.values()
            if info["occurrences"] >= 3
        ]

    def _write_signals(self, signals: list[FeedbackSignal]) -> None:
        """原子写入：先写 .tmp 再 os.replace。"""
        os.makedirs(os.path.dirname(self.signals_file), exist_ok=True)
        tmp_path = self.signals_file + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump([s.to_dict() for s in signals], f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.signals_file)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    # 自测逻辑
    import tempfile

    tmp_dir = tempfile.mkdtemp()
    tmp_file = os.path.join(tmp_dir, "test-signals.json")
    try:
        engine = FeedbackEngine(signals_file=tmp_file)

        # 测试空加载
        assert engine.load_signals() == [], "空文件应返回空列表"

        # 测试添加信号
        s1 = FeedbackSignal(
            signal_type="rule_violation",
            severity="blocking",
            rule_ref="coding-rules.md#4",
            source="tester-failed",
        )
        engine.add_signal(s1)
        loaded = engine.load_signals()
        assert len(loaded) == 1, f"加载应为 1 个信号，实际 {len(loaded)}"
        assert loaded[0].occurrences == 1, "第一次信号出现次数应为 1"

        # 测试去重
        s2 = FeedbackSignal(
            signal_type="rule_violation",
            severity="blocking",
            rule_ref="coding-rules.md#4",
            source="explorer-blocked",
        )
        engine.add_signal(s2)
        loaded = engine.load_signals()
        assert len(loaded) == 1, f"去重后应为 1 个信号，实际 {len(loaded)}"
        assert loaded[0].occurrences == 2, f"去重后 occurrences 应为 2，实际 {loaded[0].occurrences}"

        # 测试不同 signal_type 不互串
        s3 = FeedbackSignal(
            signal_type="error",
            severity="non_blocking",
            rule_ref="coding-rules.md#4",
            source="tester-failed",
        )
        engine.add_signal(s3)
        loaded = engine.load_signals()
        assert len(loaded) == 2, f"不同 signal_type 应有 2 个独立信号，实际 {len(loaded)}"

        # s1+s2+s3 对同一 rule_ref 累计 3 次 occurrence，detect_patterns 应检出
        patterns = engine.detect_patterns()
        assert len(patterns) == 1, f"同一 rule_ref 累计 3 次应检出 1 个重复模式，实际 {patterns}"
        assert patterns[0]["occurrences"] >= 3, f"重复次数应 >= 3，实际 {patterns[0]['occurrences']}"

        print("All feedback_engine self-tests passed.")

    finally:
        # 清理
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        if os.path.exists(tmp_file + ".tmp"):
            os.remove(tmp_file + ".tmp")
        os.rmdir(tmp_dir)
