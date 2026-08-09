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
