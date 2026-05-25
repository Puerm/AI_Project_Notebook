# workflow_state.py — 工作流状态管理器
"""WorkflowState：管理 current-workflow.json，支持偏差趋势判断和回环决策。"""

import json
import os
from datetime import datetime, timezone

from harness.state.feedback_signal import FeedbackSignal

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_STATE_FILE = os.path.join(_PROJECT_ROOT, "harness", "state", "current-workflow.json")


class WorkflowState:
    """工作流状态管理器 — 全部为类方法，操作共享的 current-workflow.json。"""

    _state_file: str = DEFAULT_STATE_FILE

    @classmethod
    def _get_file(cls) -> str:
        return cls._state_file

    @classmethod
    def init(cls, topic: str, stages: list[str]) -> None:
        """创建新状态 JSON，重置所有迭代计数。stages 为阶段标识列表，如 ['explorer', 'tester']。"""
        state = {
            "topic": topic,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "stages": {stage: {"iterations": 0, "history": []} for stage in stages},
        }
        cls._atomic_write(state)

    @classmethod
    def record_stage(cls, stage_id: str, deviation_count: int, status: str) -> None:
        """追加阶段记录，自动递增该 stage 的迭代计数。"""
        state = cls._load()
        if stage_id not in state.get("stages", {}):
            state.setdefault("stages", {})[stage_id] = {"iterations": 0, "history": []}
        stage = state["stages"][stage_id]
        stage["iterations"] = stage.get("iterations", 0) + 1
        stage["history"].append(
            {
                "deviation_count": deviation_count,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        cls._atomic_write(state)

    @classmethod
    def get_deviation_trend(cls, stage_id: str) -> str:
        """比较当前迭代与上一迭代的 deviation_count。返回 first_iteration/shrinking/stable/growing。"""
        state = cls._load()
        stage = state.get("stages", {}).get(stage_id, {})
        history = stage.get("history", [])
        if len(history) < 2:
            return "first_iteration"
        prev = history[-2]["deviation_count"]
        curr = history[-1]["deviation_count"]
        if curr < prev:
            return "shrinking"
        elif curr == prev:
            return "stable"
        else:
            return "growing"

    @classmethod
    def should_continue_loop(cls, stage_id: str, max_loops: int = 2) -> bool:
        """偏差缩小且未超 max_loops 返回 True，否则返回 False。"""
        state = cls._load()
        stage = state.get("stages", {}).get(stage_id, {})
        iterations = stage.get("iterations", 0)

        if iterations > max_loops:
            return False

        trend = cls.get_deviation_trend(stage_id)
        return trend == "shrinking" or trend == "first_iteration"

    @classmethod
    def to_feedback_signal(cls, stage_id: str) -> FeedbackSignal:
        """将最后一次回环记录转为 FeedbackSignal（signal_type="loop_deviation"）。"""
        state = cls._load()
        stage = state.get("stages", {}).get(stage_id, {})
        history = stage.get("history", [])
        if not history:
            return FeedbackSignal(
                signal_type="loop_deviation",
                severity="info",
                rule_ref=f"workflow-state.md#{stage_id}",
                source=stage_id,
            )
        last = history[-1]
        severity = "blocking" if last["deviation_count"] > 0 else "non_blocking"
        return FeedbackSignal(
            signal_type="loop_deviation",
            severity=severity,
            rule_ref=f"workflow-state.md#{stage_id}",
            source=stage_id,
        )

    @classmethod
    def _load(cls) -> dict:
        """加载当前状态 JSON，文件不存在返回最小默认结构。"""
        if not os.path.exists(cls._state_file):
            return {"stages": {}}
        try:
            with open(cls._state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"stages": {}}

    @classmethod
    def _atomic_write(cls, state: dict) -> None:
        """原子写入：先写 .tmp 再 os.replace。"""
        os.makedirs(os.path.dirname(cls._state_file), exist_ok=True)
        tmp = cls._state_file + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            os.replace(tmp, cls._state_file)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


if __name__ == "__main__":
    # 自测逻辑
    import tempfile

    tmp_dir = tempfile.mkdtemp()
    original_file = WorkflowState._state_file
    tmp_file = os.path.join(tmp_dir, "current-workflow.json")
    WorkflowState._state_file = tmp_file
    try:
        # 测试 init
        WorkflowState.init("test-topic", ["explorer", "tester"])
        state = WorkflowState._load()
        assert state["topic"] == "test-topic", "topic 不匹配"
        assert "explorer" in state["stages"], "explorer stage 缺失"
        assert "tester" in state["stages"], "tester stage 缺失"

        # 测试 record_stage — 模拟 Explorer 阻塞回环
        WorkflowState.record_stage("explorer", 5, "blocked")  # 迭代 1: 5 个阻塞问题
        trend = WorkflowState.get_deviation_trend("explorer")
        assert trend == "first_iteration", f"首次应为 first_iteration，实际 {trend}"

        WorkflowState.record_stage("explorer", 3, "blocked")  # 迭代 2: 3 个阻塞问题
        trend = WorkflowState.get_deviation_trend("explorer")
        assert trend == "shrinking", f"偏差缩小应为 shrinking，实际 {trend}"
        assert WorkflowState.should_continue_loop("explorer") is True, "偏差缩小应继续回环"

        WorkflowState.record_stage("explorer", 1, "blocked")  # 迭代 3: 超过 max_loops=2
        assert WorkflowState.should_continue_loop("explorer") is False, "超过 max_loops=2 应停止"

        # 测试 to_feedback_signal
        fs = WorkflowState.to_feedback_signal("explorer")
        assert fs.signal_type == "loop_deviation", f"应为 loop_deviation，实际 {fs.signal_type}"
        assert fs.source == "explorer", f"source 应为 explorer，实际 {fs.source}"

        # 测试 Tester 回环独立
        WorkflowState.record_stage("tester", 10, "blocked")  # 迭代 1
        WorkflowState.record_stage("tester", 10, "blocked")  # 迭代 2, stable
        trend = WorkflowState.get_deviation_trend("tester")
        assert trend == "stable", f"偏差不变应为 stable，实际 {trend}"
        assert WorkflowState.should_continue_loop("tester") is False, "偏差不变应停止回环"

        print("All workflow_state self-tests passed.")

    finally:
        WorkflowState._state_file = original_file
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        if os.path.exists(tmp_file + ".tmp"):
            os.remove(tmp_file + ".tmp")
        os.rmdir(tmp_dir)
