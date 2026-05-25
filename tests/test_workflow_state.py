# test_workflow_state.py — WorkflowState 工作流状态测试 (TST-3)
"""测试 WorkflowState 的状态管理、偏差趋势判断、回环决策、反馈信号转换。"""

import os
import sys
import json
import tempfile
import shutil

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from harness.state.workflow_state import WorkflowState
from harness.state.feedback_signal import FeedbackSignal


class TestWorkflowStateInit:
    """测试 WorkflowState.init() 初始化。"""

    def test_init_creates_correct_structure(self):
        """init() 创建包含 topic 和 stages 字段的正确初始状态。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test-feature", ["explorer", "tester"])

            assert os.path.exists(tmp_file)
            with open(tmp_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            assert state["topic"] == "test-feature"
            assert "started_at" in state
            assert "explorer" in state["stages"]
            assert "tester" in state["stages"]
            assert state["stages"]["explorer"]["iterations"] == 0
            assert state["stages"]["explorer"]["history"] == []
            assert state["stages"]["tester"]["iterations"] == 0
            assert state["stages"]["tester"]["history"] == []
        finally:
            _restore_state_file()

    def test_init_repeated_overwrites_old_state(self):
        """重复调用 init() 覆盖旧状态（全新 topic 和空 history）。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            # 第一次 init
            WorkflowState.init("old-topic", ["explorer"])
            # 添加一些记录
            WorkflowState.record_stage("explorer", 3, "blocked")

            # 第二次 init — 应完全覆盖
            WorkflowState.init("new-topic", ["tester"])

            with open(tmp_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            assert state["topic"] == "new-topic"
            assert "explorer" not in state["stages"]
            assert "tester" in state["stages"]
            assert state["stages"]["tester"]["iterations"] == 0
            assert state["stages"]["tester"]["history"] == []
        finally:
            _restore_state_file()

    def test_init_with_custom_stages(self):
        """init() 支持任意 stages 列表，不硬编码特定 stage id。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("custom-workflow", ["build", "test", "deploy"])

            with open(tmp_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            assert list(state["stages"].keys()) == ["build", "test", "deploy"]
            assert state["stages"]["build"]["iterations"] == 0
            assert state["stages"]["test"]["iterations"] == 0
            assert state["stages"]["deploy"]["iterations"] == 0
        finally:
            _restore_state_file()


class TestWorkflowStateRecordStage:
    """测试 record_stage() 阶段记录。"""

    def test_record_stage_appends_history(self):
        """record_stage() 追加历史记录并递增迭代计数。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("explorer", 5, "blocked")

            with open(tmp_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            stage = state["stages"]["explorer"]
            assert stage["iterations"] == 1
            assert len(stage["history"]) == 1
            assert stage["history"][0]["deviation_count"] == 5
            assert stage["history"][0]["status"] == "blocked"
            assert "timestamp" in stage["history"][0]
        finally:
            _restore_state_file()

    def test_record_stage_increments_iterations(self):
        """多次 record_stage() 正确递增迭代计数。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["tester"])
            WorkflowState.record_stage("tester", 10, "blocked")
            WorkflowState.record_stage("tester", 7, "blocked")
            WorkflowState.record_stage("tester", 3, "blocked")

            with open(tmp_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            stage = state["stages"]["tester"]
            assert stage["iterations"] == 3
            assert len(stage["history"]) == 3
            assert stage["history"][0]["deviation_count"] == 10
            assert stage["history"][1]["deviation_count"] == 7
            assert stage["history"][2]["deviation_count"] == 3
        finally:
            _restore_state_file()

    def test_record_stage_for_uninitialized_stage(self):
        """record_stage() 对未在 init 中声明的 stage 自动初始化。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("unexpected_stage", 2, "ok")

            with open(tmp_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            assert "unexpected_stage" in state["stages"]
            assert state["stages"]["unexpected_stage"]["iterations"] == 1
        finally:
            _restore_state_file()


class TestWorkflowStateDeviationTrend:
    """测试 get_deviation_trend() 偏差趋势分析。"""

    def test_first_record_returns_first_iteration(self):
        """仅一次记录时返回 first_iteration。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("explorer", 5, "blocked")
            trend = WorkflowState.get_deviation_trend("explorer")
            assert trend == "first_iteration"
        finally:
            _restore_state_file()

    def test_shrinking_when_deviation_decreases(self):
        """偏差减小时返回 shrinking。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("explorer", 10, "blocked")
            WorkflowState.record_stage("explorer", 5, "blocked")
            trend = WorkflowState.get_deviation_trend("explorer")
            assert trend == "shrinking", f"期望 shrinking，实际 {trend}"
        finally:
            _restore_state_file()

    def test_stable_when_deviation_unchanged(self):
        """偏差不变时返回 stable。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["tester"])
            WorkflowState.record_stage("tester", 7, "blocked")
            WorkflowState.record_stage("tester", 7, "blocked")
            trend = WorkflowState.get_deviation_trend("tester")
            assert trend == "stable", f"期望 stable，实际 {trend}"
        finally:
            _restore_state_file()

    def test_growing_when_deviation_increases(self):
        """偏差增加时返回 growing。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("explorer", 2, "blocked")
            WorkflowState.record_stage("explorer", 8, "blocked")
            trend = WorkflowState.get_deviation_trend("explorer")
            assert trend == "growing", f"期望 growing，实际 {trend}"
        finally:
            _restore_state_file()

    def test_trend_for_nonexistent_stage(self):
        """不存在的 stage 返回 first_iteration。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            trend = WorkflowState.get_deviation_trend("nonexistent")
            assert trend == "first_iteration"
        finally:
            _restore_state_file()

    def test_trend_zero_to_zero_is_stable(self):
        """偏差从 0 到 0 视为 stable。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["tester"])
            WorkflowState.record_stage("tester", 0, "ok")
            WorkflowState.record_stage("tester", 0, "ok")
            trend = WorkflowState.get_deviation_trend("tester")
            assert trend == "stable", f"期望 stable，实际 {trend}"
        finally:
            _restore_state_file()


class TestWorkflowStateShouldContinueLoop:
    """测试 should_continue_loop() 回环决策。"""

    def test_continue_when_shrinking_and_within_limit(self):
        """偏差缩小且未超 max_loops 返回 True。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("explorer", 10, "blocked")
            WorkflowState.record_stage("explorer", 5, "blocked")
            assert WorkflowState.should_continue_loop("explorer") is True
        finally:
            _restore_state_file()

    def test_stop_when_stable(self):
        """偏差不变返回 False（即使未超 max_loops）。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["tester"])
            WorkflowState.record_stage("tester", 5, "blocked")
            WorkflowState.record_stage("tester", 5, "blocked")
            assert WorkflowState.should_continue_loop("tester") is False
        finally:
            _restore_state_file()

    def test_stop_when_growing(self):
        """偏差增加返回 False（即使未超 max_loops）。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("explorer", 3, "blocked")
            WorkflowState.record_stage("explorer", 7, "blocked")
            assert WorkflowState.should_continue_loop("explorer") is False
        finally:
            _restore_state_file()

    def test_stop_when_exceeds_max_loops(self):
        """超过 max_loops 返回 False。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            # 3 次 record_stage → iterations=3 > max_loops=2
            WorkflowState.record_stage("explorer", 10, "blocked")
            WorkflowState.record_stage("explorer", 5, "blocked")
            WorkflowState.record_stage("explorer", 1, "blocked")
            assert WorkflowState.should_continue_loop("explorer") is False
        finally:
            _restore_state_file()

    def test_continue_when_first_iteration_and_within_limit(self):
        """首次迭代且未超限返回 True。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["tester"])
            WorkflowState.record_stage("tester", 8, "blocked")
            assert WorkflowState.should_continue_loop("tester") is True
        finally:
            _restore_state_file()

    def test_respects_custom_max_loops(self):
        """支持自定义 max_loops 参数。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            # max_loops=1: 仅一次迭代后就不继续
            WorkflowState.record_stage("explorer", 5, "blocked")
            # first_iteration + iterations=1 > max_loops=1? No, 1 is not > 1
            # iterations=1, max_loops=1, trend="first_iteration" → True
            assert WorkflowState.should_continue_loop("explorer", max_loops=1) is True

            WorkflowState.record_stage("explorer", 3, "blocked")
            # iterations=2 > max_loops=1 → False
            assert WorkflowState.should_continue_loop("explorer", max_loops=1) is False
        finally:
            _restore_state_file()


class TestWorkflowStateToFeedbackSignal:
    """测试 to_feedback_signal() 转换为 FeedbackSignal。"""

    def test_output_is_feedback_signal_instance(self):
        """to_feedback_signal() 返回合法的 FeedbackSignal 实例。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("explorer", 5, "blocked")

            fs = WorkflowState.to_feedback_signal("explorer")
            assert isinstance(fs, FeedbackSignal)
        finally:
            _restore_state_file()

    def test_signal_type_is_loop_deviation(self):
        """生成的信号 signal_type 为 loop_deviation。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["tester"])
            WorkflowState.record_stage("tester", 3, "blocked")

            fs = WorkflowState.to_feedback_signal("tester")
            assert fs.signal_type == "loop_deviation"
        finally:
            _restore_state_file()

    def test_severity_blocking_when_deviation_positive(self):
        """偏差量 >0 时 severity 为 blocking。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("explorer", 3, "blocked")

            fs = WorkflowState.to_feedback_signal("explorer")
            assert fs.severity == "blocking"
        finally:
            _restore_state_file()

    def test_severity_non_blocking_when_deviation_zero(self):
        """偏差量为 0 时 severity 为 non_blocking。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["tester"])
            WorkflowState.record_stage("tester", 0, "ok")

            fs = WorkflowState.to_feedback_signal("tester")
            assert fs.severity == "non_blocking"
        finally:
            _restore_state_file()

    def test_signal_source_matches_stage_id(self):
        """信号的 source 字段为 stage_id。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            WorkflowState.record_stage("explorer", 1, "blocked")

            fs = WorkflowState.to_feedback_signal("explorer")
            assert fs.source == "explorer"
        finally:
            _restore_state_file()

    def test_signal_for_empty_history(self):
        """空历史时仍返回合法 FeedbackSignal（severity=info）。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            # 不调用 record_stage

            fs = WorkflowState.to_feedback_signal("explorer")
            assert fs.signal_type == "loop_deviation"
            assert fs.severity == "info"
            assert fs.source == "explorer"
        finally:
            _restore_state_file()


class TestWorkflowStateAtomicWrite:
    """测试原子写入。"""

    def test_no_tmp_file_left_behind(self):
        """原子写入完成后 .tmp 文件被清理。"""
        tmp = tempfile.mkdtemp()
        try:
            tmp_file = os.path.join(tmp, "current-workflow.json")
            _patch_state_file(tmp_file)

            WorkflowState.init("test", ["explorer"])
            tmp_path = tmp_file + ".tmp"
            assert not os.path.exists(tmp_path), (
                f"原子写入后 .tmp 文件不应残留: {tmp_path}"
            )
        finally:
            _restore_state_file()


# ---------------------------------------------------------------------------
# 辅助：临时替换 WorkflowState._state_file
# ---------------------------------------------------------------------------

_ORIGINAL_STATE_FILE = WorkflowState._state_file


def _patch_state_file(tmp_file: str):
    """将 WorkflowState._state_file 指向临时文件。"""
    WorkflowState._state_file = tmp_file


def _restore_state_file():
    """恢复 WorkflowState._state_file 为原始值。"""
    # 清理临时文件
    tmp = WorkflowState._state_file
    WorkflowState._state_file = _ORIGINAL_STATE_FILE
    if os.path.exists(tmp):
        os.remove(tmp)
    tmp_path = tmp + ".tmp"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
