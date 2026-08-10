"""1 執行環境：本機模式、工作資料夾位置。"""

import re
from pathlib import Path

from ..model import CheckResult

# Judged from the text of `facts["workdir"]` the skill supplies, not from
# `platform.system()` of whatever machine runs this probe. The probe always
# runs inside the Cowork VM (Ubuntu on aarch64), never on the user's own
# Windows machine, so gating on the probe's own platform meant this branch
# could never fire for the one OS it exists to check — a UNC path slipped
# through anyway because the network-drive check did not depend on that
# gate, but the "must be under C:\Users\" constraint was unreachable dead
# code, and a Windows user with a network drive or a redirected/relocated
# "Documents" folder went green as if that had been checked.
WINDOWS_PATH = re.compile(r"^[A-Za-z]:\\|^\\\\")
SAFE_WINDOWS_ROOT = re.compile(r"^[A-Za-z]:\\Users\\", re.IGNORECASE)


def probe(facts):
    problems = []
    if facts.get("local_mode") is not True:
        problems.append(
            "現在不是本機模式。雲端模式會讀到舊的檔案內容，而且它回報的檔案時間是對的，"
            "所以從裡面怎麼檢查都查不出來。請到設定關掉「Run new tasks in the cloud」。"
        )
    workdir = str(facts.get("workdir", Path.cwd()))
    if WINDOWS_PATH.match(workdir) and not SAFE_WINDOWS_ROOT.match(workdir):
        problems.append(
            "工作資料夾不在 C:\\Users\\ 底下（可能是網路磁碟，或被搬過位置的「文件」"
            "資料夾）。Cowork 不支援這種資料夾，請搬到 C:\\Users\\<你的帳號名稱>\\ 底下。"
        )
    return CheckResult(
        id="environment",
        title="執行環境",
        ok=not problems,
        detail="；".join(problems) or f"本機模式，工作資料夾在 {workdir}",
    )
