import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from conftest import TEMPLATE


def make_db(path, marker):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE note (body TEXT)")
    conn.execute("INSERT INTO note VALUES (?)", (marker,))
    conn.commit()
    conn.close()


def test_the_snapshot_opens_and_contains_what_was_written(tmp_path):
    """備份產出的檔案能被 sqlite3 開啟，而且含備份當下寫入的那筆資料。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import snapshot

    src = tmp_path / "db.sqlite3"
    make_db(src, "健檢寫入的測試資料")

    out = snapshot(src, tmp_path / "backup.sqlite3")

    rows = sqlite3.connect(out).execute("SELECT body FROM note").fetchall()
    assert rows == [("健檢寫入的測試資料",)]


def test_a_corrupt_snapshot_is_reported_not_returned(tmp_path):
    """快照壞掉的時候會報錯，不會交出一個看起來正常的壞備份。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import SnapshotCorrupt, verify

    broken = tmp_path / "backup.sqlite3"
    broken.write_bytes(b"not a database")

    import pytest
    with pytest.raises(SnapshotCorrupt):
        verify(broken)
    assert not broken.exists()


def test_a_healthy_snapshot_passes_verification(tmp_path):
    """完整的快照通過檢查，而且檔案留著。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import verify

    good = tmp_path / "backup.sqlite3"
    make_db(good, "x")

    assert verify(good) == good
    assert good.exists()


def test_an_existing_target_does_not_silently_overwrite(tmp_path):
    """目標檔已經存在時會報錯，不會把舊備份蓋掉。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import snapshot

    src = tmp_path / "db.sqlite3"
    make_db(src, "x")
    out = tmp_path / "backup.sqlite3"
    out.write_bytes(b"previous backup")

    import pytest
    with pytest.raises(FileExistsError):
        snapshot(src, out)
    assert out.read_bytes() == b"previous backup"


def test_backups_older_than_three_months_are_removed(tmp_path):
    """超過三個月的備份會被清掉，三個月內的留著。"""
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import expired_tags

    now = datetime(2026, 8, 9, tzinfo=timezone.utc)
    releases = [
        {"tagName": "backup-2026-08-08", "createdAt": (now - timedelta(days=1)).isoformat()},
        {"tagName": "backup-2026-06-01", "createdAt": (now - timedelta(days=69)).isoformat()},
        {"tagName": "backup-2026-05-01", "createdAt": (now - timedelta(days=100)).isoformat()},
    ]

    assert expired_tags(releases, now=now, keep_days=90) == ["backup-2026-05-01"]


def test_expired_tags_handles_the_real_github_cli_timestamp_format(tmp_path):
    """`gh release list --json createdAt` 回傳的是 `Z` 結尾（例如
    `2026-08-08T12:34:56Z`），不是測試常用的 `+00:00`。

    Python 3.10 的 `datetime.fromisoformat` 解析不了 `Z` 結尾（3.11 才支援），
    這個專案的 Python 下限是 3.10，所以兩種格式都要吃得下，否則正式清理
    備份的時候會直接丟例外，而不是只在測試裡才發現。
    """
    sys.path.insert(0, str(TEMPLATE / "scripts"))
    from backup_snapshot import expired_tags

    now = datetime(2026, 8, 9, tzinfo=timezone.utc)
    fresh = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stale = (now - timedelta(days=100)).strftime("%Y-%m-%dT%H:%M:%SZ")
    releases = [
        {"tagName": "backup-fresh", "createdAt": fresh},
        {"tagName": "backup-stale", "createdAt": stale},
    ]

    assert expired_tags(releases, now=now, keep_days=90) == ["backup-stale"]


def test_main_without_a_subcommand_prints_usage_instead_of_crashing():
    """沒給任何子指令時要印出用法，不是讓 `sys.argv[1]` 的 IndexError 冒出來。"""
    result = subprocess.run(
        [sys.executable, str(TEMPLATE / "scripts" / "backup_snapshot.py")],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "IndexError" not in result.stderr
    assert "用法" in result.stdout
