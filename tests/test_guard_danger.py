"""guard_danger.py: destructive shell commands are hard-blocked; safe ones run.

This is the hard rail that lets the kit run hands-off. Deleting, force-pushing,
and dropping tables are denied so they can never happen silently; ordinary
work (and a normal deploy push) passes straight through.
"""

import pytest

from conftest import run_hook

DANGEROUS_COMMANDS = [
    "rm -rf build",
    "rm -r node_modules",
    "sudo rm -f /tmp/x",
    "git push --force origin main",
    "git push -f",
    "git reset --hard HEAD~3",
    "git clean -fd",
    "psql -c 'DROP TABLE users;'",
    "mysql -e 'TRUNCATE TABLE orders'",
    "dd if=/dev/zero of=/dev/sda",
]

SAFE_COMMANDS = [
    "pytest -q",
    "python3 -m pip install -r requirements.lock.txt",
    "git commit -m 'save'",
    "git push origin main",
    "ls -la",
    "rm",
]


@pytest.mark.parametrize("command", DANGEROUS_COMMANDS)
def test_destructive_command_is_denied(command, tmp_path):
    code, response, _ = run_hook(
        "guard_danger.py", {"tool_input": {"command": command}}, cwd=tmp_path
    )
    assert code == 0
    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("command", SAFE_COMMANDS)
def test_safe_command_is_allowed(command, tmp_path):
    code, response, _ = run_hook(
        "guard_danger.py", {"tool_input": {"command": command}}, cwd=tmp_path
    )
    assert code == 0
    assert response == {}


def test_null_tool_input_does_not_crash(tmp_path):
    code, response, _ = run_hook(
        "guard_danger.py", {"tool_input": None}, cwd=tmp_path
    )
    assert code == 0
    assert response == {}
