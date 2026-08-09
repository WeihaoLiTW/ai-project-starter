"""1 執行環境：本機模式、工作資料夾位置。"""

import platform
from pathlib import Path

from ..model import CheckResult


def probe(facts):
    problems = []
    if facts.get("local_mode") is not True:
        problems.append(
            "現在不是本機模式。雲端模式會讀到舊的檔案內容，而且它回報的檔案時間是對的，"
            "所以從裡面怎麼檢查都查不出來。請到設定關掉「Run new tasks in the cloud」。"
        )
    workdir = Path(facts.get("workdir", Path.cwd()))
    if platform.system() == "Windows" or str(workdir).startswith("\\\\"):
        text = str(workdir)
        if text.startswith("\\\\") or ":" not in text[:2]:
            problems.append("工作資料夾在網路磁碟上，Cowork 不支援。請搬到 C:\\Users\\ 底下。")
    return CheckResult(
        id="environment",
        title="執行環境",
        ok=not problems,
        detail="；".join(problems) or f"本機模式，工作資料夾在 {workdir}",
    )
