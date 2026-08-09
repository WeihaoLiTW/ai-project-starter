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
