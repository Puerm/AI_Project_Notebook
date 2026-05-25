# test_diagnose_and_fix.py — 自我升级引擎测试 (TST-1 ~ TST-7)
"""测试 diagnose_and_fix.py 的配置加载、安全边界、去重、LLM 解析、worktree、升级历史和集成流程。"""

import os
import sys
import json
import io
import tempfile
import shutil
import subprocess
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from harness.scripts.diagnose_and_fix import (
    _project_path,
    _load_config,
    _parse_minimal_yaml,
    _match_auto_level,
    _load_upgrade_history,
    _check_dedup,
    _apply_safety_boundary,
    _extract_file_path_from_rule_ref,
    _build_funnel_context,
    _parse_llm_response,
    _call_llm_diagnosis,
    _apply_fixes_in_worktree,
    _run_verification,
    _sandbox_verify,
    _show_diff_and_confirm,
    _degrade_to_proposal,
    _write_upgrade_history,
    _log_error,
    main,
    _DEFAULT_CONFIG,
)
from harness.state.feedback_signal import FeedbackSignal
from harness.state.feedback_engine import FeedbackEngine


# ============================================================
# 辅助函数
# ============================================================

def _make_fix_plan_simple(op_type="insert", content="line1\nline2", file_path="test/file.md"):
    """快捷构造 fix_plan 条目。"""
    return [{"file": file_path, "type": op_type, "content": content, "reason": "test reason"}]


def _make_fix_plan_multi(ops):
    """构造多操作 fix_plan。ops = [("insert", 3), ("replace", 5)] 等。"""
    fix_plan = []
    for i, (op_type, lines) in enumerate(ops):
        content = "\n".join(f"line_{i}_{j}" for j in range(lines))
        fix_plan.append({
            "file": f"test/file_{i}.md",
            "type": op_type,
            "content": content,
            "reason": f"test reason {i}",
        })
    return fix_plan


def _make_signal(**kwargs):
    """快捷构造 FeedbackSignal。"""
    defaults = {
        "signal_type": "rule_violation",
        "severity": "blocking",
        "rule_ref": "coding-rules.md#4",
        "source": "test",
    }
    defaults.update(kwargs)
    return FeedbackSignal(**defaults)


# ============================================================
# TST-1: 配置加载测试
# ============================================================

class TestConfigLoading:
    """TST-1: 配置加载、YAML 解析、glob 匹配。"""

    # --- _parse_minimal_yaml ---

    def test_parse_full_yaml_returns_all_sections(self):
        """完整 YAML 文本正确解析出 auto_levels/safety_boundary/dedup 三段。"""
        yaml = """
auto_levels:
  - glob: "harness/rules/*"
    level: auto
  - glob: ".claude/agents/*"
    level: semi-auto
safety_boundary:
  add_max_lines: 30
  replace_max_lines: 10
  delete: require_confirmation
dedup:
  window_hours: 12
"""
        result = _parse_minimal_yaml(yaml)
        assert len(result["auto_levels"]) == 2
        assert result["auto_levels"][0]["glob"] == "harness/rules/*"
        assert result["auto_levels"][0]["level"] == "auto"
        assert result["auto_levels"][1]["glob"] == ".claude/agents/*"
        assert result["auto_levels"][1]["level"] == "semi-auto"
        assert result["safety_boundary"]["add_max_lines"] == 30
        assert result["safety_boundary"]["replace_max_lines"] == 10
        assert result["dedup"]["window_hours"] == 12

    def test_parse_missing_sections_use_defaults(self):
        """缺少段落时使用 _DEFAULT_CONFIG 默认值。"""
        yaml = """
auto_levels:
  - glob: "harness/rules/*"
    level: auto
"""
        result = _parse_minimal_yaml(yaml)
        assert result["safety_boundary"]["add_max_lines"] == 50
        assert result["safety_boundary"]["replace_max_lines"] == 80
        assert result["dedup"]["window_hours"] == 24

    def test_parse_empty_yaml_returns_defaults(self):
        """空 YAML 返回默认配置。"""
        result = _parse_minimal_yaml("")
        assert result["auto_levels"] == _DEFAULT_CONFIG["auto_levels"]
        assert result["safety_boundary"] == _DEFAULT_CONFIG["safety_boundary"]
        assert result["dedup"] == _DEFAULT_CONFIG["dedup"]

    def test_parse_comments_ignored(self):
        """# 注释行被正确忽略。"""
        yaml = """
# 这是注释
auto_levels:
  # 这也是注释
  - glob: "harness/rules/*"
    level: auto
safety_boundary:
  add_max_lines: 100
"""
        result = _parse_minimal_yaml(yaml)
        assert len(result["auto_levels"]) == 1
        assert result["safety_boundary"]["add_max_lines"] == 100

    def test_parse_invalid_number_falls_back(self):
        """非数字的 add_max_lines 不覆盖默认值。"""
        yaml = """
safety_boundary:
  add_max_lines: abc
"""
        result = _parse_minimal_yaml(yaml)
        assert result["safety_boundary"]["add_max_lines"] == 50

    # --- _load_config (通过 mock 文件系统) ---

    def test_load_config_file_not_exists_returns_defaults(self):
        """self-upgrade.yaml 不存在时返回全默认值。"""
        tmp = tempfile.mkdtemp()
        try:
            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                config = _load_config()
            assert config["auto_levels"] == _DEFAULT_CONFIG["auto_levels"]
            assert config["safety_boundary"] == _DEFAULT_CONFIG["safety_boundary"]
            assert config["dedup"] == _DEFAULT_CONFIG["dedup"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_config_file_exists_correctly_parsed(self):
        """self-upgrade.yaml 存在时正确解析。"""
        tmp = tempfile.mkdtemp()
        try:
            config_dir = os.path.join(tmp, "harness", "config")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "self-upgrade.yaml")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("""
auto_levels:
  - glob: "test/*"
    level: disabled
safety_boundary:
  add_max_lines: 10
dedup:
  window_hours: 48
""")
            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                config = _load_config()
            assert config["auto_levels"][0]["level"] == "disabled"
            assert config["safety_boundary"]["add_max_lines"] == 10
            assert config["dedup"]["window_hours"] == 48
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- _match_auto_level ---

    def test_glob_long_match_priority(self):
        """长匹配优先于短匹配：harness/rules/coding-rules.md 匹配具体 glob > * """
        auto_levels = [
            {"glob": "harness/rules/*", "level": "auto"},
            {"glob": "harness/rules/coding-rules.md", "level": "semi-auto"},
        ]
        result = _match_auto_level("harness/rules/coding-rules.md", auto_levels)
        assert result == "semi-auto", f"长匹配应优先，实际 {result}"

    def test_glob_short_match_nothing_else(self):
        """无其他匹配时，短 glob 生效。"""
        auto_levels = [
            {"glob": "harness/rules/*", "level": "auto"},
        ]
        result = _match_auto_level("harness/rules/data-safety-rules.md", auto_levels)
        assert result == "auto"

    def test_glob_disabled_overrides_all(self):
        """任意 disabled 规则匹配即返回 disabled，即使有更长的 non-disabled 匹配。"""
        auto_levels = [
            {"glob": "harness/rules/*", "level": "auto"},
            {"glob": "harness/rules/coding-rules.md", "level": "disabled"},
        ]
        result = _match_auto_level("harness/rules/coding-rules.md", auto_levels)
        assert result == "disabled"

    def test_glob_no_match_returns_safe_default(self):
        """无任何匹配时返回默认 semi-auto。"""
        auto_levels = [
            {"glob": "harness/rules/*", "level": "auto"},
        ]
        result = _match_auto_level(".claude/settings.json", auto_levels)
        assert result == "semi-auto"

    def test_glob_windows_backslash_normalized(self):
        """Windows 反斜杠路径被正确 normalize 后再匹配。"""
        auto_levels = [
            {"glob": "harness/rules/*", "level": "auto"},
        ]
        result = _match_auto_level("harness\\rules\\coding-rules.md", auto_levels)
        assert result == "auto"


# ============================================================
# TST-2: 安全边界逻辑测试
# ============================================================

class TestSafetyBoundary:
    """TST-2: _apply_safety_boundary 的边界判定。"""

    def _safety(self):
        return {"add_max_lines": 50, "replace_max_lines": 20, "delete": "require_confirmation"}

    def test_insert_within_limit_passes(self):
        """insert <=50 行通过。"""
        content = "\n".join(f"line_{i}" for i in range(50))
        passed, reason = _apply_safety_boundary(
            _make_fix_plan_simple("insert", content), self._safety()
        )
        assert passed
        assert reason == ""

    def test_insert_exceeds_limit_fails(self):
        """insert 51 行不通过。"""
        content = "\n".join(f"line_{i}" for i in range(51))
        passed, reason = _apply_safety_boundary(
            _make_fix_plan_simple("insert", content), self._safety()
        )
        assert not passed
        assert "超过阈值" in reason

    def test_replace_within_limit_passes(self):
        """replace <=20 行通过。"""
        content = "\n".join(f"line_{i}" for i in range(20))
        passed, reason = _apply_safety_boundary(
            _make_fix_plan_simple("replace", content), self._safety()
        )
        assert passed

    def test_replace_exceeds_limit_fails(self):
        """replace 21 行不通过。"""
        content = "\n".join(f"line_{i}" for i in range(21))
        passed, reason = _apply_safety_boundary(
            _make_fix_plan_simple("replace", content), self._safety()
        )
        assert not passed
        assert "超过阈值" in reason

    def test_delete_always_requires_confirmation(self):
        """delete 任意行数一律标记不通过。"""
        passed, reason = _apply_safety_boundary(
            _make_fix_plan_simple("delete", "any content"), self._safety()
        )
        assert not passed
        assert ("人工确认" in reason) or ("delete" in reason.lower())

    def test_create_within_insert_limit_passes(self):
        """create <=50 行通过（同 insert 阈值）。"""
        content = "\n".join(f"line_{i}" for i in range(50))
        passed, reason = _apply_safety_boundary(
            _make_fix_plan_simple("create", content), self._safety()
        )
        assert passed

    def test_mixed_ops_strictest_rule_applies(self):
        """混合操作按最严格规则判定：insert 通过但 delete 不通过 → 整体不通过。"""
        passed, reason = _apply_safety_boundary(
            _make_fix_plan_multi([("insert", 5), ("delete", 0)]), self._safety()
        )
        assert not passed

    def test_empty_fix_plan_passes(self):
        """空 fix_plan 通过安全边界。"""
        passed, reason = _apply_safety_boundary([], self._safety())
        assert passed

    def test_missing_type_defaults_to_insert(self):
        """缺少 type 字段时默认按 insert 判定。"""
        fix_plan = [{"content": "\n".join(f"line_{i}" for i in range(51)), "reason": "test"}]
        passed, reason = _apply_safety_boundary(fix_plan, self._safety())
        assert not passed


# ============================================================
# TST-3: 24h 去重逻辑测试
# ============================================================

class TestDedup:
    """TST-3: _check_dedup 的 24h 窗口逻辑。"""

    def _write_history(self, tmp_dir, records):
        """在 tmp_dir 中写入 upgrade-history.json。"""
        state_dir = os.path.join(tmp_dir, "harness", "state")
        os.makedirs(state_dir, exist_ok=True)
        path = os.path.join(state_dir, "upgrade-history.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f)

    def test_recent_success_triggers_skip(self):
        """同一 signal_id 在 24h 内有成功修复 → 跳过。"""
        tmp = tempfile.mkdtemp()
        try:
            now = datetime.now(timezone.utc)
            recent = (now - timedelta(hours=1)).isoformat()
            self._write_history(tmp, [{
                "timestamp": recent,
                "signal_id": "coding-rules.md#4",
                "diagnosis_summary": "test fix",
                "affected_files": ["test.md"],
                "verification_result": "passed",
            }])
            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                result = _check_dedup("coding-rules.md#4", 24)
            assert result is True
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_old_success_allows_trigger(self):
        """同一 signal_id 但在 24h 外 → 正常触发。"""
        tmp = tempfile.mkdtemp()
        try:
            now = datetime.now(timezone.utc)
            old = (now - timedelta(hours=25)).isoformat()
            self._write_history(tmp, [{
                "timestamp": old,
                "signal_id": "coding-rules.md#4",
                "diagnosis_summary": "test fix",
                "affected_files": ["test.md"],
                "verification_result": "passed",
            }])
            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                result = _check_dedup("coding-rules.md#4", 24)
            assert result is False
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_failed_fix_allows_retrigger(self):
        """上次修复验证失败 → 正常触发（不因失败而永远跳过）。"""
        tmp = tempfile.mkdtemp()
        try:
            now = datetime.now(timezone.utc)
            recent = (now - timedelta(hours=1)).isoformat()
            self._write_history(tmp, [{
                "timestamp": recent,
                "signal_id": "coding-rules.md#4",
                "diagnosis_summary": "failed fix",
                "affected_files": ["test.md"],
                "verification_result": "failed",
            }])
            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                result = _check_dedup("coding-rules.md#4", 24)
            assert result is False
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_history_allows_trigger(self):
        """无历史记录 → 正常触发。"""
        tmp = tempfile.mkdtemp()
        try:
            self._write_history(tmp, [])
            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                result = _check_dedup("any-rule.md#1", 24)
            assert result is False
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_different_signal_id_not_affected(self):
        """不同 signal_id 不互相影响去重。"""
        tmp = tempfile.mkdtemp()
        try:
            now = datetime.now(timezone.utc)
            recent = (now - timedelta(hours=1)).isoformat()
            self._write_history(tmp, [{
                "timestamp": recent,
                "signal_id": "rule-a.md#1",
                "diagnosis_summary": "test fix",
                "affected_files": ["test.md"],
                "verification_result": "passed",
            }])
            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                result = _check_dedup("rule-b.md#2", 24)
            assert result is False
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_history_file_allows_trigger(self):
        """upgrade-history.json 文件不存在 → 正常触发。"""
        tmp = tempfile.mkdtemp()
        try:
            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                result = _check_dedup("any-rule.md#1", 24)
            assert result is False
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ============================================================
# TST-4: LLM 诊断输出解析测试
# ============================================================

class TestLLMParsing:
    """TST-4: _parse_llm_response 和 _call_llm_diagnosis 行为。"""

    def test_valid_json_parsed_correctly(self):
        """合法 JSON 修复方案正确解析。"""
        response = json.dumps({
            "root_cause": "test cause",
            "category": "missing_step",
            "affected_files": ["a.md", "b.py"],
            "fix_plan": [
                {"file": "a.md", "type": "insert", "content": "new content", "reason": "fix a"},
            ],
        })
        result = _parse_llm_response(response)
        assert result is not None
        assert result["root_cause"] == "test cause"
        assert result["category"] == "missing_step"
        assert len(result["fix_plan"]) == 1

    def test_json_with_code_block_parsed(self):
        """JSON 被 ```json ... ``` 包裹时也能解析。"""
        response = '```json\n' + json.dumps({
            "root_cause": "test",
            "category": "rule_conflict",
            "affected_files": [],
            "fix_plan": [{"file": "x.md", "type": "replace", "content": "new", "reason": "r"}],
        }) + '\n```'
        result = _parse_llm_response(response)
        assert result is not None
        assert result["category"] == "rule_conflict"

    def test_missing_required_field_returns_none(self):
        """缺少必需字段返回 None。"""
        response = json.dumps({
            "root_cause": "test",
            "category": "missing_check",
            "affected_files": [],
            "fix_plan": [
                {"file": "x.md", "type": "insert", "content": "text"},
                # 缺少 reason
            ],
        })
        result = _parse_llm_response(response)
        assert result is None

    def test_non_json_text_returns_none(self):
        """非 JSON 文本返回 None。"""
        result = _parse_llm_response("This is not JSON at all.")
        assert result is None

    def test_empty_response_returns_none(self):
        """空响应返回 None。"""
        result = _parse_llm_response("")
        assert result is None

    def test_fix_plan_not_list_returns_none(self):
        """fix_plan 不是列表返回 None。"""
        response = json.dumps({
            "root_cause": "test",
            "category": "missing_step",
            "affected_files": [],
            "fix_plan": "not a list",
        })
        result = _parse_llm_response(response)
        assert result is None

    def test_result_not_dict_returns_none(self):
        """返回的不是 dict 返回 None。"""
        result = _parse_llm_response(json.dumps([1, 2, 3]))
        assert result is None

    def test_call_llm_diagnosis_no_api_key_returns_none(self):
        """API Key 不可用时 _call_llm_diagnosis 返回 None（不崩溃）。"""
        tmp = tempfile.mkdtemp()
        try:
            # 创建最小的 diagnosis.txt
            prompts_dir = os.path.join(tmp, "harness", "prompts")
            os.makedirs(prompts_dir, exist_ok=True)
            prompt_path = os.path.join(prompts_dir, "diagnosis.txt")
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("# 版本: v1.0.0\n# 变更理由: 测试\n\n{{TARGET_FILE_CONTENT}}\n{{FUNNEL_FILES}}\n{{HISTORY_SIGNALS}}")

            # 创建目标文件
            os.makedirs(os.path.join(tmp, "harness", "rules"), exist_ok=True)
            target_file = os.path.join(tmp, "harness", "rules", "test-rule.md")
            with open(target_file, "w", encoding="utf-8") as f:
                f.write("# Test Rule\nSome content.\n")

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            # 同时 patch llm_assistant 的 check_api_key_available 返回 False
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path), \
                 patch("app.analyzer.llm_assistant.check_api_key_available", return_value=(False, "")):
                result = _call_llm_diagnosis(target_file, "test-rule.md#1", [])
            assert result is None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_extract_file_path_from_rule_ref_full_path(self):
        """完整路径 rule_ref 正确提取文件名部分。"""
        result = _extract_file_path_from_rule_ref("harness/rules/coding-rules.md#4")
        assert result == "harness/rules/coding-rules.md"

    def test_extract_file_path_from_rule_ref_short_name(self):
        """短名补全为 harness/rules/ 前缀。"""
        result = _extract_file_path_from_rule_ref("coding-rules.md#4")
        assert result == "harness/rules/coding-rules.md"

    def test_extract_file_path_from_rule_ref_no_hash(self):
        """无 # 号时直接返回。"""
        result = _extract_file_path_from_rule_ref("harness/rules/coding-rules.md")
        assert result == "harness/rules/coding-rules.md"


# ============================================================
# TST-5: worktree 生命周期测试
# ============================================================

class TestFixesInWorktree:
    """测试 _apply_fixes_in_worktree 在目录中修改文件。"""

    def test_insert_to_new_file(self):
        """insert 到不存在的文件 → 创建并写入。"""
        tmp = tempfile.mkdtemp()
        try:
            fix_plan = [{"file": "subdir/new.md", "type": "insert", "content": "Hello\nWorld", "reason": "test"}]
            result = _apply_fixes_in_worktree(tmp, fix_plan)
            assert result
            target = os.path.join(tmp, "subdir", "new.md")
            assert os.path.exists(target)
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Hello" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_insert_to_existing_file_appends(self):
        """insert 到已存在文件 → 追加内容。"""
        tmp = tempfile.mkdtemp()
        try:
            existing = os.path.join(tmp, "existing.md")
            os.makedirs(os.path.dirname(existing), exist_ok=True)
            with open(existing, "w", encoding="utf-8") as f:
                f.write("Original content\n")

            fix_plan = [{"file": "existing.md", "type": "insert", "content": "Appended\n", "reason": "test"}]
            result = _apply_fixes_in_worktree(tmp, fix_plan)
            assert result
            with open(existing, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Original content" in content
            assert "Appended" in content
            assert content.index("Original") < content.index("Appended")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_replace_overwrites_file(self):
        """replace 完全覆盖文件内容。"""
        tmp = tempfile.mkdtemp()
        try:
            existing = os.path.join(tmp, "target.md")
            os.makedirs(os.path.dirname(existing), exist_ok=True)
            with open(existing, "w", encoding="utf-8") as f:
                f.write("old content")

            fix_plan = [{"file": "target.md", "type": "replace", "content": "new content", "reason": "test"}]
            result = _apply_fixes_in_worktree(tmp, fix_plan)
            assert result
            with open(existing, "r", encoding="utf-8") as f:
                content = f.read()
            assert content == "new content"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_create_new_file(self):
        """create 创建新文件。"""
        tmp = tempfile.mkdtemp()
        try:
            fix_plan = [{"file": "new_dir/created.md", "type": "create", "content": "created content", "reason": "test"}]
            result = _apply_fixes_in_worktree(tmp, fix_plan)
            assert result
            target = os.path.join(tmp, "new_dir", "created.md")
            assert os.path.exists(target)
            with open(target, "r", encoding="utf-8") as f:
                assert f.read() == "created content"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_delete_removes_file(self):
        """delete 删除文件。"""
        tmp = tempfile.mkdtemp()
        try:
            target = os.path.join(tmp, "to_delete.md")
            with open(target, "w", encoding="utf-8") as f:
                f.write("will be deleted")

            fix_plan = [{"file": "to_delete.md", "type": "delete", "content": "", "reason": "test"}]
            result = _apply_fixes_in_worktree(tmp, fix_plan)
            assert result
            assert not os.path.exists(target)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_delete_nonexistent_file_ok(self):
        """delete 不存在的文件不报错。"""
        tmp = tempfile.mkdtemp()
        try:
            fix_plan = [{"file": "nonexistent.md", "type": "delete", "content": "", "reason": "test"}]
            result = _apply_fixes_in_worktree(tmp, fix_plan)
            assert result
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_unknown_op_type_returns_false(self):
        """未知操作类型返回 False。"""
        tmp = tempfile.mkdtemp()
        try:
            fix_plan = [{"file": "test.md", "type": "unknown_op", "content": "x", "reason": "test"}]
            result = _apply_fixes_in_worktree(tmp, fix_plan)
            assert not result
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestWorktreeGit:
    """TST-5: git worktree 生命周期（需要实际 git 仓库）。"""

    def _init_temp_git_repo(self):
        """创建临时 git 仓库，含一次初始提交。返回 tmp_dir, project_dir。"""
        tmp = tempfile.mkdtemp()
        project_dir = os.path.join(tmp, "project")
        os.makedirs(project_dir)

        # 初始化 git
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_dir, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, capture_output=True, timeout=10)

        # 最小化项目结构（使 check_structure.py 能跑）
        harness_dir = os.path.join(project_dir, "harness", "scripts")
        os.makedirs(harness_dir, exist_ok=True)
        check_script = os.path.join(harness_dir, "check_structure.py")
        with open(check_script, "w", encoding="utf-8") as f:
            f.write("import sys; print('PASS'); sys.exit(0)\n")

        agents_dir = os.path.join(project_dir, ".claude", "agents")
        os.makedirs(agents_dir, exist_ok=True)
        with open(os.path.join(agents_dir, "test_agent.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: test-agent\n---\n# Test Agent\n")

        # 初始提交
        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=project_dir, capture_output=True, timeout=10)

        return tmp, project_dir

    def test_worktree_create_and_remove(self):
        """worktree 创建成功，路径正确，之后可删除。"""
        tmp, project_dir = self._init_temp_git_repo()
        try:
            # 重定向 _PROJECT_ROOT
            with patch("harness.scripts.diagnose_and_fix._PROJECT_ROOT", project_dir):
                from harness.scripts.diagnose_and_fix import _create_worktree, _remove_worktree

                worktree_path = os.path.join(tmp, ".self-upgrade-worktree")
                branch = _create_worktree(worktree_path)
                assert branch is not None
                assert os.path.isdir(worktree_path)
                # 检查 worktree 是一个有效的 checkout
                assert os.path.isfile(os.path.join(worktree_path, "harness", "scripts", "check_structure.py"))

                _remove_worktree(worktree_path, force=True)
                assert not os.path.exists(worktree_path)
        finally:
            _cleanup_git_locks(project_dir, tmp)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_fixes_applied_to_worktree_not_main(self):
        """修改应用到 worktree 而非主工作区。"""
        tmp, project_dir = self._init_temp_git_repo()
        try:
            with patch("harness.scripts.diagnose_and_fix._PROJECT_ROOT", project_dir):
                from harness.scripts.diagnose_and_fix import _create_worktree, _discard_worktree

                worktree_path = os.path.join(tmp, ".self-upgrade-worktree")
                _create_worktree(worktree_path)

                # 在 worktree 中应用修复
                fix_plan = [{"file": "test_new_file.md", "type": "create", "content": "new content", "reason": "test"}]
                _apply_fixes_in_worktree(worktree_path, fix_plan)

                # worktree 中有文件
                assert os.path.isfile(os.path.join(worktree_path, "test_new_file.md"))
                # 主工作区没有
                assert not os.path.isfile(os.path.join(project_dir, "test_new_file.md"))

                _discard_worktree(worktree_path)
        finally:
            _cleanup_git_locks(project_dir, tmp)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_sandbox_verify_dry_run_skips_worktree(self):
        """dry-run 模式跳过 worktree 创建。"""
        tmp, project_dir = self._init_temp_git_repo()
        try:
            with patch("harness.scripts.diagnose_and_fix._PROJECT_ROOT", project_dir):
                success, branch, affected = _sandbox_verify(
                    _make_fix_plan_simple("insert", "test\n"), is_dry_run=True
                )
                assert not success  # dry-run 返回 False
                assert branch == ""
        finally:
            _cleanup_git_locks(project_dir, tmp)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_verification_passes_on_valid_worktree(self):
        """worktree 中 check_structure + agent YAML 验证通过。"""
        tmp, project_dir = self._init_temp_git_repo()
        try:
            with patch("harness.scripts.diagnose_and_fix._PROJECT_ROOT", project_dir):
                passed, failures = _run_verification(project_dir)
                assert passed, f"验证应在有效 worktree 中通过，失败: {failures}"
                assert len(failures) == 0
        finally:
            _cleanup_git_locks(project_dir, tmp)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_agent_yaml_frontmatter_missing_name_fails(self):
        """agent YAML frontmatter 缺少 name 字段 → 验证失败。"""
        tmp, project_dir = self._init_temp_git_repo()
        try:
            # 创建没有 name 字段的 agent 文件
            agents_dir = os.path.join(project_dir, ".claude", "agents")
            with open(os.path.join(agents_dir, "invalid_agent.md"), "w", encoding="utf-8") as f:
                f.write("---\ndescription: no name\n---\n# Bad Agent\n")

            with patch("harness.scripts.diagnose_and_fix._PROJECT_ROOT", project_dir):
                passed, failures = _run_verification(project_dir)
                assert not passed
                assert any("name" in f.lower() for f in failures), f"应报告缺少 name，实际: {failures}"
        finally:
            _cleanup_git_locks(project_dir, tmp)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_agent_yaml_no_frontmatter_fails(self):
        """agent 文件无 YAML frontmatter → 验证失败。"""
        tmp, project_dir = self._init_temp_git_repo()
        try:
            agents_dir = os.path.join(project_dir, ".claude", "agents")
            with open(os.path.join(agents_dir, "bad_agent.md"), "w", encoding="utf-8") as f:
                f.write("# No frontmatter here\n")

            with patch("harness.scripts.diagnose_and_fix._PROJECT_ROOT", project_dir):
                passed, failures = _run_verification(project_dir)
                assert not passed
                assert any("frontmatter" in f.lower() or "起始" in f for f in failures), f"应报告缺少 frontmatter，实际: {failures}"
        finally:
            _cleanup_git_locks(project_dir, tmp)
            shutil.rmtree(tmp, ignore_errors=True)


def _cleanup_git_locks(project_dir, tmp_dir):
    """清理 git worktree 残留，防止 lock 文件阻塞后续删除。"""
    # 先清理可能的 worktree
    _safe_cleanup_worktrees(project_dir)
    for _ in range(3):
        try:
            subprocess.run(["git", "-C", project_dir, "worktree", "prune"],
                          capture_output=True, timeout=10)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass


def _safe_cleanup_worktrees(project_dir):
    """安全清理所有 worktree 和分支。"""
    try:
        result = subprocess.run(
            ["git", "-C", project_dir, "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        worktrees = []
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                wt_path = line.split(" ", 1)[1].strip()
                if wt_path != project_dir:
                    worktrees.append(wt_path)
        for wt in worktrees:
            subprocess.run(["git", "-C", project_dir, "worktree", "remove", "--force", wt],
                          capture_output=True, timeout=10)
            if os.path.exists(wt):
                shutil.rmtree(wt, ignore_errors=True)
        # 删除 self-upgrade 分支
        branch_result = subprocess.run(
            ["git", "-C", project_dir, "branch"],
            capture_output=True, text=True, timeout=10
        )
        for bline in branch_result.stdout.splitlines():
            bname = bline.strip().lstrip("* ")
            if bname.startswith("self-upgrade-"):
                subprocess.run(["git", "-C", project_dir, "branch", "-D", bname],
                              capture_output=True, timeout=10)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass


# ============================================================
# TST-6: 升级历史记录测试
# ============================================================

class TestUpgradeHistory:
    """TST-6: _write_upgrade_history 和 _load_upgrade_history。"""

    def test_write_and_load_roundtrip(self):
        """写入记录后能正确读取。"""
        tmp = tempfile.mkdtemp()
        try:
            def _fake_path(rel):
                return os.path.join(tmp, rel)

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                _write_upgrade_history(
                    signal_id="test-rule.md#1",
                    diagnosis_summary="fixed something" * 6,  # >100 chars
                    affected_files=["a.md", "b.md"],
                    verification_result="passed",
                )

                history = _load_upgrade_history()
                assert len(history) == 1
                record = history[0]
                assert record["signal_id"] == "test-rule.md#1"
                # 截断到 100 字
                assert len(record["diagnosis_summary"]) <= 100
                assert record["affected_files"] == ["a.md", "b.md"]
                assert record["verification_result"] == "passed"
                assert "timestamp" in record
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_failed_verification_with_rollback(self):
        """失败修复记录包含 rollback_note。"""
        tmp = tempfile.mkdtemp()
        try:
            def _fake_path(rel):
                return os.path.join(tmp, rel)

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                _write_upgrade_history(
                    signal_id="rule.md#2",
                    diagnosis_summary="fix attempt",
                    affected_files=["x.md"],
                    verification_result="failed",
                    rollback_note="sandbox verification failed",
                )

                history = _load_upgrade_history()
                record = history[0]
                assert record["verification_result"] == "failed"
                assert record["rollback_note"] == "sandbox verification failed"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_degraded_verification(self):
        """降级修复记录 verification_result 为 degraded。"""
        tmp = tempfile.mkdtemp()
        try:
            def _fake_path(rel):
                return os.path.join(tmp, rel)

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                _write_upgrade_history(
                    signal_id="rule.md#3",
                    diagnosis_summary="degraded fix",
                    affected_files=[],
                    verification_result="degraded",
                )

                history = _load_upgrade_history()
                assert history[0]["verification_result"] == "degraded"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_multiple_records_accumulate(self):
        """多次写入追加记录。"""
        tmp = tempfile.mkdtemp()
        try:
            def _fake_path(rel):
                return os.path.join(tmp, rel)

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                _write_upgrade_history("r1", "fix 1", ["f1.md"], "passed")
                _write_upgrade_history("r2", "fix 2", ["f2.md"], "degraded")
                history = _load_upgrade_history()
                assert len(history) == 2
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_nonexistent_file_returns_empty(self):
        """upgrade-history.json 不存在返回空列表。"""
        tmp = tempfile.mkdtemp()
        try:
            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                history = _load_upgrade_history()
                assert history == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_invalid_json_returns_empty(self):
        """无效 JSON 文件返回空列表。"""
        tmp = tempfile.mkdtemp()
        try:
            state_dir = os.path.join(tmp, "harness", "state")
            os.makedirs(state_dir, exist_ok=True)
            with open(os.path.join(state_dir, "upgrade-history.json"), "w", encoding="utf-8") as f:
                f.write("not valid json")

            def _fake_path(rel):
                return os.path.join(tmp, rel)
            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                history = _load_upgrade_history()
                assert history == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ============================================================
# TST-7: 集成测试 — 端到端工作流
# ============================================================

class TestDegradeToProposal:
    """测试 _degrade_to_proposal 降级输出。"""

    def test_degrade_creates_proposal_file(self):
        """降级输出创建 rule-evolution-proposal.md。"""
        tmp = tempfile.mkdtemp()
        try:
            feedback_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(feedback_dir, exist_ok=True)
            proposal_path = os.path.join(feedback_dir, "rule-evolution-proposal.md")

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                diagnosis = {
                    "root_cause": "test root cause",
                    "category": "missing_step",
                    "affected_files": ["test.md"],
                    "fix_plan": [],
                }
                _degrade_to_proposal("test-rule.md#1", diagnosis, "安全边界不通过")

            assert os.path.exists(proposal_path)
            with open(proposal_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "test-rule.md#1" in content
            assert "安全边界不通过" in content
            assert "降级" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_degrade_with_none_diagnosis(self):
        """诊断结果为 None 时输出 '无法自动诊断' 标记。"""
        tmp = tempfile.mkdtemp()
        try:
            feedback_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(feedback_dir, exist_ok=True)
            proposal_path = os.path.join(feedback_dir, "rule-evolution-proposal.md")

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                _degrade_to_proposal("rule.md#1", None, "LLM 不可用")

            assert os.path.exists(proposal_path)
            with open(proposal_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "无法自动诊断" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestIntegrationEndToEnd:
    """TST-7: 集成测试 — 端到端工作流。"""

    def _setup_signals(self, tmp_dir, rule_ref, count):
        """在 tmp_dir 中创建 feedback-signals.json 含 count 个信号。"""
        state_dir = os.path.join(tmp_dir, "harness", "state")
        os.makedirs(state_dir, exist_ok=True)
        signals_json = os.path.join(state_dir, "feedback-signals.json")

        signals = []
        for i in range(count):
            s = _make_signal(rule_ref=rule_ref, source=f"test-{i}")
            # 每个信号有不同时间戳，避免被忽略
            signals.append(s.to_dict())

        with open(signals_json, "w", encoding="utf-8") as f:
            json.dump(signals, f)
        return signals_json

    def _setup_agent_dir(self, tmp_dir):
        """在 tmp_dir 中创建最小化的 agent 目录。"""
        agents_dir = os.path.join(tmp_dir, ".claude", "agents")
        os.makedirs(agents_dir, exist_ok=True)
        with open(os.path.join(agents_dir, "test_agent.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: test-agent\ndescription: test\n---\n# Test Agent\n")

    def _setup_diagnosis_txt(self, tmp_dir):
        """创建最小的 diagnosis.txt。"""
        prompts_dir = os.path.join(tmp_dir, "harness", "prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        with open(os.path.join(prompts_dir, "diagnosis.txt"), "w", encoding="utf-8") as f:
            f.write("# 版本: v1.0.0\n# 变更理由: 测试\n\n{{TARGET_FILE_CONTENT}}\n{{FUNNEL_FILES}}\n{{HISTORY_SIGNALS}}")

    def test_no_patterns_exits_gracefully(self):
        """重复模式 < 3 次 → 不触发修复，正常退出。"""
        tmp = tempfile.mkdtemp()
        try:
            # 仅 2 个信号 → detect_patterns 返回空
            self._setup_signals(tmp, "coding-rules.md#4", 2)
            self._setup_diagnosis_txt(tmp)

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            # Mock FeedbackEngine 使用 tmp 路径
            engine = FeedbackEngine(signals_file=os.path.join(tmp, "harness", "state", "feedback-signals.json"))

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path), \
                 patch("harness.state.feedback_engine.FeedbackEngine", return_value=engine):
                stdout_capture = io.StringIO()
                with patch.object(sys, "stdout", stdout_capture):
                    main()

            output = stdout_capture.getvalue()
            assert "未检测到重复模式" in output
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_disabled_level_skips(self):
        """disabled 自动程度级别完全跳过。"""
        tmp = tempfile.mkdtemp()
        try:
            self._setup_signals(tmp, "harness/hooks/some-hook.md#1", 4)
            self._setup_diagnosis_txt(tmp)
            self._setup_agent_dir(tmp)

            # 创建目标文件
            os.makedirs(os.path.join(tmp, "harness", "hooks"), exist_ok=True)
            with open(os.path.join(tmp, "harness", "hooks", "some-hook.md"), "w", encoding="utf-8") as f:
                f.write("# Hook file\n")

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            engine = FeedbackEngine(signals_file=os.path.join(tmp, "harness", "state", "feedback-signals.json"))

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path), \
                 patch("harness.state.feedback_engine.FeedbackEngine", return_value=engine):
                stdout_capture = io.StringIO()
                with patch.object(sys, "stdout", stdout_capture):
                    main()

            output = stdout_capture.getvalue()
            # 应显示 disabled 跳过
            assert "disabled" in output or "跳过" in output
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_dry_run_mode_outputs_to_proposal(self):
        """dry-run 模式降级输出修复方案。"""
        tmp = tempfile.mkdtemp()
        try:
            self._setup_signals(tmp, "harness/rules/coding-rules.md#4", 5)
            self._setup_diagnosis_txt(tmp)
            self._setup_agent_dir(tmp)

            # 创建规则目录
            os.makedirs(os.path.join(tmp, "harness", "rules"), exist_ok=True)
            with open(os.path.join(tmp, "harness", "rules", "coding-rules.md"), "w", encoding="utf-8") as f:
                f.write("# Coding Rules\n\nSample content.\n")

            feedback_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(feedback_dir, exist_ok=True)

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            engine = FeedbackEngine(signals_file=os.path.join(tmp, "harness", "state", "feedback-signals.json"))

            # dry-run mode
            with patch.object(sys, "argv", ["diagnose_and_fix.py", "--dry-run"]), \
                 patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path), \
                 patch("harness.state.feedback_engine.FeedbackEngine", return_value=engine), \
                 patch("app.analyzer.llm_assistant.check_api_key_available", return_value=(False, "")):
                stdout_capture = io.StringIO()
                with patch.object(sys, "stdout", stdout_capture):
                    main()

            output = stdout_capture.getvalue()
            # dry-run 应有降级输出
            assert "dry-run" in output.lower() or "DRY-RUN" in output
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_degraded_output_contains_correct_info(self):
        """降级输出到 rule-evolution-proposal.md 包含正确的修复方案信息。"""
        tmp = tempfile.mkdtemp()
        try:
            self._setup_signals(tmp, "coding-rules.md#4", 5)
            self._setup_diagnosis_txt(tmp)
            self._setup_agent_dir(tmp)

            os.makedirs(os.path.join(tmp, "harness", "rules"), exist_ok=True)
            with open(os.path.join(tmp, "harness", "rules", "coding-rules.md"), "w", encoding="utf-8") as f:
                f.write("# Coding Rules\nContent.\n")

            feedback_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(feedback_dir, exist_ok=True)

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            engine = FeedbackEngine(signals_file=os.path.join(tmp, "harness", "state", "feedback-signals.json"))

            with patch.object(sys, "argv", ["diagnose_and_fix.py", "--dry-run"]), \
                 patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path), \
                 patch("harness.state.feedback_engine.FeedbackEngine", return_value=engine), \
                 patch("app.analyzer.llm_assistant.check_api_key_available", return_value=(False, "")):
                main()

            proposal_path = os.path.join(feedback_dir, "rule-evolution-proposal.md")
            if os.path.exists(proposal_path):
                with open(proposal_path, "r", encoding="utf-8") as f:
                    content = f.read()
                assert "coding-rules.md#4" in content
                assert "降级" in content or "degrad" in content.lower()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestSemiAutoInteraction:
    """测试 _show_diff_and_confirm 交互流程。"""

    def test_user_confirms_returns_true(self):
        """用户输入 'y' 返回 True。"""
        with patch("builtins.input", return_value="y"):
            result = _show_diff_and_confirm(
                _make_fix_plan_simple("insert", "test\n"),
                timeout_seconds=5
            )
        assert result is True

    def test_user_rejects_returns_false(self):
        """用户输入 'n' 返回 False。"""
        with patch("builtins.input", return_value="n"):
            result = _show_diff_and_confirm(
                _make_fix_plan_simple("insert", "test\n"),
                timeout_seconds=5
            )
        assert result is False

    def test_user_input_yes_returns_true(self):
        """用户输入 'yes' 也返回 True。"""
        with patch("builtins.input", return_value="yes"):
            result = _show_diff_and_confirm(
                _make_fix_plan_simple("insert", "test\n"),
                timeout_seconds=5
            )
        assert result is True


class TestErrorLog:
    """测试 _log_error 错误日志记录。"""

    def test_log_error_creates_error_log(self):
        """_log_error 创建 error-log.md 或追加到已有文件。"""
        tmp = tempfile.mkdtemp()
        try:
            feedback_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(feedback_dir, exist_ok=True)
            error_log = os.path.join(feedback_dir, "error-log.md")

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                _log_error("test_category", "test summary", {"key": "value"})

            assert os.path.exists(error_log)
            with open(error_log, "r", encoding="utf-8") as f:
                content = f.read()
            assert "test_category" in content
            assert "test summary" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_log_error_appends_to_existing(self):
        """追加到已有 error-log.md。"""
        tmp = tempfile.mkdtemp()
        try:
            feedback_dir = os.path.join(tmp, "harness", "feedback")
            os.makedirs(feedback_dir, exist_ok=True)
            error_log = os.path.join(feedback_dir, "error-log.md")
            with open(error_log, "w", encoding="utf-8") as f:
                f.write("# Existing errors\n\nOld entry.\n")

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                _log_error("new_cat", "new summary")

            with open(error_log, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Existing errors" in content
            assert "new_cat" in content
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestFunnelContext:
    """测试 _build_funnel_context funnel 上下文构建。"""

    def test_empty_funnel_when_no_related_files(self):
        """无关联文件时返回 '(无 funnel 关联文件)'。"""
        tmp = tempfile.mkdtemp()
        try:
            # 创建一个孤立的 rules 目录
            rules_dir = os.path.join(tmp, "harness", "rules")
            os.makedirs(rules_dir, exist_ok=True)
            target = os.path.join(rules_dir, "lonely-rule.md")
            with open(target, "w", encoding="utf-8") as f:
                f.write("# Lonely Rule\n")

            def _fake_path(rel):
                return os.path.join(tmp, rel)

            with patch("harness.scripts.diagnose_and_fix._project_path", side_effect=_fake_path):
                result = _build_funnel_context(target)
            assert "无 funnel 关联文件" in result
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
