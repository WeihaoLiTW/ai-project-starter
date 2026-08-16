from pathlib import Path


def test_web_design_skill_is_present_and_auto_invocable():
    p = Path(__file__).resolve().parent.parent / "plugins/starter-kit/skills/web-design/SKILL.md"
    assert p.exists()
    fm = p.read_text("utf-8").split("---", 2)[1]
    assert "name: web-design" in fm
    assert "description:" in fm
    assert ("網頁" in fm or "HTML" in fm)
    assert "disable-model-invocation: true" not in fm
