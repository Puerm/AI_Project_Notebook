# llm_assistant.py — LLM 语义增强（可选），不可用时降级到模板描述

import json
import os
import sys
import urllib.request
import urllib.error


def _load_dotenv(project_root):
    """Parse .env file and set environment variables (no override)."""
    env_path = os.path.join(project_root, ".env")
    if not os.path.isfile(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                # Only set if not already present in environment
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


def _get_llm_config(enable_dotenv=True):
    """从环境变量读取 LLM 配置。"""
    if enable_dotenv:
        _load_dotenv(os.getcwd())
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    api_base = os.environ.get("LLM_API_BASE") or os.environ.get("OPENAI_API_BASE")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    if os.environ.get("ANTHROPIC_API_KEY"):
        model = model or "claude-3-5-sonnet-20241022"

    return {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
        "provider": "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openai",
    }


def _call_llm(system_prompt, user_prompt, config, max_tokens=256, timeout=10):
    """通过 urllib 调用 LLM API，返回响应文本或 None。"""
    if not config["api_key"]:
        return None

    if config["provider"] == "anthropic":
        url = (config.get("api_base") or "https://api.anthropic.com") + "/v1/messages"
        headers = {
            "x-api-key": config["api_key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = json.dumps({
            "model": config["model"],
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }).encode("utf-8")
    else:
        url = (config.get("api_base") or "https://api.openai.com") + "/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }
        body = json.dumps({
            "model": config["model"],
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            TimeoutError, OSError) as e:
        print(f"[LLM] API 调用失败: {e}", file=sys.stderr)
        return None

    if config["provider"] == "anthropic":
        content = data.get("content", [])
        if content and isinstance(content, list):
            return content[0].get("text", "").strip()
    else:
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()

    return None


def _template_dir_description(dir_name, files):
    """模板：目录用途描述。"""
    templates = {
        "src": "源代码目录",
        "tests": "测试代码目录",
        "test": "测试代码目录",
        "docs": "项目文档",
        "lib": "库文件目录",
        "bin": "可执行文件目录",
        "config": "配置文件目录",
        "scripts": "脚本工具目录",
        "data": "数据文件目录",
        "assets": "静态资源目录",
        "static": "静态资源目录",
        "templates": "模板文件目录",
        "examples": "示例代码目录",
        "tools": "工具集目录",
        "utils": "工具函数目录",
        "plugins": "插件目录",
        "logs": "日志目录",
        "output": "输出文件目录",
        "public": "公开资源目录",
    }
    label = templates.get(dir_name)
    if label:
        return {"enhanced": False, "description": label, "source": "template"}

    if not files:
        return {"enhanced": False, "description": "空目录", "source": "template"}

    return {"enhanced": False, "description": f"包含 {len(files)} 个文件的目录", "source": "template"}


def _template_module_description(module_name, functions, classes):
    """模板：模块职责描述。"""
    parts = []
    if functions:
        func_names = [f["name"] if isinstance(f, dict) else f for f in functions]
        parts.append(f"提供 {', '.join(func_names[:3])} 等功能")
    if classes:
        cls_names = [c["name"] if isinstance(c, dict) else c for c in classes]
        parts.append(f"定义 {', '.join(cls_names[:3])} 等类")
    if not parts:
        return {"enhanced": False, "description": f"模块 {module_name}", "source": "template"}
    return {"enhanced": False, "description": "，".join(parts), "source": "template"}


def _template_project_description(name, tech_stack, project_type):
    """模板：项目概述描述。"""
    tech_str = "/".join(tech_stack) if tech_stack else "通用技术栈"
    return {"enhanced": False, "description": f"{name} — {tech_str} {project_type}", "source": "template"}


def enhance_dir_description(dir_name, files, enable_dotenv=True):
    """LLM 增强目录用途描述。"""
    config = _get_llm_config(enable_dotenv=enable_dotenv)
    user_prompt = f"目录名: {dir_name}\n包含文件: {', '.join(files[:10])}"
    result = _call_llm("用10字以内中文描述该目录的用途", user_prompt, config)
    if result:
        return {"enhanced": True, "description": result, "source": "llm"}
    return _template_dir_description(dir_name, files)


def enhance_module_description(module_name, functions, classes, enable_dotenv=True):
    """LLM 增强模块职责描述。"""
    config = _get_llm_config(enable_dotenv=enable_dotenv)
    func_str = ", ".join(functions[:5]) if isinstance(functions, list) else str(functions)
    cls_str = ", ".join(classes[:5]) if isinstance(classes, list) else str(classes)
    user_prompt = f"模块: {module_name}\n函数: {func_str}\n类: {cls_str}"
    result = _call_llm("用20字以内中文描述该模块的职责", user_prompt, config)
    if result:
        return {"enhanced": True, "description": result, "source": "llm"}
    return _template_module_description(module_name, functions, classes)


def enhance_project_description(name, tech_stack, project_type, enable_dotenv=True):
    """LLM 增强项目概述描述。"""
    config = _get_llm_config(enable_dotenv=enable_dotenv)
    user_prompt = f"项目名: {name}\n技术栈: {tech_stack}\n类型: {project_type}"
    result = _call_llm("用30字以内中文一句描述该项目的用途和定位", user_prompt, config)
    if result:
        return {"enhanced": True, "description": result, "source": "llm"}
    return _template_project_description(name, tech_stack, project_type)


def enhance_description(text, context=None, enable_dotenv=True):
    """通用增强入口（用于简单测试调用）。"""
    config = _get_llm_config(enable_dotenv=enable_dotenv)
    result = _call_llm("用一句话描述以下内容", text, config)
    if result:
        return {"enhanced": True, "description": result, "source": "llm"}
    return {"enhanced": False, "description": text, "source": "template"}


def check_api_key_available(enable_dotenv=True):
    """Check if API key is available and return guidance if not."""
    if enable_dotenv:
        _load_dotenv(os.getcwd())
    has_key = bool(os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
    if has_key:
        return (True, "")
    guidance = (
        "LLM 功能需要 API Key，但未检测到有效的 API Key。\n\n"
        "配置步骤:\n"
        "1. 在项目根目录创建 .env 文件\n"
        "2. 添加以下内容（选择其一）:\n"
        '   ANTHROPIC_API_KEY=sk-ant-xxx...  （Anthropic Claude）\n'
        "   或\n"
        '   LLM_API_KEY=sk-xxx...           （OpenAI 兼容）\n'
        "3. 重新运行: python harness/scripts/analyze_project.py <路径> --llm\n\n"
        "可选环境变量:\n"
        "  LLM_API_BASE    自定义 API 地址\n"
        "  LLM_MODEL       模型名称 (默认: gpt-4o-mini)\n"
    )
    return (False, guidance)


# IMP-4: Adaptive batch module description enhancement
def enhance_module_descriptions_batch(dir_modules, project_name, source_root, enable_dotenv=True):
    """LLM 增强模块描述，自适应批量策略。

    模块数 <= 10: 逐模块调用 LLM
    模块数 > 10: 打包一次批量调用，要求 LLM 返回 JSON 数组
    LLM 调用失败时降级到模板描述。
    """
    config = _get_llm_config(enable_dotenv=enable_dotenv)
    if not config["api_key"]:
        return [_template_module_description(m.get("dir", "?"),
                                              m.get("functions", []),
                                              m.get("classes", []))["description"]
                for m in dir_modules]

    if len(dir_modules) <= 10:
        return _batch_individual(dir_modules, project_name, source_root, config)
    else:
        return _batch_single_call(dir_modules, project_name, source_root, config)


def _batch_individual(dir_modules, project_name, source_root, config):
    """逐模块调用 LLM 获取描述。"""
    results = []
    for mod in dir_modules:
        sr_label = mod.get("source_root", source_root) or "(项目根)"
        dir_name = mod.get("dir", "?")
        deps = mod.get("dependencies", [])
        files = mod.get("files", [])[:5]
        sibling_names = [m.get("dir", "") for m in dir_modules if m.get("dir") != dir_name]
        funcs = [f["name"] if isinstance(f, dict) else f for f in mod.get("functions", [])[:5]]
        classes = [c["name"] if isinstance(c, dict) else c for c in mod.get("classes", [])[:5]]

        user_prompt = (
            f"项目: {project_name}\n"
            f"源码根: {sr_label}\n"
            f"模块: {dir_name}\n"
            f"同级模块: {', '.join(sibling_names[:10])}\n"
            f"依赖: {', '.join(deps[:10]) if deps else '无'}\n"
            f"关键文件: {', '.join(files)}\n"
            f"关键函数: {', '.join(funcs) if funcs else '无'}\n"
            f"关键类: {', '.join(classes) if classes else '无'}"
        )
        result = _call_llm(
            '根据模块名、关键文件、同级模块关系、依赖关系，用≤30字中文描述该模块的职责。禁止出现"包含X个文件"等模板废话。',
            user_prompt, config, max_tokens=128
        )
        if result:
            results.append(result)
        else:
            tpl = _template_module_description(dir_name,
                                               mod.get("functions", []),
                                               mod.get("classes", []))
            results.append(tpl["description"])
    return results


def _batch_single_call(dir_modules, project_name, source_root, config):
    """单次批量调用 LLM，要求返回 JSON 数组。"""
    source_roots_set = set()
    modules_info = []
    for mod in dir_modules:
        dir_name = mod.get("dir", "?")
        mod_sr = mod.get("source_root", source_root) or "(项目根)"
        source_roots_set.add(mod_sr)
        deps = mod.get("dependencies", [])
        files = mod.get("files", [])[:5]
        sibling_names = [m.get("dir", "") for m in dir_modules if m.get("dir") != dir_name]
        funcs = [f["name"] if isinstance(f, dict) else f for f in mod.get("functions", [])[:5]]
        classes = [c["name"] if isinstance(c, dict) else c for c in mod.get("classes", [])[:5]]
        modules_info.append({
            "module": dir_name,
            "source_root": mod_sr,
            "siblings": sibling_names[:10],
            "deps": deps[:10],
            "files": files,
            "funcs": funcs,
            "classes": classes,
        })
    sr_label = ", ".join(sorted(source_roots_set)) if source_roots_set else (source_root or "(项目根)")

    user_prompt = (
        f"项目: {project_name}\n"
        f"源码根: {sr_label}\n"
        f"模块列表 (JSON):\n"
        + json.dumps(modules_info, ensure_ascii=False, indent=2)
        + '\n\n请为每个模块用≤30字中文描述职责，禁止使用"包含X个文件"等模板废话。'
        f"只返回 JSON 数组，格式: [\"描述1\", \"描述2\", ...]，顺序与输入一致。"
    )
    result = _call_llm(
        "根据模块名、关键文件、同级模块关系、依赖关系，为每个模块生成≤30字中文描述。只返回JSON数组。",
        user_prompt, config, max_tokens=512
    )

    if result:
        try:
            parsed = json.loads(result)
            if isinstance(parsed, list) and len(parsed) == len(dir_modules):
                return parsed
        except json.JSONDecodeError:
            pass

    # Fallback: template descriptions for all
    return [_template_module_description(m.get("dir", "?"),
                                          m.get("functions", []),
                                          m.get("classes", []))["description"]
            for m in dir_modules]


# IMP-5: LLM data flow inference
def enhance_data_flow_llm(entry_functions, dir_modules, module_deps, project_name, enable_dotenv=True):
    """LLM 推断数据流，分批处理入口函数（每批最多 5 个），返回 Markdown 或 None。"""
    if not entry_functions:
        return None

    config = _get_llm_config(enable_dotenv=enable_dotenv)
    if not config["api_key"]:
        return None

    # Build simplified module dep graph
    dep_graph = {}
    for mod in dir_modules:
        dep_graph[mod.get("dir", "?")] = mod.get("dependencies", [])

    # Split entry functions into batches of 5
    BATCH_SIZE = 5
    all_parts = []
    for batch_idx in range(0, len(entry_functions), BATCH_SIZE):
        batch = entry_functions[batch_idx:batch_idx + BATCH_SIZE]
        entries_info = []
        for ef in batch:
            entries_info.append(
                f"- {ef['name']} (文件: {ef.get('file', '?')}, 模块: {ef.get('module_dir', '?')})"
            )

        user_prompt = (
            f"项目: {project_name}\n"
            f"模块依赖图: {json.dumps(dep_graph, ensure_ascii=False)}\n"
            f"入口函数:\n" + "\n".join(entries_info)
            + "\n\n请按以下格式输出每个入口的数据流调用链:"
            "\n## 入口名"
            "\n入口 -> 模块A.函数 -> 模块B.函数 -> ... -> 输出/存储"
            "\n每步标注所属模块，不完整时说明不确定部分。"
        )
        result = _call_llm(
            "根据入口函数和模块依赖图，推断数据从入口到存储/输出的关键调用链。每步标注所属模块。",
            user_prompt, config, max_tokens=1024, timeout=30
        )
        if result:
            all_parts.append(result)
        else:
            # On failure, list batch entries without LLM inference
            fallback = "\n".join(
                f"### {ef['name']}\n入口 -> ? (LLM 推断超时)\n"
                for ef in batch
            )
            all_parts.append(fallback)

    if all_parts:
        return "# Data Flow\n\n" + "\n".join(all_parts)
    return None


# IMP-6: LLM tech stack inference
def enhance_tech_stack_llm(tech_features, rule_based_tech, rule_based_type, enable_dotenv=True):
    """LLM 推断技术栈和项目类型。返回 {"tech_stack": [...], "project_type": "..."}。"""
    config = _get_llm_config(enable_dotenv=enable_dotenv)
    if not config["api_key"]:
        return {"tech_stack": list(rule_based_tech), "project_type": rule_based_type}

    indicator_files = tech_features.get("indicator_files", []) if tech_features else []
    python_deps = tech_features.get("python_deps", {}) if tech_features else {}
    node_deps = tech_features.get("node_deps", {}) if tech_features else {}
    dir_structure = tech_features.get("dir_structure", []) if tech_features else {}

    user_prompt = (
        f"特征文件: {', '.join(indicator_files) if indicator_files else '无'}\n"
        f"Python 依赖: {json.dumps(list(python_deps.keys())[:20], ensure_ascii=False)}\n"
        f"Node.js 依赖: {json.dumps(list(node_deps.keys())[:20], ensure_ascii=False)}\n"
        f"目录结构: {', '.join(dir_structure[:20]) if isinstance(dir_structure, list) else str(dir_structure)}\n"
        f"规则推断技术栈: {rule_based_tech}\n"
        f"规则推断项目类型: {rule_based_type}\n"
        + "\n请判断项目的技术栈和项目类型。返回 JSON: {\"tech_stack\": [...], \"project_type\": \"...\"}。"
        "项目类型为: Web应用/CLI工具/库/全栈应用 + 简短说明。技术栈列出具体框架/库名。"
    )
    result = _call_llm(
        "根据特征文件和依赖列表判断项目的技术栈和项目类型。只返回JSON。",
        user_prompt, config, max_tokens=256
    )
    if result:
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "tech_stack" in parsed and "project_type" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    return {"tech_stack": list(rule_based_tech), "project_type": rule_based_type}


# IMP-7: Entry function detection for non-LLM data flow fallback
def detect_entry_functions(target_path, source_files, source_roots):
    """硬编码规则检测入口函数。仅在 source_roots 内的文件中搜索。返回列表。"""
    import re

    target = os.path.abspath(target_path)

    # Build set of files within source_roots
    eligible_files = set()
    for f in source_files:
        abs_f = os.path.join(target, f)
        for sr in source_roots:
            sr_abs = os.path.join(target, sr).replace("\\", "/")
            abs_f_norm = abs_f.replace("\\", "/")
            if abs_f_norm.startswith(sr_abs + "/") or abs_f_norm == sr_abs:
                eligible_files.add(f)
                break

    # If no source_roots specified, search all source files
    if not source_roots:
        eligible_files = set(source_files)

    # Python entry patterns: (regex_pattern, description)
    python_patterns = [
        (r'argparse\.ArgumentParser\s*\(', "argparse"),
        (r'click\.(command|group)\s*\(', "click"),
        (r'typer\.run\s*\(', "typer"),
    ]

    # JS/TS entry patterns
    js_patterns = [
        (r'app\.listen\s*\(', "express/koa"),
        (r'express\s*\(\s*\)', "express"),
        (r'fastify\.listen\s*\(', "fastify"),
        (r'commander\.program', "commander"),
    ]

    results = []
    seen = set()

    def _find_python_entries(fpath, module_dir):
        """Search a Python file for entry function patterns."""
        abs_path = os.path.join(target, fpath)
        try:
            with open(abs_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            return

        has_main_block = bool(re.search(
            r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', content
        ))

        for pattern, label in python_patterns:
            if not re.search(pattern, content):
                continue
            # Find function names defined near the match
            func_name = _extract_func_name(content, pattern)
            if not func_name:
                continue
            key = (func_name, fpath)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "name": func_name,
                "file": fpath,
                "module_dir": module_dir,
                "type": label,
            })

        # Check for standalone def main() + __name__ == "__main__"
        if has_main_block:
            main_match = re.search(r'^\s*def\s+(\w+)\s*\(', content, re.MULTILINE)
            func_name = main_match.group(1) if main_match else None
            # Also check if there's already an entry captured from above patterns
            if func_name and func_name not in {"__init__"}:
                key = (func_name, fpath)
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "name": func_name,
                        "file": fpath,
                        "module_dir": module_dir,
                        "type": "main_block",
                    })

    def _find_js_entries(fpath, module_dir):
        """Search a JS/TS file for entry function patterns."""
        abs_path = os.path.join(target, fpath)
        try:
            with open(abs_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            return

        for pattern, label in js_patterns:
            if not re.search(pattern, content, re.IGNORECASE):
                continue
            func_name = label  # Use label as function name for JS entries
            key = (func_name, fpath)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "name": func_name,
                "file": fpath,
                "module_dir": module_dir,
                "type": label,
            })

    for fpath in sorted(eligible_files):
        rel_fpath = fpath.replace("\\", "/")
        file_sr = _find_source_root_for_file(fpath, source_roots)
        module_dir = _get_module_dir(fpath, source_root=file_sr)
        ext = os.path.splitext(rel_fpath)[1].lower()
        if ext == ".py":
            _find_python_entries(fpath, module_dir)
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            _find_js_entries(fpath, module_dir)

    return results


def _extract_func_name(content, pattern):
    """Extract the function name most likely associated with an entry pattern match."""
    import re
    idx = content.find(pattern) if pattern in content else -1
    if idx < 0:
        m = re.search(pattern, content)
        if m:
            idx = m.start()
        else:
            return None

    # Look backwards for a function definition
    before = content[:idx]
    func_match = re.findall(r'def\s+(\w+)\s*\(', before)
    return func_match[-1] if func_match else None


def _get_module_dir(file_path, source_root=None):
    """Extract the first-level module directory from a file path.

    If source_root is provided (not None, not empty, not "."),
    it is stripped as a prefix before extracting the module directory.
    """
    normalized = file_path.replace("\\", "/")
    if source_root and source_root != ".":
        sr_norm = source_root.replace("\\", "/").rstrip("/") + "/"
        if normalized.startswith(sr_norm):
            normalized = normalized[len(sr_norm):]
    parts = normalized.split("/")
    if len(parts) == 1:
        return "."
    return parts[0]


def _find_source_root_for_file(file_path, source_roots):
    """Find the source_root that the file belongs to by longest prefix matching.

    Returns the matched source_root string, or None if no match found.
    """
    if not source_roots:
        return None
    normalized = file_path.replace("\\", "/").rstrip("/") + "/"
    best = None
    best_len = 0
    for sr in source_roots:
        sr_norm = sr.replace("\\", "/").rstrip("/") + "/"
        if sr_norm == "./":
            continue
        if normalized.startswith(sr_norm) and len(sr_norm) > best_len:
            best = sr
            best_len = len(sr_norm)
    return best
