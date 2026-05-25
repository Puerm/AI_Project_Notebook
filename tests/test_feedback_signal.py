# test_feedback_signal.py — FeedbackSignal 数据模型测试 (TST-1)
"""测试 FeedbackSignal dataclass 的构造、序列化往返、JSON Schema 输出。"""

import os
import sys
import json
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from harness.state.feedback_signal import FeedbackSignal


def _is_iso_timestamp(s: str) -> bool:
    """检查字符串是否为合法 ISO 8601 时间戳。"""
    try:
        datetime.fromisoformat(s)
        return True
    except (ValueError, TypeError):
        return False


class TestFeedbackSignalConstruct:
    """测试 FeedbackSignal 构造与默认值。"""

    def test_construct_minimal_fields(self):
        """最小必要字段构造不出错。"""
        s = FeedbackSignal(
            signal_type="rule_violation",
            severity="blocking",
            rule_ref="coding-rules.md#5",
        )
        assert s.signal_type == "rule_violation"
        assert s.severity == "blocking"
        assert s.rule_ref == "coding-rules.md#5"

    def test_default_occurrences_is_one(self):
        """occurrences 默认值为 1。"""
        s = FeedbackSignal(
            signal_type="error",
            severity="non_blocking",
            rule_ref="workflow-rules.md#3",
        )
        assert s.occurrences == 1

    def test_default_timestamps_are_iso_8601(self):
        """first_seen 和 last_seen 默认自动设为 ISO 8601 时间戳。"""
        s = FeedbackSignal(
            signal_type="improvement",
            severity="info",
            rule_ref="data-safety-rules.md#2",
        )
        assert _is_iso_timestamp(s.first_seen)
        assert _is_iso_timestamp(s.last_seen)

    def test_default_source_is_empty_string(self):
        """source 默认值为空字符串。"""
        s = FeedbackSignal(
            signal_type="loop_deviation",
            severity="info",
            rule_ref="workflow-state.md#explorer",
        )
        assert s.source == ""

    def test_construct_with_all_fields(self):
        """所有字段均可显式指定。"""
        s = FeedbackSignal(
            signal_type="error",
            severity="blocking",
            rule_ref="coding-rules.md#1",
            occurrences=3,
            first_seen="2026-05-01T00:00:00+00:00",
            last_seen="2026-05-25T12:00:00+00:00",
            source="explorer-blocked",
        )
        assert s.occurrences == 3
        assert s.first_seen == "2026-05-01T00:00:00+00:00"
        assert s.last_seen == "2026-05-25T12:00:00+00:00"
        assert s.source == "explorer-blocked"

    def test_invalid_signal_type_does_not_crash(self):
        """signal_type 为非法值时构造不出错（不强制校验）。"""
        s = FeedbackSignal(
            signal_type="unknown_weird_type",
            severity="blocking",
            rule_ref="test.md#1",
        )
        assert s.signal_type == "unknown_weird_type"


class TestFeedbackSignalSerialize:
    """测试 to_dict() / from_dict() 往返序列化。"""

    def test_to_dict_contains_all_fields(self):
        """to_dict() 输出包含所有 7 个字段。"""
        s = FeedbackSignal(
            signal_type="rule_violation",
            severity="blocking",
            rule_ref="coding-rules.md#4",
            source="tester-failed",
        )
        d = s.to_dict()
        assert d["signal_type"] == "rule_violation"
        assert d["severity"] == "blocking"
        assert d["rule_ref"] == "coding-rules.md#4"
        assert d["occurrences"] == 1
        assert "first_seen" in d
        assert "last_seen" in d
        assert d["source"] == "tester-failed"
        assert len(d) == 7

    def test_roundtrip_to_dict_from_dict(self):
        """to_dict() → from_dict() 往返保持数据一致。"""
        original = FeedbackSignal(
            signal_type="improvement",
            severity="info",
            rule_ref="workflow-rules.md#10",
            occurrences=5,
            first_seen="2026-05-01T00:00:00+00:00",
            last_seen="2026-05-25T12:00:00+00:00",
            source="explorer-blocked",
        )
        restored = FeedbackSignal.from_dict(original.to_dict())
        assert restored.signal_type == original.signal_type
        assert restored.severity == original.severity
        assert restored.rule_ref == original.rule_ref
        assert restored.occurrences == original.occurrences
        assert restored.first_seen == original.first_seen
        assert restored.last_seen == original.last_seen
        assert restored.source == original.source

    def test_from_dict_ignores_unknown_keys(self):
        """from_dict() 忽略未知字段，不抛异常。"""
        d = {
            "signal_type": "error",
            "severity": "blocking",
            "rule_ref": "test.md#1",
            "unknown_field": "should_be_ignored",
            "another_junk": 999,
        }
        s = FeedbackSignal.from_dict(d)
        assert s.signal_type == "error"
        assert s.severity == "blocking"
        assert s.rule_ref == "test.md#1"
        assert not hasattr(s, "unknown_field")

    def test_from_dict_missing_required_raises(self):
        """from_dict() 缺少必须字段时抛出 TypeError。"""
        import pytest
        with pytest.raises(TypeError):
            FeedbackSignal.from_dict({"signal_type": "error"})  # 缺少 severity, rule_ref


class TestFeedbackSignalJsonSchema:
    """测试 to_json_schema()。"""

    def test_schema_has_title(self):
        """JSON Schema 标题为 FeedbackSignal。"""
        schema = FeedbackSignal.to_json_schema()
        assert schema["title"] == "FeedbackSignal"

    def test_schema_type_is_object(self):
        """JSON Schema 顶层 type 为 object。"""
        schema = FeedbackSignal.to_json_schema()
        assert schema["type"] == "object"

    def test_schema_has_seven_properties(self):
        """JSON Schema 包含 7 个字段定义。"""
        schema = FeedbackSignal.to_json_schema()
        assert len(schema["properties"]) == 7

    def test_schema_signal_type_is_string(self):
        """signal_type 字段 type 为 string。"""
        schema = FeedbackSignal.to_json_schema()
        assert schema["properties"]["signal_type"]["type"] == "string"

    def test_schema_severity_is_string(self):
        """severity 字段 type 为 string。"""
        schema = FeedbackSignal.to_json_schema()
        assert schema["properties"]["severity"]["type"] == "string"

    def test_schema_rule_ref_is_string(self):
        """rule_ref 字段 type 为 string。"""
        schema = FeedbackSignal.to_json_schema()
        assert schema["properties"]["rule_ref"]["type"] == "string"

    def test_schema_occurrences_is_integer(self):
        """occurrences 字段 type 为 integer。"""
        schema = FeedbackSignal.to_json_schema()
        assert schema["properties"]["occurrences"]["type"] == "integer"

    def test_schema_first_seen_is_string_date_time(self):
        """first_seen 字段 type 为 string，format 为 date-time。"""
        schema = FeedbackSignal.to_json_schema()
        prop = schema["properties"]["first_seen"]
        assert prop["type"] == "string"
        assert prop.get("format") == "date-time"

    def test_schema_required_fields(self):
        """required 包含 signal_type, severity, rule_ref。"""
        schema = FeedbackSignal.to_json_schema()
        assert "signal_type" in schema["required"]
        assert "severity" in schema["required"]
        assert "rule_ref" in schema["required"]
        # occurrences, timestamps, source 有默认值，不应在 required 中
        assert "occurrences" not in schema["required"]
        assert "source" not in schema["required"]

    def test_schema_valid_json(self):
        """to_json_schema() 输出为合法 JSON（可被 json.dumps 序列化）。"""
        schema = FeedbackSignal.to_json_schema()
        serialized = json.dumps(schema)
        assert isinstance(serialized, str)
        restored = json.loads(serialized)
        assert restored["title"] == "FeedbackSignal"
