"""9 資料持久性與備份可還原。

這兩件事綁在一起，因為 spec 把它們綁在一起：備份要含的正是重新部署之後
還在的那筆資料。
"""

from ..model import CheckResult


def probe(facts):
    info = facts.get("backup", {})
    marker = info.get("marker")
    problems = []
    if not marker:
        problems.append("還沒有寫過測試資料，沒辦法確認資料會不會不見。")
    elif not info.get("survived_redeploy"):
        problems.append("寫進去的資料在重新部署之後不見了，代表 volume 沒掛好。")
    if not info.get("release_tag"):
        problems.append("備份還沒成功跑過一次。")
    elif not info.get("snapshot_opens"):
        problems.append("最新的備份檔打不開。")
    elif marker and marker not in info.get("snapshot_rows", []):
        problems.append("備份檔打得開，但裡面沒有那筆測試資料。")
    return CheckResult(
        id="data", title="資料安全", ok=not problems,
        detail="；".join(problems)
        or f"資料撐過重新部署，備份 {info['release_tag']} 打得開而且找得到那筆資料。",
    )
