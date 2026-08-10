"""3 測試綠且 30 秒內跑完。"""

import time
from pathlib import Path

from .._shim import run
from ..model import CheckResult

BUDGET_SECONDS = 30


def probe(facts):
    repo = facts.get("repo")
    if not repo:
        # Falling back to "." used to mean "whatever directory this process
        # happens to be running in" — per the skill's own instructions that
        # is this plugin's own directory, not the user's project, once it
        # has `cd`ed there to run `python3 -m checks.collect`. A missing
        # `repo` is the skill failing to do its job, not a fact about the
        # user's project, and must not silently turn into checking the
        # wrong one.
        return CheckResult(
            id="suite", title="測試", ok=False,
            detail="沒有拿到使用者專案的資料夾路徑（facts 裡缺了 repo），"
                   "不知道要檢查哪個專案，無法檢查。",
        )
    root = Path(repo)
    runner = root / "scripts" / "run_tests.sh"
    if not runner.exists():
        return CheckResult(
            id="suite", title="測試", ok=False,
            detail="這個專案還沒有測試入口，所以沒有任何東西在保護你。",
        )
    started = time.monotonic()
    code, out, err = run(["sh", str(runner)], cwd=root, timeout=300)
    elapsed = time.monotonic() - started
    if code != 0:
        return CheckResult(id="suite", title="測試", ok=False,
                           detail=(out + err)[-800:])
    if elapsed >= BUDGET_SECONDS:
        return CheckResult(
            id="suite", title="測試", ok=False,
            detail=f"測試是綠的，但跑了 {elapsed:.1f} 秒，超過 {BUDGET_SECONDS} 秒。",
            hint="每輪對話結束都會跑一次，太慢會讓每次對話都卡住。",
        )
    return CheckResult(id="suite", title="測試", ok=True,
                       detail=f"全綠，{elapsed:.1f} 秒。")
