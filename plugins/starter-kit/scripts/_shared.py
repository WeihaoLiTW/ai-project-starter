"""Shared helpers for the plugin's hooks.

Standard library only. These scripts must run when pip is broken, when the
network is down, and when no virtualenv is active.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def read_payload():
    """Read the hook payload from stdin. Returns {} when there is nothing."""
    raw = sys.stdin.read().strip()
    return json.loads(raw) if raw else {}


def emit(obj):
    """Write a hook response to stdout and exit cleanly."""
    if obj:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.exit(0)


def run(cmd, cwd, timeout=120):
    """Run a command, never raising. Returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"
    except FileNotFoundError as exc:
        return 127, "", str(exc)


def repo_root(start):
    """Walk up from `start` looking for a .git directory. None if not found."""
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def plugin_root():
    """The plugin directory.

    CLAUDE_PLUGIN_ROOT is documented for Claude Code and Cowork states it
    shares the same hooks schema, but Cowork does not document how the
    variable maps inside its VM. If the variable is set and names an existing
    directory, return it silently. Otherwise write one line to stderr and
    return the fallback (this file's parent directory).
    """
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    fallback = Path(__file__).resolve().parent.parent

    if env is None:
        sys.stderr.write("CLAUDE_PLUGIN_ROOT is not set; using fallback\n")
        return fallback

    path = Path(env)
    if path.is_dir():
        return path

    sys.stderr.write(f"CLAUDE_PLUGIN_ROOT={env} does not exist; using fallback\n")
    return fallback
