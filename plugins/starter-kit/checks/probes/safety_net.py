"""4 保命繩通電：三個 hook 是不是真的會跑。

安裝了不等於會跑。Cowork 官方文件沒有講它的 VM 裡哪些 hook 事件會觸發，
所以這一項驗的是實際跑過的痕跡，不是設定檔的內容。
"""

from ..model import CheckResult

EXPECTED = {
    "SessionStart": "每次對話開始載入行為設定",
    "PreToolUse": "阻止密鑰被寫進檔案",
    "Stop": "測試綠了才存檔",
}


def probe(facts):
    fired = set(facts.get("hooks_fired", []))
    missing = [f"{name}（{what}）" for name, what in EXPECTED.items() if name not in fired]
    if missing:
        return CheckResult(
            id="safety_net",
            title="三道保命繩",
            ok=False,
            detail="這幾道沒有通電：" + "；".join(missing),
            hint="沒通電代表保護是假的，不要在這個狀態下繼續做正式的東西。",
        )
    return CheckResult(
        id="safety_net", title="三道保命繩", ok=True, detail="三道都通電了。"
    )
