"""pillars.md 併入 persona 與安全 wording 之後，session start 注入內容要
帶到這些關鍵字 —— 證明是 session_start.py 實際讀出來的檔案內容在把關，
不是只看原始檔案本身。

問法節奏「一次問一輪」刻意留在 think-first skill，不該滲進這裡常駐的
behavior 注入，所以也反向斷言它不出現。
"""

from conftest import run_hook


def test_session_start_injects_persona_and_safety_wording(tmp_path):
    _, resp, _ = run_hook("session_start.py", {}, cwd=tmp_path)
    ctx = resp["hookSpecificOutput"]["additionalContext"]
    assert "白話" in ctx
    assert "業務" in ctx
    assert ("發布" in ctx or "正式版" in ctx)
    assert "查不到" in ctx
    assert "一次問一輪" not in ctx
