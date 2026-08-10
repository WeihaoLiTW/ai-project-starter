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
SCRIPT_PATH = re.compile(r"scripts/[\w.\-/]+\.(?:py|sh)")
JOBS_KEY = re.compile(r"^jobs:\s*$")
JOB_KEY = re.compile(r"^  [A-Za-z0-9_-]+:\s*$")


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


def first_job_text(workflow):
    """The text of just the first job block (2-space-indented key directly
    under `jobs:`), up to but not including the next one.

    This repository's first job (`test`) is the one that is supposed to
    mirror `scripts/run_tests.sh` exactly on every push. A later job (e.g.
    `deploy-safety`) legitimately needs things a local run cannot provide —
    real deployment secrets — so it is deliberately out of scope for
    `stray_script_commands` below; scoping by job avoids flagging a script
    that only that later job has a reason to run. Still line matching, not
    a YAML parser: it only recognizes this repository's own workflow shape.

    Anchored on the top-level `jobs:` key first, then the first
    2-space-indented key found after it. Without that anchor, the first
    2-space-indented key in a real workflow file is `push:` under `on:`
    (the trigger block sits above `jobs:`), not `test:` — this function
    would then hand back the trigger block and the caller would never see
    any job at all, let alone the first one.
    """
    lines = workflow.splitlines()
    jobs_at = None
    for i, line in enumerate(lines):
        if JOBS_KEY.match(line):
            jobs_at = i
            break
    if jobs_at is None:
        return workflow
    lines = lines[jobs_at + 1 :]
    start = None
    end = len(lines)
    for i, line in enumerate(lines):
        if JOB_KEY.match(line):
            if start is None:
                start = i
            else:
                end = i
                break
    return "\n".join(lines[start:end]) if start is not None else workflow


def stray_script_commands(job_text, local_script_text):
    """CI-only invocations of another script under `scripts/`, within a
    single job's text.

    `stray_test_commands` above only recognizes a bare `pytest` call as a
    second test path. A CI step that runs some other script under
    `scripts/` directly — bypassing the entrypoint the same way — is the
    same class of drift (a check that exists only in CI, so a green run
    locally proves nothing about it) but was invisible to that regex. This
    flags any `scripts/*.py` or `scripts/*.sh` reference on a non-comment
    line that is not the entrypoint itself and does not also appear
    somewhere inside `scripts/run_tests.sh`'s own text — a script that
    entrypoint already runs is covered locally, no matter how many times
    or where else it is also invoked.
    """
    stray = []
    for line in job_text.splitlines():
        if _is_comment_line(line):
            continue
        for match in SCRIPT_PATH.findall(line):
            if match == ENTRYPOINT or match in local_script_text:
                continue
            if match not in stray:
                stray.append(match)
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
    entrypoint_path = Path(ENTRYPOINT)
    local_script_text = entrypoint_path.read_text("utf-8") if entrypoint_path.exists() else ""
    stray_scripts = stray_script_commands(first_job_text(text), local_script_text)
    if stray_scripts:
        print("CI 的第一個 job 裡直接呼叫了另一個腳本，本機的 run_tests.sh 沒有走它，重現不了它的紅：")
        for item in stray_scripts:
            print(f"  - {item}")
        return 1
    print("CI 跟本機跑的是同一組測試。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
