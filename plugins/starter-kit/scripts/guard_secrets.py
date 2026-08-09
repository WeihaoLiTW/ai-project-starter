"""Refuse to write files that hold credentials.

The code repository is public, which is what buys unlimited CI minutes. The
price is that anything leaked is leaked publicly. This is a guard rail, not
insurance.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _shared import emit, read_payload

# Conventionally checked into version control on purpose: empty key names
# meant to document which environment variables a project needs, not actual
# secrets. Checked before BLOCKED so the template reading never reaches the
# .env rule below.
ALLOWED = [
    re.compile(r"(^|/)\.env\.example$"),
]

BLOCKED = [
    (re.compile(r"(^|/)\.env(\.|$)"), "環境變數檔"),
    (re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)$"), "SSH 私鑰"),
    (re.compile(r"\.(pem|key|p12|pfx)$"), "憑證或私鑰"),
    (re.compile(r"credentials?\.json$"), "雲端服務憑證"),
    (re.compile(r"(^|/)\.netrc$"), "登入資訊檔"),
]

payload = read_payload()
path = str(payload.get("tool_input", {}).get("file_path", ""))

for allowed in ALLOWED:
    if allowed.search(path):
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
