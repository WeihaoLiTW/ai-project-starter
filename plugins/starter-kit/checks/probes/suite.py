"""3 測試綠且 30 秒內跑完。"""

import time
from pathlib import Path

from .._shim import run
from ..model import CheckResult

BUDGET_SECONDS = 30


def probe(facts):
    root = Path(facts.get("repo", "."))
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
