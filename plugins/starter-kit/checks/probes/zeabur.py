"""7 Zeabur 走哪一條路。

Ordered by coverage, not by convenience. The CLI does everything, but
zeabur.com sits outside the network allowlist and the mechanism to add a
custom domain to that allowlist has been broken for months — even a
Team-plan admin cannot work around it, and a managed account cannot even
change that setting to try. MCP is not network-restricted, but its 26
tools have no way to rent a server, redeploy, or delete anything, while
renting is step one of installation and redeploy is a daily operation.
The browser fills exactly those gaps and is also unrestricted, but breaks
whenever Zeabur redesigns its console.

So the path is not chosen at design time, it is probed at install time.
Whether each path is actually reachable — MCP connectivity, whether the
Chrome extension is installed — is a fact that only lives on Claude's
side, not in this shell. This probe only reads the three booleans plus
`proven` from `facts["zeabur"]` and decides; detecting them is the
health-check skill's job, not this module's.
"""

from ..model import CheckResult

PATHS = [
    ("cli", "CLI", "全部操作都能做，也最快。"),
    ("mcp", "MCP", "部署、log、環境變數、網域可以做；租主機、重新部署、刪除做不到。"),
    ("browser", "瀏覽器", "MCP 做不到的那幾項靠它，但畫面改版就會壞。"),
]

WHY_BLOCKED = {
    "cli": (
        "CLI（用文字指令操作 Zeabur 的方式）：zeabur.com 不在允許連線的網域清單裡，"
        "而且加入自訂網域的功能本身故障中、修了五個月還沒修好，連系統管理員都改不了"
        "這個設定，所以連「試試看能不能連」都做不到"
    ),
    "mcp": "MCP（讓 Claude 直接呼叫 Zeabur 功能的整合方式）：連不上 Zeabur 的 MCP 伺服器",
    "browser": "瀏覽器（Claude 幫你操作 Chrome 分頁的方式）：Chrome 擴充功能沒有安裝，或還沒開啟",
}


def probe(facts):
    info = facts.get("zeabur", {})
    available = [(key, label, note) for key, label, note in PATHS if info.get(key)]

    if not available:
        return CheckResult(
            id="zeabur",
            title="Zeabur 操作路徑",
            ok=False,
            detail=(
                "三條路都不通，沒辦法對 Zeabur 做任何操作，也就沒辦法部署、也沒辦法"
                "查看正式環境現在的狀態：" +
                "；".join(WHY_BLOCKED[key] for key, _, _ in PATHS) + "。"
            ),
            hint=(
                "三條全斷就完全卡住了。先確認 Chrome 擴充功能有沒有裝、有沒有開啟——"
                "那條不受網路白名單限制，最有機會先打通。"
            ),
        )

    key, label, note = available[0]
    if info.get("proven") is False:
        return CheckResult(
            id="zeabur",
            title="Zeabur 操作路徑",
            ok=False,
            detail=(
                f"{label} 看起來可以連得上，但還沒有實際跑成功過一次操作，不算數。"
                "光是連得上不代表真的能用——沒有實測過，你不會知道它是不是卡在權限"
                "或設定上，等真的要部署時才發現行不通。"
            ),
            hint="跟我說一聲，我用這條路跑一次唯讀操作（例如列出專案），確認它真的能動。",
        )

    others = [lbl for _key, lbl, _note in available[1:]]
    backup = f"備援還有 {'、'.join(others)}。" if others else "沒有備援，這條路一斷就完全卡住。"
    return CheckResult(
        id="zeabur",
        title="Zeabur 操作路徑",
        ok=True,
        detail=f"{label} —— {note} 已實際跑成功一次操作。{backup}",
    )
