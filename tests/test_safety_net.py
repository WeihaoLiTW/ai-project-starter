"""B2：測試紅的時候不會產生 commit。B4：密鑰擋門。"""

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
    """工作區裡有沒被追蹤的 .env，自動 commit 不會把它納進去。"""
    (repo / ".env").write_text("SECRET_KEY=real-one\n", encoding="utf-8")
    (repo / "tests" / "test_more.py").write_text(
        "def test_more():\n    \"\"\"綠的。\"\"\"\n    assert True\n", encoding="utf-8"
    )

    run_hook("commit_if_green.py", {"stop_hook_active": False}, repo)

    tracked = git("ls-files", cwd=repo).splitlines()
    assert ".env" not in tracked
