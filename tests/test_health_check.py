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


def test_all_nine_probes_are_real_not_placeholders():
    """九個探針全部是真正的實作，沒有一個是佔位版本。它檢查的是「沒有任何
    一項是佔位版本」，不是「湊得出九個東西」——不要為了讓它變綠而放寬這個
    判斷條件，也不要用字串比對報告文字取代它。
    """
    from checks.runner import default_probes

    probes = default_probes()
    placeholders = [p for p in probes if getattr(p, "is_placeholder", False)]

    assert not placeholders, (
        f"還有 {len(placeholders)} 個探針是佔位版本，尚未被真正的探針取代"
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


def test_suite_probe_without_a_repo_fact_is_an_explicit_red_not_a_guess():
    """skill 沒有把 `facts["repo"]` 寫進去時，探針不能安靜地退回讀 `"."`——
    skill 說明文件寫得很清楚，跑 `checks.collect` 之前會先 `cd` 進這個 plugin
    自己的資料夾，這時候 `"."` 指的是 plugin 自己，不是使用者的專案。用
    `"."` 湊出一個結果，不管紅綠都是在講一個沒人問過的專案，比講不出結果
    更容易誤導人。"""
    from checks.probes.suite import probe

    result = probe({})

    assert result.ok is False
    assert "repo" in result.detail
    assert "沒有任何東西在保護你" not in result.detail  # not the "no runner" guess


def test_history_probe_without_a_repo_fact_is_an_explicit_red_not_a_guess():
    """跟 suite 探針同一個理由：沒有 `facts["repo"]`，不能安靜地抽驗 `"."`
    底下的 git 歷史——那很可能是這個 plugin 自己的歷史，不是使用者專案的，
    抽出來的綠燈或紅燈都跟使用者的專案無關。"""
    from checks.probes.history import probe

    result = probe({"sample": 3})

    assert result.ok is False
    assert "repo" in result.detail
    assert "抽驗" not in result.detail  # not the "sampled N commits" wording


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


def test_history_probe_is_red_when_no_sampled_commit_has_a_test_runner(tmp_path):
    """整個 repo 從來沒有 scripts/run_tests.sh，抽驗到的每個 commit 都沒有測試
    入口可以驗證。這不能算綠燈——沒有任何一次驗證真的執行過，回報綠燈等於在
    零證據上宣稱「歷史版本都跑得起來」，而使用者沒辦法分辨這跟真的驗證過的
    綠燈有什麼不同。"""
    from checks.probes.history import probe

    root = tmp_path / "work"
    root.mkdir()
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "kit@example.com", cwd=root)
    git("config", "user.name", "kit", cwd=root)
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "no test runner at all", cwd=root)

    result = probe({"repo": root, "sample": 3})

    assert result.ok is False
    assert "沒有測試入口" in result.detail


def test_history_probe_counts_only_commits_that_actually_ran(tmp_path):
    """抽驗到的版本裡，有一個沒有測試入口——這一個不能被算進「跑得起來」的
    數字裡，detail 要老實說有幾個真的被驗證過、有幾個沒有測試入口。"""
    from checks.probes.history import probe

    root = tmp_path / "work"
    root.mkdir()
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "kit@example.com", cwd=root)
    git("config", "user.name", "kit", cwd=root)
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "no test runner yet", cwd=root)

    (root / "tests").mkdir()
    (root / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"這個永遠是綠的。\"\"\"\n    assert True\n",
        encoding="utf-8",
    )
    (root / "scripts").mkdir()
    (root / "scripts" / "run_tests.sh").write_text(
        "#!/bin/sh\nexec python3 -m pytest tests/ -q \"$@\"\n", encoding="utf-8"
    )
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "add a runner", cwd=root)

    result = probe({"repo": root, "sample": 10})

    assert result.ok is True
    assert "其中 1 個有測試入口" in result.detail
    assert "另外 1 個" in result.detail


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


def test_environment_probe_flags_a_windows_network_drive_regardless_of_host_platform():
    """這個探針永遠跑在 Cowork 的 VM（Linux）裡，不是使用者真正的 Windows
    機器上——用探針自己的 `platform.system()` 判斷，永遠不會等於 Windows，
    這個分支就永遠不會觸發。判斷要看 facts 裡 workdir 這個字串本身的樣子，
    不能看跑探針的這台機器是什麼系統。"""
    from checks.probes.environment import probe

    result = probe({"local_mode": True, "workdir": "\\\\fileserver\\share\\project"})

    assert result.ok is False
    assert "C:\\Users" in result.detail


def test_environment_probe_flags_a_drive_letter_path_not_under_users():
    """`D:\\work\\project` 不是網路磁碟，但也不在 `C:\\Users\\` 底下——
    這正是原本的判斷邏輯裡永遠碰不到的那條分支（只有 platform.system() 等於
    Windows，或路徑是 UNC 開頭，才會進到判斷，兩者在這個探針執行的環境裡
    都不成立），要能被抓出來。"""
    from checks.probes.environment import probe

    result = probe({"local_mode": True, "workdir": "D:\\work\\project"})

    assert result.ok is False
    assert "C:\\Users" in result.detail


def test_environment_probe_flags_a_drive_letter_path_with_forward_slashes():
    """Windows 本身接受 `/` 當路徑分隔符，很多工具（包含這個探針的呼叫端）
    回報路徑時就是用 `/` 不是 `\\`——`D:/work/proj` 跟 `D:\\work\\proj` 是
    同一個不安全的路徑，只是分隔符不同。判斷式只認反斜線的話，換成正斜線
    的同一個路徑會直接跳過這個檢查，被當成沒事。"""
    from checks.probes.environment import probe

    result = probe({"local_mode": True, "workdir": "D:/work/proj"})

    assert result.ok is False
    assert "C:\\Users" in result.detail


def test_environment_probe_accepts_a_path_under_c_users():
    """`C:\\Users\\...` 底下的路徑是合法的，不該被誤判成網路磁碟或需要搬移。"""
    from checks.probes.environment import probe

    result = probe({
        "local_mode": True,
        "workdir": "C:\\Users\\someone\\project",
    })

    assert result.ok is True


def test_environment_probe_accepts_an_ordinary_mac_path():
    """Mac 的路徑本來就不會長得像 Windows 路徑，不該被這個判斷誤傷。"""
    from checks.probes.environment import probe

    result = probe({"local_mode": True, "workdir": "/Users/someone/project"})

    assert result.ok is True


def test_a_route_with_no_proven_key_at_all_is_red():
    """有一條路可用，但 facts 裡根本沒有 proven 這個欄位——技能還沒跑到驗證那一步，
    或半路壞掉沒寫入。這不等於「驗證過但失敗」，而是「沒驗證過」，一樣算不通過，
    不能因為 key 不存在就誤判成綠燈。"""
    from checks.probes.zeabur import probe

    result = probe({"zeabur": {"cli": True, "mcp": False, "browser": False}})

    assert result.ok is False
    assert "CLI" in result.detail


def _safe_prod_env():
    return {
        "DJANGO_DEBUG": "0",
        "DJANGO_SECRET_KEY": "a-real-secret-key-generated-at-install-time",
        "DJANGO_ALLOWED_HOSTS": "example.zeabur.app",
    }


def test_service_probe_accepts_a_string_status_code_from_curl():
    """skill 的指示是用 `curl -w '%{http_code}'` 去查網址，印出來的是字串
    `"200"`，不是整數 200。這種格式一定要被當成「200」，不能因為型別不同就
    判成沒過——之前 `"200" != 200` 永遠是 True，兩個環境明明都是 200 也會被
    回報成壞的。"""
    from checks.probes.service import probe

    result = probe({
        "endpoints": {"staging": "200", "prod": "200"},
        "prod_env": _safe_prod_env(),
    })

    assert result.ok is True
    assert "不是 200" not in result.detail


def test_service_probe_still_catches_a_string_status_code_that_is_not_200():
    """字串格式也要能抓到真正的失敗，不能因為接受字串就變成什麼都放行。"""
    from checks.probes.service import probe

    result = probe({
        "endpoints": {"staging": "500", "prod": "200"},
        "prod_env": _safe_prod_env(),
    })

    assert result.ok is False
    assert "staging 回 500，不是 200" in result.detail


def test_service_probe_still_treats_an_unreachable_endpoint_as_not_200():
    """完全連不上（沒有回應碼，只有 None 或空字串）時，還是要判定為沒過，
    而不是被字串／整數的比較邏輯意外放行。"""
    from checks.probes.service import probe

    result = probe({
        "endpoints": {"staging": None, "prod": "200"},
        "prod_env": _safe_prod_env(),
    })

    assert result.ok is False
    assert "staging 回 連不上，不是 200" in result.detail


def test_data_probe_matches_a_marker_that_is_a_substring_of_a_row():
    """skill 要求把讀到的整行資料寫進 `snapshot_rows`（例如
    `"id=1 body=m1 created=2026-08-09"`），不是只寫 marker 本身。用完全相等
    去比對 marker 找不到，備份明明含資料卻被判定成不完整——這是最高風險的
    誤判，要改成子字串比對。"""
    from checks.probes.data import probe

    result = probe({
        "backup": {
            "marker": "m1",
            "survived_redeploy": True,
            "release_tag": "backup-2026-08-09",
            "snapshot_opens": True,
            "snapshot_rows": ["id=1 body=m1 created=2026-08-09T00:00:00Z"],
        }
    })

    assert result.ok is True
    assert "不完整" not in result.detail


def test_data_probe_still_flags_a_marker_missing_from_every_row():
    """marker 真的不在任何一行資料裡時，還是要判定成不完整——子字串比對
    不能變成「什麼都算過」。"""
    from checks.probes.data import probe

    result = probe({
        "backup": {
            "marker": "m1",
            "survived_redeploy": True,
            "release_tag": "backup-2026-08-09",
            "snapshot_opens": True,
            "snapshot_rows": ["id=2 body=something-else created=2026-08-09"],
        }
    })

    assert result.ok is False
    assert "不完整" in result.detail
