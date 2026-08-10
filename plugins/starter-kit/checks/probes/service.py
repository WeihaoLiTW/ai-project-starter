"""8 兩個環境活著，而且正式環境的設定是安全的。"""

from ..model import CheckResult

TEMPLATE_DEFAULT_KEY = "django-insecure-CHANGE-ME"


def _status_code(status):
    """`status` as an int, or None if it is missing or not a status code.

    The skill's own instructions tell Claude to get this value from
    `curl -w '%{http_code}'`, which prints a string ("200"), not an int.
    Comparing that string against the int 200 with `!=` is always true,
    so every successful probe was being reported as broken. Accept either
    shape the same way; anything that is not a whole number (empty, "連不
    上", None) stays None so it still reads as "can't reach it".
    """
    try:
        return int(status)
    except (TypeError, ValueError):
        return None


def probe(facts):
    endpoints = facts.get("endpoints", {})
    env = facts.get("prod_env", {})
    problems = []
    hints = []
    for name in ("staging", "prod"):
        status = endpoints.get(name)
        if _status_code(status) != 200:
            problems.append(f"{name} 回 {status or '連不上'}，不是 200。")
    if env.get("DJANGO_DEBUG") == "1":
        problems.append(
            "正式環境的 DEBUG 是開的。正式環境開著它，出錯時會把程式碼細節顯示給"
            "所有看到這個網站的人看，等於把系統內部攤開給外人看。"
        )
        hints.append("跟我說一聲，我幫你把正式環境的 DJANGO_DEBUG 關掉。")
    key = env.get("DJANGO_SECRET_KEY", "")
    if not key or key == TEMPLATE_DEFAULT_KEY or key.startswith("django-insecure-"):
        problems.append(
            "正式環境的 SECRET_KEY 還是預設值或空的。這把鑰匙用來簽登入狀態，沒有"
            "它、或用著公開的預設值，任何人都能偽造登入，直接假冒成任何使用者。"
        )
        hints.append("跟我說一聲，我幫你產生一組新的 SECRET_KEY 並設定到正式環境。")
    if "*" in [h.strip() for h in env.get("DJANGO_ALLOWED_HOSTS", "").split(",")]:
        problems.append(
            "正式環境的 ALLOWED_HOSTS 含有萬用字元，等於接受任何網址轉過來的請求，"
            "攻擊者可以偽造成你的網站，把使用者導去別的地方騙資料。"
        )
        hints.append("跟我說一聲，我幫你把正式環境的 ALLOWED_HOSTS 換成實際的網域名稱。")
    return CheckResult(
        id="service", title="兩個環境", ok=not problems,
        detail="；".join(problems) or "staging 與 prod 都回 200，正式環境設定安全。",
        hint="；".join(hints),
    )
