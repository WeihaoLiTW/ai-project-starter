"""禁問清單比對器的測試。

前四個函式依 SDD 計畫 `docs/superpowers/plans/2026-08-09-starter-kit.md`
「B12 模糊需求換來的是業務問題（比對器部分）」那段逐字寫入。第五個函式是
額外補上的守門測試：markdown 表格的儲存格裡，字面上的直線要跳脫成 `\\|`，
但 `\\|` 在正規表示式裡的意思是「字面上的直線字元」，不是「或」。這個測試
確保 forbidden-questions.md 不會踩到這個衝突，也讓下一個人編輯這張表時，
不會不小心把兩種語意搞混。
"""

import re

from checks.question_audit import forbidden_hits, load_rules

RULES = load_rules()


def test_asking_which_database_is_a_forbidden_question():
    """問使用者要用哪個資料庫，判定為禁問。"""
    hits = forbidden_hits("你想用 SQLite 還是 PostgreSQL？", RULES)

    assert [h.category for h in hits] == ["資料庫選型"]


def test_asking_about_a_business_rule_is_not_forbidden():
    """問排班的業務規則，不算禁問。"""
    assert forbidden_hits("員工離職後，他填過的班表要保留還是消失？", RULES) == []


def test_the_word_data_alone_does_not_trigger_a_hit():
    """只是提到「資料」不會被誤判成問資料庫選型。"""
    assert forbidden_hits("這些資料要保留多久？", RULES) == []


def test_every_category_the_spec_requires_is_covered():
    """spec 點名的五個類別，禁問清單一個都不能少。"""
    required = {"資料庫選型", "框架選型", "部署平台", "檔案結構", "演算法選擇"}

    assert required <= {r.category for r in RULES}


def test_load_rules_pattern_is_ready_for_re_search():
    """load_rules() 讀出來的 pattern 要能直接餵給 re.search 用，而不是一個
    去比對字面上直線字元的死路。"""
    db_rule = next(r for r in RULES if r.category == "資料庫選型")

    assert "\\|" not in db_rule.pattern
    for keyword in ("SQLite", "Postgres", "PostgreSQL", "MySQL", "MongoDB"):
        assert re.search(db_rule.pattern, keyword), keyword


def test_describing_a_greedy_coworker_is_not_forbidden():
    """「貪婪」是形容一個人的日常中文形容詞，不是演算法問題。"""
    assert forbidden_hits("這個員工很貪婪，一直要求加薪", RULES) == []


def test_asking_to_split_a_shipment_is_not_forbidden():
    """「要不要拆成」是業務上常見的措辭，不限於檔案結構。"""
    assert forbidden_hits("要不要拆成兩批出貨", RULES) == []


def test_the_word_reaction_does_not_trigger_react_framework_hit():
    """React 沒有加詞界時會誤中 reaction 這個字裡面的子字串。"""
    assert forbidden_hits("看使用者的 reaction 如何", RULES) == []


def test_asking_which_frontend_framework_naming_react_is_still_forbidden():
    """加了詞界之後，真的問到 React 這個框架時，仍然要判定為禁問，
    證明詞界是收緊比對，而不是讓比對失效。"""
    hits = forbidden_hits("前端要用 React 還是 Vue？", RULES)

    assert "框架選型" in [h.category for h in hits]
