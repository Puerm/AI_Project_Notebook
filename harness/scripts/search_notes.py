# search_notes.py — 在 project-map 和 feedback 中搜索关键词，输出文件名和匹配行

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
SEARCH_DIRS = [
    os.path.join(PROJECT_ROOT, "harness", "project-map"),
    os.path.join(PROJECT_ROOT, "harness", "feedback"),
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def search_notes(keyword):
    found = 0
    for search_dir in SEARCH_DIRS:
        if not os.path.isdir(search_dir):
            continue
        for filename in sorted(os.listdir(search_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(search_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if keyword in line:
                        relpath = os.path.relpath(filepath, PROJECT_ROOT)
                        print(f"{relpath}:{lineno}: {line.rstrip()}")
                        found += 1
    return found


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python harness/scripts/search_notes.py <关键词>", file=sys.stderr)
        sys.exit(1)
    found = search_notes(sys.argv[1])
    if found == 0:
        print(f"(无匹配: {sys.argv[1]})")
    sys.exit(0)
