"""Tests for the read_payload() contract: it must always return a dict.

sys.executable is used to invoke a tiny driver script against the real
_shared.py module, feeding raw bytes on stdin. This exercises the same
code path a real hook process sees (bytes in on stdin, not a Python
object handed in-process), which is required to prove the undecodable-
bytes and non-object-JSON cases without ever raising.
"""

import json
import subprocess
import sys

from conftest import PLUGIN

SCRIPTS_DIR = PLUGIN / "scripts"

READ_PAYLOAD_DRIVER = (
    "import sys, json; "
    f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
    "import _shared; "
    "result = _shared.read_payload(); "
    "sys.stdout.write(json.dumps(result))"
)


def _invoke_read_payload(raw_stdin: bytes):
    """用實際的 read_payload() 介面跑一次：把原始 bytes 灌進 stdin，回傳
    (exit code, 解析後的 dict, stderr 文字)。"""
    proc = subprocess.run(
        [sys.executable, "-c", READ_PAYLOAD_DRIVER],
        input=raw_stdin,
        capture_output=True,
        timeout=30,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    parsed = json.loads(stdout) if stdout.strip() else None
    return proc.returncode, parsed, stderr


def _invoke_guard_secrets(raw_stdin: bytes, cwd):
    """用真正掛在 PreToolUse 上的 guard_secrets hook 跑一次，回傳
    (exit code, stderr 文字)。"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "guard_secrets.py")],
        input=raw_stdin,
        cwd=cwd,
        capture_output=True,
        timeout=30,
    )
    return proc.returncode, proc.stderr.decode("utf-8", errors="replace")


def test_empty_stdin_returns_empty_dict():
    """空的 stdin 應該回傳空 dict，且不寫任何東西到 stderr。"""
    code, result, stderr = _invoke_read_payload(b"")
    assert code == 0
    assert result == {}
    assert stderr == ""


def test_valid_json_object_round_trips():
    """合法的 JSON object 應該原封不動地被解析出來。"""
    payload = {"session_id": "abc", "tool": "Write", "count": 3}
    code, result, stderr = _invoke_read_payload(json.dumps(payload).encode("utf-8"))
    assert code == 0
    assert result == payload
    assert stderr == ""


def test_malformed_json_returns_empty_dict_and_warns():
    """壞掉的 JSON 應該回傳空 dict、在 stderr 留下一行訊息，且 exit code 是 0。"""
    code, result, stderr = _invoke_read_payload(b"not json at all")
    assert code == 0
    assert result == {}
    assert stderr.strip() != ""


def test_undecodable_bytes_return_empty_dict():
    """stdin 上無法解碼成 UTF-8 的 bytes 不該讓程式炸掉，應該退化成空 dict。"""
    code, result, stderr = _invoke_read_payload(b"\xff\xfe\x00garbage")
    assert code == 0
    assert result == {}


def test_non_object_json_number_returns_empty_dict():
    """合法但不是 object 的 JSON（數字）應該回傳空 dict 並在 stderr 說明拿到了什麼型別。"""
    code, result, stderr = _invoke_read_payload(b"42")
    assert code == 0
    assert result == {}
    assert stderr.strip() != ""


def test_non_object_json_array_returns_empty_dict():
    """合法但不是 object 的 JSON（array）應該回傳空 dict 並在 stderr 說明拿到了什麼型別。"""
    code, result, stderr = _invoke_read_payload(b"[1,2]")
    assert code == 0
    assert result == {}
    assert stderr.strip() != ""


def test_deeply_nested_json_returns_empty_dict():
    """極度嵌套的 JSON（超過遞迴限制）不該讓程式爆掉，應該回傳空 dict。"""
    deeply_nested = b"[" * 4000 + b"]" * 4000
    code, result, stderr = _invoke_read_payload(deeply_nested)
    assert code == 0
    assert result == {}


def test_guard_secrets_survives_hostile_payloads(tmp_path):
    """這是真正保護使用者檔案編輯的那道測試：PreToolUse 上真正掛著的
    guard_secrets 拿到這些惡意 payload 時都不能讓 hook process 以非 0 結束，
    否則使用者的 Write/Edit 會被未攔截的例外中斷。"""
    hostile_payloads = [
        b"",
        b"{}",
        b"not json at all",
        b"\xff\xfe\x00garbage",
        b"42",
        b"[1,2]",
        b"[" * 4000 + b"]" * 4000,
    ]
    for raw in hostile_payloads:
        code, stderr = _invoke_guard_secrets(raw, cwd=tmp_path)
        assert code == 0, f"guard_secrets.py exited {code} for payload {raw!r}: {stderr}"
