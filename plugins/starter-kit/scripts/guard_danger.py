"""Refuse to run a destructive shell command on its own.

The kit runs hands-off: the behavior layer lets Claude read, write, and test
without asking. The one thing that must never happen silently is destruction:
a wiped directory, a force-pushed history, a dropped table. This hook is the
hard rail behind that promise. It inspects every Bash command and denies the
ones that destroy work irreversibly, so "deleting needs your say-so" is
enforced by code, not only by instructions. This is what lets the permission
mode run wide open while staying safe.

Publishing / deploying is deliberately NOT blocked here. Going live is a wanted
action; a blanket ban would break normal deploys. It is gated instead by the
deploy flow (look at staging first, ask before prod), not by this hook.

Denied, not asked: a denied command stops and returns to the user, who can run
it themselves if they truly mean to. It is a guard rail, not a security
boundary. A determined rewrite (an obfuscated command, an unusual tool) can
slip past, and over-matching is preferred to under-matching: blocking a safe
command costs a re-run, missing a destructive one costs the work.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _shared import emit, read_payload

# (pattern, plain-language description of what it destroys). Kept broad on
# purpose: a false positive is a re-run, a false negative is lost work.
DANGEROUS = [
    (re.compile(r"\brm\b.*\s-\w*[rf]"),
     "把整個資料夾或檔案刪掉（rm -r / -f）"),
    (re.compile(r"\bgit\s+push\b.*(?:--force|\s-f\b)"),
     "強制覆蓋 GitHub 上的歷史（git push --force）"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"),
     "丟掉還沒存檔的改動（git reset --hard）"),
    (re.compile(r"\bgit\s+clean\b.*\s-\w*f"),
     "刪掉還沒追蹤的檔案（git clean -f）"),
    (re.compile(r"\b(?:DROP|TRUNCATE)\s+(?:TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE),
     "刪掉整張資料表或資料庫（DROP / TRUNCATE）"),
    (re.compile(r"\bmkfs\b|\bdd\s+if="),
     "覆寫整個磁碟（mkfs / dd）"),
]


payload = read_payload()
tool_input = payload.get("tool_input")
if not isinstance(tool_input, dict):
    tool_input = {}
command = str(tool_input.get("command", ""))

for pattern, label in DANGEROUS:
    if pattern.search(command):
        emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"這個指令會{label}，屬於「刪除／破壞」類、做了很難救回來的"
                    "動作。這套環境設定成不讓我自己執行這種指令。如果你確定要，"
                    "請自己在終端機執行，或明確告訴我理由再繼續。"
                ),
            }
        })

emit({})
