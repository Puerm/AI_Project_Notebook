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


def _call_llm(system_prompt, user_prompt, config, max_tokens=256, timeout=10, silent=False):
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
        if not silent:
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
