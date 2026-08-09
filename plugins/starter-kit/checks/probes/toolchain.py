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
    hints = []
    if sys.version_info < (3, 10):
        problems.append(
            f"Python 版本是 {platform_version()}，太舊了，這個專案需要 3.10 以上才能"
            "執行。版本不夠新的話，程式一啟動就會報錯，整個專案在這台機器上完全跑不"
            "起來。"
        )
        hints.append("跟我說一聲，我幫你確認能不能裝新版 Python，並帶你更新。")
    version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    if version < MIN_SQLITE:
        problems.append(
            f"SQLite（存資料用的資料庫引擎）版本是 {sqlite3.sqlite_version}，太舊了，"
            "備份功能需要 3.27.0 以上才能正常運作。版本不夠的話，備份可能建立失敗，"
            "或是建出來卻是壞的，等於你以為有備份，出事故時其實救不回資料。"
        )
        hints.append("跟我說一聲，我幫你確認怎麼更新 SQLite（通常要一併更新 Python 版本）。")
    code, out, _ = run(["git", "--version"], cwd=".")
    if code != 0:
        problems.append(
            "找不到 git（版本控制工具，用來記錄程式碼的變更歷史，也負責把改動送上 "
            "GitHub 觸發部署）。沒有它，你的改動沒辦法被存成紀錄，也沒辦法推上線，"
            "等於這台機器完全沒辦法把工作成果部署出去。"
        )
        hints.append("跟我說一聲，我幫你確認怎麼安裝 git（Mac 用 Homebrew，Windows 用官方安裝檔）。")
    return CheckResult(
        id="toolchain",
        title="工具鏈",
        ok=not problems,
        detail="；".join(problems)
        or f"Python {platform_version()}、SQLite {sqlite3.sqlite_version}、{out.strip()}",
        hint="；".join(hints),
    )
