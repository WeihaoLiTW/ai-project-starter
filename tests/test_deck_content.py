from pathlib import Path


def test_deck_explains_first_install_and_later_addons():
    html = (Path(__file__).resolve().parent.parent
            / "slides-output/2026-08-15-concepts/deck.html").read_text("utf-8")
    assert "第一次" in html and "之後" in html
    assert ("加購" in html or "自己" in html)
    assert "git" in html and "測試" in html and "權限" in html
