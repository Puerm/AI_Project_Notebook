# check_structure.py — 项目结构完整性检查脚本
# 检查关键目录和关键文件是否存在，输出检查结果

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REQUIRED_DIRS = [
    "harness",
    "harness/rules",
    "harness/scripts",
    "harness/skills",
    "harness/workflow",
    "harness/project-map",
    "harness/feedback",
    "harness/state",
    ".claude",
    ".claude/agents",
    ".claude/commands",
    ".claude/skills",
    "app/analyzer",
]

REQUIRED_FILES = [
    "harness/rules/coding-rules.md",
    "harness/rules/data-safety-rules.md",
    "harness/rules/workflow-rules.md",
    "harness/scripts/check_structure.py",
    "harness/scripts/help.py",
    "harness/scripts/search_notes.py",
    "harness/scripts/analyze_project.py",
    "harness/scripts/export_report.py",
    "harness/skills/README.md",
    "harness/workflow/README.md",
    "harness/workflow/full-cycle.md",
    "harness/workflow/implement.md",
    "harness/workflow/quick-fix.md",
    "harness/workflow/review-fix.md",
    "harness/project-map/overview.md",
    "harness/project-map/directory-map.md",
    "harness/project-map/module-map.md",
    "harness/project-map/command-map.md",
    "harness/project-map/data-flow.md",
    "harness/project-map/change-map.md",
    "harness/feedback/error-log.md",
    "harness/feedback/improvement-log.md",
    ".claude/agents/harness_maintainer.md",
    ".claude/agents/pm.md",
    ".claude/agents/planner.md",
    ".claude/agents/explorer.md",
    ".claude/agents/generator.md",
    ".claude/agents/reviewer.md",
    ".claude/agents/tester.md",
    ".claude/commands/pm/discuss.md",
    ".claude/commands/workflow/full-cycle.md",
    ".claude/commands/workflow/implement.md",
    ".claude/commands/workflow/quick-fix.md",
    ".claude/commands/workflow/review-fix.md",
]


def check_structure():
    missing_dirs = []
    missing_files = []
    ok = 0

    for d in REQUIRED_DIRS:
        path = os.path.join(PROJECT_ROOT, d)
        if os.path.isdir(path):
            ok += 1
        else:
            missing_dirs.append(d)
            print(f"  MISSING DIR  : {d}")

    for f in REQUIRED_FILES:
        path = os.path.join(PROJECT_ROOT, f)
        if os.path.isfile(path):
            ok += 1
        else:
            missing_files.append(f)
            print(f"  MISSING FILE : {f}")

    print(f"\n{'='*50}")
    print(f"  Directories : {len(REQUIRED_DIRS) - len(missing_dirs)}/{len(REQUIRED_DIRS)} ok")
    print(f"  Files       : {len(REQUIRED_FILES) - len(missing_files)}/{len(REQUIRED_FILES)} ok")
    print(f"  Total       : {ok}/{len(REQUIRED_DIRS) + len(REQUIRED_FILES)} ok")

    if missing_dirs or missing_files:
        print(f"\n  Result: FAIL")
        return 1
    else:
        print(f"\n  Result: PASS")
        return 0


if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Checking structure...\n")
    sys.exit(check_structure())
