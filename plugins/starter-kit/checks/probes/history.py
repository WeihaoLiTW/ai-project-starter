"""5 git 歷史抽驗：任一個 commit checkout 出來都是綠的。

Each commit is checked out into a throwaway worktree under a temporary
directory. The user's working folder is never touched — checking it out in
place would fail on a dirty tree, or strand the repository on a detached
HEAD with their work apparently gone.
"""

import random
import shutil
import tempfile
from pathlib import Path

from .._shim import run
from ..model import CheckResult


def probe(facts):
    root = Path(facts.get("repo", "."))
    sample = int(facts.get("sample", 3))
    code, out, _ = run(["git", "rev-list", "HEAD"], cwd=root)
    if code != 0:
        return CheckResult(id="history", title="歷史版本", ok=False,
                           detail="讀不到 git 歷史。")

    commits = out.split()
    chosen = commits if len(commits) <= sample else random.sample(commits, sample)
    broken = []
    unchecked = []
    exercised = 0
    scratch = Path(tempfile.mkdtemp(prefix="health-history-"))
    try:
        for commit in chosen:
            checkout = scratch / commit[:7]
            code, _, err = run(
                ["git", "worktree", "add", "--detach", "-q", str(checkout), commit],
                cwd=root,
            )
            if code != 0:
                broken.append(f"{commit[:7]}（取不出來：{err.strip()[:80]}）")
                continue
            try:
                runner = checkout / "scripts" / "run_tests.sh"
                if not runner.exists():
                    # No test entrypoint at this commit: nothing was run,
                    # so this cannot be counted toward "checked and green" —
                    # doing so is exactly how the summary below used to
                    # assert #8 ("any commit you check out runs") on zero
                    # evidence. Recorded separately so the detail line can
                    # say so instead of silently inflating the pass count.
                    unchecked.append(commit[:7])
                    continue
                exercised += 1
                code, _, _ = run(["sh", str(runner)], cwd=checkout, timeout=300)
                if code != 0:
                    broken.append(commit[:7])
            finally:
                run(["git", "worktree", "remove", "--force", str(checkout)], cwd=root)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        run(["git", "worktree", "prune"], cwd=root)

    # A commit that actually failed always wins the verdict. Otherwise,
    # zero exercised commits is its own red state rather than a silent
    # green: "nobody has a test runner to check" is not the same claim as
    # "everything checked out is green", and reporting it as green is
    # exactly the false-positive this probe exists to prevent — asserting
    # criterion #8 on evidence that was never collected. It is kept red
    # (not a separate "could not check" status) because this report has
    # no third visual state for someone who cannot read the detail text;
    # a status this audience cannot act on has to fail closed.
    if broken:
        detail = f"回不去的版本：{', '.join(broken)}"
    elif exercised == 0:
        detail = (
            f"抽驗的 {len(chosen)} 個版本都沒有 scripts/run_tests.sh，沒有測試"
            "入口可以驗證——不是「驗證過都是綠的」，是根本沒有東西可以驗證。"
        )
    else:
        detail = f"抽驗 {len(chosen)} 個版本，其中 {exercised} 個有測試入口，都跑得起來。"
        if unchecked:
            detail += f"另外 {len(unchecked)} 個（{', '.join(unchecked)}）沒有測試入口，沒辦法確認。"

    return CheckResult(
        id="history", title="歷史版本",
        ok=not broken and exercised > 0,
        detail=detail,
    )
