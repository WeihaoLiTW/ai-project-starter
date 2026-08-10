"""9 資料持久性與備份可還原。

這兩件事綁在一起，因為 spec 把它們綁在一起：備份要含的正是重新部署之後
還在的那筆資料。
"""

from ..model import CheckResult


def _marker_present(marker, rows):
    """Whether `marker` shows up anywhere in `rows`.

    The skill tells Claude to write the whole row it read back (something
    like "id=1 body=m1 created=...") into `snapshot_rows`, not the bare
    marker text by itself. Comparing `marker in rows` is exact membership
    against that list, so a row that legitimately contains the marker as
    part of a longer string never matches — a complete backup gets reported
    as missing the data it actually has, which is the most expensive false
    red this report can produce. Matching by substring across the rows is
    what the data the skill actually writes calls for.
    """
    return any(marker in row for row in rows)


def probe(facts):
    info = facts.get("backup", {})
    marker = info.get("marker")
    problems = []
    hints = []
    if not marker:
        problems.append("還沒有寫過測試資料，沒辦法確認資料會不會不見。")
    elif not info.get("survived_redeploy"):
        problems.append("寫進去的資料在重新部署之後不見了，代表 volume 沒掛好。")
    if not info.get("release_tag"):
        problems.append(
            "備份還沒成功跑過一次。如果現在資料庫壞掉或被誤刪，你沒有任何備份可以"
            "救回資料，東西會直接永久消失。"
        )
        hints.append("跟我說一聲，我來手動觸發一次備份，確認它能跑成功。")
    elif not info.get("snapshot_opens"):
        problems.append(
            "最新一次的備份檔打不開。代表就算你以為有備份，那份其實是壞的——真的"
            "出事故要救資料時，這份備份等於不存在。"
        )
        hints.append("跟我說一聲，我來檢查備份檔案壞在哪裡，並重新跑一次。")
    elif marker and not _marker_present(marker, info.get("snapshot_rows", [])):
        problems.append(
            "備份檔打得開，但裡面沒有那筆測試資料，代表備份的內容不完整或抓的時間"
            "點不對——真的需要還原時，可能會發現該有的資料早就漏掉了。"
        )
        hints.append("跟我說一聲，我來檢查備份流程抓資料的時間點，找出漏掉的原因。")
    return CheckResult(
        id="data", title="資料安全", ok=not problems,
        detail="；".join(problems)
        or f"資料撐過重新部署，備份 {info['release_tag']} 打得開而且找得到那筆資料。",
        hint="；".join(hints),
    )
