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
                    continue
                code, _, _ = run(["sh", str(runner)], cwd=checkout, timeout=300)
                if code != 0:
                    broken.append(commit[:7])
            finally:
                run(["git", "worktree", "remove", "--force", str(checkout)], cwd=root)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        run(["git", "worktree", "prune"], cwd=root)

    return CheckResult(
        id="history", title="歷史版本",
        ok=not broken,
        detail=f"回不去的版本：{', '.join(broken)}" if broken
        else f"抽驗 {len(chosen)} 個版本，都跑得起來。",
    )
