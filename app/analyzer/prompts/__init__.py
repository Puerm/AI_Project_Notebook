# prompts/__init__.py — prompt 库加载器，提供 load_prompt(name) 读取官方 prompt 文本

import os

PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def load_prompt(name: str) -> str:
    """从 prompts/ 目录加载指定名称的 prompt 文本文件。"""
    file_path = os.path.join(PROMPTS_DIR, f"{name}.txt")
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
