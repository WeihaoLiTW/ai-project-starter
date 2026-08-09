"""6 GitHub：repo 存在，而且 Actions 至少成功跑過一次。"""

from ..model import CheckResult


def probe(facts):
    info = facts.get("github", {})
    if not info.get("repo"):
        return CheckResult(id="github", title="GitHub", ok=False,
                           detail="還沒有對應的 repo。")
    if info.get("last_conclusion") != "success":
        return CheckResult(
            id="github", title="GitHub", ok=False,
            detail=f"{info['repo']} 有了，但 Actions 最近一次是 "
                   f"{info.get('last_conclusion') or '從來沒跑過'}。",
        )
    return CheckResult(id="github", title="GitHub", ok=True,
                       detail=f"{info['repo']}，Actions 最近一次成功。")
