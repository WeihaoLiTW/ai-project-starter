"""Refuse to write files that hold credentials.

The code repository is public, which is what buys unlimited CI minutes. The
price is that anything leaked is leaked publicly. This is a guard rail, not
insurance.

`.env.example` is allowed by filename because it is the conventional,
version-controlled template that documents which environment variables a
project needs. But a filename alone cannot prove a file is actually a
template rather than a real secret saved under a trusted name, so an
allowed path also gets its `content` inspected: any line assigning a
non-empty, non-placeholder value to a credential-shaped key (containing
SECRET, TOKEN, PASSWORD, PASSWD, API_KEY, or ending in _KEY, case
insensitive) is refused. Placeholder values recognized are: an empty
value, a value wrapped in `<...>`, a value made only of the characters
`x`, `X`, `.`, `-`, `_`, and whitespace, the literal `changeme`, and
`your-...-here`-shaped phrases. This catches the careless case — pasting
a real key into `.env.example` "for now" — and nothing more. It does not
catch a deliberately obfuscated or split secret, a secret assigned via
multi-line syntax, or a credential-shaped value under a key name that
does not match the list above. It is a guard rail, not a security
boundary; if `content` is absent from the payload (e.g. an `Edit` call
rather than a `Write`), there is nothing to inspect and the write is
allowed.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _shared import emit, read_payload, SECRET_PATH_ALLOWED, SECRET_PATH_BLOCKED

# ALLOWED/BLOCKED live in _shared.py so commit_if_green.py judges the same
# paths the same way — an allow-list checked before a block-list is the one
# place where a loose anchor fails open instead of closed, which is why
# _shared.py anchors `.env.example` with \Z rather than $.
ALLOWED = SECRET_PATH_ALLOWED
BLOCKED = SECRET_PATH_BLOCKED

# Key names that look like they hold a credential. Deliberately broad: any
# key containing one of these substrings, or ending in _KEY.
CREDENTIAL_KEY = re.compile(r"SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|_KEY\Z", re.IGNORECASE)

# "key = value" lines, optionally prefixed with "export " as shells allow.
ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")

# A value made only of filler characters (xxx, x.x.x, ---, blank, ...).
PLACEHOLDER_FILLER = re.compile(r"^[xX.\-_\s]*$")

# "your-secret-key-here", "your_api_key_here", etc.
PLACEHOLDER_YOUR_HERE = re.compile(r"^your[-_].+[-_]here$", re.IGNORECASE)


def _is_placeholder_value(value):
    """Whether a `.env.example` value looks like a template placeholder,
    as opposed to a populated real credential."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1].strip()
    if not value:
        return True
    if value.startswith("<") and value.endswith(">"):
        return True
    if PLACEHOLDER_FILLER.match(value):
        return True
    if value.lower() == "changeme":
        return True
    if PLACEHOLDER_YOUR_HERE.match(value):
        return True
    return False


def _offending_credential_key(content):
    """The first key in `content` that assigns a populated, non-placeholder
    value to a credential-shaped name. None if there is no such line."""
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ASSIGNMENT.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        if not CREDENTIAL_KEY.search(key):
            continue
        if not _is_placeholder_value(value):
            return key
    return None


payload = read_payload()
tool_input = payload.get("tool_input")
if not isinstance(tool_input, dict):
    tool_input = {}
path = str(tool_input.get("file_path", ""))

for allowed in ALLOWED:
    if allowed.search(path):
        content = tool_input.get("content")
        if isinstance(content, str):
            offending_key = _offending_credential_key(content)
            if offending_key:
                name = path.rsplit("/", 1)[-1]
                emit({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"{name} 看起來是環境變數範本檔，但其中的 "
                            f"{offending_key} 被填入了實際的值，不是空白或"
                            "佔位字串。這個檔案會照慣例進版控，寫進真的密鑰"
                            "就等於公開。請把這個值清空或換成佔位字串"
                            "（例如 changeme），真正的密鑰改存進不進版控的 "
                            ".env。"
                        ),
                    }
                })
        emit({})

for pattern, label in BLOCKED:
    if pattern.search(path):
        name = path.rsplit("/", 1)[-1]
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"{name} 看起來是{label}。這個專案的程式碼是公開的，"
                    "密鑰寫進去就等於公開。請改成用環境變數，"
                    "或告訴我你確定要這樣做的理由。"
                ),
            }
        })

emit({})
