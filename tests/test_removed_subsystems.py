from pathlib import Path


def test_procedural_skills_and_checks_engine_are_gone():
    root = Path(__file__).resolve().parent.parent / "plugins/starter-kit"
    assert not (root / "skills/deploy").exists()
    assert not (root / "skills/health-check").exists()
    assert not (root / "checks").exists()
