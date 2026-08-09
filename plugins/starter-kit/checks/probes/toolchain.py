"""2 工具鏈：Python、git、SQLite 版本。"""

import sqlite3
import sys

from .._shim import run
from ..model import CheckResult

MIN_SQLITE = (3, 27, 0)


def platform_version():
    return ".".join(str(part) for part in sys.version_info[:3])


def probe(facts):
    problems = []
    if sys.version_info < (3, 10):
        problems.append(f"Python 太舊（{platform_version()}），需要 3.10 以上。")
    version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    if version < MIN_SQLITE:
        problems.append(
            f"SQLite 是 {sqlite3.sqlite_version}，備份用的功能需要 3.27.0 以上。"
        )
    code, out, _ = run(["git", "--version"], cwd=".")
    if code != 0:
        problems.append("找不到 git。")
    return CheckResult(
        id="toolchain",
        title="工具鏈",
        ok=not problems,
        detail="；".join(problems)
        or f"Python {platform_version()}、SQLite {sqlite3.sqlite_version}、{out.strip()}",
    )
