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
