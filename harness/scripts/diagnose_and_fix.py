# diagnose_and_fix.py — 自我升级引擎：反馈信号驱动的自动诊断与修复
# 扫描反馈信号中的重复模式 → LLM 根因诊断 → git worktree 沙盒验证 → 合并或降级。
# 用法: python harness/scripts/diagnose_and_fix.py [--dry-run] [--timeout N]

import os
import sys
import json
import re
import fnmatch
import subprocess
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

_DEFAULT_CONFIG = {
    "auto_levels": [
        {"glob": "harness/rules/*", "level": "auto"},
        {"glob": "harness/workflow/*", "level": "semi-auto"},
        {"glob": ".claude/agents/*", "level": "semi-auto"},
        {"glob": ".claude/commands/*", "level": "semi-auto"},
        {"glob": "harness/hooks/*", "level": "disabled"},
        {"glob": "harness/skills/*", "level": "disabled"},
        {"glob": "harness/prompts/*", "level": "semi-auto"},
    ],
    "safety_boundary": {
        "add_max_lines": 50,
        "replace_max_lines": 20,
        "delete": "require_confirmation",
    },
    "dedup": {
        "window_hours": 24,
    },
}


def _project_path(rel: str) -> str:
    return os.path.join(_PROJECT_ROOT, rel)


# ============================================================
# 配置加载
# ============================================================

def _load_config() -> dict:
    """加载 self-upgrade.yaml 配置，缺失时返回默认值。"""
    config_path = _project_path("harness/config/self-upgrade.yaml")
    if not os.path.exists(config_path):
        print(f"[config] {config_path} 不存在，使用默认配置。")
        return dict(_DEFAULT_CONFIG)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        print(f"[config] 读取 {config_path} 失败: {e}，使用默认配置。")
        return dict(_DEFAULT_CONFIG)

    config = _parse_minimal_yaml(raw)
    return config


def _parse_minimal_yaml(raw: str) -> dict:
    """最小化 YAML 解析器：仅处理 self-upgrade.yaml 的简单结构。

    支持顶层三段：auto_levels（列表）、safety_boundary（键值对）、dedup（键值对）。
    复杂 YAML 特性（anchor、tag、flow style 嵌套）不实现。
    """
    result = {
        "auto_levels": list(_DEFAULT_CONFIG["auto_levels"]),
        "safety_boundary": dict(_DEFAULT_CONFIG["safety_boundary"]),
        "dedup": dict(_DEFAULT_CONFIG["dedup"]),
    }

    section: str = ""
    auto_levels: list[dict] = []

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # 检测段落边界
        if "auto_levels:" in stripped and not stripped.startswith(" ") and not stripped.startswith("\t"):
            section = "auto_levels"
            auto_levels = []
            continue
        if "safety_boundary:" in stripped and not stripped.startswith(" ") and not stripped.startswith("\t"):
            section = "safety_boundary"
            continue
        if "dedup:" in stripped and not stripped.startswith(" ") and not stripped.startswith("\t"):
            section = "dedup"
            continue

        if section == "auto_levels":
            # 列表项: - glob: "pattern" 或   level: value
            m_glob = re.match(r'^\s*-\s*glob:\s*["\']?(.+?)["\']?\s*$', stripped)
            if m_glob:
                auto_levels.append({"glob": m_glob.group(1).strip(), "level": "auto"})
                continue
            m_level = re.match(r'^\s*level:\s*(.+?)\s*$', stripped)
            if m_level and auto_levels:
                auto_levels[-1]["level"] = m_level.group(1).strip()

        elif section == "safety_boundary":
            if "add_max_lines" in stripped:
                try:
                    result["safety_boundary"]["add_max_lines"] = int(
                        re.split(r'[:：]', stripped, maxsplit=1)[1].strip()
                    )
                except (ValueError, IndexError):
                    pass
            elif "replace_max_lines" in stripped:
                try:
                    result["safety_boundary"]["replace_max_lines"] = int(
                        re.split(r'[:：]', stripped, maxsplit=1)[1].strip()
                    )
                except (ValueError, IndexError):
                    pass
            elif "delete" in stripped:
                val = re.split(r'[:：]', stripped, maxsplit=1)[1].strip()
                result["safety_boundary"]["delete"] = val

        elif section == "dedup":
            if "window_hours" in stripped:
                try:
                    result["dedup"]["window_hours"] = int(
                        re.split(r'[:：]', stripped, maxsplit=1)[1].strip()
                    )
                except (ValueError, IndexError):
                    pass

    if auto_levels:
        result["auto_levels"] = auto_levels

    return result


# ============================================================
# 自动程度匹配
# ============================================================

def _match_auto_level(file_path: str, auto_levels: list[dict]) -> str:
    """对文件路径匹配 glob，长匹配优先。返回 'auto' | 'semi-auto' | 'disabled'。

    未匹配到任何 glob 时默认返回 'semi-auto'（安全默认值）。
    如果任何匹配的 glob 的 level 为 disabled，即使有更长的 non-disabled 匹配也返回 disabled。
    """
    best_match_len = -1
    best_level = "semi-auto"  # 安全默认

    for entry in auto_levels:
        pattern = entry.get("glob", "")
        level = entry.get("level", "semi-auto")

        # fnmatch 在 Windows 上使用 / 作为分隔符，需统一格式避免匹配遗漏
        normalized_path = file_path.replace("\\", "/")
        normalized_pattern = pattern.replace("\\", "/")

        if fnmatch.fnmatch(normalized_path, normalized_pattern):
            match_len = len(normalized_pattern)

            # disabled 优先：任一 glob 匹配到 disabled 就是 disabled
            if level == "disabled":
                return "disabled"

            if match_len > best_match_len:
                best_match_len = match_len
                best_level = level

    return best_level


# ============================================================
# 24h 去重
# ============================================================

def _load_upgrade_history() -> list[dict]:
    """加载 upgrade-history.json，不存在则返回空列表。"""
    history_path = _project_path("harness/state/upgrade-history.json")
    if not os.path.exists(history_path):
        return []
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _check_dedup(signal_id: str, window_hours: int) -> bool:
    """检查 signal_id 在 window_hours 内是否有成功修复记录。

    返回 True 表示应跳过（已去重击中），False 表示可以继续。
    """
    history = _load_upgrade_history()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    for record in history:
        if record.get("signal_id") != signal_id:
            continue
        if record.get("verification_result") != "passed":
            continue  # 只有成功修复才触发去重
        try:
            ts = datetime.fromisoformat(record.get("timestamp", ""))
            if ts > cutoff:
                return True  # 24h 内已有成功修复，跳过
        except (ValueError, TypeError):
            continue

    return False


# ============================================================
# 安全边界检查
# ============================================================

def _apply_safety_boundary(fix_plan: list[dict], safety_config: dict) -> tuple[bool, str]:
    """对 fix_plan 中每个操作进行安全边界检查。

    返回 (passes, reason)。
    任一操作不过即整体不通过。混合操作按最严格规则判定。
    """
    add_max = safety_config.get("add_max_lines", 50)
    replace_max = safety_config.get("replace_max_lines", 20)
    delete_policy = safety_config.get("delete", "require_confirmation")

    issues: list[str] = []

    for i, fix in enumerate(fix_plan):
        op_type = fix.get("type", "insert")
        content = fix.get("content", "")
        line_count = len(content.splitlines()) if isinstance(content, str) else 0

        if op_type == "delete":
            # 删除任何行 → 降级
            issues.append(f"fix_plan[{i}]: delete 操作需要人工确认（文件: {fix.get('file', '?')})")

        elif op_type == "insert" or op_type == "create":
            if line_count > add_max:
                issues.append(
                    f"fix_plan[{i}]: insert {line_count} 行超过阈值 {add_max} "
                    f"（文件: {fix.get('file', '?')})"
                )

        elif op_type == "replace":
            if line_count > replace_max:
                issues.append(
                    f"fix_plan[{i}]: replace {line_count} 行超过阈值 {replace_max} "
                    f"（文件: {fix.get('file', '?')})"
                )

    if issues:
        return False, "; ".join(issues)

    # 也检查是否有任何 delete
    has_delete = any(f.get("type") == "delete" for f in fix_plan)
    if has_delete and delete_policy == "require_confirmation":
        return False, "fix_plan 包含 delete 操作，需要人工确认"

    return True, ""


# ============================================================
# Funnel 上下文构建
# ============================================================

def _extract_file_path_from_rule_ref(rule_ref: str) -> str:
    """从 rule_ref 中提取文件路径。

    如 "harness/rules/coding-rules.md#4" → "harness/rules/coding-rules.md"
    如 "coding-rules.md#4" → "harness/rules/coding-rules.md" (补全)
    """
    file_part = rule_ref.split("#")[0].strip() if "#" in rule_ref else rule_ref.strip()
    # 如果是短名，尝试补全到 harness/rules/
    if not file_part.startswith("harness/") and not file_part.startswith(".claude/"):
        file_part = f"harness/rules/{file_part}"
    return file_part


def _build_funnel_context(target_file: str) -> str:
    """构建宽上下文 — 收集 funnel 关联文件的内容。

    funnel: agent 定义文件 → workflow 文件中引用；规则文件 → 其他规则文件的交叉引用。
    """
    parts: list[str] = []
    target_normalized = target_file.replace("\\", "/")

    # agent→workflow 引用链
    if ".claude/agents/" in target_normalized:
        agent_name = os.path.splitext(os.path.basename(target_normalized))[0]
        # 搜索 workflow 文件中是否提到了此 agent
        for wf_file in _find_related_workflow_files(agent_name):
            content = _read_file_snippet(wf_file, 3000)
            if content:
                parts.append(f"### 关联工作流: {wf_file}\n```\n{content}\n```")

    # 规则交叉引用
    if "harness/rules/" in target_normalized:
        for rule_file in _find_related_rule_files(target_normalized):
            content = _read_file_snippet(rule_file, 3000)
            if content:
                parts.append(f"### 关联规则: {rule_file}\n```\n{content}\n```")

    return "\n\n".join(parts) if parts else "(无 funnel 关联文件)"


def _find_related_workflow_files(agent_name: str) -> list[str]:
    """搜索 workflow 命令文件中提及该 agent 的文件。"""
    results: list[str] = []
    search_dirs = [
        _project_path(".claude/commands/workflow"),
    ]
    for sdir in search_dirs:
        if not os.path.isdir(sdir):
            continue
        for fname in os.listdir(sdir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(sdir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                if agent_name in content:
                    results.append(fpath)
            except OSError:
                continue
    return results


def _find_related_rule_files(target_file: str) -> list[str]:
    """搜索其他规则文件中引用目标规则的部分。"""
    results: list[str] = []
    rules_dir = _project_path("harness/rules")
    if not os.path.isdir(rules_dir):
        return results

    target_basename = os.path.basename(target_file)
    for fname in os.listdir(rules_dir):
        fpath = os.path.join(rules_dir, fname)
        fpath_normalized = fpath.replace("\\", "/")
        if fpath_normalized == target_file.replace("\\", "/"):
            continue  # 跳过自己
        if not fname.endswith(".md"):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            if target_basename in content:
                results.append(fpath)
        except OSError:
            continue
    return results


def _read_file_snippet(file_path: str, max_chars: int) -> str:
    """读取文件内容，超过 max_chars 时截断。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n... [截断: 原文件 {len(content)} 字符]"
        return content
    except OSError:
        return ""


# ============================================================
# LLM 诊断
# ============================================================

def _call_llm_diagnosis(target_file: str, rule_ref: str, history_signals: list[dict]) -> dict | None:
    """调用 LLM 进行根因诊断，返回解析后的 fix_plan 或 None。"""
    from app.analyzer.llm_assistant import _get_llm_config, _call_llm, check_api_key_available

    has_key, _ = check_api_key_available(enable_dotenv=True)
    if not has_key:
        print("[LLM] API Key 未配置，无法自动诊断。")
        return None

    config = _get_llm_config(enable_dotenv=True)
    if not config.get("api_key"):
        print("[LLM] API Key 为空，无法自动诊断。")
        return None

    # 加载 prompt 模板
    prompt_path = _project_path("harness/prompts/diagnosis.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except OSError as e:
        print(f"[LLM] 无法读取 diagnosis.txt: {e}")
        return None

    # 构建上下文（带截断）
    target_content = _read_file_snippet(target_file, 5000)
    funnel_context = _build_funnel_context(target_file)
    if len(funnel_context) > 3000:
        funnel_context = funnel_context[:3000] + "\n\n... [funnel 上下文截断]"

    signals_text = json.dumps(history_signals, ensure_ascii=False, indent=2)
    if len(signals_text) > 2000:
        signals_text = signals_text[:2000] + "\n... [信号内容截断]"

    # 填充模板
    diagnosis_prompt = prompt_template.replace("{{TARGET_FILE_CONTENT}}", target_content)
    diagnosis_prompt = diagnosis_prompt.replace("{{FUNNEL_FILES}}", funnel_context)
    diagnosis_prompt = diagnosis_prompt.replace("{{HISTORY_SIGNALS}}", signals_text)

    system_prompt = diagnosis_prompt
    user_prompt = f"请分析以下 rule_ref 的重复反馈信号并生成修复方案: {rule_ref}"

    print(f"[LLM] 正在调用诊断 API (model={config.get('model')}, max_tokens=4096, timeout=60)...")
    response = _call_llm(system_prompt, user_prompt, config, max_tokens=4096, timeout=60, silent=False)

    if response is None:
        print("[LLM] API 调用失败或返回为空。")
        return None

    return _parse_llm_response(response)


def _parse_llm_response(response: str) -> dict | None:
    """解析 LLM 返回的 JSON 修复方案，校验格式。"""
    # 尝试提取 JSON—— LLM 可能用 ```json 包裹或直接输出
    json_text = response.strip()

    # 尝试匹配 ```json ... ``` 代码块
    m = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', json_text)
    if m:
        json_text = m.group(1).strip()

    # 尝试匹配裸 JSON 对象
    try:
        result = json.loads(json_text)
    except json.JSONDecodeError:
        # 再试一次：找第一个 { 到最后一个 }
        m2 = re.search(r'\{[\s\S]*\}', json_text)
        if m2:
            try:
                result = json.loads(m2.group(0))
            except json.JSONDecodeError:
                print("[LLM] 返回内容无法解析为 JSON，降级输出。")
                return None
        else:
            print("[LLM] 返回内容不包含 JSON 对象，降级输出。")
            return None

    if not isinstance(result, dict):
        print("[LLM] 返回 JSON 不是 dict 类型，降级输出。")
        return None

    # 校验必需字段
    fix_plan = result.get("fix_plan")
    if not isinstance(fix_plan, list):
        print("[LLM] fix_plan 缺失或不是列表，降级输出。")
        return None

    for i, fix in enumerate(fix_plan):
        if not isinstance(fix, dict):
            print(f"[LLM] fix_plan[{i}] 不是 dict，降级输出。")
            return None
        for field in ("file", "type", "content", "reason"):
            if field not in fix:
                print(f"[LLM] fix_plan[{i}] 缺少必需字段 '{field}'，降级输出。")
                return None

    return result


# ============================================================
# Git Worktree 沙盒验证
# ============================================================

def _get_current_branch() -> str | None:
    """获取当前分支名。"""
    try:
        result = subprocess.run(
            ["git", "-C", _PROJECT_ROOT, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def _create_worktree(worktree_path: str) -> str | None:
    """创建 git worktree，返回 worktree 分支名。"""
    current_branch = _get_current_branch()
    if current_branch is None:
        print("[worktree] 无法确定当前分支。")
        return None

    # worktree 分支名：基于当前分支和时间戳
    branch_name = f"self-upgrade-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    try:
        result = subprocess.run(
            ["git", "-C", _PROJECT_ROOT, "worktree", "add", "-b", branch_name, worktree_path, current_branch],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"[worktree] 创建失败: {result.stderr.strip()}")
            return None
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        print(f"[worktree] 创建异常: {e}")
        return None
    except FileNotFoundError:
        print("[worktree] git 命令不可用。")
        return None

    print(f"[worktree] 已创建: {worktree_path} (branch: {branch_name})")
    return branch_name


def _apply_fixes_in_worktree(worktree_path: str, fix_plan: list[dict]) -> bool:
    """在 worktree 中应用修复方案。返回 True 表示全部应用成功。"""
    for i, fix in enumerate(fix_plan):
        op_type = fix.get("type", "insert")
        file_rel = fix.get("file", "")
        content = fix.get("content", "")

        file_abs = os.path.join(worktree_path, file_rel)

        try:
            if op_type == "create":
                os.makedirs(os.path.dirname(file_abs), exist_ok=True)
                with open(file_abs, "w", encoding="utf-8") as f:
                    f.write(content)

            elif op_type == "insert":
                # 插入到文件末尾
                os.makedirs(os.path.dirname(file_abs), exist_ok=True)
                existing = ""
                if os.path.exists(file_abs):
                    with open(file_abs, "r", encoding="utf-8") as f:
                        existing = f.read()
                # 确保换行分隔
                if existing and not existing.endswith("\n"):
                    existing += "\n"
                with open(file_abs, "w", encoding="utf-8") as f:
                    f.write(existing + content)

            elif op_type == "replace":
                os.makedirs(os.path.dirname(file_abs), exist_ok=True)
                with open(file_abs, "w", encoding="utf-8") as f:
                    f.write(content)

            elif op_type == "delete":
                if os.path.exists(file_abs):
                    os.remove(file_abs)

            else:
                print(f"[fix] 未知操作类型 '{op_type}'，跳过 fix_plan[{i}]。")
                return False

        except OSError as e:
            print(f"[fix] 应用 fix_plan[{i}] 到 {file_abs} 失败: {e}")
            return False

    return True


def _run_verification(worktree_path: str) -> tuple[bool, list[str]]:
    """在 worktree 中运行验证：check_structure + pytest + agent YAML frontmatter。

    返回 (passed, failures)。
    """
    failures: list[str] = []

    # 1. check_structure.py
    check_script = os.path.join(worktree_path, "harness", "scripts", "check_structure.py")
    if os.path.exists(check_script):
        try:
            result = subprocess.run(
                [sys.executable, check_script],
                capture_output=True, text=True, timeout=30, cwd=worktree_path
            )
            combined = result.stdout + result.stderr
            if "FAIL" in combined or result.returncode != 0:
                failures.append(f"check_structure.py 失败: {combined[-300:]}")
            else:
                print("[verify] check_structure.py PASS")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            failures.append(f"check_structure.py 异常: {e}")
    else:
        failures.append("check_structure.py 在 worktree 中不存在")

    # 2. pytest
    tests_dir = os.path.join(worktree_path, "tests")
    if os.path.isdir(tests_dir):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v"],
                capture_output=True, text=True, timeout=120, cwd=worktree_path
            )
            combined = result.stdout + result.stderr
            if "FAILED" in combined:
                # 提取失败数量
                failed_match = re.search(r'(\d+)\s+failed', combined)
                failed_count = failed_match.group(1) if failed_match else "?"
                failures.append(f"pytest: {failed_count} 个测试失败")
            elif result.returncode != 0:
                failures.append(f"pytest 执行异常 (exit={result.returncode})")
            else:
                print("[verify] pytest PASS")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            failures.append(f"pytest 异常: {e}")
    else:
        print("[verify] tests/ 目录不存在，跳过 pytest。")

    # 3. agent YAML frontmatter 有效性检查
    agents_dir = os.path.join(worktree_path, ".claude", "agents")
    if os.path.isdir(agents_dir):
        for fname in os.listdir(agents_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(agents_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                # 检查是否有 --- 包裹的 YAML frontmatter，且包含 name 字段
                if not content.startswith("---"):
                    failures.append(f"agent {fname}: 缺少 YAML frontmatter 起始标记")
                    continue
                second_delim = content.find("---", 3)
                if second_delim == -1:
                    failures.append(f"agent {fname}: YAML frontmatter 未闭合")
                    continue
                frontmatter = content[3:second_delim].strip()
                if "name:" not in frontmatter:
                    failures.append(f"agent {fname}: frontmatter 缺少 name 字段")
            except OSError as e:
                failures.append(f"agent {fname}: 读取失败: {e}")
        if not failures:
            print("[verify] Agent YAML frontmatter PASS")
    else:
        print("[verify] .claude/agents/ 目录不存在，跳过 frontmatter 检查。")

    return (len(failures) == 0, failures)


def _merge_worktree(worktree_path: str, branch_name: str) -> bool:
    """将 worktree 分支合并回当前分支并清理 worktree。"""
    result = None
    try:
        # 合并
        result = subprocess.run(
            ["git", "-C", _PROJECT_ROOT, "merge", branch_name, "--no-edit"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"[worktree] merge 失败: {result.stderr.strip()}")
            return False

        print("[worktree] merge 成功")
        return True

    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        print(f"[worktree] merge 异常: {e}")
        return False
    finally:
        _remove_worktree(worktree_path, force=(result is not None and result.returncode != 0))


def _remove_worktree(worktree_path: str, force: bool = False) -> None:
    """移除 worktree。"""
    try:
        cmd = ["git", "-C", _PROJECT_ROOT, "worktree", "remove"]
        if force:
            cmd.append("--force")
        cmd.append(worktree_path)
        subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # 如果目录仍然存在，手动删除
        if os.path.exists(worktree_path):
            shutil.rmtree(worktree_path, ignore_errors=True)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        # 尝试手动删除
        if os.path.exists(worktree_path):
            shutil.rmtree(worktree_path, ignore_errors=True)


def _discard_worktree(worktree_path: str) -> None:
    """丢弃 worktree（不合并）。"""
    # git branch -D 不支持 glob，需先列出匹配分支再逐一删除
    try:
        result = subprocess.run(
            ["git", "-C", _PROJECT_ROOT, "branch", "--list", "self-upgrade-*"],
            capture_output=True, text=True, timeout=10
        )
        branches = [b.strip() for b in result.stdout.splitlines() if b.strip()]
        for branch in branches:
            subprocess.run(
                ["git", "-C", _PROJECT_ROOT, "branch", "-D", branch],
                capture_output=True, text=True, timeout=10
            )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    _remove_worktree(worktree_path, force=True)


def _sandbox_verify(fix_plan: list[dict], is_dry_run: bool) -> tuple[bool, str, list[str]]:
    """在 git worktree 沙盒中验证修复方案。

    返回 (success, branch_name, affected_files)。
    若 is_dry_run 为 True，跳过 worktree 创建，仅模拟输出。
    """
    if is_dry_run:
        print("[dry-run] 跳过 worktree 沙盒验证。")
        affected = [f.get("file", "?") for f in fix_plan]
        return False, "", affected

    # 检查 worktree 基础路径是否在同一磁盘分区
    worktree_path = os.path.normpath(os.path.join(_PROJECT_ROOT, "..", ".self-upgrade-worktree"))
    if os.path.exists(worktree_path):
        # 清理旧的残留 worktree
        _remove_worktree(worktree_path, force=True)
        if os.path.exists(worktree_path):
            shutil.rmtree(worktree_path, ignore_errors=True)

    # 检查磁盘分区
    project_drive = os.path.splitdrive(_PROJECT_ROOT)[0]
    worktree_drive = os.path.splitdrive(os.path.abspath(worktree_path))[0]
    if project_drive and worktree_drive and project_drive != worktree_drive:
        print(f"[worktree] 错误: worktree 必须在同一磁盘分区 ({project_drive})，"
              f"但目标路径在 {worktree_drive}")
        return False, "", []

    branch_name = _create_worktree(worktree_path)
    if branch_name is None:
        return False, "", []

    # 应用修复
    if not _apply_fixes_in_worktree(worktree_path, fix_plan):
        _discard_worktree(worktree_path)
        return False, "", []

    # 运行验证
    passed, failures = _run_verification(worktree_path)

    if passed:
        # 合并
        merged = _merge_worktree(worktree_path, branch_name)
        if merged:
            affected = [f.get("file", "?") for f in fix_plan]
            return True, branch_name, affected
        else:
            _discard_worktree(worktree_path)
            # 记录失败到 error-log
            _log_error("sandbox_merge_failed", f"merge {branch_name} 失败",
                       {"failures": ["merge 失败"]})
            return False, branch_name, []
    else:
        # 验证失败 → 丢弃沙盒
        _discard_worktree(worktree_path)
        # 记录失败
        _log_error("sandbox_verify_failed", f"worktree 验证失败 ({len(failures)} 项)",
                   {"failures": failures})
        return False, branch_name, []


# ============================================================
# Semi-auto 交互流程
# ============================================================

def _show_diff_and_confirm(fix_plan: list[dict], timeout_seconds: int) -> bool:
    """展示修复方案摘要，等待用户确认 y/n。

    返回 True 表示用户确认，False 表示拒绝或超时。
    """
    print("\n" + "=" * 60)
    print("  [semi-auto] 以下修复方案等待确认：")
    print("=" * 60)
    for i, fix in enumerate(fix_plan):
        op_type = fix.get("type", "?")
        file_path = fix.get("file", "?")
        reason = fix.get("reason", "(无说明)")
        content = fix.get("content", "")
        line_count = len(content.splitlines()) if isinstance(content, str) else 0
        print(f"\n  [{i+1}] {op_type.upper()} | {file_path} | {line_count} 行")
        print(f"       理由: {reason}")
        # 展示内容预览（最多 10 行）
        if isinstance(content, str) and content:
            preview = content[:500]
            if len(content) > 500:
                preview += "..."
            print(f"       内容: {preview[:300]}")

    print("\n" + "-" * 60)

    try:
        import threading
        import time as time_mod

        result_container: list[str] = []

        def input_thread():
            try:
                reply = input("  是否应用以上修复? (y/n) [默认 n, {0} 秒超时]: ".format(timeout_seconds))
                result_container.append(reply.strip().lower() if reply else "")
            except (EOFError, OSError):
                result_container.append("")

        thread = threading.Thread(target=input_thread, daemon=True)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if not result_container:
            print(f"\n  [semi-auto] 等待超时 ({timeout_seconds}s)，降级输出。")
            return False

        reply = result_container[0]
        if reply in ("y", "yes"):
            return True
        else:
            print("  [semi-auto] 用户拒绝，降级输出。")
            return False

    except KeyboardInterrupt:
        print("\n  [semi-auto] 用户中断，降级输出。")
        return False


# ============================================================
# 降级输出
# ============================================================

def _degrade_to_proposal(rule_ref: str, diagnosis: dict | None, reason: str) -> None:
    """将修复方案降级输出到 rule-evolution-proposal.md。"""
    proposal_path = _project_path("harness/feedback/rule-evolution-proposal.md")
    now = datetime.now(timezone.utc).isoformat()

    if diagnosis and isinstance(diagnosis, dict):
        diag_text = json.dumps(diagnosis, ensure_ascii=False, indent=2)
    else:
        diag_text = "无法自动诊断 — LLM 不可用或返回格式异常"

    entry = (
        f"\n## 自我升级诊断 [降级] — `{rule_ref}`\n\n"
        f"> 生成时间: {now}\n"
        f"> 状态: 待确认（降级 — {reason}）\n\n"
        f"**诊断结果**:\n```json\n{diag_text}\n```\n\n"
        f"**降级原因**: {reason}\n"
    )

    # 原子追加写入
    if os.path.exists(proposal_path):
        with open(proposal_path, "r", encoding="utf-8") as f:
            existing = f.read()
        new_content = existing + f"\n---\n{entry}"
    else:
        new_content = f"# 规则演化建议\n\n> 自动生成于 {now}\n\n---\n{entry}"

    tmp_path = proposal_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, proposal_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    print(f"[degrade] 修复方案已降级输出到 {proposal_path}")


# ============================================================
# 升级历史记录
# ============================================================

def _write_upgrade_history(signal_id: str, diagnosis_summary: str, affected_files: list[str],
                           verification_result: str, rollback_note: str = "") -> None:
    """将修复记录原子写入 upgrade-history.json。"""
    history_path = _project_path("harness/state/upgrade-history.json")
    history = _load_upgrade_history()

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signal_id": signal_id,
        "diagnosis_summary": diagnosis_summary[:100],
        "affected_files": affected_files,
        "verification_result": verification_result,
    }
    if rollback_note:
        record["rollback_note"] = rollback_note

    history.append(record)

    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    tmp_path = history_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, history_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================
# 错误日志
# ============================================================

def _log_error(category: str, summary: str, details: dict | None = None) -> None:
    """记录错误到 harness/feedback/error-log.md。"""
    error_log_path = _project_path("harness/feedback/error-log.md")
    now = datetime.now(timezone.utc).isoformat()
    details_str = json.dumps(details, ensure_ascii=False, indent=2) if details else "(无)"

    entry = (
        f"\n### {now} — [{category}] {summary}\n\n"
        f"```json\n{details_str}\n```\n"
    )

    if os.path.exists(error_log_path):
        with open(error_log_path, "r", encoding="utf-8") as f:
            existing = f.read()
        new_content = existing + f"\n---\n{entry}"
    else:
        new_content = f"# Error Log\n\n> 自动生成于 {now}\n\n{entry}"

    tmp_path = error_log_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, error_log_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================
# 主流程
# ============================================================

def main() -> None:
    is_dry_run = "--dry-run" in sys.argv
    timeout_seconds = 300

    # 解析 --timeout 参数
    for i, arg in enumerate(sys.argv):
        if arg == "--timeout" and i + 1 < len(sys.argv):
            try:
                timeout_seconds = int(sys.argv[i + 1])
            except ValueError:
                pass

    if is_dry_run:
        print("[mode] DRY-RUN — 仅诊断，不修改文件。")

    print("=" * 60)
    print("  Harness 自我升级引擎 v0.1")
    print("=" * 60)

    # 1. 加载配置
    config = _load_config()
    auto_levels = config.get("auto_levels", _DEFAULT_CONFIG["auto_levels"])
    safety_boundary = config.get("safety_boundary", _DEFAULT_CONFIG["safety_boundary"])
    dedup_config = config.get("dedup", _DEFAULT_CONFIG["dedup"])
    window_hours = dedup_config.get("window_hours", 24)
    print(f"[config] auto_levels: {len(auto_levels)} 条 glob 规则")
    print(f"[config] safety_boundary: add≤{safety_boundary.get('add_max_lines', '?')}, "
          f"replace≤{safety_boundary.get('replace_max_lines', '?')}, "
          f"delete={safety_boundary.get('delete', '?')}")
    print(f"[config] dedup: {window_hours}h 窗口")

    # 2. 加载反馈信号
    from harness.state.feedback_engine import FeedbackEngine
    engine = FeedbackEngine()
    patterns = engine.detect_patterns()

    if not patterns:
        print("\n[result] 未检测到重复模式 (occurrences >= 3)。无需处理。")
        return

    print(f"\n[patterns] 检测到 {len(patterns)} 个重复模式：")
    for p in patterns:
        print(f"  - {p['rule_ref']}: {p['occurrences']} 次 ({p['severity']})")

    # 3. 按 rule_ref 分组历史信号
    all_signals = engine.load_signals()
    signals_by_rule: dict[str, list[dict]] = {}
    for s in all_signals:
        ref = s.rule_ref
        if ref not in signals_by_rule:
            signals_by_rule[ref] = []
        signals_by_rule[ref].append(s.to_dict())

    # 4. 逐模式处理
    auto_fixed = 0
    degraded = 0
    skipped = 0

    for pattern in patterns:
        rule_ref = pattern["rule_ref"]
        print(f"\n{'─' * 60}")
        print(f"[处理] rule_ref: {rule_ref} ({pattern['occurrences']} 次)")

        # 4a. 24h 去重
        if _check_dedup(rule_ref, window_hours):
            print(f"[dedup] {rule_ref} 在 {window_hours}h 内已有成功修复，跳过。")
            skipped += 1
            continue

        # 4b. 确定目标文件
        target_file = _extract_file_path_from_rule_ref(rule_ref)
        target_abs = _project_path(target_file)
        print(f"[target] 目标文件: {target_file}")

        # 4c. 自动程度检查（二级门禁 — 预检查）
        auto_level = _match_auto_level(target_file, auto_levels)
        print(f"[auto_level] {target_file} → {auto_level}")

        if auto_level == "disabled":
            print(f"[skip] {target_file} 的自动程度为 disabled，跳过。")
            skipped += 1
            continue

        # 4d. LLM 诊断
        history_signals = signals_by_rule.get(rule_ref, [])
        diagnosis = _call_llm_diagnosis(target_abs, rule_ref, history_signals)

        root_cause = ""
        if diagnosis is None:
            # LLM 不可用 → 降级
            root_cause = "无法自动诊断 — LLM 不可用或返回格式异常"
            print(f"[LLM] {root_cause}")
            _degrade_to_proposal(rule_ref, None, root_cause)
            _write_upgrade_history(
                signal_id=rule_ref,
                diagnosis_summary=root_cause[:100],
                affected_files=[],
                verification_result="degraded",
                rollback_note=root_cause,
            )
            degraded += 1
            continue

        root_cause = diagnosis.get("root_cause", "(未提供根因)")
        category = diagnosis.get("category", "unknown")
        fix_plan = diagnosis.get("fix_plan", [])
        print(f"[diagnosis] 根因: {root_cause}")
        print(f"[diagnosis] 类别: {category}")
        print(f"[diagnosis] 修复项: {len(fix_plan)} 个")

        if not fix_plan:
            print("[diagnosis] fix_plan 为空，降级输出。")
            _degrade_to_proposal(rule_ref, diagnosis, "fix_plan 为空")
            _write_upgrade_history(
                signal_id=rule_ref,
                diagnosis_summary=root_cause[:100],
                affected_files=[],
                verification_result="degraded",
                rollback_note="fix_plan 为空",
            )
            degraded += 1
            continue

        # 4e. 安全边界检查（一级门禁）
        sb_passed, sb_reason = _apply_safety_boundary(fix_plan, safety_boundary)
        print(f"[safety] 安全边界: {'通过' if sb_passed else '不通过 — ' + sb_reason}")

        if not sb_passed:
            # 一级门禁不通过 → 降级（二级门禁即使是 auto 也降级）
            _degrade_to_proposal(rule_ref, diagnosis, sb_reason)
            _write_upgrade_history(
                signal_id=rule_ref,
                diagnosis_summary=root_cause[:100],
                affected_files=[f.get("file", "?") for f in fix_plan],
                verification_result="degraded",
                rollback_note=sb_reason,
            )
            degraded += 1
            continue

        # 4f. 根据二级门禁（auto_level）决定执行方式
        if is_dry_run:
            print(f"[dry-run] 修复方案验证跳过，将输出到 proposal。")
            _degrade_to_proposal(rule_ref, diagnosis, "dry-run 模式")
            degraded += 1
            continue

        if auto_level == "semi-auto":
            # 展示 diff 等待确认
            if not _show_diff_and_confirm(fix_plan, timeout_seconds):
                _degrade_to_proposal(rule_ref, diagnosis, f"semi-auto: 用户拒绝或超时 ({timeout_seconds}s)")
                _write_upgrade_history(
                    signal_id=rule_ref,
                    diagnosis_summary=root_cause[:100],
                    affected_files=[f.get("file", "?") for f in fix_plan],
                    verification_result="degraded",
                    rollback_note="用户拒绝",
                )
                degraded += 1
                continue

        # 4g. 沙盒验证 + 合并（auto 级别 + semi-auto 已确认 都走这条路）
        success, branch, affected = _sandbox_verify(fix_plan, is_dry_run)

        if success:
            print(f"\n[success] 自动修复完成! {len(affected)} 个文件已修改。")
            _write_upgrade_history(
                signal_id=rule_ref,
                diagnosis_summary=root_cause[:100],
                affected_files=affected,
                verification_result="passed",
            )
            auto_fixed += 1
        else:
            print(f"\n[fail] 沙盒验证失败，修复方案已降级输出。")
            _degrade_to_proposal(rule_ref, diagnosis, "沙盒验证失败")
            _write_upgrade_history(
                signal_id=rule_ref,
                diagnosis_summary=root_cause[:100],
                affected_files=[f.get("file", "?") for f in fix_plan],
                verification_result="failed",
                rollback_note="沙盒验证失败",
            )
            degraded += 1

    # 5. 汇总
    print(f"\n{'=' * 60}")
    print(f"  完成: 自动修复 {auto_fixed} | 降级输出 {degraded} | 跳过 {skipped}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
