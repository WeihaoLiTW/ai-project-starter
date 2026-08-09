"""Keep CI and local on one test path.

Parsing YAML would need a dependency, and these scripts are standard library
only. The workflow is ours, so matching on lines is enough — but it is only
line matching, not a YAML parser. Comment lines (first non-whitespace
character is '#') are excluded from both checks below, so a script name or
the word "pytest" mentioned only in a comment does not count as evidence of
anything. Anything else on a line is treated as executable: a step's `name:`
field that happens to contain the word "pytest" is indistinguishable from a
real `run:` command and will still be flagged. This module can tell an
executable line from a comment; it cannot tell a `run:` command from
arbitrary prose.
"""

import re
import sys
from pathlib import Path

ENTRYPOINT = "scripts/run_tests.sh"
TEST_COMMAND = re.compile(r"^\s*(?:-\s*run:\s*)?(.*\bpytest\b.*)$")


def _is_comment_line(line):
    """A line whose first non-whitespace character is '#'."""
    return line.lstrip().startswith("#")


def uses_shared_entrypoint(workflow):
    """True when a non-comment line runs the same script local runs."""
    for line in workflow.splitlines():
        if _is_comment_line(line):
            continue
        if ENTRYPOINT in line:
            return True
    return False


def stray_test_commands(workflow):
    """Test invocations that bypass the shared entrypoint."""
    stray = []
    for line in workflow.splitlines():
        if _is_comment_line(line):
            continue
        if ENTRYPOINT in line:
            continue
        match = TEST_COMMAND.match(line)
        if match:
            stray.append(match.group(1).strip())
    return stray


def main():
    workflow = Path(".github/workflows/tests.yml")
    if not workflow.exists():
        print("找不到 CI 設定檔。")
        return 1
    text = workflow.read_text("utf-8")
    if not uses_shared_entrypoint(text):
        print(f"CI 沒有走 {ENTRYPOINT}，本機跟 CI 會跑出不一樣的結果。")
        return 1
    stray = stray_test_commands(text)
    if stray:
        print("CI 裡有另一條測試路徑，本機重現不了它的紅：")
        for item in stray:
            print(f"  - {item}")
        return 1
    print("CI 跟本機跑的是同一組測試。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
