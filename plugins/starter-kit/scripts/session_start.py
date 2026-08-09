"""Load the behaviour pillars at the start of every session."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _shared import emit, plugin_root, read_payload

read_payload()

pillars = plugin_root() / "behavior" / "pillars.md"
if not pillars.exists():
    emit({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "警告：環境包的行為設定檔找不到，Claude 現在是預設行為。"
                f"預期路徑：{pillars}"
            ),
        }
    })

emit({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": pillars.read_text("utf-8"),
    }
})
