"""Shared helpers for the plugin's hooks.

Standard library only. These scripts must run when pip is broken, when the
network is down, and when no virtualenv is active.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


_JSON_TYPE_NAMES = {
    bool: "boolean",
    int: "number",
    float: "number",
    str: "string",
    list: "array",
    type(None): "null",
}


def read_payload():
    """Read the hook payload from stdin.

    Always returns a dict. This is a guarantee, not a convention: every
    caller downstream can treat the result as a dict without checking.

    - Empty or whitespace-only stdin returns {} silently.
    - Malformed JSON writes one line to stderr and returns {}.
    - Valid JSON that is not a JSON object (a number, string, boolean,
      null, or array) writes one line to stderr naming what it got, and
      returns {}.
    - Bytes on stdin that are not valid UTF-8 are decoded with
      errors="replace" instead of raising.

    Never raises, for any byte sequence on stdin.
    """
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is not None:
        raw = buffer.read().decode("utf-8", errors="replace").strip()
    else:
        raw = sys.stdin.read().strip()

    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        sys.stderr.write(f"Failed to parse hook payload: {exc}\n")
        return {}

    if not isinstance(parsed, dict):
        type_name = _JSON_TYPE_NAMES.get(type(parsed), type(parsed).__name__)
        sys.stderr.write(f"Hook payload must be a JSON object; got {type_name}\n")
        return {}

    return parsed


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
    except OSError as exc:
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

    The fallback must be audible. A silent one would make a plugin that
    cannot find its own files look like a working plugin.
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


# Path patterns describing what counts as a secret file. Shared by
# guard_secrets.py (refuses to write these) and commit_if_green.py (refuses
# to commit these even if they reached disk some other way, e.g. created
# directly rather than through a Write/Edit tool call). One definition, so
# the two hooks cannot drift apart on what counts as a secret.
#
# `.env.example` is checked first: it is the conventional, version-controlled
# template that documents which environment variables a project needs, not a
# real credential. Anchored with \Z (not $) so a trailing newline in the path
# string cannot slip a distinct filename like ".env.example\n" through as if
# it were the exact allowed name.
SECRET_PATH_ALLOWED = [
    re.compile(r"(^|/)\.env\.example\Z"),
]

SECRET_PATH_BLOCKED = [
    (re.compile(r"(^|/)\.env(\.|$)"), "環境變數檔"),
    (re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)$"), "SSH 私鑰"),
    (re.compile(r"\.(pem|key|p12|pfx)$"), "憑證或私鑰"),
    (re.compile(r"credentials?\.json$"), "雲端服務憑證"),
    (re.compile(r"(^|/)\.netrc$"), "登入資訊檔"),
]


def secret_label(path):
    """The human-readable label for the secret category `path` matches, or
    None if `path` does not look like a secret.

    This only judges the path string, the same way commit_if_green.py needs
    to (files on disk at commit time, no `tool_input.content` to inspect).
    guard_secrets.py additionally inspects file content for the
    `.env.example` case, which is a Write-time concern this function does
    not need to cover.
    """
    for allowed in SECRET_PATH_ALLOWED:
        if allowed.search(path):
            return None
    for pattern, label in SECRET_PATH_BLOCKED:
        if pattern.search(path):
            return label
    return None
