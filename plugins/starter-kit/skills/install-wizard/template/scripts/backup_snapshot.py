"""Take a consistent snapshot of the SQLite database.

Copying the file can capture a torn write, producing a backup that looks
valid and is not — a failure only discovered during a restore. VACUUM INTO
avoids that, but SQLite documents that an interrupted run leaves a corrupt
output, so every snapshot is verified before it is handed back.
"""

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SnapshotCorrupt(RuntimeError):
    """The snapshot did not pass its integrity check and was discarded."""


def verify(path):
    """Return `path` if it is a healthy database; delete it and raise if not.

    Kept separate from `snapshot` so the corrupt path is reachable from a
    test without a test-only branch living in production code. The backup
    workflow also calls it on its own, after transferring the file.
    """
    path = Path(path)
    if path.stat().st_size == 0:
        path.unlink(missing_ok=True)
        raise SnapshotCorrupt(f"{path} 是空檔案，代表備份內容根本沒有送達（不是檔案損毀），已刪除。")

    conn = sqlite3.connect(path)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        healthy = bool(result) and result[0] == "ok"
    except sqlite3.DatabaseError:
        healthy = False
    finally:
        conn.close()

    if not healthy:
        path.unlink(missing_ok=True)
        raise SnapshotCorrupt(f"{path} 沒通過完整性檢查，已刪除。")
    return path


def snapshot(db_path, out_path):
    """Write a verified snapshot of `db_path` to `out_path`."""
    out_path = Path(out_path)
    if out_path.exists() and out_path.stat().st_size > 0:
        raise FileExistsError(f"{out_path} 已經存在，不覆蓋既有備份。")

    source = sqlite3.connect(db_path)
    try:
        source.execute("VACUUM INTO ?", (str(out_path),))
    finally:
        source.close()

    return verify(out_path)


def _parse_iso8601(value):
    """Parse an ISO-8601 timestamp, accepting a trailing `Z` (UTC).

    `datetime.fromisoformat` only learned to read a trailing `Z` in Python
    3.11. This project's floor is 3.10, and `gh release list --json
    createdAt` returns exactly that shape (`2026-08-08T12:34:56Z`) — so
    without this normalization, parsing real release data raises on every
    run, not just in tests that happen to use a `+00:00` offset instead.
    """
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def expired_tags(releases, now, keep_days):
    """Release tags older than the retention window."""
    cutoff = now - timedelta(days=keep_days)
    expired = []
    for release in releases:
        created = _parse_iso8601(release["createdAt"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created < cutoff:
            expired.append(release["tagName"])
    return expired


def main():
    import json

    usage = (
        "用法：\n"
        "  backup_snapshot.py expired <releases.json>\n"
        "  backup_snapshot.py verify <db 檔案路徑>\n"
        "  backup_snapshot.py <來源 db 路徑> <輸出檔路徑>"
    )

    if len(sys.argv) < 2:
        print(usage)
        return 1

    command = sys.argv[1]
    if command == "expired":
        if len(sys.argv) < 3:
            print(usage)
            return 1
        releases = json.loads(Path(sys.argv[2]).read_text("utf-8"))
        for tag in expired_tags(releases, datetime.now(timezone.utc), keep_days=90):
            print(tag)
        return 0
    if command == "verify":
        if len(sys.argv) < 3:
            print(usage)
            return 1
        verify(sys.argv[2])
        print("備份檔完整。")
        return 0
    if len(sys.argv) < 3:
        print(usage)
        return 1
    snapshot(command, sys.argv[2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
