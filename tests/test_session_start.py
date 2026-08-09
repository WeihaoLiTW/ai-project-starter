"""session_start.py 的兩種情境：設定檔在、設定檔不在。

第二種情境是額外補上的守門測試——task 8 的要求是「找不到行為設定檔的時候
要大聲失敗」，這條分支必須真的被逼著走到一次，而不是只讀程式碼判斷「看起來
應該沒問題」。
"""

import json
import os
import shutil
import subprocess
import sys

from conftest import PLUGIN

SCRIPTS_DIR = PLUGIN / "scripts"


def test_session_start_injects_the_pillars_when_present():
    """設定檔存在時，開場注入要完整帶出三支柱裡「放手模式」與「翻譯是有損的」
    這兩句，證明整份 pillars.md 真的被讀進去、而不是只回傳片段。"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "session_start.py")],
        input="{}",
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode == 0
    context = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "放手模式" in context
    assert "翻譯是有損的" in context


def test_session_start_warns_loudly_when_pillars_missing(tmp_path):
    """行為設定檔找不到時，輸出的必須是警告，不能是靜默的空內容。

    模擬一個裝壞的環境包：只複製 scripts/ 底下這兩個檔案，不帶 behavior/
    目錄，再把 CLAUDE_PLUGIN_ROOT 指到一個不存在的路徑，逼 plugin_root()
    落回 fallback（也就是這個裝壞環境包自己的位置），讓 session_start.py
    真的走到「找不到 pillars.md」那個分支，而不是意外落回真正的 plugin
    根目錄（那裡有真的 pillars.md，測不到這條分支）。
    """
    broken_plugin = tmp_path / "broken-plugin"
    (broken_plugin / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPTS_DIR / "_shared.py", broken_plugin / "scripts" / "_shared.py")
    shutil.copy(
        SCRIPTS_DIR / "session_start.py", broken_plugin / "scripts" / "session_start.py"
    )
    assert not (broken_plugin / "behavior").exists()

    env = dict(os.environ)
    env["CLAUDE_PLUGIN_ROOT"] = str(tmp_path / "does-not-exist")

    proc = subprocess.run(
        [sys.executable, str(broken_plugin / "scripts" / "session_start.py")],
        input="{}",
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode == 0
    assert proc.stdout.strip() != ""
    context = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "警告" in context
    assert "找不到" in context
