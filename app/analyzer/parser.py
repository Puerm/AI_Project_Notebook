# parser.py — 代码解析引擎：Python AST + JS/TS（acorn 子进程或正则降级）

import ast
import os
import re
import subprocess
import sys


def parse_python(file_path):
    """使用 stdlib ast 解析 Python 文件，提取 imports / functions / classes。"""
    result = {"imports": [], "functions": [], "classes": [], "language": "python"}

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except (OSError, PermissionError):
        return result

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({
                    "name": alias.name,
                    "from": None,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    result["imports"].append({
                        "name": alias.name,
                        "from": node.module,
                        "line": node.lineno,
                    })
        elif isinstance(node, ast.FunctionDef):
            result["functions"].append({
                "name": node.name,
                "line": node.lineno,
            })
        elif isinstance(node, ast.ClassDef):
            result["classes"].append({
                "name": node.name,
                "line": node.lineno,
            })

    return result


def check_nodejs():
    """检查 Node.js 是否可用。返回 True/False。"""
    try:
        subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_js_parser():
    """检查 JS 解析器（acorn 优先）。返回 (parser_name, available, install_hint)。"""
    if not check_nodejs():
        return (None, False, "未检测到 Node.js，JS/TS 解析将使用正则降级模式")

    for parser_name, check_cmd in [("acorn", "require('acorn')"), ("esprima", "require('esprima')")]:
        try:
            result = subprocess.run(
                ["node", "-e", f"try {{ {check_cmd} }} catch(e) {{ process.exit(1) }}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return (parser_name, True, None)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    return (
        None,
        False,
        "未检测到 acorn 或 esprima，请运行 `npm install -g acorn` 安装 JS 解析器（推荐），"
        "或 `npm install -g esprima`。当前将使用正则降级模式。",
    )


def _parse_js_with_acorn(file_path):
    """通过 acorn 子进程解析 JS/TS 文件。"""
    code = f"""
    const fs = require('fs');
    const acorn = require('acorn');
    const source = fs.readFileSync({repr(file_path)}, 'utf-8');
    let ast;
    try {{
        ast = acorn.parse(source, {{ ecmaVersion: 'latest', sourceType: 'module', locations: true }});
    }} catch(e) {{
        // Try with script mode
        ast = acorn.parse(source, {{ ecmaVersion: 'latest', sourceType: 'script', locations: true }});
    }}
    const results = {{ imports: [], functions: [], classes: [] }};
    function walk(node) {{
        if (!node || typeof node !== 'object') return;
        if (node.type === 'ImportDeclaration') {{
            results.imports.push({{ name: node.source.value, from: null, line: node.loc.start.line }});
        }} else if (node.type === 'CallExpression' && node.callee && node.callee.name === 'require') {{
            if (node.arguments[0] && node.arguments[0].value) {{
                results.imports.push({{ name: node.arguments[0].value, from: null, line: node.loc ? node.loc.start.line : 0 }});
            }}
        }} else if (node.type === 'FunctionDeclaration' && node.id) {{
            results.functions.push({{ name: node.id.name, line: node.loc.start.line }});
        }} else if (node.type === 'VariableDeclarator' && node.init) {{
            if (node.init.type === 'ArrowFunctionExpression' || node.init.type === 'FunctionExpression') {{
                if (node.id && node.id.name) {{
                    results.functions.push({{ name: node.id.name, line: node.loc.start.line }});
                }}
            }}
        }} else if (node.type === 'ClassDeclaration' && node.id) {{
            results.classes.push({{ name: node.id.name, line: node.loc.start.line }});
        }}
        for (const key of Object.keys(node)) {{
            if (key === 'loc') continue;
            const child = node[key];
            if (Array.isArray(child)) {{
                child.forEach(walk);
            }} else if (child && typeof child.type === 'string') {{
                walk(child);
            }}
        }}
    }}
    walk(ast);
    console.log(JSON.stringify(results));
    """

    try:
        result = subprocess.run(
            ["node", "-e", code],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.abspath(file_path)),
        )
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


def _parse_js_regex(file_path):
    """正则降级模式解析 JS/TS 文件。"""
    result = {"imports": [], "functions": [], "classes": [], "language": "javascript"}

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except (OSError, PermissionError):
        return result

    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".ts", ".tsx"):
        result["language"] = "typescript"

    # ES import: import ... from '...'
    for m in re.finditer(r"import\s+(?:[\w{},*\s]+\s+from\s+)?['\"]([^'\"]+)['\"]", source):
        result["imports"].append({"name": m.group(1), "from": None, "line": source[:m.start()].count("\n") + 1})

    # require(): const x = require('...')
    for m in re.finditer(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", source):
        name = m.group(1)
        if not any(imp["name"] == name for imp in result["imports"]):
            result["imports"].append({"name": name, "from": None, "line": source[:m.start()].count("\n") + 1})

    # function declarations: function name(...)
    for m in re.finditer(r"\bfunction\s+(\w+)\s*\(", source):
        result["functions"].append({"name": m.group(1), "line": source[:m.start()].count("\n") + 1})

    # arrow functions assigned to variables: const name = (...) => ...
    for m in re.finditer(r"(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>", source):
        result["functions"].append({"name": m.group(1), "line": source[:m.start()].count("\n") + 1})

    # class declarations
    for m in re.finditer(r"\bclass\s+(\w+)", source):
        result["classes"].append({"name": m.group(1), "line": source[:m.start()].count("\n") + 1})

    return result


def parse_file(file_path):
    """解析单个文件，自动判断语言类型。"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".py":
        return parse_python(file_path)

    if ext in (".js", ".jsx", ".ts", ".tsx"):
        parser_name, available, _ = check_js_parser()
        if available:
            acorn_result = _parse_js_with_acorn(file_path)
            if acorn_result is not None:
                lang = "typescript" if ext in (".ts", ".tsx") else "javascript"
                acorn_result["language"] = lang
                return acorn_result
        return _parse_js_regex(file_path)

    return {"imports": [], "functions": [], "classes": [], "language": "unknown"}
