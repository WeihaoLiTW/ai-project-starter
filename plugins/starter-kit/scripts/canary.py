"""Prove that hooks actually fire inside Cowork.

Writes one line per event into the working folder. Task 1 is the only user
of this script; the health check replaces it with a real probe in Task 12.
"""

import datetime
import sys
from pathlib import Path

from _shared import emit, read_payload

payload = read_payload()
event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
line = f"{datetime.datetime.now().isoformat()} {event} keys={sorted(payload)}\n"

with (Path.cwd() / "hook-canary.log").open("a", encoding="utf-8") as handle:
    handle.write(line)

emit({})
