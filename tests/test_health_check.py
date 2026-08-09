import sys
import types

from conftest import git

from checks.model import CheckResult
from checks.runner import run_all


def ok_probe(facts):
    return CheckResult(id="ok", title="一切正常", ok=True, detail="")


def failing_probe(facts):
    return CheckResult(id="bad", title="這項不通", ok=False, detail="缺了東西")


def exploding_probe(facts):
    raise RuntimeError("探針自己爆了")


def test_one_red_item_does_not_affect_the_others():
    """有一項不通，其餘各項照常給出自己的結果。"""
    results = run_all({}, [ok_probe, failing_probe, ok_probe])

    assert [r.ok for r in results] == [True, False, True]


def test_a_probe_that_crashes_becomes_a_red_item_not_a_dead_report():
    """探針自己壞掉，變成那一項紅燈，整份報告還是產得出來。"""
    results = run_all({}, [ok_probe, exploding_probe, ok_probe])

    assert len(results) == 3
    assert results[1].ok is False
    assert "探針自己爆了" in results[1].detail


def test_the_report_covers_all_nine_items():
    """正式的九項探針，一項不多一項不少。"""
    from checks.runner import default_probes

    assert len(default_probes()) == 9


def test_all_nine_probes_are_real_not_placeholders_expected_red_until_task_13():
    """刻意保留的紅燈：在 Task 13 把九個真正的探針全部寫完之前，這個測試都應該是
    失敗的。它檢查的是「沒有任何一項是佔位版本」，不是「湊得出九個東西」——
    不要為了讓它變綠而放寬這個判斷條件，也不要用字串比對報告文字取代它。
    """
    from checks.runner import default_probes

    probes = default_probes()
    placeholders = [p for p in probes if getattr(p, "is_placeholder", False)]

    assert not placeholders, (
        f"還有 {len(placeholders)} 個探針是佔位版本，尚未被 Task 13 的真正探針取代"
    )


def test_default_probes_contains_an_execution_time_failure_end_to_end(monkeypatch):
    """走完整的 default_probes() 路徑：某個探針模組匯入成功，但一執行就爆炸，
    仍然只讓那一項變紅，其餘結果照樣都在——證明 containment 不只對手寫的假探針
    有效，對透過 default_probes() 載入的真實模組也一樣。"""
    fake_module = types.ModuleType("checks.probes.environment")

    def exploding(facts):
        raise RuntimeError("執行時炸了")

    fake_module.probe = exploding
    monkeypatch.setitem(sys.modules, "checks.probes.environment", fake_module)

    results = run_all({})

    assert len(results) == 9
    assert results[0].ok is False
    assert "執行時炸了" in results[0].detail


def test_history_probe_reports_green_when_every_commit_passes(repo):
    """歷史抽驗：git 歷史上每一個 commit checkout 出來測試都是綠的，探針回報綠燈。"""
    from checks.probes.history import probe

    (repo / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"另一個永遠是綠的。\"\"\"\n    assert True\n",
        encoding="utf-8",
    )
    git("add", "-A", cwd=repo)
    git("commit", "-q", "-m", "add another green test", cwd=repo)

    result = probe({"repo": repo, "sample": 10})

    assert result.ok is True


def test_history_probe_names_the_commit_that_fails(repo):
    """歷史抽驗：有一個 commit 的測試是紅的，探針要在 detail 裡指名是哪個 commit。"""
    from checks.probes.history import probe

    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"這個 commit 的測試被改成紅的。\"\"\"\n    assert False\n",
        encoding="utf-8",
    )
    git("add", "-A", cwd=repo)
    git("commit", "-q", "-m", "break the suite", cwd=repo)
    bad_commit = git("rev-parse", "HEAD", cwd=repo).strip()

    result = probe({"repo": repo, "sample": 10})

    assert result.ok is False
    assert bad_commit[:7] in result.detail


def test_checking_history_leaves_the_working_folder_exactly_as_it_was(repo):
    """歷史抽驗絕對不能動到使用者的工作區：跑完之後 branch、HEAD、工作區狀態
    要一個字不變。這條線的價值全部在這裡——用 worktree 而不是 checkout，
    就是為了讓這個測試通過。"""
    from checks.probes.history import probe

    before_branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo).strip()
    before_head = git("rev-parse", "HEAD", cwd=repo).strip()
    before_status = git("status", "--porcelain", cwd=repo)

    probe({"repo": repo, "sample": 10})

    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo).strip() == before_branch
    assert git("rev-parse", "HEAD", cwd=repo).strip() == before_head
    assert git("status", "--porcelain", cwd=repo) == before_status


def test_the_cli_is_named_when_it_is_reachable():
    """CLI 這條路通的時候，報告指名走 CLI。"""
    from checks.probes.zeabur import probe

    result = probe({"zeabur": {"cli": True, "mcp": True, "browser": True,
                               "proven": True}})

    assert result.ok is True
    assert result.detail.startswith("CLI")


def test_mcp_is_named_when_the_cli_is_blocked():
    """CLI 不通、MCP 通，報告指名走 MCP。"""
    from checks.probes.zeabur import probe

    result = probe({"zeabur": {"cli": False, "mcp": True, "browser": True,
                               "proven": True}})

    assert result.ok is True
    assert result.detail.startswith("MCP")


def test_the_browser_is_named_when_it_is_the_only_one_left():
    """只剩瀏覽器可用，報告指名走瀏覽器。"""
    from checks.probes.zeabur import probe

    result = probe({"zeabur": {"cli": False, "mcp": False, "browser": True,
                               "proven": True}})

    assert result.ok is True
    assert result.detail.startswith("瀏覽器")


def test_all_three_blocked_turns_the_item_red_with_a_reason():
    """三條路都不通，這一項紅燈，而且說得出三條各自為什麼不通。"""
    from checks.probes.zeabur import probe

    result = probe({"zeabur": {"cli": False, "mcp": False, "browser": False}})

    assert result.ok is False
    for name in ("CLI", "MCP", "瀏覽器"):
        assert name in result.detail


def test_a_named_path_without_a_proven_operation_is_red():
    """指名了一條路，但沒有實際跑成功一次操作，這一項不算過。"""
    from checks.probes.zeabur import probe

    result = probe({"zeabur": {"cli": True, "mcp": False, "browser": False,
                               "proven": False}})

    assert result.ok is False
    assert "CLI" in result.detail


def test_a_route_with_no_proven_key_at_all_is_red():
    """有一條路可用，但 facts 裡根本沒有 proven 這個欄位——技能還沒跑到驗證那一步，
    或半路壞掉沒寫入。這不等於「驗證過但失敗」，而是「沒驗證過」，一樣算不通過，
    不能因為 key 不存在就誤判成綠燈。"""
    from checks.probes.zeabur import probe

    result = probe({"zeabur": {"cli": True, "mcp": False, "browser": False}})

    assert result.ok is False
    assert "CLI" in result.detail
