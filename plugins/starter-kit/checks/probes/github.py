"""6 GitHub：repo 存在，而且 Actions 至少成功跑過一次。"""

from ..model import CheckResult


def probe(facts):
    info = facts.get("github", {})
    if not info.get("repo"):
        return CheckResult(
            id="github", title="GitHub", ok=False,
            detail=(
                "這個專案還沒有建立對應的 GitHub repo（存放程式碼、也是部署流程抓"
                "版本上線的地方）。沒有它，程式碼只存在這台機器上——機器壞掉或換一"
                "台電腦，工作成果就全部不見了，也沒辦法部署上線。"
            ),
            hint="跟我說一聲，我幫你建立 repo 並把現有的程式碼推上去。",
        )
    if info.get("last_conclusion") != "success":
        return CheckResult(
            id="github", title="GitHub", ok=False,
            detail=(
                f"{info['repo']} 有了，但 GitHub Actions（每次推程式碼上去，自動幫"
                f"你跑測試、部署的流程）最近一次結果是 "
                f"{info.get('last_conclusion') or '從來沒跑過'}。這代表你目前的改動"
                "可能沒被真的驗證過，正式環境上跑的也可能不是你以為的最新版本。"
            ),
            hint="跟我說一聲，我去看 Actions 的執行紀錄，找出卡在哪一步再修。",
        )
    return CheckResult(id="github", title="GitHub", ok=True,
                       detail=f"{info['repo']}，Actions 最近一次成功。")
