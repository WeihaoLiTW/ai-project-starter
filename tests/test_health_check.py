import sys
import types

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


def test_all_nine_probes_are_real_not_placeholders_expected_red_until_task_13():
    """刻意保留的紅燈：在 Task 13 把九個真正的探針全部寫完之前，這個測試都應該是
    失敗的。它檢查的是「沒有任何一項是佔位版本」，不是「湊得出九個東西」——
    不要為了讓它變綠而放寬這個判斷條件，也不要用字串比對報告文字取代它。
    """
    from checks.runner import default_probes

    probes = default_probes()
    placeholders = [p for p in probes if getattr(p, "is_placeholder", False)]

    assert not placeholders, (
        f"還有 {len(placeholders)} 個探針是佔位版本，尚未被 Task 13 的真正探針取代"
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
