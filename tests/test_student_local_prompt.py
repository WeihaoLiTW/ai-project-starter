"""B1: the student's local-mode kickoff prompt carries no deploy/Google steps.

Spec condition 6 (2026-08-14-sunday-101-training-readiness-design): the student
prompt and all student-facing instructions must contain no Zeabur or Google
registration/authorization steps. The student copies exactly one fenced
```markdown block into their Cowork; this test asserts on that block only, so
the explanatory prose around it may still name Zeabur/Google while the pasted
instructions stay clean.
"""

import re
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent
PROMPT = KIT_ROOT / "docs" / "onboarding" / "kickoff-prompt-local.md"


def _paste_block(text):
    m = re.search(r"```markdown\n(.*?)```", text, re.DOTALL)
    assert m, "kickoff-prompt-local.md must contain one ```markdown paste block"
    return m.group(1)


def test_student_paste_block_has_no_deploy_or_google_steps():
    block = _paste_block(PROMPT.read_text(encoding="utf-8"))
    assert "Zeabur" not in block, "student paste block must not mention Zeabur"
    assert "Google" not in block, "student paste block must not mention Google"


def test_student_paste_block_requests_local_mode():
    block = _paste_block(PROMPT.read_text(encoding="utf-8"))
    assert "本機檔位" in block, "student paste block must ask for local mode"
