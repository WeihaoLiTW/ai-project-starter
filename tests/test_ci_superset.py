import sys

from conftest import TEMPLATE

sys.path.insert(0, str(TEMPLATE / "scripts"))
from check_ci_superset import (
    first_job_text,
    stray_script_commands,
    stray_test_commands,
    uses_shared_entrypoint,
)


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


def test_the_shipped_workflow_calls_the_glossary_and_superset_checks_only_through_run_tests_sh():
    """回歸測試：`check_glossary.py` 跟 `check_ci_superset.py` 曾經是 CI 才有、
    本機 `run_tests.sh` 沒有的兩個額外檢查（Important 8 修的那個問題）。這裡
    釘住修好之後的狀態：CI 的第一個 job（`test`）沒有繞過 `run_tests.sh` 直接
    再呼叫其他 scripts/ 底下的腳本。"""
    workflow = (TEMPLATE / ".github" / "workflows" / "tests.yml").read_text("utf-8")
    local_script = (TEMPLATE / "scripts" / "run_tests.sh").read_text("utf-8")

    assert stray_script_commands(first_job_text(workflow), local_script) == []


def test_a_ci_only_script_call_outside_run_tests_sh_is_flagged():
    """`test` job 裡直接呼叫了一個 `run_tests.sh` 沒有走的腳本——這是 CI 多跑
    一項本機重現不了的檢查，要被抓出來，不能靠只認 pytest 的正規表達式漏掉。"""
    workflow = (
        "jobs:\n"
        "  test:\n"
        "    steps:\n"
        "      - run: sh scripts/run_tests.sh\n"
        "      - run: python3 scripts/check_something_extra.py\n"
        "  deploy-safety:\n"
        "    steps:\n"
        "      - run: python3 scripts/check_deploy.py\n"
    )
    local_script = "#!/bin/sh\npython3 -m pytest tests/\n"

    result = stray_script_commands(first_job_text(workflow), local_script)

    assert result == ["scripts/check_something_extra.py"]


def test_a_script_only_the_deploy_safety_job_needs_is_not_flagged():
    """`deploy-safety` job 需要真的部署密鑰才能跑，本機重現不了本來就是預期
    行為（跟 glossary／superset 那兩個不需要密鑰的檢查不是同一類問題）——
    這個檢查只看第一個 job，不該把 `deploy-safety` 專屬的腳本也算成 stray。"""
    workflow = (
        "jobs:\n"
        "  test:\n"
        "    steps:\n"
        "      - run: sh scripts/run_tests.sh\n"
        "  deploy-safety:\n"
        "    steps:\n"
        "      - run: python3 scripts/check_deploy.py\n"
    )
    local_script = "#!/bin/sh\npython3 -m pytest tests/\n"

    result = stray_script_commands(first_job_text(workflow), local_script)

    assert result == []


def test_a_script_call_also_present_in_run_tests_sh_is_not_flagged():
    """腳本已經在 `run_tests.sh` 裡跑過了，CI 裡另外再呼叫一次同一個腳本
    不算 stray——本機已經涵蓋這個檢查，不會有「本機重現不了 CI 的紅」的問題。"""
    workflow = (
        "jobs:\n"
        "  test:\n"
        "    steps:\n"
        "      - run: sh scripts/run_tests.sh\n"
        "      - run: python3 scripts/check_glossary.py\n"
    )
    local_script = "#!/bin/sh\npython3 -m pytest tests/\npython3 scripts/check_glossary.py\n"

    result = stray_script_commands(first_job_text(workflow), local_script)

    assert result == []


def test_pytest_mentioned_only_in_a_step_name_is_still_flagged():
    """pytest 只出現在 step 的 name 欄位（不是 run 指令），目前的實作還是會抓成 stray。

    這是誠實的限制，不是保證:模組只用逐行比對，沒有解析 YAML，所以分不出
    `name:` 欄位跟 `run:` 指令的差別。`name: run pytest twice` 只是敘述文字，
    但程式碼看不出來，於是照樣把它當成一條可疑的測試指令回報。
    """
    workflow = "jobs:\n  t:\n    steps:\n      - name: run pytest twice\n"

    assert stray_test_commands(workflow) == ["- name: run pytest twice"]
