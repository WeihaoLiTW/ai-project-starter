"""B5: install-wizard must not auto-invoke — the wizard is a heavy, opinionated
flow that a returning user's vague phrasing should never trigger by accident.
"""

from pathlib import Path


def test_install_wizard_is_not_auto_invoked():
    fm = (Path(__file__).resolve().parent.parent
          / "plugins/starter-kit/skills/install-wizard/SKILL.md").read_text("utf-8").split("---", 2)[1]
    assert "disable-model-invocation: true" in fm
