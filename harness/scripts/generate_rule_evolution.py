# generate_rule_evolution.py — 规则演化建议生成脚本
# 扫描反馈信号中的重复模式，生成/更新 rule-evolution-proposal.md。
# 由 workflow 编排器在阶段结束时调用，无命令行参数。

import os
import sys
from datetime import datetime, timezone

# 计算项目根目录（__file__ 上溯 3 级）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _project_path(rel: str) -> str:
    return os.path.join(_PROJECT_ROOT, rel)


def main() -> None:
    from harness.state.feedback_engine import FeedbackEngine

    engine = FeedbackEngine()
    patterns = engine.detect_patterns()

    if not patterns:
        print("No repeated patterns detected.")
        return

    proposal_path = _project_path("harness/feedback/rule-evolution-proposal.md")
    now = datetime.now(timezone.utc).isoformat()

    existing_suggestions: set[str] = set()
    if os.path.exists(proposal_path):
        try:
            with open(proposal_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 提取已有建议的 rule_ref
            for line in content.splitlines():
                if line.startswith("## 建议") and "`" in line:
                    # 格式：## 建议 N: `rule_ref` -- ...
                    parts = line.split("`")
                    if len(parts) >= 2:
                        existing_suggestions.add(parts[1])
        except OSError:
            pass

    new_entries: list[str] = []
    for i, pattern in enumerate(patterns):
        rule_ref = pattern["rule_ref"]
        if rule_ref in existing_suggestions:
            continue

        rule_filename = rule_ref.split("#")[0] if "#" in rule_ref else rule_ref
        line_ref = rule_ref.split("#")[1] if "#" in rule_ref else ""

        entry = (
            f"\n## 建议 {i + 1}: `{rule_ref}` -- 重复模式 ({pattern['occurrences']} 次)\n\n"
            f"> 生成时间: {now}\n"
            f"> 状态: 待确认\n\n"
            f"**变更理由**: 规则 `{rule_ref}` 在工作流执行期间触发了 {pattern['occurrences']} 次反馈信号"
        )
        if line_ref:
            entry += f"（规则第 {line_ref} 条）"
        entry += (
            f"，严重程度均为 {pattern['severity']}。重复频率表明该规则可能需要调整或补充说明。\n\n"
            f"**支持证据**: 检测到 {pattern['occurrences']} 次 `signal_type=rule_violation` 或 `loop_deviation` 信号关联此规则。\n\n"
            f"**建议修改**: 请人工审查规则文件 `harness/rules/{rule_filename}`，考虑是否需要放宽约束条件、"
            f"补充例外情况、或增加示例说明。\n"
        )

        new_entries.append(entry)

    if not new_entries:
        print("No new repeated patterns detected beyond existing proposals.")
        return

    combined = "".join(new_entries)

    if os.path.exists(proposal_path):
        # 追加到已有文件：先读取已有内容，再原子写入合并后的完整内容
        with open(proposal_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
        new_content = existing_content + f"\n---\n{combined}"
    else:
        new_content = f"# 规则演化建议\n\n> 自动生成于 {now}\n\n---\n{combined}"

    # 原子写入
    tmp_path = proposal_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, proposal_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    print(f"Generated {len(new_entries)} new rule evolution proposal(s) at {proposal_path}")


if __name__ == "__main__":
    sys.path.insert(0, _PROJECT_ROOT)
    main()
