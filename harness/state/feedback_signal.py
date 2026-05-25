# feedback_signal.py — 反馈信号数据模型
"""定义 FeedbackSignal dataclass，用于在工作流中记录可量化的反馈事件。"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class FeedbackSignal:
    """反馈信号 — 记录工作流中的异常、错误和改进机会。"""

    signal_type: str  # "rule_violation" | "error" | "improvement" | "loop_deviation"
    severity: str  # "blocking" | "non_blocking" | "info"
    rule_ref: str  # 关联规则文件路径，如 "harness/rules/coding-rules.md#4"
    occurrences: int = 1
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = ""  # 来源，如 "explorer-blocked" / "tester-failed"

    def to_dict(self) -> dict:
        """导出为字典（字段与 JSON Schema 一致）。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FeedbackSignal":
        """从字典构造实例。"""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def to_json_schema(cls) -> dict:
        """返回合法的 JSON Schema dict。"""
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "FeedbackSignal",
            "type": "object",
            "properties": {
                "signal_type": {
                    "type": "string",
                    "description": "信号类型：rule_violation | error | improvement | loop_deviation",
                },
                "severity": {
                    "type": "string",
                    "description": "严重程度：blocking | non_blocking | info",
                },
                "rule_ref": {
                    "type": "string",
                    "description": "关联规则文件路径，如 harness/rules/coding-rules.md#4",
                },
                "occurrences": {
                    "type": "integer",
                    "description": "出现次数，默认 1",
                },
                "first_seen": {
                    "type": "string",
                    "format": "date-time",
                    "description": "首次出现的 ISO 时间戳",
                },
                "last_seen": {
                    "type": "string",
                    "format": "date-time",
                    "description": "最近出现的 ISO 时间戳",
                },
                "source": {
                    "type": "string",
                    "description": "来源标识，如 explorer-blocked / tester-failed",
                },
            },
            "required": ["signal_type", "severity", "rule_ref"],
        }
