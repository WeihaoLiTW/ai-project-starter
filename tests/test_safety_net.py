"""B2：測試紅的時候不會產生 commit。B4：密鑰擋門。"""

import os

import pytest

from conftest import git, run_hook

SECRET_FILES = [
    ".env",
    ".env.local",
    "id_rsa",
    "server.pem",
    "gcp-credentials.json",
    "api.key",
]


@pytest.mark.parametrize("filename", SECRET_FILES)
def test_writing_a_secret_file_is_refused(filename, tmp_path):
    """六種常見的密鑰檔名都要被擋下，而且擋門訊息要講清楚三件事：
    這是什麼檔案、為什麼危險、可以怎麼做——不能只丟檔名和規則代號。
    """
    code, response, stderr = run_hook(
        "guard_secrets.py",
        {"tool_input": {"file_path": str(tmp_path / filename)}},
        cwd=tmp_path,
    )

    assert code == 0
    output = response["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"

    reason = output["permissionDecisionReason"]
    assert filename in reason  # 是什麼檔案
    assert "公開" in reason  # 為什麼危險
    assert "環境變數" in reason  # 可以怎麼做


def test_writing_an_ordinary_file_is_allowed(tmp_path):
    """一般檔案（例如原始碼）不受影響，放行時輸出空字串。"""
    code, response, stderr = run_hook(
        "guard_secrets.py",
        {"tool_input": {"file_path": str(tmp_path / "app.py")}},
        cwd=tmp_path,
    )

    assert code == 0
    assert response == {}


def test_env_example_template_is_allowed(tmp_path):
    """`.env.example` 是慣例上會進版控的範本檔，裡面只放空鍵名，不是密鑰。

    擋掉它會讓使用者連一個標準的環境變數說明檔都生不出來，而且擋下來的
    理由（「這看起來是環境變數檔」）在這個情況下是錯的，所以放行。
    """
    code, response, stderr = run_hook(
        "guard_secrets.py",
        {"tool_input": {"file_path": str(tmp_path / ".env.example")}},
        cwd=tmp_path,
    )

    assert code == 0
    assert response == {}


def test_real_env_file_is_still_refused_next_to_its_template(tmp_path):
    """放行 `.env.example` 不能連帶放行真正的 `.env`——兩者要能被分辨。"""
    code, response, stderr = run_hook(
        "guard_secrets.py",
        {"tool_input": {"file_path": str(tmp_path / ".env")}},
        cwd=tmp_path,
    )

    assert code == 0
    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_env_example_with_trailing_newline_is_refused(tmp_path):
    """`$` 在 Python regex 裡除了比對字串結尾，也會比對「結尾換行符前」，

    所以 `.env.example\\n` 這個合法但不同的檔名會被允許清單誤放行。
    這個路徑必須被當成一般檔案處理，而不是被當成範本放行。
    """
    path = str(tmp_path / ".env.example") + "\n"
    code, response, stderr = run_hook(
        "guard_secrets.py",
        {"tool_input": {"file_path": path}},
        cwd=tmp_path,
    )

    assert code == 0
    assert response != {}


def test_env_example_with_only_placeholder_values_is_allowed(tmp_path):
    """真正的範本檔：密鑰欄位留空或填佔位字串，其餘一般設定不受影響。"""
    content = (
        "SECRET_KEY=\n"
        "DJANGO_SECRET_KEY=your-secret-key-here\n"
        "API_TOKEN=changeme\n"
        "DB_PASSWORD=xxx\n"
        "AUTH_TOKEN=<your token>\n"
        "DEBUG=1\n"
        "DJANGO_ALLOWED_HOSTS=example.com\n"
    )
    code, response, stderr = run_hook(
        "guard_secrets.py",
        {"tool_input": {"file_path": str(tmp_path / ".env.example"), "content": content}},
        cwd=tmp_path,
    )

    assert code == 0
    assert response == {}


def test_env_example_with_a_real_secret_value_is_refused(tmp_path):
    """`.env.example` 掛著範本的名字，但實際塞了一組看起來能用的密鑰，

    不是範本該有的樣子。擋門訊息要點名是哪個鍵造成的。
    """
    content = "DEBUG=1\nSECRET_KEY=sk_live_abc123realvalue\n"
    code, response, stderr = run_hook(
        "guard_secrets.py",
        {"tool_input": {"file_path": str(tmp_path / ".env.example"), "content": content}},
        cwd=tmp_path,
    )

    assert code == 0
    output = response["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert "SECRET_KEY" in output["permissionDecisionReason"]


def test_null_tool_input_does_not_crash_the_hook(tmp_path):
    """`tool_input` 是 `null` 時不能讓 hook 掛掉丟例外，只能正常放行。

    `read_payload()` 只保證最外層是 dict，`tool_input` 這種巢狀欄位仍可能
    是任何 JSON 型別，包含 null。
    """
    code, response, stderr = run_hook(
        "guard_secrets.py",
        {"tool_input": None},
        cwd=tmp_path,
    )

    assert code == 0
    assert response == {}


def test_red_suite_leaves_history_untouched(repo):
    """改動讓測試變紅，對話結束後 git 歷史沒有新 commit。"""
    before = git("rev-parse", "HEAD", cwd=repo).strip()
    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"這個現在是紅的。\"\"\"\n    assert False\n",
        encoding="utf-8",
    )

    code, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    assert git("rev-parse", "HEAD", cwd=repo).strip() == before
    assert out["decision"] == "block"
    assert git("status", "--porcelain", cwd=repo).strip() != ""


def test_red_suite_tells_claude_to_fix_it(repo):
    """測試紅的時候，回饋訊息說得出是哪個測試壞了。"""
    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"這個現在是紅的。\"\"\"\n    assert False\n",
        encoding="utf-8",
    )

    _, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    assert "test_ok" in out["reason"]


def test_green_suite_produces_exactly_one_commit(repo):
    """測試綠的時候，對話結束後多一個 commit，而且只多一個。"""
    before = int(git("rev-list", "--count", "HEAD", cwd=repo).strip())
    (repo / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"另一個綠的。\"\"\"\n    assert True\n", encoding="utf-8"
    )

    code, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    after = int(git("rev-list", "--count", "HEAD", cwd=repo).strip())
    assert after == before + 1
    assert out.get("decision") != "block"


def test_nothing_changed_means_no_commit(repo):
    """這一輪沒動到任何檔案，不會產生空的 commit。"""
    before = int(git("rev-list", "--count", "HEAD", cwd=repo).strip())

    run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    assert int(git("rev-list", "--count", "HEAD", cwd=repo).strip()) == before


def test_second_consecutive_failure_does_not_block_again(repo):
    """已經擋過一次還是紅的，就不再擋，避免對話卡死在同一個迴圈。"""
    (repo / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"還是紅的。\"\"\"\n    assert False\n",
        encoding="utf-8",
    )

    _, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": True}, repo)

    assert out.get("decision") != "block"


def test_an_untracked_env_file_never_gets_committed(repo):
    """工作區裡有沒被追蹤的 .env，自動 commit 不會把它納進去，
    而且使用者要看得到、看得懂為什麼——不能只是安靜地漏掉它。"""
    (repo / ".env").write_text("SECRET_KEY=real-one\n", encoding="utf-8")
    (repo / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"綠的。\"\"\"\n    assert True\n", encoding="utf-8"
    )

    _, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    tracked = git("ls-files", cwd=repo).splitlines()
    assert ".env" not in tracked
    assert ".env" in out.get("systemMessage", "")


def test_when_every_staged_path_is_a_secret_nothing_is_committed_and_user_is_told(repo):
    """這一輪唯一有變動的檔案就是一個密鑰檔時，排除完就沒有東西可以
    commit。這跟「這一輪什麼都沒改」是不同的靜默——使用者要知道
    有東西本來要存但被擋下來了，而不是誤以為這一輪什麼都沒發生。"""
    before = int(git("rev-list", "--count", "HEAD", cwd=repo).strip())
    (repo / ".env").write_text("SECRET_KEY=real-one\n", encoding="utf-8")

    _, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    after = int(git("rev-list", "--count", "HEAD", cwd=repo).strip())
    assert after == before
    assert ".env" in out.get("systemMessage", "")


def test_a_missing_command_is_reported_as_could_not_run_not_as_a_test_failure(repo):
    """`scripts/run_tests.sh` 存在，但它呼叫的指令根本不存在（例如套件還沒裝好，
    `python3 -m pytest` 找不到 pytest）——這不是「這次改動讓測試變紅」，是環境
    跑不起來測試。訊息要講清楚是這個原因，不能說成「測試沒過」，也不能因為
    找不到 FAILED/ERROR 這種格式的輸出，就印出佔位字「（看不出是哪一個）」，
    讓人誤以為是自己剛剛的改動壞掉了。"""
    (repo / "scripts" / "run_tests.sh").write_text(
        "#!/bin/sh\nexec this_command_does_not_exist_xyz\n", encoding="utf-8"
    )
    (repo / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"綠的。\"\"\"\n    assert True\n", encoding="utf-8"
    )

    _, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    assert out.get("decision") == "block"
    reason = out["reason"]
    assert "沒辦法執行測試" in reason
    assert "測試沒過" not in reason
    assert "看不出是哪一個）" not in reason


def test_a_check_failure_with_no_named_test_shows_the_real_output(repo):
    """`run_tests.sh` 跑起來了、也真的失敗了，但輸出不是 pytest 的
    `FAILED test_x` 格式（例如換成另一個檢查腳本失敗）——這種情況下不該
    印出「看不出是哪一個」這種空話，而要把實際輸出貼出來，讓人看得到
    線索。這跟上一個測試不同：這裡指令確實跑了、確實失敗了，所以歸類
    是「測試沒過」，不是「沒辦法執行測試」。"""
    (repo / "scripts" / "run_tests.sh").write_text(
        "#!/bin/sh\necho '這裡缺了一個定義的詞：某某詞'\nexit 1\n", encoding="utf-8"
    )
    (repo / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"綠的。\"\"\"\n    assert True\n", encoding="utf-8"
    )

    _, out, _ = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    assert out.get("decision") == "block"
    reason = out["reason"]
    assert "測試沒過" in reason
    assert "某某詞" in reason
    assert "看不出是哪一個）" not in reason


def test_missing_test_runner_names_the_path_on_stderr(repo):
    """`scripts/run_tests.sh` 不存在時（裝壞了的安裝），不能安靜地什麼都
    不做——stderr 要點名它找的是哪個路徑，裝機的人才查得出來。"""
    (repo / "scripts" / "run_tests.sh").unlink()
    (repo / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"綠的。\"\"\"\n    assert True\n", encoding="utf-8"
    )

    _, out, stderr = run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    assert out == {}
    assert str(repo / "scripts" / "run_tests.sh") in stderr


@pytest.fixture
def repo_no_identity(tmp_path, monkeypatch):
    """一個跟 `repo` 一樣的 git repo，但刻意讓 user.name / user.email
    在任何地方都沒有設定——模擬一個從沒跑過 git 指令的使用者。

    `GIT_CONFIG_GLOBAL` 指向一個空檔案，隔絕跑測試這台機器上真正使用者
    的全域 git 設定；`user.useConfigOnly` 關掉 git 從作業系統帳號
    （gecos/使用者全名）自動推斷身份的後備行為——沒有這一步，在一台
    已經替真人使用者設定好全名的 macOS/Linux 開發機上，git 仍然會成功
    推斷出一個身份，這個測試想模擬的失敗就不會發生。
    """
    empty_config = tmp_path / "empty.gitconfig"
    empty_config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty_config))

    root = tmp_path / "work"
    root.mkdir()
    (root / "tests").mkdir()
    (root / "tests" / "test_ok.py").write_text(
        "def test_ok():\n    \"\"\"這個永遠是綠的。\"\"\"\n    assert True\n",
        encoding="utf-8",
    )
    (root / "scripts").mkdir()
    (root / "scripts" / "run_tests.sh").write_text(
        "#!/bin/sh\nexec python3 -m pytest tests/ -q \"$@\"\n", encoding="utf-8"
    )
    os.chmod(root / "scripts" / "run_tests.sh", 0o755)
    git("init", "-q", "-b", "main", cwd=root)
    # The initial baseline commit still needs *some* identity to be created
    # at all; set one locally just long enough for it, then take it away
    # again so the repo the hook runs against has none.
    git("config", "user.email", "kit@example.com", cwd=root)
    git("config", "user.name", "kit", cwd=root)
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "initial", cwd=root)
    git("config", "--unset", "user.email", cwd=root)
    git("config", "--unset", "user.name", cwd=root)
    git("config", "user.useConfigOnly", "true", cwd=root)
    return root


def test_commit_failure_from_missing_identity_blocks_with_the_fix_named(repo_no_identity):
    """核心案例：從沒設定過 git 身份的使用者，測試是綠的，但存檔
    （commit）會失敗。這時 hook 絕對不能落到 emit({})、讓使用者以為
    存好了——要用 block 講清楚三件事：測試過了、存檔失敗了、git 的
    實際錯誤是什麼，並且點名是身份沒設定，附上修好它的兩行指令。"""
    before = git("rev-parse", "HEAD", cwd=repo_no_identity).strip()
    (repo_no_identity / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"綠的。\"\"\"\n    assert True\n", encoding="utf-8"
    )

    code, out, _ = run_hook(
        "commit_if_green.py", {"stop_hook_active": False}, repo_no_identity
    )

    # No commit happened, and the hook did not report success.
    assert git("rev-parse", "HEAD", cwd=repo_no_identity).strip() == before
    assert out.get("decision") == "block"
    reason = out["reason"]
    assert "測試都通過了" in reason  # tests passed
    assert "存檔" in reason and "失敗" in reason  # saving failed
    assert "Please tell me who you are" in reason  # git's actual error
    assert "user.name" in reason and "user.email" in reason  # identity named
    assert "git config --global user.name" in reason  # the fix commands
    assert "git config --global user.email" in reason


def test_second_consecutive_commit_failure_does_not_block_again(repo_no_identity):
    """存檔失敗已經擋過一次了，還是失敗就不再擋，理由跟測試紅時的
    迴圈防呆一樣：不能把對話卡死在同一個訊息裡出不來。"""
    (repo_no_identity / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"綠的。\"\"\"\n    assert True\n", encoding="utf-8"
    )

    _, out, _ = run_hook(
        "commit_if_green.py", {"stop_hook_active": True}, repo_no_identity
    )

    assert out.get("decision") != "block"
