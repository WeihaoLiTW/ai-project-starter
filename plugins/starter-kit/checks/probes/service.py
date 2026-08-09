"""8 兩個環境活著，而且正式環境的設定是安全的。"""

from ..model import CheckResult

TEMPLATE_DEFAULT_KEY = "django-insecure-CHANGE-ME"


def probe(facts):
    endpoints = facts.get("endpoints", {})
    env = facts.get("prod_env", {})
    problems = []
    for name in ("staging", "prod"):
        status = endpoints.get(name)
        if status != 200:
            problems.append(f"{name} 回 {status or '連不上'}，不是 200。")
    if env.get("DJANGO_DEBUG") == "1":
        problems.append("正式環境的 DEBUG 是開的。")
    key = env.get("DJANGO_SECRET_KEY", "")
    if not key or key == TEMPLATE_DEFAULT_KEY or key.startswith("django-insecure-"):
        problems.append("正式環境的 SECRET_KEY 還是預設值或空的。")
    if "*" in [h.strip() for h in env.get("DJANGO_ALLOWED_HOSTS", "").split(",")]:
        problems.append("正式環境的 ALLOWED_HOSTS 含有萬用字元。")
    return CheckResult(
        id="service", title="兩個環境", ok=not problems,
        detail="；".join(problems) or "staging 與 prod 都回 200，正式環境設定安全。",
    )
