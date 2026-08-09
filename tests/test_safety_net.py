"""B4：密鑰擋門。

第三個測試（未追蹤的 `.env` 不會被 commit）留到 Task 10——那個測試依賴
還沒寫出來的 commit hook，這裡先不寫假的。
"""

import pytest

from conftest import run_hook

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
