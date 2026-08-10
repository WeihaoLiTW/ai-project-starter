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

# `_shared.run` never raises; it turns two specific environment failures into
# fake return codes so callers can tell them apart from a real test result:
# 127 (the OSError branch) when the command itself could not even start —
# most commonly because the interpreter or a dependency (e.g. pytest) is not
# installed yet — and 124 when it ran past the timeout without finishing.
# Neither of those is "this turn's changes broke something"; both are
# "the environment cannot run the suite at all right now". Telling the user
# their tests failed when nothing ever ran points them at the wrong problem
# and, for someone who cannot read a stack trace, is indistinguishable from
# a real regression.
COULD_NOT_RUN = {
    127: "找不到執行測試需要的指令或套件。這台機器上很可能還沒裝好這個專案需要的東西（例如 pytest）。",
    124: "測試跑了太久，超過時間限制被中斷了，沒有跑出結果。",
}

# `python3 -m pytest` when `pytest` (or `django`, or any other module the
# suite needs) is not installed does NOT raise the OSError that produces
# the 127 above — the interpreter itself starts fine, so subprocess never
# sees a launch failure. Python's own `-m` machinery prints exactly one
# bare line to stderr and exits 1: the same code a real test failure uses.
# The exit code alone cannot tell these apart; only the text can.
#
# The tell is the *shape* of that line: `<path-to-python>: No module named
# <bareword>`, with no quotes around the module name and no preceding
# "Traceback (most recent call last):". A module a test or app file itself
# fails to import shows up quoted, inside a full traceback
# (`ModuleNotFoundError: No module named 'foo'`) — that IS a real
# regression from this turn's change and must still be reported as a test
# failure, not excused as an environment problem.
RUNNER_COULD_NOT_START_PATTERNS = [
    re.compile(r"^\S+:\s*No module named [A-Za-z_][\w.]*\s*$", re.MULTILINE),
    re.compile(r"command not found", re.IGNORECASE),
    re.compile(r":\s*not found\s*$", re.MULTILINE),
    re.compile(r"is not recognized as an internal or external command", re.IGNORECASE),
]

# pytest's own exit code for "collected zero tests" — distinct from both a
# real pass (0) and a real failure (1/2). This template ships with a green
# baseline precisely so a project should never legitimately land here; if
# it does, the test files most likely got deleted or moved out of the path
# pytest looks in, and someone needs to see that rather than a placeholder
# claiming "not sure which test broke" for a run that never found a test
# to break in the first place.
NO_TESTS_COLLECTED = 5


def runner_could_not_start(out, err):
    """The offending line if the output shows the runner never got going,
    or None if it does not. See RUNNER_COULD_NOT_START_PATTERNS above for
    why this needs to inspect text and cannot rely on the exit code alone.
    """
    combined = out + "\n" + err
    for pattern in RUNNER_COULD_NOT_START_PATTERNS:
        match = pattern.search(combined)
        if match:
            line_start = combined.rfind("\n", 0, match.start()) + 1
            line_end = combined.find("\n", match.end())
            if line_end == -1:
                line_end = len(combined)
            return combined[line_start:line_end].strip()
    return None


def failure_reason(code, out, err):
    """The message to show when the test runner exits non-zero.

    Three different situations all look the same to someone who cannot
    inspect a stack trace or an exit code, but they are not the same
    thing, so each gets its own message: the environment could not run
    the tests at all (not caused by this turn's changes), the environment
    ran but found nothing to run (also not a pass or a fail), and the
    tests actually ran with something in them broken.
    """
    if code in COULD_NOT_RUN:
        return (
            "沒辦法執行測試，所以這一輪的改動還沒有存檔——這不是這次改動造成的，"
            f"是環境本身跑不起來測試。{COULD_NOT_RUN[code]}\n"
            "改動都還在，沒有東西不見，把環境修好之後會自動存檔。"
        )

    evidence = runner_could_not_start(out, err)
    if evidence:
        return (
            "沒辦法執行測試，所以這一輪的改動還沒有存檔——這不是這次改動造成的，"
            "是環境本身缺了跑測試需要的東西（例如某個套件還沒裝好）。"
            f"實際訊息：\n{evidence}\n"
            "改動都還在，沒有東西不見，把缺的東西裝好之後會自動存檔。"
        )

    if code == NO_TESTS_COLLECTED:
        return (
            "這一輪一個測試都沒有跑到——不是通過，也不是失敗，是「根本沒找到測試可以跑」。"
            "這個專案原本是帶著會通過的測試出貨的，正常不該發生這種事，"
            "很可能是測試檔案被刪掉了或移到別的地方去了，需要有人看一下發生了什麼事。\n"
            "改動都還在，還沒有存檔，等看得到測試真的有在跑再說。"
        )

    names = [name for _, name in FAILED_TEST.findall(out + err)]
    if names:
        detail = f"壞掉的是：{', '.join(names[:5])}"
    else:
        tail = (out + err).strip()[-500:] or "（沒有任何輸出）"
        detail = f"看不出是哪一個測試，完整訊息如下：\n{tail}"
    return (
        "測試沒過，所以這一輪的改動還沒有存檔。\n"
        f"{detail}\n"
        "先把它修好，修好之後會自動存檔。改動都還在，沒有東西不見。"
    )


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
    # A misconfigured install: no runner means no way to ever produce a
    # commit, silently, forever. Nothing the user reads is affected (there
    # is no test result to report), but whoever debugs the install needs
    # to see what path was expected.
    sys.stderr.write(f"No test runner found at {runner}; skipping commit.\n")
    emit({})

code, out, err = run(["sh", str(runner), "--maxfail=1", "-q"], cwd=root, timeout=180)

if code != 0:
    # Already blocked once on this failure. Blocking again would trap the
    # conversation in a loop the user cannot get out of.
    if payload.get("stop_hook_active"):
        emit({})
    emit({"decision": "block", "reason": failure_reason(code, out, err)})


def save_failed(step, stderr_text):
    """Block, telling the user the tests passed but saving the checkpoint
    itself failed — and why, in git's own words.

    This is the state the safety net exists to prevent from going unnoticed:
    "green but not saved" reads to the user exactly like "green and saved"
    unless something says otherwise. Green-and-blocked is worse than
    red-and-blocked, because with red the user already knows nothing was
    supposed to be saved.

    The most common cause is a git identity (`user.name` / `user.email`)
    that was never configured — expected for the people this plugin targets,
    who may never have run a git command before. That specific case gets the
    two fix commands named explicitly, because here naming a command is more
    useful than making the user guess. Any other git failure is reported
    with git's own error text, not swallowed into a generic message.
    """
    lines = [
        "測試都通過了，但存檔（commit）失敗了，這一輪的改動還沒有變成一個存檔點。",
        f"git 在「{step}」這一步回報的錯誤：",
        stderr_text.strip() or "（git 沒有輸出任何訊息）",
    ]
    if "Please tell me who you are" in stderr_text:
        lines.append(
            "這通常是因為這個 git 倉庫從來沒有設定過身份（user.name 和 "
            "user.email）。執行這兩行就能修好：\n"
            '  git config --global user.name "你的名字"\n'
            '  git config --global user.email "you@example.com"\n'
            "設定好之後，這一輪的改動下次還會再自動存一次。"
        )
    lines.append("改動還留在工作目錄裡，沒有不見，只是還沒有存檔。")
    return "\n".join(lines)


# Green. Stage everything git is willing to track, then pull back out
# anything that looks like a secret. Relying on .gitignore alone is not
# enough: the person driving this plugin cannot read .gitignore to tell
# whether it is correct, and this repository is public, so a leaked
# credential is a public one. `secret_label` is the exact same path rule
# guard_secrets.py uses to refuse writes (imported from _shared.py, not
# copied here) — this catches a secret file even when it reached disk some
# other way than a Write/Edit tool call, which is the case guard_secrets.py
# cannot see.
add_code, _, add_err = run(["git", "add", "-A"], cwd=root)
if add_code != 0:
    if payload.get("stop_hook_active"):
        emit({})
    emit({"decision": "block", "reason": save_failed("git add -A", add_err)})

_, staged, _ = run(["git", "diff", "--cached", "--name-only"], cwd=root)
staged_paths = [line for line in staged.splitlines() if line.strip()]

excluded = [(path, secret_label(path)) for path in staged_paths]
excluded = [(path, label) for path, label in excluded if label]

# Visible to the user via `systemMessage`, not stderr: this hook exits 0 on
# every path below, and stderr from a non-blocking Stop hook is not surfaced
# to the person driving the conversation. A warning nobody reads is the same
# as no warning — it must ride in the one channel the caller actually shows.
warning = None
if excluded:
    run(["git", "reset", "-q", "HEAD", "--", *[path for path, _ in excluded]], cwd=root)
    listing = "\n".join(f"- {path}（{label}）" for path, label in excluded)
    warning = (
        "這幾個檔案看起來裝著密鑰，這次自動存檔沒有把它們存進去：\n"
        f"{listing}\n"
        "檔案還留在工作目錄裡，只是沒有進版控。如果不是密鑰，需要進版控的話，"
        "請自己手動處理。"
    )

_, staged, _ = run(["git", "diff", "--cached", "--name-only"], cwd=root)
if not staged.strip():
    # Either nothing needed saving, or everything that was staged turned
    # out to be a secret — either way there is no commit, and if it is the
    # latter the user still needs to know why nothing was saved.
    emit({"systemMessage": warning} if warning else {})

commit_code, _, commit_err = run(
    ["git", "commit", "-q", "-m", "chore: save a working version"], cwd=root
)
if commit_code != 0:
    if payload.get("stop_hook_active"):
        emit({})
    emit({"decision": "block", "reason": save_failed("git commit", commit_err)})

emit({"systemMessage": warning} if warning else {})
