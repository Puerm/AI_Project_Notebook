# harness_deploy.py — Harness 框架个性化部署：LLM 检测新项目并生成适配建议，交互式确认
# 用法: python harness/scripts/harness_deploy.py <目标路径>

import os
import sys
import json
import shutil
import subprocess
import tempfile

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HARNESS_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(HARNESS_ROOT)
sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# Shared detection logic (from init_project.py)
# ============================================================

EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", "dist", "build", "harness", ".claude",
}

CONFIG_PATTERNS = {
    "python": [
        ("pyproject.toml", "pip"), ("setup.py", "pip"),
        ("requirements.txt", "pip"), ("Pipfile", "pipenv"), ("poetry.lock", "poetry"),
    ],
    "javascript": [
        ("package.json", "npm"), ("yarn.lock", "yarn"),
        ("pnpm-lock.yaml", "pnpm"), ("bun.lockb", "bun"),
    ],
    "typescript": [
        ("package.json", "npm"), ("yarn.lock", "yarn"), ("tsconfig.json", "npm"),
    ],
    "go": [("go.mod", "go")],
    "rust": [("Cargo.toml", "cargo")],
}

TEST_PATTERNS = {
    "python": {
        "pytest": ("import pytest", "pytest", "python -m pytest tests/ -v"),
        "unittest": ("import unittest", "unittest", "python -m unittest discover tests/"),
    },
    "javascript": {
        "jest": (r'jest|"jest"', "jest", "npx jest"),
        "vitest": ("vitest", "vitest", "npx vitest"),
        "mocha": ("mocha", "mocha", "npx mocha"),
    },
    "typescript": {
        "jest": (r'jest|"jest"', "jest", "npx jest"),
        "vitest": ("vitest", "vitest", "npx vitest"),
        "mocha": ("mocha", "mocha", "npx mocha"),
    },
    "go": {"go_test": ("testing", "go test", "go test ./...")},
    "rust": {"cargo_test": ("#[test]", "cargo test", "cargo test")},
}

DEFAULT_TEST_COMMANDS = {
    "python": "python -m pytest tests/ -v",
    "javascript": "npm test", "typescript": "npm test",
    "go": "go test ./...", "rust": "cargo test",
}

DEFAULT_PACKAGE_MANAGERS = {
    "python": "pip", "javascript": "npm",
    "typescript": "npm", "go": "go", "rust": "cargo",
}

VALIDATION_COMMANDS = {
    "python": "python harness/scripts/check_structure.py",
    "javascript": "node harness/scripts/check_structure.js",
    "typescript": "node harness/scripts/check_structure.js",
    "go": "go run harness/scripts/check_structure.go",
    "rust": "cargo run --manifest-path harness/scripts/check_structure.toml",
}

FRAMEWORK_NAMES = {
    "python": "Flask / Django / FastAPI",
    "javascript": "Express / React / Vue",
    "typescript": "Next.js / NestJS / Angular",
    "go": "Gin / Echo / Chi",
    "rust": "Actix / Rocket / Axum",
}

EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".jsx": "javascript", ".go": "go",
    ".rs": "rust", ".java": "java", ".rb": "ruby",
}


# ============================================================
# Static detection
# ============================================================

def _detect_project_features(target_path):
    """静态检测项目特征，LLM 不可用时的降级路径。"""
    ext_count = {}
    config_found = {}
    languages = []

    for root, _dirs, files in os.walk(target_path):
        dirs_to_skip = set()
        for d in _dirs:
            if d.startswith(".") or d in EXCLUDE_DIRS:
                dirs_to_skip.add(d)
        _dirs[:] = [d for d in _dirs if d not in dirs_to_skip]

        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext:
                ext = ext.lower()
                ext_count[ext] = ext_count.get(ext, 0) + 1
            for lang, patterns in CONFIG_PATTERNS.items():
                for cfg_file, pkg_mgr in patterns:
                    if fname == cfg_file:
                        config_found[lang] = pkg_mgr
        if root.count(os.sep) - target_path.count(os.sep) > 3:
            _dirs[:] = []

    lang_count = {}
    for ext, count in ext_count.items():
        lang = EXT_TO_LANG.get(ext)
        if lang:
            lang_count[lang] = lang_count.get(lang, 0) + count

    sorted_langs = sorted(lang_count.items(), key=lambda x: x[1], reverse=True)
    languages = [lang for lang, _ in sorted_langs[:2]]
    if not languages:
        languages = ["unknown"]
    primary_lang = languages[0]

    package_manager = config_found.get(primary_lang, DEFAULT_PACKAGE_MANAGERS.get(primary_lang, "unknown"))
    test_command = DEFAULT_TEST_COMMANDS.get(primary_lang, "echo 'no tests configured'")
    if primary_lang in TEST_PATTERNS:
        test_info = list(TEST_PATTERNS[primary_lang].values())[0]
        test_command = test_info[2]

    return {
        "languages": languages,
        "framework": FRAMEWORK_NAMES.get(primary_lang, "unknown"),
        "domain": "待确认",
        "description": "（请用户提供项目描述）",
        "entry_point": "",
        "test_framework": test_info[1] if primary_lang in TEST_PATTERNS else "unknown",
        "test_command": test_command,
        "package_manager": package_manager,
        "source": "static",
    }


def _try_find_entry_point(target_path, languages):
    """尝试检测入口文件。"""
    candidates = {
        "python": ["main.py", "app.py", "manage.py", "cli.py"],
        "javascript": ["index.js", "main.js", "server.js", "app.js"],
        "typescript": ["src/index.ts", "src/main.ts", "src/server.ts"],
        "go": ["main.go", "cmd/main.go"],
        "rust": ["src/main.rs"],
    }
    for lang in languages:
        if lang in candidates:
            for c in candidates[lang]:
                full = os.path.join(target_path, c)
                if os.path.isfile(full):
                    return c
    return ""


def _collect_guiding_files(target_path, max_size=100):
    """收集引导文件内容用于 LLM 检测。"""
    guiding = {}
    guiding_names = [
        "README.md", "README", "readme.md",
        "package.json", "go.mod", "Cargo.toml", "pyproject.toml",
        "CMakeLists.txt", "Makefile", "docker-compose.yml",
    ]
    for fname in guiding_names:
        fpath = os.path.join(target_path, fname)
        if os.path.isfile(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                if len(content) > max_size * 100:
                    content = content[:max_size * 100] + "\n... (truncated)"
                guiding[fname] = content
            except (OSError, UnicodeDecodeError):
                guiding[fname] = "(binary or unreadable)"
    return guiding


def _collect_directory_summary(target_path, max_depth=3):
    """收集目录结构摘要。"""
    lines = []
    try:
        entries = sorted(os.listdir(target_path))
    except PermissionError:
        return "(permission denied)"

    for name in entries:
        if name in EXCLUDE_DIRS or name.startswith("."):
            continue
        full = os.path.join(target_path, name)
        if os.path.isdir(full):
            sub_entries = []
            try:
                subs = sorted(os.listdir(full))
            except PermissionError:
                subs = []
            for sn in subs:
                sub_full = os.path.join(full, sn)
                if os.path.isfile(sub_full):
                    sub_entries.append(sn)
            sub_count = len([s for s in subs if os.path.isdir(os.path.join(full, s))])
            lines.append(f"  {name}/ ({sub_count} dirs, {len(sub_entries)} files, e.g. {', '.join(sub_entries[:5])})")
        else:
            lines.append(f"  {name}")
    return "\n".join(lines[:50])


# ============================================================
# LLM detection
# ============================================================

def _check_llm_available():
    """检查 LLM API Key 是否可用。"""
    from app.analyzer.llm_assistant import check_api_key_available
    has_key, _ = check_api_key_available(enable_dotenv=True)
    return has_key


def _llm_detect_project(target_path, focus_fields=None):
    """使用 LLM 检测项目特征。focus_fields 限制只请求指定字段。"""
    from app.analyzer.llm_assistant import _get_llm_config, _call_llm

    config = _get_llm_config(enable_dotenv=True)
    if not config.get("api_key"):
        return None

    guiding = _collect_guiding_files(target_path)
    dir_summary = _collect_directory_summary(target_path)

    system_prompt = (
        "你是一个项目分析助手。根据提供的项目目录结构和关键文件内容，"
        "推断项目的基本信息。只输出 JSON，不要有任何其他文本。"
    )

    user_prompt = f"""分析以下项目并返回 JSON：

项目根目录: {os.path.basename(target_path)}

目录结构摘要:
{dir_summary}

关键文件内容:
"""
    for fname, content in guiding.items():
        preview = content[:500] if len(content) > 500 else content
        user_prompt += f"\n--- {fname} ---\n{preview}\n"

    if focus_fields:
        field_desc = ", ".join(focus_fields)
        user_prompt += f"\n只需返回以下字段（其他字段无需检测）：{field_desc}\n"
        user_prompt += r"""
请返回以下 JSON 格式：
{
"""
        for f in focus_fields:
            if f == "domain":
                user_prompt += '    "domain": "业务领域（如 Web 后端/前端/CLI 工具/数据科学，≤5字）",\n'
            elif f == "description":
                user_prompt += '    "description": "一句话项目描述（≤30字）",\n'
            elif f == "entry_point":
                user_prompt += '    "entry_point": "入口文件相对路径（如 main.py，未找到填空字符串）",\n'
        user_prompt += "}\n"
    else:
        user_prompt += r"""
请返回以下 JSON 格式（所有字段为字符串或字符串数组）：
{
    "languages": ["主要语言"],
    "framework": "主要框架（如 Flask/Django/React/Vue/Gin/Spring Boot，未知填 unknown）",
    "domain": "业务领域（如 Web 后端/前端/CLI 工具/数据科学，≤5字）",
    "description": "一句话项目描述（≤30字）",
    "entry_point": "入口文件相对路径（如 main.py，未找到填空字符串）"
}
"""

    try:
        response, _ = _call_llm(system_prompt, user_prompt, config, max_tokens=1024, timeout=60)
    except Exception as e:
        print(f"  [LLM] API 调用异常: {e}", file=sys.stderr)
        return None

    if not response:
        print("  [LLM] API 返回空响应", file=sys.stderr)
        return None

    try:
        # 尝试提取 JSON
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(response[json_start:json_end])
        else:
            print("  [LLM] 响应中未找到 JSON 对象", file=sys.stderr)
            return None
    except json.JSONDecodeError as e:
        print(f"  [LLM] JSON 解析失败: {e}", file=sys.stderr)
        return None

    return result


# ============================================================
# Phase 1: Project detection
# ============================================================

def _read_project_yaml_baseline(target_path):
    """读取已有 project.yaml 作为基线（init_project.py 或上次 deploy 的产出）。"""
    yaml_path = os.path.join(target_path, "harness", "config", "project.yaml")
    if not os.path.isfile(yaml_path):
        return None
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            baseline = yaml.safe_load(f)
        if isinstance(baseline, dict) and "project_name" in baseline:
            return baseline
    except Exception:
        pass
    return None


def detect_project(target_path, baseline=None):
    """检测项目特征，LLM 优先，不可用时降级为静态检测。

    baseline 为已有 project.yaml 内容（dict），存在时只补充缺失字段，
    不覆盖已确认的值。这保证 init → deploy 流水线不会互相覆盖。
    """
    print("\n[Phase 1] 检测项目特征...")
    primary_lang = None
    has_llm = _check_llm_available()

    if baseline:
        print("  检测到已有 project.yaml（由 init_project.py 生成），以此为基线补充缺失字段。")
    else:
        print("  未检测到 project.yaml，执行完整检测。")

    llm_result = None
    is_focus_mode = False
    llm_attempted = False
    if has_llm:
        print("  LLM API Key 已配置，使用 LLM 增强检测...")
        if baseline:
            # 只让 LLM 补充 baseline 中缺失的高阶字段（domain, description, entry_point）
            missing_fields = [k for k in ("domain", "description", "entry_point")
                            if not baseline.get(k) or baseline.get(k) == "待确认"]
            if missing_fields:
                is_focus_mode = True
                llm_attempted = True
                llm_result = _llm_detect_project(target_path, focus_fields=missing_fields)
            else:
                print("  所有字段已有值，跳过 LLM 检测。")
                llm_result = None
        else:
            llm_attempted = True
            llm_result = _llm_detect_project(target_path)
        if is_focus_mode:
            llm_success = bool(llm_result and isinstance(llm_result, dict) and llm_result)
        else:
            llm_success = bool(llm_result and "languages" in llm_result)
        if llm_success:
            print("  LLM 检测成功")
        else:
            if llm_attempted:
                print("  LLM 检测失败，降级为静态检测")
            llm_result = None
    else:
        print("  LLM API Key 未配置，使用静态检测（配置 ANTHROPIC_API_KEY 以获得更准确的适配）")

    static_result = _detect_project_features(target_path)
    entry_point = _try_find_entry_point(target_path, static_result.get("languages", []))

    # 从 baseline 继承已有字段，再叠加新检测结果（不覆盖已有值）
    result = {}
    if baseline:
        result.update(baseline)
        # 确保 languages 是列表格式
        if isinstance(result.get("languages"), str):
            result["languages"] = [result["languages"]]

    # LLM 增强：补充 baseline 中的缺失字段
    if llm_result:
        if llm_result.get("languages"):
            primary_lang = llm_result.get("languages", [""])[0]
            if not result.get("languages"):
                result["languages"] = llm_result.get("languages", static_result["languages"])
            if not result.get("framework") or result.get("framework") == "unknown":
                result["framework"] = llm_result.get("framework", static_result.get("framework", "unknown"))
        if not result.get("domain") or result.get("domain") == "待确认":
            result["domain"] = llm_result.get("domain", "")
        if not result.get("description"):
            result["description"] = llm_result.get("description", "")
        if not result.get("entry_point"):
            result["entry_point"] = llm_result.get("entry_point", entry_point or "")
        result["source"] = "llm"
    else:
        if not baseline:
            result = static_result
            result["entry_point"] = entry_point
            primary_lang = result["languages"][0] if result.get("languages") else "python"
        else:
            if not result.get("domain"):
                result["domain"] = static_result.get("domain", "")
            if not result.get("description"):
                result["description"] = static_result.get("description", "")
            if not result.get("entry_point"):
                result["entry_point"] = entry_point or ""
            if not primary_lang and result.get("languages"):
                primary_lang = result["languages"][0]

    # 静态检测结果补充 baseline 可能缺失的技术字段
    for key in ("test_framework", "test_command", "package_manager", "languages"):
        if not result.get(key):
            if key in static_result and static_result[key]:
                result[key] = static_result[key]

    if not primary_lang and result.get("languages"):
        primary_lang = result["languages"][0]

    if primary_lang and primary_lang not in VALIDATION_COMMANDS:
        result["validation_command"] = ""
    elif primary_lang:
        result["validation_command"] = VALIDATION_COMMANDS.get(primary_lang, result.get("validation_command", ""))

    result.setdefault("source", "static")
    result.setdefault("project_name", os.path.basename(target_path))

    _print_detection_summary(result)
    return result


def _print_detection_summary(features):
    """打印检测摘要供用户确认（spec 风险 1 缓解措施）。"""
    print("\n" + "=" * 60)
    print("  检测摘要（请确认以下检测结果是否正确）")
    print("=" * 60)
    print(f"  语言:        {', '.join(features['languages'])}")
    print(f"  框架:        {features.get('framework', 'unknown')}")
    print(f"  领域:        {features.get('domain', '待确认')}")
    print(f"  描述:        {features.get('description', '')}")
    print(f"  入口文件:     {features.get('entry_point', '(未检测到)')}")
    print(f"  包管理器:     {features.get('package_manager', 'unknown')}")
    print(f"  测试命令:     {features.get('test_command', '')}")
    print(f"  检测方式:     {features.get('source', 'unknown')}")
    print()


# ============================================================
# Phase 2: Adaptation
# ============================================================

def _parse_adaptable_zones(content):
    """解析 ADAPTABLE_ZONE 标记，返回 (通用区内容列表, 可适配区内容列表)。"""
    import re
    zones = []
    general = []
    pattern = r'<!-- ADAPTABLE_ZONE_START -->(.*?)<!-- ADAPTABLE_ZONE_END -->'
    last_end = 0
    for match in re.finditer(pattern, content, re.DOTALL):
        zones.append(match.group(1))
        general.append(content[last_end:match.start()])
        last_end = match.end()
    general.append(content[last_end:])
    return general, zones


def _adapt_agent_content(content, features, has_llm):
    """适配 agent 文件的 ADAPTABLE_ZONE 内容。"""
    if not has_llm:
        return content

    from app.analyzer.llm_assistant import _get_llm_config, _call_llm
    config = _get_llm_config(enable_dotenv=True)
    if not config.get("api_key"):
        return content

    general_parts, zones = _parse_adaptable_zones(content)
    if not zones:
        return content

    system_prompt = (
        "你是一个项目配置文件适配助手。将提供的文本块调整为适合目标项目的版本。"
        "只修改语言特定的部分（命令、文件命名约定、示例代码段），保持通用逻辑不变。"
        "只输出修改后的文本块，不要输出其他任何内容。"
    )

    adapted_zones = []
    for i, zone in enumerate(zones):
        user_prompt = f"""目标项目特征:
- 语言: {', '.join(features.get('languages', ['unknown']))}
- 框架: {features.get('framework', 'unknown')}
- 测试命令: {features.get('test_command', '')}
- 包管理器: {features.get('package_manager', 'unknown')}

需要适配的文本块（第 {i+1}/{len(zones)} 块）:
{zone}
"""
        try:
            response, _ = _call_llm(system_prompt, user_prompt, config, max_tokens=2048, timeout=60)
        except Exception:
            response = None

        if response:
            adapted_zones.append(response)
        else:
            adapted_zones.append(zone)

    # Reconstruct with adapted zones
    result_parts = []
    for j in range(len(zones)):
        result_parts.append(general_parts[j])
        result_parts.append(adapted_zones[j])
    result_parts.append(general_parts[-1])
    return "".join(result_parts)


def _adapt_workflow_content(content, features):
    """适配 workflow 文件的 stages 配置。"""
    langs = features.get("languages", [])
    is_frontend_only = all(l in ("javascript", "typescript") for l in langs) and "python" not in langs
    is_go_only = all(l == "go" for l in langs)
    is_rust_only = all(l == "rust" for l in langs)

    # 根据项目类型确定需要标记为 skip 的阶段 id
    skip_stage_ids = set()
    if is_frontend_only:
        # 纯前端项目：tester 阶段和关联的回环修复阶段不适用
        skip_stage_ids.update({"tester", "generator-fix", "generator-test-fix"})
    # Go/Rust 项目：所有阶段适用 (go test / cargo test 替代 pytest)，无需跳过
    # is_go_only 和 is_rust_only 在此显式判断，防止死代码

    replacements = {
        "{{test_command}}": features.get("test_command", ""),
        "{{test_framework}}": features.get("test_framework", "unknown"),
        "{{package_manager}}": features.get("package_manager", "unknown"),
        "{{validation_command}}": features.get("validation_command", ""),
        "{{project_name}}": features.get("project_name", os.path.basename(os.getcwd())),
        "{{version}}": "0.1",
    }
    result = content
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    # 在 YAML frontmatter 中对不适用阶段添加 skip: true
    if skip_stage_ids and result.startswith("---"):
        parts = result.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                if fm and "stages" in fm:
                    for stage in fm["stages"]:
                        if isinstance(stage, dict) and stage.get("id") in skip_stage_ids:
                            stage["skip"] = True
                    new_yaml = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
                    new_yaml = new_yaml.rstrip("\n")
                    result = "---\n" + new_yaml + "\n---" + parts[2]
            except Exception:
                pass

    return result


def _adapt_rule_content(content, features, has_llm):
    """适配规则文件 — 先替换占位符，LLM 可用时改写语言特定部分。"""
    # Always replace template variables
    replacements = {
        "{{test_command}}": features.get("test_command", ""),
        "{{test_framework}}": features.get("test_framework", "unknown"),
        "{{package_manager}}": features.get("package_manager", "unknown"),
        "{{validation_command}}": features.get("validation_command", ""),
    }
    result = content
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    if not has_llm:
        return result

    from app.analyzer.llm_assistant import _get_llm_config, _call_llm
    config = _get_llm_config(enable_dotenv=True)
    if not config.get("api_key"):
        return result

    system_prompt = (
        "你是一个编码规则适配助手。将规则文件中的语言特定部分调整为适合目标技术栈的版本。"
        "通用规则语义保持不变。只修改与语言/框架相关的具体描述。"
        "只输出修改后的完整文件内容。"
    )

    user_prompt = f"""目标项目特征:
- 语言: {', '.join(features.get('languages', ['unknown']))}
- 框架: {features.get('framework', 'unknown')}
- 测试命令: {features.get('test_command', '')}
- 包管理器: {features.get('package_manager', 'unknown')}

原始规则文件内容:
{result}
"""
    try:
        response, _ = _call_llm(system_prompt, user_prompt, config, max_tokens=3072, timeout=60)
    except Exception:
        return result

    return response if response else result


def _generate_adapted_project_yaml(features):
    """生成适配后的 project.yaml 内容。"""
    lines = [
        "# project.yaml — 项目模板变量定义，所有占位符 {{...}} 的单一数据源",
        "# 由 harness_deploy.py 自动生成",
        "",
        f"project_name: {features.get('project_name', 'Unknown Project')}",
        f'version: "0.1"',
        "languages:",
    ]
    for lang in features.get("languages", ["unknown"]):
        lines.append(f"  - {lang}")
    lines.append(f"test_framework: {features.get('test_framework', 'unknown')}")
    lines.append(f"test_command: {features.get('test_command', '')}")
    lines.append(f"package_manager: {features.get('package_manager', 'unknown')}")
    lines.append(f"validation_command: {features.get('validation_command', '')}")
    lines.append(f'domain: "{features.get("domain", "待确认")}"')
    lines.append(f'description: "{features.get("description", "")}"')
    lines.append(f'entry_point: "{features.get("entry_point", "")}"')
    return "\n".join(lines) + "\n"


def _generate_adapted_claude_md(features):
    """生成适配后的 CLAUDE.md。"""
    project_name = features.get("project_name", "Unknown Project")
    description = features.get("description", "")
    or_short = description[:50] if description else ""
    lines = [
        "# CLAUDE.md",
        "",
        "## 项目定位",
        "",
        f"{project_name} — {or_short}。v0.1。",
        "",
        "## 工作原则",
        "",
        "- 所有变更必须先读 `harness/project-map/overview.md` 了解项目全貌",
        "- 修改文件后检查 `harness/rules/` 下的相关规则是否命中",
        "- 代码修改后运行项目配置的结构验证命令",
        "- 遇到错误记录到 `harness/feedback/error-log.md`",
        "- 发现可改进的规则记录到 `harness/feedback/improvement-log.md`",
        "- 每次任务完成后更新 `harness/project-map/change-map.md`",
        "",
        "## 项目地图入口",
        "",
        "| 文档 | 用途 |",
        "| ---- | ---- |",
        "| `harness/project-map/overview.md` | 项目总览 |",
        "| `harness/project-map/directory-map.md` | 目录结构 |",
        "| `harness/project-map/module-map.md` | 模块职责 |",
        "| `harness/project-map/command-map.md` | 命令索引 |",
        "| `harness/project-map/data-flow.md` | 数据流 |",
        "| `harness/project-map/change-map.md` | 变更记录 |",
        "",
        "## 规则入口",
        "",
        "| 文档 | 用途 |",
        "| ---- | ---- |",
        "| `harness/rules/coding-rules.md` | 编码规则 |",
        "| `harness/rules/data-safety-rules.md` | 数据安全规则 |",
        "| `harness/rules/workflow-rules.md` | 工作流规则 |",
    ]
    return "\n".join(lines) + "\n"


def _collect_adaptable_files(target_path):
    """收集所有需要适配的文件。"""
    files = []

    # Agent files
    agent_dir = os.path.join(target_path, ".claude", "agents")
    if os.path.isdir(agent_dir):
        for fname in sorted(os.listdir(agent_dir)):
            if fname.endswith(".md"):
                files.append(("agent", os.path.join(agent_dir, fname)))

    # Workflow files
    workflow_dir = os.path.join(target_path, "harness", "workflow")
    if os.path.isdir(workflow_dir):
        for fname in sorted(os.listdir(workflow_dir)):
            if fname.endswith(".md"):
                files.append(("workflow", os.path.join(workflow_dir, fname)))

    # Rule files
    rules_dir = os.path.join(target_path, "harness", "rules")
    if os.path.isdir(rules_dir):
        for fname in sorted(os.listdir(rules_dir)):
            if fname.endswith(".md"):
                files.append(("rule", os.path.join(rules_dir, fname)))

    # Command files
    commands_dir = os.path.join(target_path, ".claude", "commands")
    if os.path.isdir(commands_dir):
        for root, _dirs, fnames in os.walk(commands_dir):
            for fname in fnames:
                if fname.endswith(".md"):
                    files.append(("command", os.path.join(root, fname)))

    return files


def generate_adaptations(target_path, features, has_llm):
    """生成所有适配内容，返回 {file_path: adapted_content} 字典。"""
    print("\n[Phase 2] 生成适配建议...")
    adaptations = {}
    files = _collect_adaptable_files(target_path)

    for file_type, fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                original = f.read()
        except OSError:
            continue

        adapted = None
        if file_type == "agent":
            adapted = _adapt_agent_content(original, features, has_llm)
        elif file_type == "workflow":
            adapted = _adapt_workflow_content(original, features)
        elif file_type == "rule":
            adapted = _adapt_rule_content(original, features, has_llm)
        elif file_type == "command":
            adapted = _adapt_workflow_content(original, features)

        if adapted is not None and adapted != original:
            rel_path = os.path.relpath(fpath, target_path)
            adaptations[rel_path] = {"original": original, "adapted": adapted}
            print(f"  已生成: {rel_path}")

    # project.yaml
    yaml_adapted = _generate_adapted_project_yaml(features)
    adaptations["harness/config/project.yaml"] = {
        "original": "",
        "adapted": yaml_adapted,
    }

    # CLAUDE.md
    claude_adapted = _generate_adapted_claude_md(features)
    claude_path = os.path.join(target_path, "CLAUDE.md")
    claude_original = ""
    if os.path.isfile(claude_path):
        try:
            with open(claude_path, "r", encoding="utf-8") as f:
                claude_original = f.read()
        except OSError:
            pass
    adaptations["CLAUDE.md"] = {
        "original": claude_original,
        "adapted": claude_adapted,
    }

    print(f"  已生成: harness/config/project.yaml")
    print(f"  已生成: CLAUDE.md")
    print(f"  共 {len(adaptations)} 个文件待确认")

    return adaptations


# ============================================================
# Phase 3: Interactive confirmation
# ============================================================

def _show_diff(original, adapted, context_lines=3):
    """显示修改前后的 diff。"""
    if not original:
        print("  [新文件]")
        preview = adapted[:500]
        if len(adapted) > 500:
            preview += "\n  ... (truncated)"
        print("  " + preview.replace("\n", "\n  "))
        return

    orig_lines = original.splitlines()
    adapted_lines = adapted.splitlines()
    max_len = max(len(orig_lines), len(adapted_lines))

    # Simple line-by-line diff
    i = 0
    j = 0
    diff_shown = 0
    print("  --- 原始内容")
    print("  +++ 适配后内容")
    while i < max_len or j < max_len:
        if i < len(orig_lines) and j < len(adapted_lines) and orig_lines[i] == adapted_lines[j]:
            i += 1
            j += 1
        else:
            # Show context before
            if diff_shown == 0:
                start_i = max(0, i - context_lines)
                for k in range(start_i, i):
                    if k < len(orig_lines):
                        print(f"    {orig_lines[k]}")
            if i < len(orig_lines):
                print(f"  - {orig_lines[i]}")
                i += 1
            if j < len(adapted_lines):
                print(f"  + {adapted_lines[j]}")
                j += 1
            diff_shown += 1
            if diff_shown > 50:
                print("  ... (差异行数过多，已截断)")
                break


def _open_editor(content, file_label):
    """打开编辑器让用户手动修改。"""
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", ""))
    if not editor:
        if sys.platform == "win32":
            editor = "notepad"
        else:
            editor = "vi"

    # Write to temp file
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()

    try:
        print(f"  启动编辑器: {editor} {tmp.name}")
        subprocess.run([editor, tmp.name], check=False)
    except FileNotFoundError:
        print(f"  编辑器 `{editor}` 未找到，请在终端中手动输入修改后的内容（输入 END 结束）:")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line.strip() == "END":
                break
            lines.append(line)
        with open(tmp.name, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    # Read back
    result = ""
    try:
        with open(tmp.name, "r", encoding="utf-8") as f:
            result = f.read()
    except OSError:
        pass
    os.unlink(tmp.name)
    return result


def _check_consistency(target_path):
    """一致性检查：扫描确认无残留 {{...}} 占位符和 ADAPTABLE_ZONE 标记。"""
    issues = []
    for root, _dirs, files in os.walk(target_path):
        for fname in files:
            if not (fname.endswith(".md") or fname.endswith(".yaml") or fname.endswith(".txt")):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            if "{{" in content and "}}" in content:
                rel = os.path.relpath(fpath, target_path)
                issues.append(f"残留占位符: {rel}")
            if "ADAPTABLE_ZONE_START" in content or "ADAPTABLE_ZONE_END" in content:
                rel = os.path.relpath(fpath, target_path)
                issues.append(f"残留适配标记: {rel}")
    return issues


def _atomic_write(fpath, content):
    """原子写入：先写 .tmp，再 os.replace。"""
    tmp_path = fpath + ".tmp"
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, fpath)


def interactive_confirm(target_path, features, adaptations):
    """交互式确认流程。"""
    print("\n[Phase 3] 交互式确认...")

    items = list(adaptations.items())
    confirmed = {}
    skipped = []
    edited = {}

    # First: detection summary confirmation
    print("\n第一个确认项：检测摘要")
    _print_detection_summary(features)
    while True:
        choice = input("  确认检测结果? [y/N/e]: ").strip().lower()
        if choice in ("y", "yes", ""):
            break
        elif choice in ("n", "no"):
            print("  已跳过，将使用静态检测结果作为默认值。")
            break
        elif choice == "e":
            print("  编辑检测结果（输入键值对，一行一对，输入 END 结束）:")
            while True:
                line = input("    ").strip()
                if line.upper() == "END":
                    break
                if "=" in line:
                    key, _, val = line.partition("=")
                    features[key.strip()] = val.strip()
            _print_detection_summary(features)
        else:
            print("  请输入 y(确认) / n(跳过) / e(编辑)")

    # Then: each adapted file
    for rel_path, data in items:
        print(f"\n--- 文件: {rel_path} ---")
        original = data["original"]
        adapted = data["adapted"]

        if original == adapted:
            print("  (无变化，跳过)")
            continue

        _show_diff(original, adapted)

        while True:
            choice = input(f"  应用此修改? [y/N/e]: ").strip().lower()
            if choice in ("y", "yes"):
                confirmed[rel_path] = adapted
                break
            elif choice in ("n", "no", ""):
                skipped.append(rel_path)
                break
            elif choice == "e":
                edited_content = _open_editor(adapted, rel_path)
                if edited_content != adapted:
                    print("  已编辑。重新展示 diff:")
                    _show_diff(original, edited_content)
                    while True:
                        sub_choice = input("  确认应用编辑后的版本? [y/N/e]: ").strip().lower()
                        if sub_choice in ("y", "yes"):
                            confirmed[rel_path] = edited_content
                            break
                        elif sub_choice in ("n", "no", ""):
                            skipped.append(rel_path)
                            break
                        elif sub_choice == "e":
                            edited_content = _open_editor(edited_content, rel_path)
                            print("  已重新编辑。重新展示 diff:")
                            _show_diff(original, edited_content)
                        else:
                            print("  请输入 y(确认) / n(跳过) / e(继续编辑)")
                else:
                    skipped.append(rel_path)
                break
            else:
                print("  请输入 y(确认) / n(跳过) / e(编辑)")

    # Execute atomic writes
    print("\n  正在写入确认的修改...")
    for rel_path, content in confirmed.items():
        fpath = os.path.join(target_path, rel_path)
        _atomic_write(fpath, content)
        print(f"  已写入: {rel_path}")

    # Consistency check
    print("\n  运行一致性检查...")
    issues = _check_consistency(target_path)
    if issues:
        print("  发现以下问题:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  一致性检查: 通过")

    print(f"\n  适配完成: {len(confirmed)} 个文件已修改, {len(skipped)} 个已跳过")
    return confirmed, skipped, edited


# ============================================================
# Main entry
# ============================================================

def main(target_path):
    target = os.path.abspath(target_path)

    if "--help" in sys.argv or "-h" in sys.argv:
        print("用法: python harness/scripts/harness_deploy.py <目标路径>")
        print()
        print("Harness 框架个性化部署 — LLM 增强项目检测并生成适配建议，交互式确认。")
        print()
        print("典型迁移流程 (3 步):")
        print("  1. python harness/scripts/init_project.py <目标>    # 复制框架 + 基础检测 + 生成 project.yaml")
        print("  2. python app/analyze_project.py                   # 深度分析 (架构/用户故事/风险)")
        print("  3. python harness/scripts/harness_deploy.py <目标>  # 个性化部署 (本脚本)")
        print()
        print("harness_deploy 内部流程:")
        print("  Phase 1: 项目检测 — 优先读取 init 生成的 project.yaml 为基线，LLM 补充缺失字段")
        print("  Phase 2: 适配建议生成 — agent / workflow / rules / project.yaml / CLAUDE.md")
        print("  Phase 3: 交互式确认 — 逐项展示 diff -> y/n/e 交互")
        print()
        print("选项:")
        print("  --help, -h  显示此帮助信息")
        print()
        print("交互选项:")
        print("  y  确认应用修改")
        print("  n  跳过此修改")
        print("  e  打开编辑器手动修改")
        return 0

    if len(sys.argv) < 2:
        print("用法: python harness/scripts/harness_deploy.py <目标路径>", file=sys.stderr)
        print("      python harness/scripts/harness_deploy.py --help", file=sys.stderr)
        return 1

    if not os.path.isdir(target):
        print(f"错误: 目标路径不存在或不是目录: {target}", file=sys.stderr)
        return 1

    # Check if harness already exists in target
    target_harness = os.path.join(target, "harness")
    if not os.path.exists(target_harness):
        print(f"警告: 目标路径下未找到 harness 目录。请先运行 init_project.py 初始化 harness 骨架。",
              file=sys.stderr)
        print(f"  python harness/scripts/init_project.py {target}", file=sys.stderr)
        return 1

    has_llm = _check_llm_available()

    # Phase 1: 读取 init_project.py 的产出作为基线
    baseline = _read_project_yaml_baseline(target)
    if baseline:
        print(f"\n  检测到已有 project.yaml（项目名: {baseline.get('project_name', 'unknown')}）")
        print(f"  已有字段: {', '.join(k for k in baseline if baseline[k])}")
    features = detect_project(target, baseline=baseline)
    if baseline:
        features["project_name"] = baseline.get("project_name", os.path.basename(target))
    else:
        features["project_name"] = os.path.basename(target)

    # Phase 2
    adaptations = generate_adaptations(target, features, has_llm)

    # Phase 3
    confirmed, skipped, edited = interactive_confirm(target, features, adaptations)

    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        sys.exit(main(""))
    elif len(sys.argv) != 2:
        print("用法: python harness/scripts/harness_deploy.py <目标路径>", file=sys.stderr)
        print("      python harness/scripts/harness_deploy.py --help", file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(main(sys.argv[1]))
