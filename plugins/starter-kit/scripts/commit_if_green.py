"""Run the tests at the end of each turn and commit only when they are green.

Every commit in history is therefore a working version. When the suite is
red the changes stay in the working tree — nothing is thrown away, it just
does not become a commit.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _shared import emit, read_payload, repo_root, run, secret_label

FAILED_TEST = re.compile(r"^(FAILED|ERROR)\s+(\S+)", re.MULTILINE)

payload = read_payload()
root = repo_root(Path.cwd())

if root is None:
    emit({})

# Nothing changed this turn, so there is nothing to test and nothing to commit.
_, status, _ = run(["git", "status", "--porcelain"], cwd=root)
if not status.strip():
    emit({})

runner = root / "scripts" / "run_tests.sh"
if not runner.exists():
    emit({})

code, out, err = run(["sh", str(runner), "--maxfail=1", "-q"], cwd=root, timeout=180)

if code != 0:
    # Already blocked once on this failure. Blocking again would trap the
    # conversation in a loop the user cannot get out of.
    if payload.get("stop_hook_active"):
        emit({})
    names = [name for _, name in FAILED_TEST.findall(out + err)] or ["（看不出是哪一個）"]
    emit({
        "decision": "block",
        "reason": (
            "測試沒過，所以這一輪的改動還沒有存檔。\n"
            f"壞掉的是：{', '.join(names[:5])}\n"
            "先把它修好，修好之後會自動存檔。改動都還在，沒有東西不見。"
        ),
    })

# Green. Stage everything git is willing to track, then pull back out
# anything that looks like a secret. Relying on .gitignore alone is not
# enough: the person driving this plugin cannot read .gitignore to tell
# whether it is correct, and this repository is public, so a leaked
# credential is a public one. `secret_label` is the exact same path rule
# guard_secrets.py uses to refuse writes (imported from _shared.py, not
# copied here) — this catches a secret file even when it reached disk some
# other way than a Write/Edit tool call, which is the case guard_secrets.py
# cannot see.
run(["git", "add", "-A"], cwd=root)
_, staged, _ = run(["git", "diff", "--cached", "--name-only"], cwd=root)
staged_paths = [line for line in staged.splitlines() if line.strip()]

excluded = [(path, secret_label(path)) for path in staged_paths]
excluded = [(path, label) for path, label in excluded if label]

if excluded:
    run(["git", "reset", "-q", "HEAD", "--", *[path for path, _ in excluded]], cwd=root)
    listing = "\n".join(f"- {path}（{label}）" for path, label in excluded)
    sys.stderr.write(
        "這幾個檔案看起來裝著密鑰，這次自動存檔沒有把它們存進去：\n"
        f"{listing}\n"
        "檔案還留在工作目錄裡，只是沒有進版控。如果不是密鑰，需要進版控的話，"
        "請自己手動處理。\n"
    )

_, staged, _ = run(["git", "diff", "--cached", "--name-only"], cwd=root)
if not staged.strip():
    emit({})

run(["git", "commit", "-q", "-m", "chore: save a working version"], cwd=root)
emit({})
