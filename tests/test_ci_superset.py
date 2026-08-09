import sys

from conftest import TEMPLATE

sys.path.insert(0, str(TEMPLATE / "scripts"))
from check_ci_superset import stray_test_commands, uses_shared_entrypoint


def test_ci_runs_the_same_entrypoint_as_local():
    """CI 的測試步驟走的是本機那支同一個入口腳本。"""
    workflow = (TEMPLATE / ".github" / "workflows" / "tests.yml").read_text("utf-8")

    assert uses_shared_entrypoint(workflow)


def test_ci_does_not_run_tests_a_second_way():
    """CI 不會用另一套指令再跑一次測試，否則本機重現不了 CI 的紅。"""
    workflow = (TEMPLATE / ".github" / "workflows" / "tests.yml").read_text("utf-8")

    assert stray_test_commands(workflow) == []


def test_a_workflow_with_its_own_pytest_call_is_rejected():
    """自己另外呼叫 pytest 的 workflow，檢查要抓得出來。"""
    bad = "jobs:\n  t:\n    steps:\n      - run: pytest tests/ -k slow\n"

    assert stray_test_commands(bad) == ["pytest tests/ -k slow"]


def test_entrypoint_mentioned_only_in_a_comment_does_not_count():
    """只在註解裡提到 scripts/run_tests.sh，不代表 workflow 真的有跑它。"""
    workflow = (
        "jobs:\n"
        "  t:\n"
        "    steps:\n"
        "      # this step used to call scripts/run_tests.sh directly\n"
        "      - run: echo hi\n"
    )

    assert uses_shared_entrypoint(workflow) is False


def test_pytest_mentioned_only_in_a_comment_is_not_a_stray_command():
    """pytest 這個字只出現在註解裡，不該被算成另一條測試路徑。"""
    workflow = (
        "jobs:\n"
        "  t:\n"
        "    steps:\n"
        "      - run: scripts/run_tests.sh\n"
        "      # this used to call pytest directly before we switched\n"
    )

    assert stray_test_commands(workflow) == []


def test_pytest_mentioned_only_in_a_step_name_is_still_flagged():
    """pytest 只出現在 step 的 name 欄位（不是 run 指令），目前的實作還是會抓成 stray。

    這是誠實的限制，不是保證:模組只用逐行比對，沒有解析 YAML，所以分不出
    `name:` 欄位跟 `run:` 指令的差別。`name: run pytest twice` 只是敘述文字，
    但程式碼看不出來，於是照樣把它當成一條可疑的測試指令回報。
    """
    workflow = "jobs:\n  t:\n    steps:\n      - name: run pytest twice\n"

    assert stray_test_commands(workflow) == ["- name: run pytest twice"]
