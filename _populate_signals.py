"""Temp: populate feedback signals from improvement-log for self-upgrade test."""
from harness.state.feedback_engine import FeedbackEngine
from harness.state.feedback_signal import FeedbackSignal
from datetime import datetime, timezone

engine = FeedbackEngine()
now = datetime.now(timezone.utc).isoformat()

# 6 improvements, each with 3 signals for >=3 detect_patterns threshold
signal_sets = [
    (".claude/agents/generator.md", 3),   # 1. Spec覆盖度自检 + 输出可用性自检
    (".claude/agents/pm.md", 3),           # 2. 关键概念定义
    (".claude/agents/planner.md", 3),      # 3. 输出质量约束
    ("harness/rules/workflow-rules.md", 6),# 4+5. 用户上手引导 + 部署边界
    ("harness/rules/coding-rules.md", 3),  # 6. 部署边界质量闸门
]

for rule_ref, count in signal_sets:
    for _ in range(count):
        s = FeedbackSignal(
            signal_type="improvement",
            severity="non_blocking",
            rule_ref=rule_ref,
            occurrences=1,
            first_seen=now,
            last_seen=now,
            source="improvement-log-conversion",
        )
        engine.add_signal(s)

patterns = engine.detect_patterns()
print(f"Patterns detected: {len(patterns)}")
for p in patterns:
    print(f"  {p['rule_ref']}: {p['occurrences']} occurrences, severity={p['severity']}")
